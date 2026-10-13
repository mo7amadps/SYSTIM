"""
نظام التذاكر — منقول بأقرب شكل ممكن من مشروع Node (ticketHandler.js).
"""

from __future__ import annotations

import io
import time
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from utils.storage import Storage

SECTION = "tickets"
COOLDOWN_SEC = 10 * 60
_closing: set[str] = set()
_cooldowns: dict[str, float] = {}

_EMOJI = {
    "claim": discord.PartialEmoji(name="claim", id=1361433613513658398),
    "unclaim": discord.PartialEmoji(name="unclaim", id=1180554100639801454),
    "rename": discord.PartialEmoji(name="rename", id=1424467612854911127),
    "support": discord.PartialEmoji(name="support", id=1395521401854890004),
    "admin": discord.PartialEmoji(name="admin", id=1438284480153387209),
    "dm": discord.PartialEmoji(name="dm", id=1317304004027486258),
}


def _em(key: str, fallback: str):
    try:
        return _EMOJI[key]
    except Exception:
        return fallback


def _s(settings: dict, *keys, default=None):
    for k in keys:
        if k in settings and settings[k] is not None:
            return settings[k]
    return default


def _cd(user_id: int, button_id: str, channel_id: int) -> str | None:
    key = f"{user_id}-{button_id}-{channel_id}"
    now = time.time()
    last = _cooldowns.get(key)
    if last and now - last < COOLDOWN_SEC:
        remaining = int(COOLDOWN_SEC - (now - last))
        mins, secs = divmod(remaining, 60)
        return f"⏳ انتظر {mins}:{secs:02d} دقيقة قبل الاستخدام مجدداً."
    _cooldowns[key] = now
    return None


class TicketReasonModal(discord.ui.Modal, title="سبب فتح التذكرة"):
    reason = discord.ui.TextInput(label="اكتب السبب", style=discord.TextStyle.paragraph, required=True, max_length=500)

    def __init__(self, cog, ticket_num: int):
        super().__init__()
        self.cog = cog
        self.ticket_num = ticket_num

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.open_ticket(interaction, self.ticket_num, str(self.reason))


class TicketAddUserModal(discord.ui.Modal, title="إضافة شخص للتذكرة"):
    user_id = discord.ui.TextInput(label="ادخل ID المستخدم", required=True, max_length=25)

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        ticket = await self.cog._get_open(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ هذا ليس شانل تذكرة!", ephemeral=True)
            return
        try:
            uid = int(str(self.user_id).strip())
        except ValueError:
            await interaction.response.send_message("❌ ID غير صالح.", ephemeral=True)
            return
        member = interaction.guild.get_member(uid)
        if not member:
            try:
                member = await interaction.guild.fetch_member(uid)
            except discord.HTTPException:
                member = None
        if not member:
            await interaction.response.send_message("❌ المستخدم غير موجود، تأكد من الـ ID.", ephemeral=True)
            return
        await interaction.channel.set_permissions(member, view_channel=True, send_messages=True, read_message_history=True)
        await interaction.response.send_message(f"✅ تم إضافة {member.mention} للتذكرة.")


class TicketRenameModal(discord.ui.Modal, title="تغيير اسم التذكرة"):
    new_name = discord.ui.TextInput(label="اكتب الاسم الجديد", required=True, max_length=90)

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        ticket = await self.cog._get_open(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ هذا ليس شانل تذكرة!", ephemeral=True)
            return
        if not await self.cog._can_staff(interaction, ticket):
            await interaction.response.send_message("❌ بس مستلم التذكرة أو الإداريين يقدرون يغيرون اسم التذكرة!", ephemeral=True)
            return
        raw = str(self.new_name).strip().lower().replace(" ", "-")
        safe = "".join(c for c in raw if c.isalnum() or c in "-_")[:90]
        if not safe:
            await interaction.response.send_message("❌ اسم غير صالح!", ephemeral=True)
            return
        try:
            await interaction.channel.edit(name=safe)
            await interaction.response.send_message(f"✅ تم تغيير اسم التذكرة إلى **{safe}**")
        except discord.HTTPException:
            await interaction.response.send_message("❌ ما قدرت أغيّر الاسم.", ephemeral=True)


class TicketControlView(discord.ui.View):
    def __init__(self, cog, claimed_by=None):
        super().__init__(timeout=None)
        self.cog = cog
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.custom_id == "ticket:claim":
                    child.label = "مستلمة ✅" if claimed_by else "استلام"
                    child.disabled = bool(claimed_by)
                if child.custom_id == "ticket:unclaim":
                    child.disabled = not bool(claimed_by)

    @discord.ui.button(label="إغلاق", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="ticket:close", row=0)
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket = await self.cog._get_open(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ هذا ليس شانل تذكرة!", ephemeral=True)
            return
        settings = await self.cog._type_settings(interaction.guild.id, ticket["ticket_num"])
        member = interaction.user
        has_admin = await self.cog._has_role(member, _s(settings, "admin_id", "admin"))
        has_role = await self.cog._has_role(member, _s(settings, "role_id", "role"))
        is_claimer = ticket.get("claimed_by") == member.id
        is_owner = interaction.guild.owner_id == member.id
        is_towner = member.id == ticket.get("user_id")
        # role و admin يقدرون يسكرون + المستلم + صاحب التذكرة + الأونر
        if not (has_admin or has_role or is_claimer or is_owner or is_towner):
            await interaction.response.send_message("❌ بس الستاف أو صاحب التذكرة يقدر يسكرها!", ephemeral=True)
            return
        tqeem = _s(settings, "tqeem_room_id", "tqeem_room")
        if tqeem:
            await interaction.response.send_message(
                f"<@{ticket['user_id']}>\n⭐ **قيّم تجربتك قبل إغلاق التذكرة**\n(أو اضغط إغلاق بدون تقييم)",
                view=TicketRatingView(self.cog, closer_id=interaction.user.id),
            )
            return
        await interaction.response.send_message("🔒 جاري إغلاق التذكرة...")
        await self.cog.close_ticket(interaction.guild, interaction.channel, interaction.user, ticket, 0)

    @discord.ui.button(label="استلام", emoji="✅", style=discord.ButtonStyle.success, custom_id="ticket:claim", row=0)
    async def claim_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket = await self.cog._get_open(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ هذا ليس شانل تذكرة!", ephemeral=True)
            return
        if not await self.cog._is_support(interaction, ticket):
            await interaction.response.send_message("❌ ما عندك صلاحية الاستلام.", ephemeral=True)
            return
        if ticket.get("claimed_by"):
            await interaction.response.send_message(f"⚠️ مستلمة مسبقاً من <@{ticket['claimed_by']}>", ephemeral=True)
            return
        ticket["claimed_by"] = interaction.user.id
        await self.cog._save_open(interaction.guild.id, interaction.channel.id, ticket)
        await interaction.channel.set_permissions(
            interaction.user, view_channel=True, send_messages=True, read_message_history=True, manage_messages=True
        )
        try:
            await interaction.message.edit(view=TicketControlView(self.cog, claimed_by=interaction.user.id))
        except discord.HTTPException:
            pass
        await interaction.response.send_message(f"✅ استلم التذكرة {interaction.user.mention}")

    @discord.ui.button(label="ترك التذكرة", emoji="🚪", style=discord.ButtonStyle.secondary, custom_id="ticket:unclaim", row=0)
    async def unclaim_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket = await self.cog._get_open(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ هذا ليس شانل تذكرة!", ephemeral=True)
            return
        if ticket.get("claimed_by") != interaction.user.id and not await self.cog._can_staff(interaction, ticket):
            await interaction.response.send_message("❌ بس المستلم يقدر يتركها.", ephemeral=True)
            return
        prev = ticket.get("claimed_by")
        ticket["claimed_by"] = None
        await self.cog._save_open(interaction.guild.id, interaction.channel.id, ticket)
        # لو المستلم السابق role عادي (مو admin) يرجع ما يقدر يكتب
        if prev:
            settings = await self.cog._type_settings(interaction.guild.id, ticket["ticket_num"])
            prev_member = interaction.guild.get_member(prev)
            if prev_member:
                is_adm = await self.cog._has_role(prev_member, _s(settings, "admin_id", "admin"))
                if not is_adm and not prev_member.guild_permissions.administrator:
                    try:
                        await interaction.channel.set_permissions(
                            prev_member,
                            view_channel=True,
                            send_messages=False,
                            read_message_history=True,
                        )
                    except discord.HTTPException:
                        pass
        try:
            await interaction.message.edit(view=TicketControlView(self.cog, claimed_by=None))
        except discord.HTTPException:
            pass
        await interaction.response.send_message("🚪 تم ترك التذكرة.")

    @discord.ui.button(label="إضافة شخص", emoji="➕", style=discord.ButtonStyle.primary, custom_id="ticket:add", row=0)
    async def add_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket = await self.cog._get_open(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ هذا ليس شانل تذكرة!", ephemeral=True)
            return
        if not await self.cog._can_staff(interaction, ticket):
            await interaction.response.send_message("❌ ما عندك صلاحية.", ephemeral=True)
            return
        await interaction.response.send_modal(TicketAddUserModal(self.cog))

    @discord.ui.button(label="تغيير الاسم", emoji="✏️", style=discord.ButtonStyle.secondary, custom_id="ticket:rename", row=0)
    async def rename_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket = await self.cog._get_open(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ هذا ليس شانل تذكرة!", ephemeral=True)
            return
        await interaction.response.send_modal(TicketRenameModal(self.cog))

    @discord.ui.button(label="استدعاء سبورت", emoji="🆘", style=discord.ButtonStyle.secondary, custom_id="ticket:call_support", row=1)
    async def call_support(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket = await self.cog._get_open(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ هذا ليس شانل تذكرة!", ephemeral=True)
            return
        msg = _cd(interaction.user.id, "call_support", interaction.channel.id)
        if msg:
            await interaction.response.send_message(msg, ephemeral=True)
            return
        settings = await self.cog._type_settings(interaction.guild.id, ticket["ticket_num"])
        mention = f"<@&{role_id}>" if role_id else "@here"
        await interaction.response.send_message(f"📢 {mention} مطلوبون في هذه التذكرة!")

    @discord.ui.button(label="استدعاء ادمن", emoji="👤", style=discord.ButtonStyle.secondary, custom_id="ticket:call_admin", row=1)
    async def call_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket = await self.cog._get_open(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ هذا ليس شانل تذكرة!", ephemeral=True)
            return
        if not await self.cog._can_staff(interaction, ticket):
            await interaction.response.send_message("❌ بس مستلم التذكرة أو الإداريين يقدرون يستخدمون هذا الزر!", ephemeral=True)
            return
        msg = _cd(interaction.user.id, "call_admin", interaction.channel.id)
        if msg:
            await interaction.response.send_message(msg, ephemeral=True)
            return
        settings = await self.cog._type_settings(interaction.guild.id, ticket["ticket_num"])
        admin_id = _s(settings, "admin_id", "admin")
        mention = f"<@&{admin_id}>" if admin_id else "@here"
        await interaction.response.send_message(f"👤 {mention} مطلوبون في هذه التذكرة!")

    @discord.ui.button(label="استدعاء العضو بالخاص", emoji="📩", style=discord.ButtonStyle.secondary, custom_id="ticket:dm_user", row=1)
    async def dm_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket = await self.cog._get_open(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ هذا ليس شانل تذكرة!", ephemeral=True)
            return
        if not await self.cog._can_staff(interaction, ticket):
            await interaction.response.send_message("❌ بس مستلم التذكرة أو الإداريين يقدرون يستخدمون هذا الزر!", ephemeral=True)
            return
        msg = _cd(interaction.user.id, "dm_user", interaction.channel.id)
        if msg:
            await interaction.response.send_message(msg, ephemeral=True)
            return
        try:
            user = await self.cog.bot.fetch_user(ticket["user_id"])
            embed = discord.Embed(
                description=f"📩 **يرجى التوجه للتذكرة التي قمت بفتحها**\n\n🔗 {interaction.channel.mention}",
                color=0x5865F2,
            )
            await user.send(embed=embed)
            await interaction.response.send_message("✅ تم إرسال رسالة للعضو بالخاص.")
        except discord.HTTPException:
            await interaction.response.send_message("❌ ما قدرت أرسل للعضو (الخاص مقفل غالباً).", ephemeral=True)


class TicketRatingView(discord.ui.View):
    def __init__(self, cog, closer_id: int | None = None):
        super().__init__(timeout=300)
        self.cog = cog
        self.closer_id = closer_id
        for i in range(1, 6):
            self.add_item(self._star(i))
        skip = discord.ui.Button(
            label="إغلاق بدون تقييم",
            style=discord.ButtonStyle.danger,
            emoji="🔒",
            custom_id="ticket:rate:skip",
            row=1,
        )
        skip.callback = self._skip_cb
        self.add_item(skip)

    def _star(self, stars: int) -> discord.ui.Button:
        btn = discord.ui.Button(label="⭐" * stars, style=discord.ButtonStyle.secondary, custom_id=f"ticket:rate:{stars}")

        async def callback(interaction: discord.Interaction):
            ticket = await self.cog._get_open(interaction.channel.id)
            if not ticket:
                await interaction.response.send_message("❌ خطأ في التذكرة!", ephemeral=True)
                return
            if interaction.user.id != ticket.get("user_id"):
                await interaction.response.send_message("❌ بس صاحب التذكرة يقدر يقيّم!", ephemeral=True)
                return
            await interaction.response.edit_message(
                content=f"✅ شكراً على تقييمك! **{'⭐' * stars}**\nجاري إغلاق التذكرة...",
                view=None,
            )
            closer = interaction.guild.get_member(self.closer_id) if self.closer_id else interaction.user
            await self.cog.close_ticket(interaction.guild, interaction.channel, closer or interaction.user, ticket, stars)

        btn.callback = callback
        return btn

    async def _skip_cb(self, interaction: discord.Interaction):
        ticket = await self.cog._get_open(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ خطأ في التذكرة!", ephemeral=True)
            return
        # صاحب التذكرة أو الستاف يقدرون يسكرون بدون تقييم
        is_owner = interaction.user.id == ticket.get("user_id")
        can_staff = await self.cog._can_staff(interaction, ticket)
        if not (is_owner or can_staff or interaction.user.id == interaction.guild.owner_id):
            await interaction.response.send_message("❌ ما عندك صلاحية الإغلاق بدون تقييم.", ephemeral=True)
            return
        await interaction.response.edit_message(content="🔒 جاري إغلاق التذكرة بدون تقييم...", view=None)
        closer = interaction.guild.get_member(self.closer_id) if self.closer_id else interaction.user
        await self.cog.close_ticket(interaction.guild, interaction.channel, closer or interaction.user, ticket, 0)




# ═══════════════════════════════════════════════════════════
# بانل التذاكر — نفس تدفق بوت التذاكر المرجعي 100%
# Modal → صورة مصغّرة → روم → منيو/أزرار → اختيار أرقام
# → لون + إيموجي + اسم لكل تذكرة → إرسال
# ═══════════════════════════════════════════════════════════

_panel_sessions: dict[int, dict] = {}  # user_id → session data

_BTN_STYLE = {
    "Primary": discord.ButtonStyle.primary,
    "Secondary": discord.ButtonStyle.secondary,
    "Success": discord.ButtonStyle.success,
    "Danger": discord.ButtonStyle.danger,
}


class TicketPanelSelect(discord.ui.Select):
    """القائمة الدائمة على رسالة البانل (منيو)."""

    def __init__(self, cog, options):
        # خيار Refresh مثل البوت المرجعي
        opts = list(options[:24])
        opts.append(discord.SelectOption(label="Refresh", value="panel_refresh", emoji="🔄"))
        super().__init__(
            placeholder="بانل التذكرة",
            options=opts,
            custom_id="ticket:panel_select",
            min_values=1,
            max_values=1,
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "panel_refresh":
            await interaction.response.send_message("🔄 البانل شغال! اختر نوع التذكرة من المنيو.", ephemeral=True)
            return
        ticket_num = int(self.values[0])
        settings = await self.cog._type_settings(interaction.guild.id, ticket_num)
        if not settings:
            await interaction.response.send_message("❌ هذا النوع مش معدّ. استخدم `/ticket-setup`.", ephemeral=True)
            return
        if _s(settings, "reason") == "yes":
            await interaction.response.send_modal(TicketReasonModal(self.cog, ticket_num))
            return
        await self.cog.open_ticket(interaction, ticket_num, None)


class TicketPanelView(discord.ui.View):
    def __init__(self, cog, options=None):
        super().__init__(timeout=None)
        if options:
            self.add_item(TicketPanelSelect(cog, options))


class TicketPanelButtonsView(discord.ui.View):
    """بانل بأزرار + Refresh — نفس شكل البوت المرجعي."""

    def __init__(self, cog, button_defs: list[dict] | None = None):
        super().__init__(timeout=None)
        self.cog = cog
        defs = button_defs or []
        for d in defs[:20]:
            style = _BTN_STYLE.get(d.get("color") or "Primary", discord.ButtonStyle.primary)
            kwargs = {
                "label": (d.get("label") or f"تذكرة {d.get('num')}")[:80],
                "style": style,
                "custom_id": f"ticket:open_btn:{d['num']}",
            }
            if d.get("emoji"):
                kwargs["emoji"] = d["emoji"]
            btn = discord.ui.Button(**kwargs)
            btn.callback = self._make_open_cb(int(d["num"]))
            self.add_item(btn)
        refresh = discord.ui.Button(
            label="Refresh",
            style=discord.ButtonStyle.secondary,
            emoji="🔄",
            custom_id="ticket:panel_refresh",
        )
        refresh.callback = self._refresh_cb
        self.add_item(refresh)

    def _make_open_cb(self, ticket_num: int):
        async def cb(interaction: discord.Interaction):
            settings = await self.cog._type_settings(interaction.guild.id, ticket_num)
            if not settings:
                await interaction.response.send_message("❌ هذا النوع مش معدّ.", ephemeral=True)
                return
            if _s(settings, "reason") == "yes":
                await interaction.response.send_modal(TicketReasonModal(self.cog, ticket_num))
                return
            await self.cog.open_ticket(interaction, ticket_num, None)
        return cb

    async def _refresh_cb(self, interaction: discord.Interaction):
        await interaction.response.send_message("🔄 البانل شغال! اختر نوع التذكرة من فوق.", ephemeral=True)


# ── خطوات إنشاء البانل (جلسة مؤقتة) ──

class PanelEmbedModal(discord.ui.Modal, title="انشاء معلومات الايمبد 🎫"):
    embed_msg = discord.ui.TextInput(
        label="رسالة الايمبد (اختياري)",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=4000,
    )
    embed_title = discord.ui.TextInput(
        label="عنوان الايمبد (اختياري)",
        style=discord.TextStyle.short,
        required=False,
        max_length=256,
    )
    embed_image = discord.ui.TextInput(
        label="رابط صورة الايمبد (اختياري)",
        style=discord.TextStyle.short,
        required=False,
        max_length=300,
    )

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        _panel_sessions[interaction.user.id] = {
            "embedMsg": str(self.embed_msg).strip() or None,
            "embedTitle": str(self.embed_title).strip() or None,
            "embedImage": str(self.embed_image).strip() or None,
            "cog": self.cog,
        }
        view = discord.ui.View(timeout=300)
        sel = discord.ui.Select(
            placeholder="اختر صورة الايمبد على اليمين",
            options=[
                discord.SelectOption(label="صورتك", value="user", emoji="👤"),
                discord.SelectOption(label="صورة السيرفر", value="guild", emoji="🏠"),
                discord.SelectOption(label="صورة البوت", value="bot", emoji="🤖"),
                discord.SelectOption(label="لاشي", value="none", emoji="🚫"),
            ],
            custom_id="panel_thumbnail_type",
        )

        async def on_thumb(inter: discord.Interaction):
            if inter.user.id != interaction.user.id:
                await inter.response.send_message("❌ هاد الإعداد مو إلك.", ephemeral=True)
                return
            sess = _panel_sessions.get(inter.user.id) or {}
            sess["thumbnailType"] = inter.data["values"][0]
            _panel_sessions[inter.user.id] = sess
            ch_view = discord.ui.View(timeout=300)
            ch_sel = discord.ui.ChannelSelect(
                placeholder="اختر روم لإرسال البانل (تقدر تكتب وتدور باسمه)",
                channel_types=[discord.ChannelType.text],
                custom_id="panel_channel_select",
            )

            async def on_channel(inter2: discord.Interaction):
                if inter2.user.id != interaction.user.id:
                    await inter2.response.send_message("❌ هاد الإعداد مو إلك.", ephemeral=True)
                    return
                sess2 = _panel_sessions.get(inter2.user.id) or {}
                vals = inter2.data.get("values") or []
                sess2["channelId"] = int(vals[0]) if vals else None
                _panel_sessions[inter2.user.id] = sess2
                type_view = discord.ui.View(timeout=300)
                type_sel = discord.ui.Select(
                    placeholder="اختر نوع التذاكر",
                    options=[
                        discord.SelectOption(label="منيو / Menu", value="menu", emoji="📋"),
                        discord.SelectOption(label="ازرار / Buttons", value="buttons", emoji="🔘"),
                    ],
                    custom_id="panel_ticket_type",
                )

                async def on_type(inter3: discord.Interaction):
                    if inter3.user.id != interaction.user.id:
                        await inter3.response.send_message("❌ هاد الإعداد مو إلك.", ephemeral=True)
                        return
                    sess3 = _panel_sessions.get(inter3.user.id) or {}
                    sess3["panelType"] = inter3.data["values"][0]
                    sess3["selectedTickets"] = []
                    sess3["currentTicketIndex"] = 0
                    sess3["ticketConfigs"] = {}
                    _panel_sessions[inter3.user.id] = sess3

                    section = await self.cog._section(inter3.guild.id)
                    types = section.get("types", {}) or {}
                    available = []
                    # مثل المرجعي: أرقام 1–15 اللي معدّة، أو 1–5 لو فاضي
                    nums = sorted((int(k) for k in types.keys()), key=int) if types else list(range(1, 6))
                    if not nums:
                        nums = list(range(1, 6))
                    for i in nums[:25]:
                        cfg = types.get(str(i), {}) or {}
                        label = f"التذكرة رقم {i}"
                        if cfg.get("name"):
                            label = f"التذكرة رقم {i} - {cfg['name']}"
                        available.append(discord.SelectOption(label=label[:100], value=str(i), emoji="🎫"))

                    if not available:
                        await inter3.response.edit_message(content="❌ ما في أنواع تذاكر. استخدم `/ticket-setup`.", view=None)
                        return

                    pick_view = discord.ui.View(timeout=300)
                    pick_sel = discord.ui.Select(
                        placeholder="اختر التذاكر اللي تبيها في البانل",
                        options=available,
                        min_values=1,
                        max_values=len(available),
                        custom_id="panel_tickets_select",
                    )

                    async def on_pick(inter4: discord.Interaction):
                        if inter4.user.id != interaction.user.id:
                            await inter4.response.send_message("❌ هاد الإعداد مو إلك.", ephemeral=True)
                            return
                        sess4 = _panel_sessions.get(inter4.user.id) or {}
                        sess4["selectedTickets"] = [int(v) for v in inter4.data.get("values", [])]
                        sess4["ticketConfigs"] = {}
                        sess4["currentTicketIndex"] = 0
                        _panel_sessions[inter4.user.id] = sess4
                        await _ask_ticket_color(inter4, sess4, follow_up=False)

                    pick_sel.callback = on_pick
                    pick_view.add_item(pick_sel)
                    await inter3.response.edit_message(content="**اختر التذاكر اللي تبيها في البانل**", view=pick_view)

                type_sel.callback = on_type
                type_view.add_item(type_sel)
                await inter2.response.edit_message(content="**اختر نوع التذاكر**", view=type_view)

            ch_sel.callback = on_channel
            ch_view.add_item(ch_sel)
            await inter.response.edit_message(content="**اختر روم لإرسال البانل**", view=ch_view)

        sel.callback = on_thumb
        view.add_item(sel)
        await interaction.response.send_message("**صورة الايمبد على اليمين**", view=view, ephemeral=True)


async def _ask_ticket_color(interaction: discord.Interaction, session: dict, follow_up: bool = False):
    idx = session.get("currentTicketIndex", 0)
    selected = session.get("selectedTickets") or []
    if idx >= len(selected):
        await _send_panel(interaction, session)
        return
    ticket_num = selected[idx]
    view = discord.ui.View(timeout=300)
    sel = discord.ui.Select(
        placeholder=f"اختر لون الزر للتذكرة رقم {ticket_num}",
        options=[
            discord.SelectOption(label="أزرق", value="Primary", emoji="🔵"),
            discord.SelectOption(label="رصاصي", value="Secondary", emoji="⚪"),
            discord.SelectOption(label="أخضر", value="Success", emoji="🟢"),
            discord.SelectOption(label="أحمر", value="Danger", emoji="🔴"),
        ],
        custom_id=f"panel_color_{ticket_num}",
    )

    async def on_color(inter: discord.Interaction):
        if inter.user.id not in _panel_sessions:
            await inter.response.send_message("❌ انتهت الجلسة. أعد `/ticket-panel`.", ephemeral=True)
            return
        sess = _panel_sessions[inter.user.id]
        tnum = sess["selectedTickets"][sess["currentTicketIndex"]]
        sess.setdefault("ticketConfigs", {})[tnum] = sess.get("ticketConfigs", {}).get(tnum) or {}
        sess["ticketConfigs"][tnum]["color"] = inter.data["values"][0]
        _panel_sessions[inter.user.id] = sess
        # رسالة مخفية: اكتب الإيموجي في الشات
        await inter.response.edit_message(
            content=(
                f"**التذكرة رقم {tnum}**\n"
                f"📩 اكتب **الإيموجي** في الشات الآن (أو اكتب `لا` بدون إيموجي)\n"
                f"_رسالتك رح تنحذف تلقائياً_"
            ),
            view=None,
        )
        await _collect_emoji_then_name(inter, sess, tnum)

    sel.callback = on_color
    view.add_item(sel)
    content = f"**اختر لون الزر للتذكرة رقم {ticket_num}**"
    if follow_up:
        await interaction.followup.send(content, view=view, ephemeral=True)
    else:
        await interaction.response.edit_message(content=content, view=view)


async def _collect_emoji_then_name(interaction: discord.Interaction, session: dict, ticket_num: int):
    """يجمع الإيموجي ثم الاسم برسائل من الشات (مثل البوت المرجعي)."""
    channel = interaction.channel
    user_id = interaction.user.id

    def check(m: discord.Message) -> bool:
        return m.author.id == user_id and m.channel.id == channel.id

    # 1) الإيموجي
    try:
        collected = await interaction.client.wait_for("message", check=check, timeout=90)
    except Exception:
        await interaction.followup.send("⌛ انتهى الوقت — أعد `/ticket-panel`.", ephemeral=True)
        _panel_sessions.pop(user_id, None)
        return

    emoji_raw = (collected.content or "").strip()
    try:
        await collected.delete()
    except Exception:
        pass

    emoji = None if (not emoji_raw or emoji_raw.lower() == "لا") else emoji_raw
    cfg = session.setdefault("ticketConfigs", {}).setdefault(ticket_num, {})
    cfg["emoji"] = emoji
    _panel_sessions[user_id] = session

    # 2) اسم التذكرة — رسالة مخفية
    await interaction.followup.send(
        f"**التذكرة رقم {ticket_num}**\n"
        f"✍️ اكتب الآن **اسم التذكرة** (مثل: دعم فني)\n"
        f"_رسالتك رح تنحذف تلقائياً_",
        ephemeral=True,
    )

    try:
        collected2 = await interaction.client.wait_for("message", check=check, timeout=90)
    except Exception:
        await interaction.followup.send("⌛ انتهى الوقت — أعد `/ticket-panel`.", ephemeral=True)
        _panel_sessions.pop(user_id, None)
        return

    label = (collected2.content or "").strip() or f"تذكرة {ticket_num}"
    try:
        await collected2.delete()
    except Exception:
        pass

    cfg["label"] = label[:80]
    session["currentTicketIndex"] = session.get("currentTicketIndex", 0) + 1
    _panel_sessions[user_id] = session

    selected = session.get("selectedTickets") or []
    if session["currentTicketIndex"] < len(selected):
        nxt = selected[session["currentTicketIndex"]]
        await interaction.followup.send(
            f"✅ تم ضبط التذكرة رقم **{ticket_num}**\n"
            f"➡️ ننتقل للتذكرة رقم **{nxt}**...",
            ephemeral=True,
        )
        await _ask_ticket_color(interaction, session, follow_up=True)
    else:
        await _send_panel(interaction, session)


async def _send_panel(interaction: discord.Interaction, session: dict):
    cog = session.get("cog")
    if not cog:
        await interaction.followup.send("❌ خطأ داخلي.", ephemeral=True)
        return
    channel = interaction.guild.get_channel(session.get("channelId"))
    if not channel:
        await interaction.followup.send("❌ الروم غير موجود", ephemeral=True)
        return

    thumb = None
    tt = session.get("thumbnailType")
    if tt == "user":
        thumb = interaction.user.display_avatar.url
    elif tt == "guild" and interaction.guild.icon:
        thumb = interaction.guild.icon.url
    elif tt == "bot" and interaction.client.user:
        thumb = interaction.client.user.display_avatar.url

    embed = discord.Embed(
        title=session.get("embedTitle") or "SERVER",
        description=session.get("embedMsg") or "اضغط على الزر بالاسفل واملأ المعلومات لارسال بانل التذكرة",
        color=0x5865F2,
        timestamp=datetime.now(timezone.utc),
    )
    if thumb:
        embed.set_thumbnail(url=thumb)
    if session.get("embedImage"):
        try:
            embed.set_image(url=session["embedImage"])
        except Exception:
            pass

    selected = session.get("selectedTickets") or []
    configs = session.get("ticketConfigs") or {}

    if session.get("panelType") == "buttons":
        button_defs = []
        for num in selected:
            cfg = configs.get(num) or {}
            button_defs.append({
                "num": num,
                "label": cfg.get("label") or f"تذكرة {num}",
                "emoji": cfg.get("emoji"),
                "color": cfg.get("color") or "Primary",
            })
        view = TicketPanelButtonsView(cog, button_defs)
    else:
        options = []
        for num in selected:
            cfg = configs.get(num) or {}
            kwargs = {
                "label": (cfg.get("label") or f"تذكرة {num}")[:100],
                "value": str(num),
            }
            if cfg.get("emoji"):
                try:
                    kwargs["emoji"] = cfg["emoji"]
                except Exception:
                    pass
            options.append(discord.SelectOption(**kwargs))
        view = TicketPanelView(cog, options)

    msg = await channel.send(embed=embed, view=view)
    # تسجيل البانل
    section = await cog._section(interaction.guild.id)
    panels = dict(section.get("panels", {}))
    panels[str(msg.id)] = {
        "channel_id": channel.id,
        "types": [str(n) for n in selected],
        "style": session.get("panelType"),
        "button_defs": [
            {
                "num": n,
                "label": (configs.get(n) or {}).get("label"),
                "emoji": (configs.get(n) or {}).get("emoji"),
                "color": (configs.get(n) or {}).get("color"),
            }
            for n in selected
        ] if session.get("panelType") == "buttons" else None,
    }
    await Storage.update_guild(interaction.guild.id, SECTION, {"panels": panels})
    _panel_sessions.pop(interaction.user.id, None)
    await interaction.followup.send(
        f"✅ تم إرسال البانل إلى {channel.mention}\n\n🙏 **شكراً لك!** اكتمل إعداد البانل بنجاح.",
        ephemeral=True,
    )


class TicketSystem(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(TicketControlView(self, claimed_by=None))
        # بانل المنيو — custom_id ثابت يعمل لكل الرسائل
        self.bot.add_view(TicketPanelView(self, [
            discord.SelectOption(label="placeholder", value="0", emoji="🎫")
        ]))
        self.bot.add_view(TicketPanelButtonsView(self, []))
        # استعادة بانلات الأزرار المحفوظة بعد إعادة التشغيل
        try:
            data = await Storage.get_all() if hasattr(Storage, "get_all") else None
        except Exception:
            data = None
        if not data:
            try:
                # نمر على السيرفرات المتصلة بعد ready — نسجّل من التخزين عند أول استخدام
                pass
            except Exception:
                pass
        # مستمع عام لأزرار البانل بعد الريستارت
        if not getattr(self.bot, "_ticket_panel_hook", False):
            self.bot._ticket_panel_hook = True

            @self.bot.listen("on_interaction")
            async def _panel_btn_fallback(interaction: discord.Interaction):
                if interaction.type != discord.InteractionType.component:
                    return
                cid = (interaction.data or {}).get("custom_id") or ""
                if not cid.startswith("ticket:open_btn:"):
                    return
                if interaction.response.is_done():
                    return
                try:
                    ticket_num = int(cid.split(":")[-1])
                except ValueError:
                    return
                # إذا view الأصلي ما اشتغل (بعد restart) نعالج هنا
                settings = await self._type_settings(interaction.guild.id, ticket_num)
                if not settings:
                    await interaction.response.send_message("❌ هذا النوع مش معدّ.", ephemeral=True)
                    return
                if _s(settings, "reason") == "yes":
                    await interaction.response.send_modal(TicketReasonModal(self, ticket_num))
                    return
                await self.open_ticket(interaction, ticket_num, None)

    async def _section(self, guild_id: int) -> dict:
        conf = await Storage.get_guild(guild_id)
        return conf.get(SECTION, {})

    async def _type_settings(self, guild_id: int, ticket_num: int) -> dict:
        section = await self._section(guild_id)
        return dict(section.get("types", {}).get(str(ticket_num), {}) or {})

    async def _get_open(self, channel_id: int):
        channel = self.bot.get_channel(channel_id)
        if not channel or not getattr(channel, "guild", None):
            return None
        section = await self._section(channel.guild.id)
        return section.get("open", {}).get(str(channel_id))

    async def _save_open(self, guild_id: int, channel_id: int, ticket):
        section = await self._section(guild_id)
        open_map = dict(section.get("open", {}))
        key = str(channel_id)
        if ticket is None:
            open_map.pop(key, None)
        else:
            open_map[key] = ticket
        await Storage.update_guild(guild_id, SECTION, {"open": open_map})

    async def _has_role(self, member, role_id) -> bool:
        if not role_id or not isinstance(member, discord.Member):
            return False
        try:
            rid = int(role_id)
        except (TypeError, ValueError):
            return False
        return any(r.id == rid for r in member.roles)

    async def _is_support(self, interaction, ticket) -> bool:
        member = interaction.user
        if not isinstance(member, discord.Member):
            return False
        if member.guild_permissions.administrator or member.id == interaction.guild.owner_id:
            return True
        settings = await self._type_settings(interaction.guild.id, ticket["ticket_num"])
        for key in ("admin_id", "admin", "role_id", "role"):
            if await self._has_role(member, _s(settings, key)):
                return True
        return False


    async def _can_close(self, member, guild, ticket) -> bool:
        """role أو admin أو المستلم أو صاحب التذكرة أو الأونر."""
        if not isinstance(member, discord.Member):
            return False
        if member.guild_permissions.administrator or member.id == guild.owner_id:
            return True
        if member.id == ticket.get("user_id") or member.id == ticket.get("claimed_by"):
            return True
        settings = await self._type_settings(guild.id, ticket["ticket_num"])
        if await self._has_role(member, _s(settings, "admin_id", "admin")):
            return True
        if await self._has_role(member, _s(settings, "role_id", "role")):
            return True
        return False

    async def _can_staff(self, interaction, ticket) -> bool:
        member = interaction.user
        if not isinstance(member, discord.Member):
            return False
        if member.guild_permissions.administrator or member.id == interaction.guild.owner_id:
            return True
        if ticket.get("claimed_by") == member.id:
            return True
        settings = await self._type_settings(interaction.guild.id, ticket["ticket_num"])
        return await self._has_role(member, _s(settings, "admin_id", "admin"))

    async def _transcript(self, channel: discord.TextChannel) -> io.BytesIO | None:
        try:
            messages = [m async for m in channel.history(limit=None, oldest_first=True)]
            lines = [
                "═══════════════════════════════════════",
                f"📋 سجل التذكرة: #{channel.name}",
                f"📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "═══════════════════════════════════════",
                "",
            ]
            for msg in messages:
                lines.append(f"[{msg.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {msg.author}:")
                lines.append(msg.content or "[لا يوجد نص]")
                for att in msg.attachments:
                    lines.append(f"  📎 مرفق: {att.url}")
                lines.append("")
            lines.append("═══════════════════════════════════════")
            lines.append(f"إجمالي الرسائل: {len(messages)}")
            return io.BytesIO(chr(10).join(lines).encode("utf-8"))
        except Exception as e:
            print("Transcript error:", e)
            return None

    async def open_ticket(self, interaction: discord.Interaction, ticket_num: int, reason: str | None):
        settings = await self._type_settings(interaction.guild.id, ticket_num)
        if not settings:
            await interaction.response.send_message("❌ نوع التذكرة غير معدّ.", ephemeral=True)
            return
        section = await self._section(interaction.guild.id)
        open_map = section.get("open", {}) or {}
        user_open = [t for t in open_map.values() if t and t.get("user_id") == interaction.user.id]
        # نفس نوع التذكرة مفتوح مسبقاً
        for t in user_open:
            if t.get("ticket_num") == ticket_num:
                await interaction.response.send_message(
                    f"❌ لديك تذكرة من هذا النوع مفتوحة بالفعل.",
                    ephemeral=True,
                )
                return
        # حد أقصى لعدد التذاكر المفتوحة لكل عضو
        max_open = 4
        if len(user_open) >= max_open:
            await interaction.response.send_message(
                f"❌ وصلت للحد الأقصى من التذاكر المفتوحة (**{max_open}**). سكّر واحدة قبل ما تفتح جديدة.",
                ephemeral=True,
            )
            return

        category_id = _s(settings, "category_id", "category")
        category = interaction.guild.get_channel(int(category_id)) if category_id else None
        uname = interaction.user.name.replace(" ", "-")[:20]
        base = _s(settings, "name") or "ticket"
        channel_name = f"{base}-{uname}"
        if _s(settings, "username_number") == "yes":
            channel_name = f"{base}-{uname}-{interaction.guild.member_count}"

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, read_message_history=True),
        }
        role_id = _s(settings, "role_id", "role")
        if role_id:
            role = interaction.guild.get_role(int(role_id))
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=False, read_message_history=True)
        admin_id = _s(settings, "admin_id", "admin")
        if admin_id:
            admin = interaction.guild.get_role(int(admin_id))
            if admin:
                overwrites[admin] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_messages=True)
        if _s(settings, "ownership") == "yes" and interaction.guild.owner:
            overwrites[interaction.guild.owner] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        try:
            channel = await interaction.guild.create_text_channel(
                name=channel_name[:100],
                category=category if isinstance(category, discord.CategoryChannel) else None,
                overwrites=overwrites,
                reason=f"تذكرة بواسطة {interaction.user}",
            )
        except (discord.Forbidden, discord.HTTPException) as e:
            await interaction.response.send_message(f"❌ فشل إنشاء التذكرة: {e}", ephemeral=True)
            return

        ticket = {
            "user_id": interaction.user.id,
            "ticket_num": ticket_num,
            "claimed_by": None,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "reason": reason,
            "guild_id": interaction.guild.id,
        }
        await self._save_open(interaction.guild.id, channel.id, ticket)

        welcome = _s(settings, "welcome_msg") or f"مرحباً {interaction.user.mention}، شكراً لفتح التذكرة. يرجى انتظار الاداريين!"
        desc = welcome + (f"\n\n📝 **السبب:** {reason}" if reason else "")
        embed = discord.Embed(title="Ticket Opened", description=desc, color=0x5865F2, timestamp=datetime.now(timezone.utc))
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        if interaction.guild.icon:
            embed.set_footer(text=f"{interaction.guild.name} | Tickets", icon_url=interaction.guild.icon.url)
        else:
            embed.set_footer(text=f"{interaction.guild.name} | Tickets")
        if _s(settings, "welcome_image"):
            embed.set_image(url=str(_s(settings, "welcome_image")))

        content_parts = [interaction.user.mention]
        if _s(settings, "mentions"):
            content_parts.append(str(_s(settings, "mentions")))
        if _s(settings, "ownership") == "yes" and interaction.guild.owner:
            content_parts.append(interaction.guild.owner.mention)

        await channel.send(content=" ".join(content_parts), embed=embed, view=TicketControlView(self, claimed_by=None))
        if _s(settings, "line"):
            await channel.send(content=str(_s(settings, "line")))

        log_id = _s(settings, "log_channel_id", "ticket_logs")
        if log_id:
            log_ch = interaction.guild.get_channel(int(log_id))
            if log_ch:
                type_name = _s(settings, "name") or f"ticket {ticket_num}"
                log_desc = f"**المستخدم:** {interaction.user}\n**التذكرة:** {channel.mention}\n**النوع:** {type_name}"
                if reason:
                    log_desc += f"\n**السبب:** {reason}"
                try:
                    await log_ch.send(embed=discord.Embed(title="🎫 تذكرة جديدة", description=log_desc, color=0x57F287, timestamp=datetime.now(timezone.utc)))
                except discord.HTTPException:
                    pass

        if interaction.response.is_done():
            await interaction.followup.send(f"✅ تم فتح تذكرتك: {channel.mention}", ephemeral=True)
        else:
            await interaction.response.send_message(f"✅ تم فتح تذكرتك: {channel.mention}", ephemeral=True)

    async def close_ticket(self, guild, channel, closer, ticket, stars: int):
        key = f"{guild.id}:{channel.id}"
        if key in _closing:
            return
        _closing.add(key)
        try:
            await self._close_internal(guild, channel, closer, ticket, stars)
        finally:
            _closing.discard(key)

    async def _close_internal(self, guild, channel, closer, ticket, stars: int):
        settings = await self._type_settings(guild.id, ticket["ticket_num"])
        await self._save_open(guild.id, channel.id, None)

        tqeem_id = _s(settings, "tqeem_room_id", "tqeem_room")
        if tqeem_id and stars:
            tqeem_ch = guild.get_channel(int(tqeem_id))
            if tqeem_ch:
                ticket_user = claimed_user = None
                try:
                    ticket_user = await self.bot.fetch_user(ticket["user_id"])
                except discord.HTTPException:
                    pass
                if ticket.get("claimed_by"):
                    try:
                        claimed_user = await self.bot.fetch_user(ticket["claimed_by"])
                    except discord.HTTPException:
                        pass
                emb = discord.Embed(
                    title="⭐ تقييم جديد",
                    description=(
                        f"👤 **العضو:** {ticket_user or ticket['user_id']}\n"
                        f"🛡️ **الاداري المستلم:** {claimed_user or 'لم يُستلم'}\n"
                        f"⭐ **التقييم:** {'⭐' * stars} ({stars}/5)"
                    ),
                    color=0xFEE75C,
                    timestamp=datetime.now(timezone.utc),
                )
                if ticket_user:
                    emb.set_thumbnail(url=ticket_user.display_avatar.url)
                try:
                    await tqeem_ch.send(embed=emb)
                except discord.HTTPException:
                    pass

        log_id = _s(settings, "log_channel_id", "ticket_logs")
        if log_id:
            log_ch = guild.get_channel(int(log_id))
            if log_ch:
                ticket_user = claimed_user = None
                try:
                    ticket_user = await self.bot.fetch_user(ticket["user_id"])
                except discord.HTTPException:
                    pass
                if ticket.get("claimed_by"):
                    try:
                        claimed_user = await self.bot.fetch_user(ticket["claimed_by"])
                    except discord.HTTPException:
                        pass
                log_embed = discord.Embed(
                    title="🔒 تذكرة مغلقة",
                    description=(
                        f"**التذكرة:** {channel.name}\n"
                        f"**فتحها:** {ticket_user or ticket['user_id']}\n"
                        f"**استلمها:** {claimed_user or 'لم يتم الاستلام'}\n"
                        f"**أُغلقت بواسطة:** {closer}\n"
                        f"**التقييم:** {'⭐' * stars} ({stars}/5)"
                    ),
                    color=0xED4245,
                    timestamp=datetime.now(timezone.utc),
                )
                buf = await self._transcript(channel)
                try:
                    if buf:
                        await log_ch.send(embed=log_embed, file=discord.File(buf, filename=f"transcript-{channel.name}.txt"))
                    else:
                        await log_ch.send(embed=log_embed)
                except discord.HTTPException:
                    try:
                        await log_ch.send(embed=log_embed)
                    except discord.HTTPException:
                        pass

        # عد تنازلي 5 ثواني ثم حذف الروم
        try:
            await channel.send("🔒 تم إغلاق التذكرة.\n⏳ الروم راح ينحذف خلال **5 ثواني**...")
        except discord.HTTPException:
            pass
        import asyncio
        await asyncio.sleep(5)
        try:
            await channel.delete(reason=f"إغلاق تذكرة بواسطة {closer}")
        except discord.HTTPException:
            # لو ما قدر يحذف (صلاحيات)، جرّب النقل للكاتيقوري كبديل
            close_cat = _s(settings, "close_category_id", "close_category")
            if close_cat:
                cat = guild.get_channel(int(close_cat))
                if isinstance(cat, discord.CategoryChannel):
                    try:
                        await channel.edit(category=cat, name=f"closed-{channel.name}"[:100])
                        await channel.send("🔒 تم إغلاق التذكرة. (ما قدرت أحذف الروم — نُقل للأرشيف)")
                        return
                    except discord.HTTPException:
                        pass
            try:
                await channel.send("🔒 تم إغلاق التذكرة (ما قدرت أحذف الروم — تأكد صلاحيات البوت).")
            except discord.HTTPException:
                pass

    @app_commands.command(name="ticket-setup", description="ضبط اعدادات تذكرة")
    @app_commands.describe(
        ticket="اختر رقم التذكرة", name="اسم التذكرة", category="الكاتيقوري",
        role="الرول اللي يشوف التذكرة", admin="رول الادمن",
        ownership="استدعاء صاحب السيرفر؟", reason="طلب سبب عند الفتح؟",
        username_number="إظهار اسم ورقم المستخدم", welcome_msg="رسالة الترحيب",
        welcome_image="رابط صورة الترحيب", mentions="منشن عند الفتح", line="سطر إضافي",
        ticket_logs="روم اللوقز", close_category="كاتيقوري بعد الإغلاق",
    )
    @app_commands.choices(
        ownership=[app_commands.Choice(name="نعم", value="yes"), app_commands.Choice(name="لا", value="no")],
        reason=[app_commands.Choice(name="نعم", value="yes"), app_commands.Choice(name="لا", value="no")],
        username_number=[app_commands.Choice(name="نعم", value="yes"), app_commands.Choice(name="لا", value="no")],
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ticket_setup(
        self, interaction: discord.Interaction, ticket: app_commands.Range[int, 1, 15],
        name: str | None = None, category: discord.CategoryChannel | None = None,
        role: discord.Role | None = None, admin: discord.Role | None = None,
        ownership: str | None = None, reason: str | None = None, username_number: str | None = None,
        welcome_msg: str | None = None, welcome_image: str | None = None, mentions: str | None = None,
        line: str | None = None, ticket_logs: discord.TextChannel | None = None,
        close_category: discord.CategoryChannel | None = None,
        tqeem_room: discord.TextChannel | None = None,
    ):
        section = await self._section(interaction.guild.id)
        types = dict(section.get("types", {}))
        current = dict(types.get(str(ticket), {}))
        mapping = {
            "name": name, "category_id": category.id if category else None,
            "role_id": role.id if role else None, "admin_id": admin.id if admin else None,
            "ownership": ownership, "reason": reason, "username_number": username_number,
            "welcome_msg": welcome_msg, "welcome_image": welcome_image, "mentions": mentions, "line": line,
            "log_channel_id": ticket_logs.id if ticket_logs else None,
            "close_category_id": close_category.id if close_category else None,
            "tqeem_room_id": tqeem_room.id if tqeem_room else None,
        }
        for k, v in mapping.items():
            if v is not None:
                current[k] = v
        types[str(ticket)] = current
        await Storage.update_guild(interaction.guild.id, SECTION, {"types": types})

        lines = []
        if current.get("name"): lines.append(f"📝 الاسم: **{current['name']}**")
        if current.get("category_id"): lines.append(f"📁 الكاتيقوري: <#{current['category_id']}>")
        if current.get("role_id"): lines.append(f"👤 الرول: <@&{current['role_id']}>")
        if current.get("admin_id"): lines.append(f"🛡️ الادمن: <@&{current['admin_id']}>")
        if current.get("ownership"): lines.append(f"👑 استدعاء صاحب السيرفر: **{'نعم' if current['ownership']=='yes' else 'لا'}**")
        if current.get("reason"): lines.append(f"❓ طلب السبب: **{'نعم' if current['reason']=='yes' else 'لا'}**")
        if current.get("username_number"): lines.append(f"🔢 إظهار الاسم والرقم: **{'نعم' if current['username_number']=='yes' else 'لا'}**")
        if current.get("welcome_msg"): lines.append(f"💬 رسالة الترحيب: **{current['welcome_msg']}**")
        if current.get("welcome_image"): lines.append("🖼️ صورة الترحيب: موجودة")
        if current.get("mentions"): lines.append(f"📢 منشن: **{current['mentions']}**")
        if current.get("line"): lines.append(f"➖ الـ Line: **{current['line']}**")
        if current.get("log_channel_id"): lines.append(f"📋 لوقز: <#{current['log_channel_id']}>")
        if current.get("close_category_id"): lines.append(f"🔒 كاتيقوري الإغلاق: <#{current['close_category_id']}>")
        if current.get("tqeem_room_id"): lines.append(f"⭐ روم التقييم: <#{current['tqeem_room_id']}>")

        await interaction.response.send_message(
            embed=discord.Embed(title=f"✅ تم ضبط التذكرة رقم {ticket}", description=chr(10).join(lines) if lines else "لم يتم تغيير أي إعداد", color=0x5865F2),
            ephemeral=True,
        )

    @app_commands.command(name="ticket-panel", description="إنشاء بانل التذاكر")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ticket_panel(self, interaction: discord.Interaction):
        """نفس تدفق البوت المرجعي: Modal → صورة → روم → منيو/أزرار → اختيار → لون/إيموجي/اسم."""
        await interaction.response.send_modal(PanelEmbedModal(self))



    @app_commands.command(name="close", description="إغلاق التذكرة الحالية (مع طلب تقييم إن وُجد)")
    @app_commands.guild_only()
    async def close_cmd(self, interaction: discord.Interaction):
        ticket = await self._get_open(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ هذا الشانل ليس تذكرة!", ephemeral=True)
            return
        if not await self._can_close(interaction.user, interaction.guild, ticket):
            await interaction.response.send_message("❌ بس الستاف أو صاحب التذكرة يقدر يسكرها!", ephemeral=True)
            return
        settings = await self._type_settings(interaction.guild.id, ticket["ticket_num"])
        tqeem = _s(settings, "tqeem_room_id", "tqeem_room")
        if tqeem:
            await interaction.response.send_message(
                f"<@{ticket['user_id']}>\n⭐ **قيّم تجربتك قبل إغلاق التذكرة**\n(أو اضغط إغلاق بدون تقييم)",
                view=TicketRatingView(self, closer_id=interaction.user.id),
            )
            return
        await interaction.response.send_message("🔒 جاري إغلاق التذكرة...")
        await self.close_ticket(interaction.guild, interaction.channel, interaction.user, ticket, 0)

    @app_commands.command(name="forceclose", description="إغلاق التذكرة فوراً بدون تقييم")
    @app_commands.guild_only()
    async def forceclose_cmd(self, interaction: discord.Interaction):
        ticket = await self._get_open(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ هذا الشانل ليس تذكرة!", ephemeral=True)
            return
        if not await self._can_close(interaction.user, interaction.guild, ticket):
            await interaction.response.send_message("❌ بس الستاف أو صاحب التذكرة يقدر يسكرها!", ephemeral=True)
            return
        await interaction.response.send_message("🔒 جاري إغلاق التذكرة بدون تقييم...")
        await self.close_ticket(interaction.guild, interaction.channel, interaction.user, ticket, 0)

    @commands.command(name="close")
    @commands.guild_only()
    async def close_prefix(self, ctx: commands.Context):
        ticket = await self._get_open(ctx.channel.id)
        if not ticket:
            return
        settings = await self._type_settings(ctx.guild.id, ticket["ticket_num"])
        member = ctx.author
        ok = await self._can_close(member, ctx.guild, ticket)
        if not ok:
            await ctx.reply("❌ بس الستاف أو صاحب التذكرة يقدر يسكرها!")
            return
        tqeem = _s(settings, "tqeem_room_id", "tqeem_room")
        if tqeem:
            await ctx.reply(
                f"<@{ticket['user_id']}>\n⭐ **قيّم تجربتك قبل إغلاق التذكرة**\n(أو اضغط إغلاق بدون تقييم)",
                view=TicketRatingView(self, closer_id=ctx.author.id),
            )
            return
        await ctx.reply("🔒 جاري إغلاق التذكرة...")
        await self.close_ticket(ctx.guild, ctx.channel, ctx.author, ticket, 0)

    @commands.command(name="forceclose", aliases=["سكر", "اقفل"])
    @commands.guild_only()
    async def forceclose_prefix(self, ctx: commands.Context):
        """إغلاق التذكرة فوراً بدون طلب تقييم."""
        ticket = await self._get_open(ctx.channel.id)
        if not ticket:
            return
        settings = await self._type_settings(ctx.guild.id, ticket["ticket_num"])
        member = ctx.author
        ok = await self._can_close(member, ctx.guild, ticket)
        if not ok:
            await ctx.reply("❌ بس الستاف أو صاحب التذكرة يقدر يسكرها!")
            return
        await ctx.reply("🔒 جاري إغلاق التذكرة بدون تقييم...")
        await self.close_ticket(ctx.guild, ctx.channel, ctx.author, ticket, 0)

    @commands.command(name="rename")
    @commands.guild_only()
    async def rename_prefix(self, ctx: commands.Context, *, new_name: str = ""):
        ticket = await self._get_open(ctx.channel.id)
        if not ticket:
            return
        settings = await self._type_settings(ctx.guild.id, ticket["ticket_num"])
        member = ctx.author
        ok = await self._has_role(member, _s(settings, "admin_id", "admin")) or ticket.get("claimed_by") == member.id or member.id == ctx.guild.owner_id
        if not ok:
            await ctx.reply("❌ بس مستلم التذكرة أو الإداريين يقدرون يغيرون اسم التذكرة!")
            return
        if not new_name.strip():
            await ctx.reply("❌ اكتب الاسم الجديد بعد الأمر، مثال: `!rename 1000 روب`")
            return
        raw = new_name.strip().lower().replace(" ", "-")
        safe = "".join(c for c in raw if c.isalnum() or c in "-_")[:90]
        if not safe:
            await ctx.reply("❌ اسم غير صالح!")
            return
        try:
            await ctx.channel.edit(name=safe)
            await ctx.reply(f"✅ تم تغيير اسم التذكرة إلى **{safe}**")
        except discord.HTTPException:
            await ctx.reply("❌ ما قدرت أغيّر الاسم.")

    @ticket_setup.error
    @ticket_panel.error
    @forceclose_cmd.error
    async def _err(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            return


async def setup(bot: commands.Bot):
    await bot.add_cog(TicketSystem(bot))
