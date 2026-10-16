"""داشبورد البوت — واجهة جميلة ومنظمة لكل الأنظمة والأوامر."""

from __future__ import annotations

import os

from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from utils.storage import Storage

# ألوان حسب القسم
C_HOME = 0x5865F2
C_MOD = 0xED4245
C_ROLES = 0xEB459E
C_SEC = 0xFEE75C
C_XP = 0x57F287
C_VOICE = 0x9B59B6
C_TICKET = 0x3498DB
C_FUN = 0xE67E22
C_UTIL = 0x1ABC9C
C_CMD = 0x95A5A6

SEP = "────────────────────────"


def _ok(v) -> str:
    return "✅" if v else "❌"


def _roles(guild: discord.Guild, ids) -> str:
    if not ids:
        return "`—`"
    parts = []
    for i in ids[:6]:
        r = guild.get_role(int(i)) if i else None
        parts.append(r.mention if r else f"`{i}`")
    extra = len(ids) - 6
    s = " · ".join(parts)
    if extra > 0:
        s += f" +{extra}"
    return s


def _ch(guild: discord.Guild, cid) -> str:
    if not cid:
        return "`—`"
    c = guild.get_channel(int(cid))
    return c.mention if c else f"`{cid}`"


def _base(title: str, color: int, guild: discord.Guild, page_hint: str = "") -> discord.Embed:
    emb = discord.Embed(
        title=title,
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    if guild.icon:
        emb.set_thumbnail(url=guild.icon.url)
    footer = f"{guild.name} · ROW Dashboard"
    if page_hint:
        footer = f"{page_hint} · {footer}"
    emb.set_footer(text=footer, icon_url=guild.icon.url if guild.icon else None)
    return emb


class DashboardSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _conf(self, guild_id: int) -> dict:
        return await Storage.get_guild(guild_id)

    # ── صفحات ──

    def page_home(self, guild: discord.Guild, conf: dict) -> discord.Embed:
        emb = _base("✨ ROW Control Center", C_HOME, guild, "الرئيسية")
        emb.description = (
            f"مرحباً بك في **داشبورد البوت** لسيرفر **{guild.name}**\n"
            f"{SEP}\n"
            "استخدم **القائمة بالأسفل** للتنقل بين الأقسام\n"
            "أو أزرار ◀️ ▶️ للتصفح السريع\n"
            f"{SEP}"
        )
        # ملخص سريع
        tickets = conf.get("tickets", {}).get("types", {})
        av = conf.get("auto_voice", {})
        xp = conf.get("xp", {})
        filt = conf.get("word_filter", {})
        emb.add_field(
            name="📊 لمحة سريعة",
            value=(
                f"🎫 أنواع تذاكر معدّة: **{len(tickets)}**\n"
                f"🔊 رومات فويس نشطة: **{len(av.get('rooms') or {})}**\n"
                f"⭐ نظام XP: **{'مفعّل' if xp.get('enabled', True) else 'متوقف'}**\n"
                f"🛡️ فلتر كلمات: **{len(filt.get('words') or {})}** كلمة"
            ),
            inline=False,
        )
        emb.add_field(name="🛡️ إشراف", value="`تايم · باند · تحذير · سجن`", inline=True)
        emb.add_field(name="🎭 رتب", value="`رتب · ستاف · أوتو رول`", inline=True)
        emb.add_field(name="🎟️ تذاكر", value="`بانل · استلام · تقييم`", inline=True)
        emb.add_field(name="🔊 فويس", value="`/room-voice · auto-voice`", inline=True)
        emb.add_field(name="🎉 فعاليات", value="`قيف · عجلة · برود`", inline=True)
        emb.add_field(name="🧰 أدوات", value="`باكاب · فلتر · لوقات`", inline=True)
        return emb

    def page_moderation(self, guild: discord.Guild, conf: dict) -> discord.Embed:
        emb = _base("🛡️ الإشراف والعقوبات", C_MOD, guild, "إشراف")
        emb.description = f"حالة أنظمة الموديريشن\n{SEP}"

        def block(key, label, extra_keys=()):
            s = conf.get(key, {})
            roles = s.get("allowed_role_ids") or s.get("giver_role_ids") or []
            log = s.get("log_channel_id")
            lines = [f"{_ok(roles)} **{label}**", f"الرتب: {_roles(guild, roles)}", f"اللوق: {_ch(guild, log)}"]
            for ek, el in extra_keys:
                lines.append(f"{el}: `{s.get(ek) or '—'}`")
            return "\n".join(lines)

        emb.add_field(name="⏱️ تايم", value=block("time", "تايم", [("daily_limit", "الحد")]), inline=True)
        emb.add_field(name="⚠️ تحذير", value=block("warn", "تحذير"), inline=True)
        emb.add_field(name="🔨 باند", value=block("ban", "باند", [("daily_limit", "الحد")]), inline=True)
        emb.add_field(name="🏷️ نك", value=block("nickname", "نك"), inline=True)
        emb.add_field(name="🧹 rar", value=block("rar", "rar"), inline=True)
        emb.add_field(name="🗑️ مسح", value=block("clear", "مسح"), inline=True)

        prison = conf.get("prison", {})
        emb.add_field(
            name=f"{_ok(prison.get('role_id') or prison.get('allowed_role_ids'))} ⛓️ سجن",
            value=(
                f"الرتب: {_roles(guild, prison.get('allowed_role_ids') or [])}\n"
                f"رتبة السجن: {_roles(guild, [prison['role_id']] if prison.get('role_id') else [])}\n"
                f"اللوق: {_ch(guild, prison.get('log_channel_id'))}"
            ),
            inline=False,
        )
        emb.add_field(
            name="📌 أوامر",
            value="`تايم` `ان` `باند` `فك-الباند` `تحذير` `شيل` `سجن` `انسجن` `نك` `$rar` `ق` `ف` `مسح`",
            inline=False,
        )
        return emb

    def page_roles(self, guild: discord.Guild, conf: dict) -> discord.Embed:
        emb = _base("🎭 الرتب والستاف", C_ROLES, guild, "رتب")
        emb.description = f"سلاسل الرتب والأوتو رول\n{SEP}"
        for key, label in (
            ("role", "رتب"),
            ("staff", "ستاف صغرى"),
            ("highstaff", "ستاف عليا"),
            ("owner_chain", "اونر"),
        ):
            s = conf.get(key, conf.get("owner", {})) if key != "owner_chain" else conf.get("owner", {})
            if key == "owner_chain":
                s = conf.get("owner", {})
            roles = s.get("allowed_role_ids") or []
            emb.add_field(
                name=f"{_ok(roles)} {label}",
                value=f"المسموح: {_roles(guild, roles)}",
                inline=True,
            )
        ar = conf.get("auto_role", {})
        emb.add_field(
            name=f"{_ok(ar.get('enabled') and ar.get('role_ids'))} 🤖 Auto Role",
            value=(
                f"الحالة: `{'مفعّل' if ar.get('enabled') else 'متوقف'}`\n"
                f"الرتب: {_roles(guild, ar.get('role_ids') or [])}"
            ),
            inline=False,
        )
        emb.add_field(
            name="📌 أوامر",
            value="`رتب` `رول` `ترقية` `تخفيض` `صغرى` `عليا` `اونر` `مفصول` `/autorole` `/role-all`",
            inline=False,
        )
        return emb

    def page_security(self, guild: discord.Guild, conf: dict) -> discord.Embed:
        emb = _base("🔐 الحماية والفلتر", C_SEC, guild, "حماية")
        emb.description = f"أنظمة الحماية ومنع الإساءة\n{SEP}"
        sec = conf.get("security", {})
        emb.add_field(
            name="🛡️ Security",
            value=f"معدّ: {_ok(bool(sec))}\nاستخدم `/set-up-security`",
            inline=True,
        )
        wf = conf.get("word_filter", {})
        words = wf.get("words") or []
        emb.add_field(
            name=f"{_ok(wf.get('enabled', True))} 🚫 فلتر كلمات",
            value=(
                f"كلمات: **{len(words)}**\n"
                f"منع دعوات: `{'نعم' if wf.get('block_invites', True) else 'لا'}`\n"
                f"اللوق: {_ch(guild, wf.get('log_channel_id'))}"
            ),
            inline=True,
        )
        emb.add_field(
            name="📌 أوامر",
            value="`/set-up-security` · `/filter add|remove|list|toggle|invites|log`",
            inline=False,
        )
        return emb

    def page_xp(self, guild: discord.Guild, conf: dict) -> discord.Embed:
        emb = _base("⭐ المستويات والمهام", C_XP, guild, "XP")
        emb.description = f"نظام التفاعل والمهام\n{SEP}"
        xp = conf.get("xp", {})
        emb.add_field(
            name=f"{_ok(xp.get('enabled', True))} XP",
            value=(
                f"الحالة: `{'مفعّل' if xp.get('enabled', True) else 'متوقف'}`\n"
                f"روم الإعلان: {_ch(guild, xp.get('announce_channel_id') or xp.get('log_channel_id'))}"
            ),
            inline=True,
        )
        for tier, label in (("quest_staff", "مهام صغرى"), ("quest_highstaff", "مهام عليا"), ("quest_owner", "مهام اونر")):
            q = conf.get(tier, {})
            emb.add_field(
                name=f"{_ok(q.get('quest_channel_id'))} {label}",
                value=f"روم: {_ch(guild, q.get('quest_channel_id'))}",
                inline=True,
            )
        emb.add_field(
            name="📌 أوامر",
            value="`رانك` `توب` `$top` `اعطي-اكسبي` `صغرى` `عليا` `اونر` `/set-up-xp` `/add-xp`",
            inline=False,
        )
        return emb

    def page_voice(self, guild: discord.Guild, conf: dict) -> discord.Embed:
        emb = _base("🔊 الرومات الصوتية", C_VOICE, guild, "فويس")
        emb.description = f"نظام الرومات المؤقتة + بانل التحكم\n{SEP}"
        av = conf.get("auto_voice", {})
        emb.add_field(
            name=f"{_ok(av.get('trigger_channel_id'))} Auto Voice",
            value=(
                f"روم الزرار: {_ch(guild, av.get('trigger_channel_id'))}\n"
                f"الكاتيغوري: {_ch(guild, av.get('category_id'))}\n"
                f"قالب الاسم: `{av.get('name_template') or '—'}`\n"
                f"رومات نشطة: **{len(av.get('rooms') or {})}**"
            ),
            inline=False,
        )
        emb.add_field(
            name="📌 أوامر",
            value="`/set-up-auto-voice` · `/room-voice`",
            inline=False,
        )
        return emb

    def page_tickets(self, guild: discord.Guild, conf: dict) -> discord.Embed:
        emb = _base("🎫 التذاكر", C_TICKET, guild, "تذاكر")
        emb.description = f"نظام التذاكر الكامل\n{SEP}"
        types = conf.get("tickets", {}).get("types", {}) or {}
        open_t = conf.get("tickets", {}).get("open", {}) or {}
        emb.add_field(name="أنواع معدّة", value=f"**{len(types)}** / 15", inline=True)
        emb.add_field(name="تذاكر مفتوحة", value=f"**{len(open_t)}**", inline=True)
        if types:
            lines = []
            for num, cfg in sorted(types.items(), key=lambda x: int(x[0]))[:8]:
                lines.append(f"`#{num}` {cfg.get('name') or 'بدون اسم'}")
            emb.add_field(name="الأنواع", value="\n".join(lines) or "`—`", inline=False)
        emb.add_field(
            name="📌 أوامر",
            value="`/ticket-setup` · `/ticket-panel` · `/close` · `!close` · `!rename`",
            inline=False,
        )
        return emb

    def page_fun(self, guild: discord.Guild, conf: dict) -> discord.Embed:
        emb = _base("🎉 الفعاليات والتفاعل", C_FUN, guild, "فعاليات")
        emb.description = f"قيف أواي · عجلة · برودكاست · اقتراحات\n{SEP}"
        emb.add_field(name="🎁 قيف أواي", value="`/giveaway` · `/gend` · `/mo7_win`", inline=True)
        emb.add_field(name="🎡 عجلة", value="`/wheel-panel` · `/points` · `/add-points`", inline=True)
        emb.add_field(name="📢 برودكاست", value="`/send-broadcast-panel` · `!bc` · `!obc`", inline=True)
        sug = conf.get("suggestions", {})
        emb.add_field(
            name=f"{_ok(sug.get('channel_id'))} 💡 اقتراحات",
            value=f"الروم: {_ch(guild, sug.get('channel_id'))}\n`/suggest` · `اقتراح`",
            inline=False,
        )
        return emb

    def page_utils(self, guild: discord.Guild, conf: dict) -> discord.Embed:
        emb = _base("🧰 أدوات وإعدادات", C_UTIL, guild, "أدوات")
        emb.description = f"نسخ احتياطي · لوقات · ردود · إمبد\n{SEP}"
        emb.add_field(
            name="📦 باكاب",
            value="`/backup` تصدير\n`/back` استعادة من رابط\n(أعلى رتبة بالسيرفر)",
            inline=True,
        )
        logs = conf.get("logs", conf.get("command_log", {}))
        emb.add_field(
            name="📋 لوقات",
            value=f"`/mo7-log`\nأوامر: {_ch(guild, conf.get('command_log', {}).get('channel_id'))}",
            inline=True,
        )
        emb.add_field(
            name="💬 ردود / إمبد",
            value="`/set-up-reply`\n`/set-up-embed`",
            inline=True,
        )
        emb.add_field(
            name="📌 عام",
            value="`/dashboard` · `اعدادات` · `/help` · `اوامر`",
            inline=False,
        )
        return emb

    def page_commands(self, guild: discord.Guild) -> discord.Embed:
        emb = _base("📚 دليل الأوامر السريع", C_CMD, guild, "أوامر")
        emb.description = f"أهم الأوامر حسب الفئة\n{SEP}"
        emb.add_field(
            name="⚔️ إشراف",
            value="`باند` `فك-الباند` `تايم` `ان` `تحذير` `شيل` `سجن` `انسجن` `ق` `ف` `مسح`",
            inline=False,
        )
        emb.add_field(
            name="🎭 رتب",
            value="`رتب` `رول` `ترقية` `تخفيض` `صغرى` `عليا` `اونر` `مفصول`",
            inline=False,
        )
        emb.add_field(
            name="⭐ تفاعل",
            value="`رانك` `توب` `$top` `اقتراح`",
            inline=False,
        )
        emb.add_field(
            name="⚙️ سلاش إعداد",
            value=(
                "`/set-up-time` `/set-up-ban` `/set-up-prison` `/set-up-xp`\n"
                "`/set-up-auto-voice` `/ticket-setup` `/ticket-panel`\n"
                "`/room-voice` `/filter` `/backup` `/back` `/autorole`"
            ),
            inline=False,
        )
        return emb

    async def build_pages(self, guild: discord.Guild) -> list[discord.Embed]:
        conf = await self._conf(guild.id)
        return [
            self.page_home(guild, conf),
            self.page_moderation(guild, conf),
            self.page_roles(guild, conf),
            self.page_security(guild, conf),
            self.page_xp(guild, conf),
            self.page_voice(guild, conf),
            self.page_tickets(guild, conf),
            self.page_fun(guild, conf),
            self.page_utils(guild, conf),
            self.page_commands(guild),
        ]

    @commands.command(name="اعدادات", aliases=["داشبورد", "dashboard"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def dashboard_cmd(self, ctx: commands.Context):
        pages = await self.build_pages(ctx.guild)
        view = DashboardView(pages, ctx.author.id)
        await ctx.reply(embed=pages[0], view=view)

    @dashboard_cmd.error
    async def dashboard_cmd_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            return

    @app_commands.command(name="dashboard", description="داشبورد البوت — كل الإعدادات والأوامر")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def dashboard_slash(self, interaction: discord.Interaction):
        pages = await self.build_pages(interaction.guild)
        view = DashboardView(pages, interaction.user.id)
        await interaction.response.send_message(embed=pages[0], view=view, ephemeral=True)

    @dashboard_slash.error
    async def dashboard_slash_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            return

    @app_commands.command(name="dashboard-mo7", description="رابط الداشبورد الويب (مخفي — بس إلك)")
    @app_commands.guild_only()
    async def dashboard_mo7(self, interaction: discord.Interaction):
        """يرسل رابط داشبورد الويب بشكل ephemeral — يظهر فقط لمن نفّذ الأمر."""
        # فقط الأدمن / صاحب السيرفر / صاحب التطبيق
        is_admin = interaction.user.guild_permissions.administrator
        is_owner = interaction.user.id == interaction.guild.owner_id
        app_owner = False
        try:
            app = await interaction.client.application_info()
            if app.owner:
                app_owner = interaction.user.id == app.owner.id
            if getattr(app, "team", None) and app.team:
                app_owner = app_owner or any(m.id == interaction.user.id for m in (app.team.members or []))
        except Exception:
            pass
        if not (is_admin or is_owner or app_owner):
            await interaction.response.send_message("❌ هاد الأمر بس للإدارة.", ephemeral=True)
            return

        base = (os.getenv("DASHBOARD_PUBLIC_URL") or os.getenv("RAILWAY_PUBLIC_DOMAIN") or "").strip()
        if base and not base.startswith("http"):
            base = "https://" + base
        if not base:
            # fallback: منفذ محلي أو رسالة توضيح
            port = os.getenv("PORT") or os.getenv("WEB_PORT") or "8080"
            base = f"(حط متغير DASHBOARD_PUBLIC_URL في الاستضافة — حالياً المنفذ {port})"
            await interaction.response.send_message(
                f"🌐 **داشبورد الويب**\n"
                f"أضف المتغير `DASHBOARD_PUBLIC_URL` (رابط الاستضافة الكامل) ثم أعد التشغيل.\n"
                f"مثال: `https://your-app.up.railway.app`",
                ephemeral=True,
            )
            return

        url = base.rstrip("/")
        secret_hint = "استخدم كلمة `DASHBOARD_SECRET` عند تسجيل الدخول."
        emb = discord.Embed(
            title="🌐 داشبورد ROW",
            description=(
                f"رابط الداشبورد الخاص فيك:\n"
                f"**{url}**\n\n"
                f"🔐 {secret_hint}\n"
                f"الرسالة **مخفية** — بس إنت تشوفها."
            ),
            color=0x5865F2,
        )
        await interaction.response.send_message(embed=emb, ephemeral=True)

    @dashboard_mo7.error
    async def dashboard_mo7_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            return


class DashboardSelect(discord.ui.Select):
    def __init__(self, parent: "DashboardView"):
        self.parent_view = parent
        options = [
            discord.SelectOption(label="الرئيسية", value="0", emoji="✨", description="لمحة عامة"),
            discord.SelectOption(label="الإشراف", value="1", emoji="🛡️", description="تايم باند تحذير سجن"),
            discord.SelectOption(label="الرتب والستاف", value="2", emoji="🎭", description="رتب أوتو رول"),
            discord.SelectOption(label="الحماية والفلتر", value="3", emoji="🔐", description="سكوريتي فلتر"),
            discord.SelectOption(label="XP والمهام", value="4", emoji="⭐", description="مستويات ومهام"),
            discord.SelectOption(label="الرومات الصوتية", value="5", emoji="🔊", description="auto-voice"),
            discord.SelectOption(label="التذاكر", value="6", emoji="🎫", description="ticket system"),
            discord.SelectOption(label="الفعاليات", value="7", emoji="🎉", description="قيف عجلة برود"),
            discord.SelectOption(label="أدوات", value="8", emoji="🧰", description="باكاب لوقات"),
            discord.SelectOption(label="دليل الأوامر", value="9", emoji="📚", description="كل الأوامر"),
        ]
        super().__init__(placeholder="📂 اختر قسماً من الداشبورد...", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.page = int(self.values[0])
        self.parent_view._sync()
        await interaction.response.edit_message(embed=self.parent_view.pages[self.parent_view.page], view=self.parent_view)


class DashboardView(discord.ui.View):
    def __init__(self, pages: list, author_id: int):
        super().__init__(timeout=180)
        self.pages = pages
        self.author_id = author_id
        self.page = 0
        self.add_item(DashboardSelect(self))
        self._sync()

    def _sync(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.custom_id == "dash:prev":
                    child.disabled = self.page <= 0
                if child.custom_id == "dash:next":
                    child.disabled = self.page >= len(self.pages) - 1
                if child.custom_id == "dash:home":
                    child.disabled = self.page == 0

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ بس يلي فتح الداشبورد يقدر يتنقل.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

    @discord.ui.button(label="الرئيسية", emoji="✨", style=discord.ButtonStyle.primary, custom_id="dash:home", row=1)
    async def home_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = 0
        self._sync()
        await interaction.response.edit_message(embed=self.pages[0], view=self)

    @discord.ui.button(label="السابق", emoji="◀️", style=discord.ButtonStyle.secondary, custom_id="dash:prev", row=1)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = max(0, self.page - 1)
        self._sync()
        await interaction.response.edit_message(embed=self.pages[self.page], view=self)

    @discord.ui.button(label="التالي", emoji="▶️", style=discord.ButtonStyle.secondary, custom_id="dash:next", row=1)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = min(len(self.pages) - 1, self.page + 1)
        self._sync()
        await interaction.response.edit_message(embed=self.pages[self.page], view=self)

    @discord.ui.button(label="إغلاق", emoji="✖️", style=discord.ButtonStyle.danger, custom_id="dash:close", row=1)
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()


async def setup(bot: commands.Bot):
    await bot.add_cog(DashboardSystem(bot))
