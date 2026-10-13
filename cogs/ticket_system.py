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
        is_claimer = ticket.get("claimed_by") == member.id
        is_owner = interaction.guild.owner_id == member.id
        is_towner = member.id == ticket.get("user_id")
        if not (has_admin or is_claimer or is_owner or is_towner):
            await interaction.response.send_message("❌ بس مستلم التذكرة أو الإداري يقدر يسكرها!", ephemeral=True)
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
        ticket["claimed_by"] = None
        await self.cog._save_open(interaction.guild.id, interaction.channel.id, ticket)
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
        role_id = _s(settings, "support_role_id", "role_id", "role")
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



class TicketPanelSelect(discord.ui.Select):
    def __init__(self, cog, options):
        super().__init__(placeholder="بانل التذكرة", options=options[:25], custom_id="ticket:panel_select", min_values=1, max_values=1)
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
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



class TicketPanelSetupView(discord.ui.View):
    """خطوة اختيار ستايل البانل ثم أنواع التذاكر."""

    def __init__(self, cog, types: dict):
        super().__init__(timeout=300)
        self.cog = cog
        self.types = types
        self.style = "classic"
        self.selected_nums: list[str] = []

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True

    @discord.ui.button(label="كلاسيك (قائمة منسدلة)", style=discord.ButtonStyle.primary, emoji="📋", row=0)
    async def style_classic(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.style = "classic"
        await self._ask_types(interaction)

    @discord.ui.button(label="أزرار (حتى 5 أنواع)", style=discord.ButtonStyle.secondary, emoji="🔘", row=0)
    async def style_buttons(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.style = "buttons"
        await self._ask_types(interaction)

    @discord.ui.button(label="قائمة + وصف ملوّن", style=discord.ButtonStyle.success, emoji="✨", row=0)
    async def style_fancy(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.style = "fancy"
        await self._ask_types(interaction)

    async def _ask_types(self, interaction: discord.Interaction):
        options = []
        for num, cfg in sorted(self.types.items(), key=lambda x: int(x[0])):
            label = (cfg.get("name") or f"تذكرة {num}")[:100]
            options.append(discord.SelectOption(label=label, value=str(num), description=f"نوع #{num}"[:100], emoji="🎫"))
        view = TicketTypePickView(self.cog, self.types, self.style, options)
        emb = discord.Embed(
            title="🎫 اختر أنواع التذاكر للبانل",
            description="اختر **رقم أو أكثر** (مثلاً 1 و 5 فقط — بدون 2 و 3 و 4).\nبعد الاختيار اضغط تأكيد.",
            color=0x57F287,
        )
        await interaction.response.edit_message(embed=emb, view=view)


class TicketTypePickView(discord.ui.View):
    def __init__(self, cog, types: dict, style: str, options: list):
        super().__init__(timeout=300)
        self.cog = cog
        self.types = types
        self.style = style
        self.picked: list[str] = []
        sel = discord.ui.Select(
            placeholder="اختر أنواع التذاكر (متعدد)",
            options=options[:25],
            min_values=1,
            max_values=min(len(options), 25),
            custom_id="ticket:panel_pick_types",
        )
        sel.callback = self._on_select
        self.add_item(sel)

    async def _on_select(self, interaction: discord.Interaction):
        self.picked = list(interaction.data.get("values") or [])
        await interaction.response.send_modal(TicketPanelMetaModal(self.cog, self.types, self.style, self.picked))


class TicketPanelMetaModal(discord.ui.Modal, title="تفاصيل بانل التذاكر"):
    title_in = discord.ui.TextInput(label="عنوان الإمبد", default="التذاكر", max_length=100, required=True)
    desc_in = discord.ui.TextInput(
        label="وصف الإمبد",
        style=discord.TextStyle.paragraph,
        default="اختر نوع التذكرة من القائمة",
        max_length=400,
        required=True,
    )
    color_in = discord.ui.TextInput(label="لون الإمبد (hex مثل 5865F2)", default="5865F2", max_length=7, required=False)
    image_in = discord.ui.TextInput(label="رابط صورة (اختياري)", required=False, max_length=300)
    emoji_in = discord.ui.TextInput(
        label="إيموجي للأنواع (مثال: 🎫,🛠️,💎 أو اتركه فاضي)",
        required=False,
        max_length=100,
        placeholder="إيموجي مفصولة بفاصلة بنفس ترتيب الأنواع المختارة",
    )

    def __init__(self, cog, types: dict, style: str, picked: list[str]):
        super().__init__()
        self.cog = cog
        self.types = types
        self.style = style
        self.picked = picked

    async def on_submit(self, interaction: discord.Interaction):
        raw_color = str(self.color_in).strip().lstrip("#") or "5865F2"
        try:
            color = int(raw_color, 16)
        except ValueError:
            color = 0x5865F2
        title = str(self.title_in).strip() or "التذاكر"
        description = str(self.desc_in).strip() or "اختر نوع التذكرة"
        image = str(self.image_in).strip() or None
        emoji_raw = str(self.emoji_in).strip()
        emojis = [e.strip() for e in emoji_raw.replace("،", ",").split(",") if e.strip()] if emoji_raw else []

        options = []
        for i, num in enumerate(sorted(self.picked, key=lambda x: int(x))):
            cfg = self.types.get(str(num), {})
            label = (cfg.get("name") or f"تذكرة {num}")[:100]
            em = None
            if i < len(emojis):
                em = emojis[i]
            try:
                opt = discord.SelectOption(label=label, value=str(num), description=f"نوع #{num}"[:100], emoji=em or "🎫")
            except Exception:
                opt = discord.SelectOption(label=label, value=str(num), description=f"نوع #{num}"[:100], emoji="🎫")
            options.append(opt)

        embed = discord.Embed(title=title, description=description, color=color)
        if image:
            try:
                embed.set_image(url=image)
            except Exception:
                pass
        if interaction.guild and interaction.guild.icon:
            embed.set_footer(text=f"{interaction.guild.name} | Tickets", icon_url=interaction.guild.icon.url)

        if self.style == "buttons" and len(options) <= 5:
            view = TicketPanelButtonsView(self.cog, options)
        else:
            view = TicketPanelView(self.cog, options)

        await interaction.response.send_message("✅ تم إرسال البانل للقناة.", ephemeral=True)
        msg = await interaction.channel.send(embed=embed, view=view)
        section = await self.cog._section(interaction.guild.id)
        panels = dict(section.get("panels", {}))
        panels[str(msg.id)] = {"channel_id": interaction.channel.id, "types": [o.value for o in options], "style": self.style}
        await Storage.update_guild(interaction.guild.id, SECTION, {"panels": panels})


class TicketPanelButtonsView(discord.ui.View):
    """بانل بأزرار بدل القائمة (حتى 5 أنواع)."""

    def __init__(self, cog, options: list):
        super().__init__(timeout=None)
        self.cog = cog
        for opt in options[:5]:
            btn = discord.ui.Button(
                label=opt.label[:80],
                style=discord.ButtonStyle.primary,
                emoji=getattr(opt, "emoji", None) or "🎫",
                custom_id=f"ticket:open_btn:{opt.value}",
            )
            btn.callback = self._make_cb(int(opt.value))
            self.add_item(btn)

    def _make_cb(self, ticket_num: int):
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


class TicketSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(TicketControlView(self, claimed_by=None))
        # بانل الأزرار يحتاج تسجيل ديناميكي عند الإرسال؛ القائمة المنسدلة تستخدم custom_id ثابت

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
        for key in ("admin_id", "admin", "role_id", "role", "support_role_id"):
            if await self._has_role(member, _s(settings, key)):
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
        for t in section.get("open", {}).values():
            if t.get("user_id") == interaction.user.id and t.get("ticket_num") == ticket_num:
                await interaction.response.send_message("❌ لديك تذكرة بالفعل", ephemeral=True)
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

        close_cat = _s(settings, "close_category_id", "close_category")
        if close_cat:
            cat = guild.get_channel(int(close_cat))
            if isinstance(cat, discord.CategoryChannel):
                try:
                    await channel.edit(category=cat, name=f"closed-{channel.name}"[:100])
                    await channel.send("🔒 تم إغلاق التذكرة. الروم نُقل لأرشيف الإغلاق.")
                    return
                except discord.HTTPException:
                    pass
        try:
            await channel.delete(reason=f"إغلاق تذكرة بواسطة {closer}")
        except discord.HTTPException:
            try:
                await channel.send("🔒 تم إغلاق التذكرة (ما قدرت أحذف الروم).")
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
        support_role="رتبة السبورت", tqeem_room="روم التقييمات",
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
        close_category: discord.CategoryChannel | None = None, support_role: discord.Role | None = None,
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
            "support_role_id": support_role.id if support_role else None,
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

    @app_commands.command(name="ticket-panel", description="إرسال بانل فتح التذاكر — إعداد تفاعلي")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ticket_panel(self, interaction: discord.Interaction):
        section = await self._section(interaction.guild.id)
        types = section.get("types", {})
        if not types:
            await interaction.response.send_message("❌ ما في أنواع معدّة. استخدم `/ticket-setup` أولاً.", ephemeral=True)
            return
        # خطوة 1: اختيار ستايل البانل
        emb = discord.Embed(
            title="🎫 إعداد بانل التذاكر",
            description=(
                "اختر **شكل البانل** من الأزرار تحت، ثم رح نكمل الإعداد خطوة بخطوة:\n"
                "• اختيار أنواع التذاكر (مثلاً 1 و 5 فقط)\n"
                "• عنوان ووصف ولون البانل\n"
                "• إيموجي لكل نوع (اختياري)"
            ),
            color=0x5865F2,
        )
        await interaction.response.send_message(embed=emb, view=TicketPanelSetupView(self, types), ephemeral=True)

    @app_commands.command(name="close", description="إغلاق التذكرة الحالية (مع طلب تقييم إن وُجد)")
    @app_commands.guild_only()
    async def close_cmd(self, interaction: discord.Interaction):
        ticket = await self._get_open(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ هذا الشانل ليس تذكرة!", ephemeral=True)
            return
        if not await self._can_staff(interaction, ticket) and interaction.user.id != ticket.get("user_id"):
            await interaction.response.send_message("❌ بس مستلم التذكرة أو الإداري يقدر يسكرها!", ephemeral=True)
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
        if not await self._can_staff(interaction, ticket) and interaction.user.id != ticket.get("user_id"):
            await interaction.response.send_message("❌ بس مستلم التذكرة أو الإداري يقدر يسكرها!", ephemeral=True)
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
        ok = (
            member.guild_permissions.administrator or member.id == ctx.guild.owner_id
            or ticket.get("claimed_by") == member.id or ticket.get("user_id") == member.id
            or await self._has_role(member, _s(settings, "admin_id", "admin"))
        )
        if not ok:
            await ctx.reply("❌ بس مستلم التذكرة أو الإداري يقدر يسكرها!")
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
        ok = (
            member.guild_permissions.administrator or member.id == ctx.guild.owner_id
            or ticket.get("claimed_by") == member.id or ticket.get("user_id") == member.id
            or await self._has_role(member, _s(settings, "admin_id", "admin"))
        )
        if not ok:
            await ctx.reply("❌ بس مستلم التذكرة أو الإداري يقدر يسكرها!")
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
