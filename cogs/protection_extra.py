"""
حماية إضافية:
- Anti-Spam: تكرار نفس الرسالة → تايم أوت (حد ومدة قابلان للضبط)
- Anti-Link: تعزيز منع روابط الدعوة + إعداد
- /hide-all و /show-all: إخفاء/إظهار كل الرومات (@everyone)
- تنبيه DM للأونر + أصحاب أعلى رتبة بالسيرفر
"""

from __future__ import annotations

import re
import time
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

from utils.storage import Storage
from utils.embeds import branded_embed
from utils.checks import has_any_role

SECTION = "security"

# روابط دعوة أوسع من الفلتر الأساسي
_INVITE_RE = re.compile(
    r"(?:https?://)?(?:www\.)?"
    r"(?:"
    r"discord\.gg|"
    r"discord(?:app)?\.com/invite|"
    r"discord\.me|"
    r"discord\.io|"
    r"discord\.li|"
    r"discordapp\.com/invite|"
    r"invite\.gg"
    r")/[a-zA-Z0-9-]+",
    re.IGNORECASE,
)

# أي رابط عام (عند تفعيل منع كل الروابط)
_URL_RE = re.compile(
    r"https?://[^\s<>\[\]()]+|www\.[^\s<>\[\]()]+",
    re.IGNORECASE,
)

# امتدادات ملفات خطرة + اختصارات روابط
_DANGEROUS_EXTS = (
    ".exe", ".bat", ".cmd", ".msi", ".scr", ".com", ".pif",
    ".vbs", ".vbe", ".js", ".jse", ".wsf", ".wsh",
    ".ps1", ".psm1", ".psd1",
    ".apk", ".ipa", ".dmg", ".pkg",
    ".jar", ".hta", ".cpl", ".msc",
    ".lnk", ".url", ".reg", ".iso", ".img",
)
_SHORTENER_RE = re.compile(
    r"(?:https?://)?(?:www\.)?"
    r"(?:bit\.ly|tinyurl\.com|t\.co|goo\.gl|ow\.ly|is\.gd|cutt\.ly|rebrand\.ly|shorturl\.at|rb\.gy)/[^\s]+",
    re.IGNORECASE,
)


def _top_role(guild: discord.Guild) -> discord.Role | None:
    candidates = [r for r in guild.roles if not r.is_default() and not r.managed]
    if not candidates:
        return None
    return max(candidates, key=lambda r: r.position)


async def alert_leadership(
    guild: discord.Guild,
    title: str,
    description: str,
    color: int = 0xED4245,
    bot: commands.Bot | None = None,
):
    """يرسل DM للأونر (الشيب) + أعضاء أعلى رتبة حقيقية بالسيرفر."""
    emb = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=discord.utils.utcnow(),
    )
    emb.set_footer(text=f"{guild.name} · حماية ROW")
    if guild.icon:
        emb.set_thumbnail(url=guild.icon.url)

    targets: set[int] = set()

    # الأونر / صاحب السيرفر
    if guild.owner_id:
        targets.add(guild.owner_id)

    top = _top_role(guild)
    if top:
        for m in top.members[:15]:
            if not m.bot:
                targets.add(m.id)

    client = bot
    for uid in targets:
        user = guild.get_member(uid)
        if user is None and client is not None:
            try:
                user = await client.fetch_user(uid)
            except discord.HTTPException:
                user = None
        if user is None:
            continue
        try:
            await user.send(embed=emb)
        except (discord.Forbidden, discord.HTTPException):
            pass


class ProtectionExtra(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # (guild_id, user_id) -> {"content": str, "count": int, "last": float}
        self._spam_track: dict[tuple[int, int], dict] = {}

    async def _sec(self, guild_id: int) -> dict:
        conf = await Storage.get_guild(guild_id)
        return conf.get(SECTION, {})

    async def _anti_spam_cfg(self, guild_id: int) -> dict:
        sec = await self._sec(guild_id)
        return sec.get("anti_spam") or {}

    async def _anti_link_cfg(self, guild_id: int) -> dict:
        sec = await self._sec(guild_id)
        return sec.get("anti_link") or {}

    def _is_mod(self, member: discord.Member) -> bool:
        if member.guild_permissions.administrator or member.guild_permissions.manage_guild:
            return True
        if member.id == member.guild.owner_id:
            return True
        return False

    async def _exempt(self, member: discord.Member, cfg: dict) -> bool:
        if self._is_mod(member):
            return True
        exempt = cfg.get("exempt_role_ids") or []
        return has_any_role(member, exempt)

    # ───────────── Anti-Spam ─────────────

    @app_commands.command(name="set-up-antispam", description="إعداد مكافحة تكرار نفس الرسالة (سبام)")
    @app_commands.describe(
        max_repeats="كم مرة نفس الرسالة قبل التايم (مثال: 2 أو 3)",
        timeout_minutes="مدة التايم بالدقائق",
        enabled="تشغيل أو إيقاف",
        log_channel="قناة اللوق (اختياري)",
        exempt_role="رتبة مستثناة (اختياري)",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_antispam(
        self,
        interaction: discord.Interaction,
        max_repeats: app_commands.Range[int, 2, 10] = 3,
        timeout_minutes: app_commands.Range[int, 1, 10080] = 10,
        enabled: bool = True,
        log_channel: discord.TextChannel | None = None,
        exempt_role: discord.Role | None = None,
    ):
        updates = {
            "enabled": enabled,
            "max_repeats": int(max_repeats),
            "timeout_seconds": int(timeout_minutes) * 60,
        }
        if log_channel:
            updates["log_channel_id"] = log_channel.id
        if exempt_role:
            updates["exempt_role_ids"] = [exempt_role.id]

        conf = await Storage.get_guild(interaction.guild.id)
        sec = dict(conf.get(SECTION, {}) or {})
        spam = dict(sec.get("anti_spam") or {})
        spam.update(updates)
        sec["anti_spam"] = spam
        await Storage.update_guild(interaction.guild.id, SECTION, sec)

        await interaction.response.send_message(
            embed=branded_embed(
                title="✅ تم إعداد Anti-Spam",
                color=discord.Color.green(),
            ).add_field(name="الحالة", value="مفعّل" if enabled else "متوقف")
            .add_field(name="عدد التكرار", value=str(max_repeats))
            .add_field(name="مدة التايم", value=f"{timeout_minutes} دقيقة"),
            ephemeral=True,
        )

    # ───────────── Anti-Link ─────────────

    @app_commands.command(name="set-up-antilink", description="إعداد منع روابط دعوة ديسكورد")
    @app_commands.describe(
        enabled="تشغيل أو إيقاف",
        timeout_minutes="تايم أوت بعد المخالفة (0 = حذف فقط بدون تايم)",
        log_channel="قناة اللوق",
        exempt_role="رتبة مستثناة",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_antilink(
        self,
        interaction: discord.Interaction,
        enabled: bool = True,
        timeout_minutes: app_commands.Range[int, 0, 10080] = 5,
        log_channel: discord.TextChannel | None = None,
        exempt_role: discord.Role | None = None,
    ):
        updates = {
            "enabled": enabled,
            "timeout_seconds": int(timeout_minutes) * 60,
        }
        if log_channel:
            updates["log_channel_id"] = log_channel.id
        if exempt_role:
            updates["exempt_role_ids"] = [exempt_role.id]

        conf = await Storage.get_guild(interaction.guild.id)
        sec = dict(conf.get(SECTION, {}) or {})
        link = dict(sec.get("anti_link") or {})
        link.update(updates)
        sec["anti_link"] = link
        # مزامنة مع فلتر الكلمات الحالي
        await Storage.update_guild(interaction.guild.id, SECTION, sec)
        await Storage.update_guild(interaction.guild.id, "word_filter", {"block_invites": enabled})

        await interaction.response.send_message(
            embed=branded_embed(title="✅ تم إعداد Anti-Link", color=discord.Color.green())
            .add_field(name="الحالة", value="مفعّل" if enabled else "متوقف")
            .add_field(
                name="التايم",
                value=f"{timeout_minutes} دقيقة" if timeout_minutes else "حذف فقط",
            ),
            ephemeral=True,
        )

    # ───────────── hide-all / show-all ─────────────

    @app_commands.command(name="hide-all", description="إخفاء كل الرومات عن @everyone (Lockdown)")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def hide_all(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        snapshot: dict[str, dict] = {}
        hidden = 0
        failed = 0

        for ch in guild.channels:
            if not isinstance(ch, (discord.TextChannel, discord.VoiceChannel, discord.ForumChannel, discord.StageChannel)):
                continue
            try:
                ow = ch.overwrites_for(guild.default_role)
                snapshot[str(ch.id)] = {
                    "view_channel": ow.view_channel,
                    "connect": getattr(ow, "connect", None),
                    "send_messages": getattr(ow, "send_messages", None),
                }
                # إخفاء
                kwargs = {"view_channel": False}
                if isinstance(ch, (discord.VoiceChannel, discord.StageChannel)):
                    kwargs["connect"] = False
                else:
                    kwargs["send_messages"] = False
                await ch.set_permissions(guild.default_role, **kwargs, reason=f"hide-all بواسطة {interaction.user}")
                hidden += 1
            except (discord.Forbidden, discord.HTTPException):
                failed += 1

        conf = await Storage.get_guild(guild.id)
        sec = dict(conf.get(SECTION, {}) or {})
        sec["lockdown_snapshot"] = snapshot
        sec["lockdown_active"] = True
        await Storage.update_guild(guild.id, SECTION, sec)

        await interaction.followup.send(
            f"🔒 **hide-all**\nتم إخفاء **{hidden}** روم.\nفشل: **{failed}**",
            ephemeral=True,
        )

    @app_commands.command(name="show-all", description="إظهار الرومات وإرجاع صلاحيات @everyone (إلغاء Lockdown)")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def show_all(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        conf = await Storage.get_guild(guild.id)
        sec = dict(conf.get(SECTION, {}) or {})
        snapshot = dict(sec.get("lockdown_snapshot") or {})

        restored = 0
        failed = 0

        if snapshot:
            for cid, perms in snapshot.items():
                ch = guild.get_channel(int(cid))
                if not ch:
                    continue
                try:
                    kwargs = {}
                    for k, v in perms.items():
                        if v is not None:
                            kwargs[k] = v
                    # إذا كانت None بالأصل، نرجّعها None (وراثة)
                    for k in ("view_channel", "send_messages", "connect"):
                        if k in perms and perms[k] is None:
                            kwargs[k] = None
                    if not kwargs:
                        kwargs = {"view_channel": None, "send_messages": None}
                    await ch.set_permissions(guild.default_role, **kwargs, reason=f"show-all بواسطة {interaction.user}")
                    restored += 1
                except (discord.Forbidden, discord.HTTPException):
                    failed += 1
        else:
            # ما في لقطة — نرجّع view للوراثة على كل الرومات
            for ch in guild.channels:
                if not isinstance(ch, (discord.TextChannel, discord.VoiceChannel, discord.ForumChannel, discord.StageChannel)):
                    continue
                try:
                    await ch.set_permissions(
                        guild.default_role,
                        view_channel=None,
                        send_messages=None,
                        connect=None,
                        reason=f"show-all بواسطة {interaction.user}",
                    )
                    restored += 1
                except (discord.Forbidden, discord.HTTPException):
                    failed += 1

        sec["lockdown_snapshot"] = {}
        sec["lockdown_active"] = False
        await Storage.update_guild(guild.id, SECTION, sec)

        await interaction.followup.send(
            f"🔓 **show-all**\nتم استرجاع **{restored}** روم.\nفشل: **{failed}**",
            ephemeral=True,
        )

    # ───────────── مراقب الرسائل ─────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return
        if not isinstance(message.author, discord.Member):
            return

        # ملفات خطرة
        await self._check_dangerous_files(message)
        # Anti-Link
        await self._check_antilink(message)
        # Anti-Spam
        await self._check_antispam(message)

    async def _check_dangerous_files(self, message: discord.Message):
        """حذف مرفقات وملفات خطرة + روابط اختصار مشبوهة."""
        if not isinstance(message.author, discord.Member):
            return
        if self._is_mod(message.author):
            return

        reasons: list[str] = []

        for att in message.attachments:
            name = (att.filename or "").lower()
            for ext in _DANGEROUS_EXTS:
                if name.endswith(ext):
                    reasons.append(f"مرفق خطر: `{att.filename}`")
                    break

        content = message.content or ""
        # روابط تنتهي بامتداد خطر
        for ext in _DANGEROUS_EXTS:
            if re.search(rf"https?://\S+{re.escape(ext)}(?:\s|$|\?)", content, re.I):
                reasons.append(f"رابط ملف خطر (`{ext}`)")
                break
        if _SHORTENER_RE.search(content):
            reasons.append("رابط اختصار مشبوه (bit.ly وغيره)")

        if not reasons:
            return

        try:
            await message.delete()
        except (discord.Forbidden, discord.HTTPException):
            return

        reason_txt = " · ".join(reasons)
        try:
            await message.channel.send(
                f"⚠️ {message.author.mention} رسالتك انحذفت — **ملف/رابط خطر**: {reason_txt}",
                delete_after=10,
            )
        except discord.HTTPException:
            pass

        conf = await Storage.get_guild(message.guild.id)
        log_id = (conf.get(SECTION) or {}).get("anti_link", {}).get("log_channel_id")
        await self._log_channel(
            message.guild,
            log_id,
            "☠️ ملف/رابط خطر",
            f"**العضو:** {message.author.mention}\n**القناة:** {message.channel.mention}\n**السبب:** {reason_txt}",
        )

    async def _check_antilink(self, message: discord.Message):
        cfg = await self._anti_link_cfg(message.guild.id)
        # إذا ما اتعيّن anti_link، نعتمد على word_filter.block_invites كافتراضي مفعّل
        if cfg:
            if not cfg.get("enabled", True):
                return
        else:
            conf = await Storage.get_guild(message.guild.id)
            if not conf.get("word_filter", {}).get("block_invites", True):
                return
            cfg = {"enabled": True, "timeout_seconds": 0, "exempt_role_ids": [], "block_invites": True}

        if await self._exempt(message.author, cfg):
            return

        content = message.content or ""
        hit = None
        block_invites = cfg.get("block_invites", True)
        block_all = cfg.get("block_all_links", False)
        if block_invites and _INVITE_RE.search(content):
            hit = "رابط دعوة ديسكورد"
        elif block_all and _URL_RE.search(content):
            hit = "رابط ممنوع"
        elif _SHORTENER_RE.search(content):
            hit = "رابط اختصار مشبوه"

        if not hit:
            return

        try:
            await message.delete()
        except (discord.Forbidden, discord.HTTPException):
            return

        timeout_sec = int(cfg.get("timeout_seconds") or 0)
        timed = False
        if timeout_sec > 0 and message.guild.me.guild_permissions.moderate_members:
            try:
                until = discord.utils.utcnow() + timedelta(seconds=timeout_sec)
                await message.author.timeout(until, reason=f"Anti-Link: {hit}")
                timed = True
            except (discord.Forbidden, discord.HTTPException):
                pass

        try:
            extra = f" + تايم {timeout_sec // 60}د" if timed else ""
            await message.channel.send(
                f"⚠️ {message.author.mention} ممنوع: **{hit}**.{extra}",
                delete_after=8,
            )
        except discord.HTTPException:
            pass

        await self._log_channel(
            message.guild,
            cfg.get("log_channel_id"),
            "🔗 Anti-Link",
            f"**العضو:** {message.author.mention}\n**القناة:** {message.channel.mention}\n"
            f"**السبب:** {hit}\n**تايم:** {'نعم' if timed else 'لا'}\n**المحتوى:** `{content[:200]}`",
        )

    async def _check_antispam(self, message: discord.Message):
        cfg = await self._anti_spam_cfg(message.guild.id)
        if not cfg.get("enabled", True):
            return
        if await self._exempt(message.author, cfg):
            return

        content = (message.content or "").strip()
        key = (message.guild.id, message.author.id)
        now = time.monotonic()
        state = self._spam_track.get(key) or {}

        # 1) سبام سريع: رسائل كثيرة خلال نافذة زمنية قصيرة
        window = float(cfg.get("window_seconds") or 8)
        max_messages = int(cfg.get("max_messages") or 6)
        times = [x for x in (state.get("times") or []) if now - x < window]
        times.append(now)
        state["times"] = times
        rapid_hit = len(times) >= max_messages

        # 2) تكرار نفس النص خلال 45 ثانية
        max_repeats = int(cfg.get("max_repeats") or 3)
        if content and len(content) >= 2:
            if state.get("content") == content and now - state.get("last", 0) < 45:
                state["count"] = int(state.get("count", 1)) + 1
            else:
                state["count"] = 1
                state["content"] = content
            state["last"] = now
        else:
            state["count"] = int(state.get("count") or 0)

        self._spam_track[key] = state
        repeat_hit = bool(content and len(content) >= 2 and state["count"] >= max_repeats)

        if not rapid_hit and not repeat_hit:
            return

        # وصل للحد → حذف + تايم
        self._spam_track.pop(key, None)
        timeout_sec = int(cfg.get("timeout_seconds") or 600)
        reason = "رسائل سريعة" if rapid_hit else f"تكرار نفس الرسالة {max_repeats} مرات"

        try:
            await message.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass

        timed = False
        if message.guild.me.guild_permissions.moderate_members:
            try:
                until = discord.utils.utcnow() + timedelta(seconds=timeout_sec)
                await message.author.timeout(until, reason=f"Anti-Spam: {reason}")
                timed = True
            except (discord.Forbidden, discord.HTTPException):
                pass

        mins = max(1, timeout_sec // 60)
        try:
            await message.channel.send(
                f"🔇 {message.author.mention} تايم **{mins}د** بسبب السبام ({reason}).",
                delete_after=10,
            )
        except discord.HTTPException:
            pass

        await self._log_channel(
            message.guild,
            cfg.get("log_channel_id"),
            "🔇 Anti-Spam",
            f"**العضو:** {message.author.mention}\n**القناة:** {message.channel.mention}\n"
            f"**السبب:** {reason}\n**التايم:** {mins}د\n**النص:** `{(content or '')[:200]}`",
        )

    async def _log_channel(self, guild: discord.Guild, channel_id, title: str, desc: str):
        if not channel_id:
            return
        ch = guild.get_channel(int(channel_id))
        if not ch:
            return
        try:
            await ch.send(
                embed=discord.Embed(title=title, description=desc, color=0xED4245, timestamp=discord.utils.utcnow())
            )
        except discord.HTTPException:
            pass

    @setup_antispam.error
    @setup_antilink.error
    @hide_all.error
    @show_all.error
    async def _err(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            return


async def setup(bot: commands.Bot):
    await bot.add_cog(ProtectionExtra(bot))
