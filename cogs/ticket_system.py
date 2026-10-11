"""نظام التذاكر — منقول ومُبسّط من مشروع Node مع نفس الأوامر الأساسية."""

from __future__ import annotations

from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import branded_embed
from utils.storage import Storage

SECTION = "tickets"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class TicketReasonModal(discord.ui.Modal, title="سبب فتح التذكرة"):
    reason = discord.ui.TextInput(
        label="اكتب السبب",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500,
    )

    def __init__(self, cog: "TicketSystem", ticket_num: int):
        super().__init__()
        self.cog = cog
        self.ticket_num = ticket_num

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.open_ticket(interaction, self.ticket_num, str(self.reason))


class TicketAddUserModal(discord.ui.Modal, title="إضافة شخص للتذكرة"):
    user_id = discord.ui.TextInput(label="آيدي المستخدم", required=True, max_length=25)

    def __init__(self, cog: "TicketSystem"):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        ticket = await self.cog._get_open(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ هذا ليس روم تذكرة.", ephemeral=True)
            return
        try:
            uid = int(str(self.user_id).strip())
        except ValueError:
            await interaction.response.send_message("❌ آيدي غير صالح.", ephemeral=True)
            return
        member = interaction.guild.get_member(uid) or await interaction.guild.fetch_member(uid)
        if not member:
            await interaction.response.send_message("❌ المستخدم غير موجود.", ephemeral=True)
            return
        await interaction.channel.set_permissions(
            member,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
        )
        await interaction.response.send_message(f"✅ تم إضافة {member.mention} للتذكرة.")


class TicketRenameModal(discord.ui.Modal, title="تغيير اسم التذكرة"):
    new_name = discord.ui.TextInput(label="الاسم الجديد", required=True, max_length=90)

    def __init__(self, cog: "TicketSystem"):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        ticket = await self.cog._get_open(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ هذا ليس روم تذكرة.", ephemeral=True)
            return
        if not await self.cog._can_staff(interaction, ticket):
            await interaction.response.send_message(
                "❌ بس المستلم أو الأدمن يقدر يغيّر الاسم.", ephemeral=True
            )
            return
        raw = str(self.new_name).strip().lower().replace(" ", "-")
        safe = "".join(c for c in raw if c.isalnum() or c in "-_أبتثجحخدذرزسشصضطظعغفقكلمنهويىئءؤة")[:90]
        if not safe:
            await interaction.response.send_message("❌ اسم غير صالح.", ephemeral=True)
            return
        try:
            await interaction.channel.edit(name=safe)
            await interaction.response.send_message(f"✅ صار اسم التذكرة: **{safe}**")
        except discord.HTTPException:
            await interaction.response.send_message("❌ ما قدرت أغيّر الاسم.", ephemeral=True)


class TicketControlView(discord.ui.View):
    def __init__(self, cog: "TicketSystem"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="إغلاق", emoji="🔐", style=discord.ButtonStyle.danger, custom_id="ticket:close")
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket = await self.cog._get_open(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ هذا ليس روم تذكرة.", ephemeral=True)
            return
        if not await self.cog._can_staff(interaction, ticket) and interaction.user.id != ticket.get("user_id"):
            # صاحب التذكرة أو الستاف
            if interaction.user.id != ticket.get("user_id"):
                await interaction.response.send_message("❌ ما عندك صلاحية الإغلاق.", ephemeral=True)
                return
        settings = await self.cog._type_settings(interaction.guild.id, ticket["ticket_num"])
        if settings.get("tqeem_room_id") and interaction.user.id == ticket.get("user_id"):
            view = TicketRatingView(self.cog)
            await interaction.response.send_message(
                f"<@{ticket['user_id']}>\n⭐ **قيّم تجربتك قبل إغلاق التذكرة**",
                view=view,
            )
            return
        await interaction.response.send_message("🔒 جاري إغلاق التذكرة...")
        await self.cog.close_ticket(interaction.guild, interaction.channel, interaction.user, ticket, 0)

    @discord.ui.button(label="استلام", emoji="🎯", style=discord.ButtonStyle.success, custom_id="ticket:claim")
    async def claim_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket = await self.cog._get_open(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ هذا ليس روم تذكرة.", ephemeral=True)
            return
        if not await self.cog._is_support(interaction, ticket):
            await interaction.response.send_message("❌ ما عندك صلاحية الاستلام.", ephemeral=True)
            return
        if ticket.get("claimed_by"):
            await interaction.response.send_message(
                f"⚠️ مستلمة مسبقاً من <@{ticket['claimed_by']}>", ephemeral=True
            )
            return
        ticket["claimed_by"] = interaction.user.id
        await self.cog._save_open(interaction.guild.id, interaction.channel.id, ticket)
        # السماح للكلايمر بالكتابة
        await interaction.channel.set_permissions(
            interaction.user,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
        )
        await interaction.response.send_message(f"✅ استلم التذكرة {interaction.user.mention}")

    @discord.ui.button(label="ترك التذكرة", emoji="📤", style=discord.ButtonStyle.secondary, custom_id="ticket:unclaim")
    async def unclaim_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket = await self.cog._get_open(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ هذا ليس روم تذكرة.", ephemeral=True)
            return
        if ticket.get("claimed_by") != interaction.user.id and not await self.cog._can_staff(interaction, ticket):
            await interaction.response.send_message("❌ بس المستلم يقدر يتركها.", ephemeral=True)
            return
        ticket["claimed_by"] = None
        await self.cog._save_open(interaction.guild.id, interaction.channel.id, ticket)
        await interaction.response.send_message("🚪 تم ترك التذكرة.")

    @discord.ui.button(label="إضافة عضو", emoji="👤", style=discord.ButtonStyle.primary, custom_id="ticket:add")
    async def add_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket = await self.cog._get_open(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ هذا ليس روم تذكرة.", ephemeral=True)
            return
        if not await self.cog._can_staff(interaction, ticket):
            await interaction.response.send_message("❌ ما عندك صلاحية.", ephemeral=True)
            return
        await interaction.response.send_modal(TicketAddUserModal(self.cog))

    @discord.ui.button(label="تغيير الاسم", emoji="✏️", style=discord.ButtonStyle.secondary, custom_id="ticket:rename")
    async def rename_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket = await self.cog._get_open(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ هذا ليس روم تذكرة.", ephemeral=True)
            return
        await interaction.response.send_modal(TicketRenameModal(self.cog))


class TicketRatingView(discord.ui.View):
    def __init__(self, cog: "TicketSystem"):
        super().__init__(timeout=300)
        self.cog = cog
        for i in range(1, 6):
            self.add_item(self._star_button(i))

    def _star_button(self, stars: int) -> discord.ui.Button:
        button = discord.ui.Button(
            label="⭐" * stars,
            style=discord.ButtonStyle.secondary,
            custom_id=f"ticket:rate:{stars}",
        )

        async def callback(interaction: discord.Interaction):
            ticket = await self.cog._get_open(interaction.channel.id)
            if not ticket:
                await interaction.response.send_message("❌ التذكرة غير موجودة.", ephemeral=True)
                return
            if interaction.user.id != ticket.get("user_id"):
                await interaction.response.send_message("❌ بس صاحب التذكرة يقيّم.", ephemeral=True)
                return
            await interaction.response.edit_message(
                content=f"✅ شكراً! تقييمك: **{'⭐' * stars}**\nجاري الإغلاق...",
                view=None,
            )
            await self.cog.close_ticket(
                interaction.guild, interaction.channel, interaction.user, ticket, stars
            )

        button.callback = callback
        return button


class TicketPanelSelect(discord.ui.Select):
    def __init__(self, cog: "TicketSystem", options: list[discord.SelectOption]):
        super().__init__(
            placeholder="اختر نوع التذكرة...",
            options=options[:25],
            custom_id="ticket:panel_select",
            min_values=1,
            max_values=1,
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        ticket_num = int(self.values[0])
        settings = await self.cog._type_settings(interaction.guild.id, ticket_num)
        if not settings:
            await interaction.response.send_message(
                "❌ هذا النوع مش معدّ. استخدم `/ticket-setup`.", ephemeral=True
            )
            return
        if settings.get("reason") == "yes":
            await interaction.response.send_modal(TicketReasonModal(self.cog, ticket_num))
            return
        await self.cog.open_ticket(interaction, ticket_num, None)


class TicketPanelView(discord.ui.View):
    def __init__(self, cog: "TicketSystem", options: list[discord.SelectOption] | None = None):
        super().__init__(timeout=None)
        if options:
            self.add_item(TicketPanelSelect(cog, options))


class TicketSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        # أزرار دائمة — select يُعاد بناؤه من الرسالة عند الحاجة عبر listener
        self.bot.add_view(TicketControlView(self))

    async def _section(self, guild_id: int) -> dict:
        conf = await Storage.get_guild(guild_id)
        return conf.get(SECTION, {})

    async def _type_settings(self, guild_id: int, ticket_num: int) -> dict:
        section = await self._section(guild_id)
        return dict(section.get("types", {}).get(str(ticket_num), {}) or {})

    async def _get_open(self, channel_id: int) -> dict | None:
        # نبحث بكل السيرفرات عبر الـ channel
        # القناة معرفة — نجيبها من الكاش
        channel = self.bot.get_channel(channel_id)
        if not channel or not getattr(channel, "guild", None):
            return None
        section = await self._section(channel.guild.id)
        return section.get("open", {}).get(str(channel_id))

    async def _save_open(self, guild_id: int, channel_id: int, ticket: dict | None):
        section = await self._section(guild_id)
        open_map = dict(section.get("open", {}))
        key = str(channel_id)
        if ticket is None:
            open_map.pop(key, None)
        else:
            open_map[key] = ticket
        await Storage.update_guild(guild_id, SECTION, {"open": open_map})

    async def _is_support(self, interaction: discord.Interaction, ticket: dict) -> bool:
        member = interaction.user
        if not isinstance(member, discord.Member):
            return False
        if member.guild_permissions.administrator or member.id == interaction.guild.owner_id:
            return True
        settings = await self._type_settings(interaction.guild.id, ticket["ticket_num"])
        for key in ("admin_id", "role_id", "support_role_id"):
            rid = settings.get(key)
            if rid and any(r.id == rid for r in member.roles):
                return True
        return False

    async def _can_staff(self, interaction: discord.Interaction, ticket: dict) -> bool:
        member = interaction.user
        if not isinstance(member, discord.Member):
            return False
        if member.guild_permissions.administrator or member.id == interaction.guild.owner_id:
            return True
        if ticket.get("claimed_by") == member.id:
            return True
        settings = await self._type_settings(interaction.guild.id, ticket["ticket_num"])
        admin_id = settings.get("admin_id")
        if admin_id and any(r.id == admin_id for r in member.roles):
            return True
        return False

    async def open_ticket(
        self, interaction: discord.Interaction, ticket_num: int, reason: str | None
    ):
        settings = await self._type_settings(interaction.guild.id, ticket_num)
        if not settings:
            await interaction.response.send_message(
                "❌ نوع التذكرة غير معدّ.", ephemeral=True
            )
            return

        section = await self._section(interaction.guild.id)
        open_map = section.get("open", {})
        for t in open_map.values():
            if t.get("user_id") == interaction.user.id and t.get("ticket_num") == ticket_num:
                await interaction.response.send_message(
                    "❌ لديك تذكرة مفتوحة من هذا النوع.", ephemeral=True
                )
                return

        category_id = settings.get("category_id")
        category = interaction.guild.get_channel(category_id) if category_id else None

        base = settings.get("name") or "ticket"
        uname = interaction.user.name.replace(" ", "-")[:20]
        channel_name = f"{base}-{uname}"
        if settings.get("username_number") == "yes":
            channel_name = f"{base}-{uname}-{interaction.guild.member_count}"

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            ),
            interaction.guild.me: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, manage_channels=True, read_message_history=True
            ),
        }
        role_id = settings.get("role_id")
        if role_id:
            role = interaction.guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=False, read_message_history=True
                )
        admin_id = settings.get("admin_id")
        if admin_id:
            admin = interaction.guild.get_role(admin_id)
            if admin:
                overwrites[admin] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_messages=True,
                )
        if settings.get("ownership") == "yes":
            owner = interaction.guild.owner
            if owner:
                overwrites[owner] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True
                )

        try:
            channel = await interaction.guild.create_text_channel(
                name=channel_name[:100],
                category=category if isinstance(category, discord.CategoryChannel) else None,
                overwrites=overwrites,
                reason=f"تذكرة بواسطة {interaction.user}",
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ البوت ما معه صلاحية إنشاء رومات.", ephemeral=True
            )
            return
        except discord.HTTPException as e:
            await interaction.response.send_message(f"❌ فشل إنشاء التذكرة: {e}", ephemeral=True)
            return

        ticket = {
            "user_id": interaction.user.id,
            "ticket_num": ticket_num,
            "claimed_by": None,
            "created_at": _now(),
            "reason": reason,
        }
        await self._save_open(interaction.guild.id, channel.id, ticket)

        welcome = settings.get("welcome_msg") or f"مرحباً {interaction.user.mention}، فريق الدعم بيرد عليك قريباً."
        embed = branded_embed(
            title=f"🎟️ تذكرة #{ticket_num} — {settings.get('name') or 'دعم'}",
            description=welcome,
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="العضو", value=interaction.user.mention, inline=True)
        if reason:
            embed.add_field(name="السبب", value=reason, inline=False)
        if settings.get("welcome_image"):
            embed.set_image(url=settings["welcome_image"])

        content_parts = [interaction.user.mention]
        if settings.get("mentions"):
            content_parts.append(str(settings["mentions"]))
        line = settings.get("line")
        msg = await channel.send(
            content=" ".join(content_parts),
            embed=embed,
            view=TicketControlView(self),
        )
        if line:
            await channel.send(line)

        log_id = settings.get("log_channel_id")
        if log_id:
            log_ch = interaction.guild.get_channel(log_id)
            if log_ch:
                try:
                    await log_ch.send(
                        embed=branded_embed(
                            title="📨 تذكرة جديدة",
                            description=f"{channel.mention} بواسطة {interaction.user.mention}",
                            color=discord.Color.green(),
                        )
                    )
                except discord.HTTPException:
                    pass

        if interaction.response.is_done():
            await interaction.followup.send(f"✅ تم فتح تذكرتك: {channel.mention}", ephemeral=True)
        else:
            await interaction.response.send_message(
                f"✅ تم فتح تذكرتك: {channel.mention}", ephemeral=True
            )

    async def close_ticket(
        self,
        guild: discord.Guild,
        channel: discord.TextChannel,
        closer: discord.abc.User,
        ticket: dict,
        stars: int,
    ):
        settings = await self._type_settings(guild.id, ticket["ticket_num"])
        await self._save_open(guild.id, channel.id, None)

        log_id = settings.get("log_channel_id")
        if log_id:
            log_ch = guild.get_channel(log_id)
            if log_ch:
                desc = (
                    f"**الروم:** {channel.name}\n"
                    f"**العضو:** <@{ticket['user_id']}>\n"
                    f"**أغلقها:** {closer.mention}\n"
                )
                if stars:
                    desc += f"**التقييم:** {'⭐' * stars}\n"
                try:
                    await log_ch.send(
                        embed=branded_embed(
                            title="🔐 تذكرة مغلقة",
                            description=desc,
                            color=discord.Color.red(),
                        )
                    )
                except discord.HTTPException:
                    pass

        tqeem = settings.get("tqeem_room_id")
        if tqeem and stars:
            rate_ch = guild.get_channel(tqeem)
            if rate_ch:
                try:
                    await rate_ch.send(
                        f"⭐ تقييم تذكرة <@{ticket['user_id']}>: **{'⭐' * stars}** (بواسطة {closer.mention})"
                    )
                except discord.HTTPException:
                    pass

        close_cat_id = settings.get("close_category_id")
        if close_cat_id:
            cat = guild.get_channel(close_cat_id)
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

    # ─── Slash commands ───

    @app_commands.command(name="ticket-setup", description="ضبط إعدادات نوع تذكرة (1-15)")
    @app_commands.describe(
        ticket="رقم نوع التذكرة (1-15)",
        name="اسم النوع",
        category="الكاتيجوري",
        role="رتبة تشوف التذكرة",
        admin="رتبة الأدمن",
        ownership="استدعاء صاحب السيرفر؟",
        reason="طلب سبب عند الفتح؟",
        username_number="إضافة رقم للأعضاء في الاسم؟",
        welcome_msg="رسالة الترحيب",
        welcome_image="رابط صورة الترحيب",
        mentions="منشن عند الفتح",
        line="سطر إضافي تحت الترحيب",
        ticket_logs="روم اللوق",
        close_category="كاتيجوري بعد الإغلاق",
        support_role="رتبة السبورت",
        tqeem_room="روم التقييمات",
    )
    @app_commands.choices(
        ownership=[
            app_commands.Choice(name="نعم", value="yes"),
            app_commands.Choice(name="لا", value="no"),
        ],
        reason=[
            app_commands.Choice(name="نعم", value="yes"),
            app_commands.Choice(name="لا", value="no"),
        ],
        username_number=[
            app_commands.Choice(name="نعم", value="yes"),
            app_commands.Choice(name="لا", value="no"),
        ],
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ticket_setup(
        self,
        interaction: discord.Interaction,
        ticket: app_commands.Range[int, 1, 15],
        name: str | None = None,
        category: discord.CategoryChannel | None = None,
        role: discord.Role | None = None,
        admin: discord.Role | None = None,
        ownership: str | None = None,
        reason: str | None = None,
        username_number: str | None = None,
        welcome_msg: str | None = None,
        welcome_image: str | None = None,
        mentions: str | None = None,
        line: str | None = None,
        ticket_logs: discord.TextChannel | None = None,
        close_category: discord.CategoryChannel | None = None,
        support_role: discord.Role | None = None,
        tqeem_room: discord.TextChannel | None = None,
    ):
        section = await self._section(interaction.guild.id)
        types = dict(section.get("types", {}))
        current = dict(types.get(str(ticket), {}))

        mapping = {
            "name": name,
            "category_id": category.id if category else None,
            "role_id": role.id if role else None,
            "admin_id": admin.id if admin else None,
            "ownership": ownership,
            "reason": reason,
            "username_number": username_number,
            "welcome_msg": welcome_msg,
            "welcome_image": welcome_image,
            "mentions": mentions,
            "line": line,
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

        embed = branded_embed(title=f"⚙️ إعداد تذكرة #{ticket}", color=discord.Color.green())
        for k, v in current.items():
            embed.add_field(name=k, value=str(v), inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="ticket-panel", description="إرسال بانل فتح التذاكر")
    @app_commands.describe(
        title="عنوان الإمبد",
        description="وصف الإمبد",
        image="رابط صورة اختياري",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ticket_panel(
        self,
        interaction: discord.Interaction,
        title: str = "🎟️ مركز التذاكر",
        description: str = "اختر نوع التذكرة من القائمة بالأسفل 👇",
        image: str | None = None,
    ):
        section = await self._section(interaction.guild.id)
        types = section.get("types", {})
        if not types:
            await interaction.response.send_message(
                "❌ ما في أنواع معدّة. استخدم `/ticket-setup` أولاً.", ephemeral=True
            )
            return

        options = []
        for num, cfg in sorted(types.items(), key=lambda x: int(x[0])):
            label = cfg.get("name") or f"تذكرة {num}"
            options.append(
                discord.SelectOption(
                    label=label[:100],
                    value=str(num),
                    emoji="🎟️",
                    description=f"نوع #{num}"[:100],
                )
            )

        embed = branded_embed(title=title, description=description, color=discord.Color.blurple())
        if image:
            embed.set_image(url=image)

        view = TicketPanelView(self, options)
        await interaction.response.send_message("✅ تم إرسال البانل.", ephemeral=True)
        msg = await interaction.channel.send(embed=embed, view=view)

        panels = dict(section.get("panels", {}))
        panels[str(msg.id)] = {
            "channel_id": interaction.channel.id,
            "types": list(types.keys()),
        }
        await Storage.update_guild(interaction.guild.id, SECTION, {"panels": panels})

    @app_commands.command(name="close", description="إغلاق التذكرة الحالية")
    @app_commands.guild_only()
    async def close_cmd(self, interaction: discord.Interaction):
        ticket = await self._get_open(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ هذا الروم ليس تذكرة.", ephemeral=True)
            return
        if not await self._can_staff(interaction, ticket) and interaction.user.id != ticket.get("user_id"):
            await interaction.response.send_message(
                "❌ بس المستلم أو الأدمن أو صاحب التذكرة.", ephemeral=True
            )
            return
        await interaction.response.send_message("🔒 جاري إغلاق التذكرة...")
        await self.close_ticket(interaction.guild, interaction.channel, interaction.user, ticket, 0)

    @commands.command(name="close")
    @commands.guild_only()
    async def close_prefix(self, ctx: commands.Context):
        ticket = await self._get_open(ctx.channel.id)
        if not ticket:
            return
        interaction_like = ctx
        # permission check simplified
        member = ctx.author
        ok = (
            member.guild_permissions.administrator
            or member.id == ctx.guild.owner_id
            or ticket.get("claimed_by") == member.id
            or ticket.get("user_id") == member.id
        )
        settings = await self._type_settings(ctx.guild.id, ticket["ticket_num"])
        if settings.get("admin_id") and any(r.id == settings["admin_id"] for r in member.roles):
            ok = True
        if not ok:
            await ctx.reply("❌ بس المستلم أو الأدمن يقدر يسكرها.")
            return
        await ctx.reply("🔒 جاري إغلاق التذكرة...")
        await self.close_ticket(ctx.guild, ctx.channel, ctx.author, ticket, 0)

    @ticket_setup.error
    @ticket_panel.error
    async def _setup_err(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            return


async def setup(bot: commands.Bot):
    await bot.add_cog(TicketSystem(bot))
