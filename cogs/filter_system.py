"""فلتر كلمات وروابط دعوة — إدارة قائمة ومنع التكرار."""

from __future__ import annotations

import re

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import branded_embed
from utils.storage import Storage

SECTION = "word_filter"

# روابط دعوة ديسكورد الشائعة
_INVITE_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:discord\.gg|discord(?:app)?\.com/invite)/[a-zA-Z0-9-]+",
    re.IGNORECASE,
)


def _normalize_word(word: str) -> str:
    return " ".join((word or "").strip().lower().split())


class FilterSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _cfg(self, guild_id: int) -> dict:
        conf = await Storage.get_guild(guild_id)
        return conf.get(SECTION, {})

    async def _log(self, guild: discord.Guild, embed: discord.Embed):
        cfg = await self._cfg(guild.id)
        channel_id = cfg.get("log_channel_id")
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if not channel:
            return
        try:
            await channel.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            pass

    # ---------- إدارة القائمة ----------

    filter_group = app_commands.Group(
        name="filter",
        description="إدارة فلتر الكلمات الممنوعة",
        guild_only=True,
    )

    @filter_group.command(name="add", description="إضافة كلمة أو عبارة للقائمة الممنوعة")
    @app_commands.describe(word="الكلمة أو العبارة الممنوعة")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def filter_add(self, interaction: discord.Interaction, word: str):
        normalized = _normalize_word(word)
        if not normalized or len(normalized) < 2:
            await interaction.response.send_message(
                "❌ الكلمة قصيرة جداً (حد أدنى حرفين).", ephemeral=True
            )
            return
        if len(normalized) > 100:
            await interaction.response.send_message(
                "❌ الكلمة طويلة جداً (حد أقصى 100 حرف).", ephemeral=True
            )
            return

        cfg = await self._cfg(interaction.guild.id)
        words = list(cfg.get("words") or [])
        if normalized in words:
            await interaction.response.send_message(
                f"⚠️ هالكلمة **مكررة** وموجودة بالقائمة أصلاً: `{normalized}`",
                ephemeral=True,
            )
            return

        words.append(normalized)
        await Storage.update_guild(
            interaction.guild.id,
            SECTION,
            {"words": words, "enabled": True},
        )

        embed = branded_embed(
            title="✅ تمت إضافة كلمة للفلتر",
            description=(
                f"**الكلمة:** `{normalized}`\n"
                f"**عدد الكلمات الآن:** `{len(words)}`\n"
                "────────────────────\n"
                "استخدم `/filter list` لعرض القائمة كاملة."
            ),
            color=discord.Color.green(),
            timestamp=True,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @filter_group.command(name="remove", description="إزالة كلمة من القائمة الممنوعة")
    @app_commands.describe(word="الكلمة المراد إزالتها")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def filter_remove(self, interaction: discord.Interaction, word: str):
        normalized = _normalize_word(word)
        cfg = await self._cfg(interaction.guild.id)
        words = list(cfg.get("words") or [])
        if normalized not in words:
            await interaction.response.send_message(
                f"❌ الكلمة `{normalized}` مش موجودة بالقائمة.",
                ephemeral=True,
            )
            return
        words = [w for w in words if w != normalized]
        await Storage.update_guild(interaction.guild.id, SECTION, {"words": words})
        await interaction.response.send_message(
            f"🗑️ تم حذف `{normalized}` من الفلتر. المتبقي: **{len(words)}**",
            ephemeral=True,
        )

    @filter_group.command(name="list", description="عرض كل الكلمات الممنوعة")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def filter_list(self, interaction: discord.Interaction):
        cfg = await self._cfg(interaction.guild.id)
        words = list(cfg.get("words") or [])
        enabled = cfg.get("enabled", True)
        block_invites = cfg.get("block_invites", True)

        status = "🟢 مفعّل" if enabled else "🔴 متوقف"
        inv = "🟢 مفعّل" if block_invites else "🔴 متوقف"
        embed = branded_embed(
            title="🛡️ قائمة فلتر الكلمات",
            description=(
                f"**الحالة:** {status}\n"
                f"**منع الدعوات:** {inv}\n"
                f"**عدد الكلمات:** `{len(words)}`\n"
                "────────────────────"
            ),
            color=discord.Color.blurple(),
            timestamp=True,
        )

        if not words:
            embed.description += "\nالقائمة فارغة. أضف كلمات بـ `/filter add`."
        else:
            # نجزّئ لو طويلة
            chunks = []
            line = ""
            for i, w in enumerate(words, 1):
                piece = f"`{w}`"
                if len(line) + len(piece) > 900:
                    chunks.append(line)
                    line = piece
                else:
                    line = f"{line} · {piece}" if line else piece
            if line:
                chunks.append(line)
            for idx, chunk in enumerate(chunks[:5], 1):
                embed.add_field(
                    name=f"الكلمات ({idx})" if len(chunks) > 1 else "الكلمات",
                    value=chunk,
                    inline=False,
                )
            if len(chunks) > 5:
                embed.set_footer(text=f"وأكثر... المجموع {len(words)}")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @filter_group.command(name="toggle", description="تشغيل أو إيقاف فلتر الكلمات")
    @app_commands.checks.has_permissions(administrator=True)
    async def filter_toggle(self, interaction: discord.Interaction):
        cfg = await self._cfg(interaction.guild.id)
        new_state = not cfg.get("enabled", True)
        await Storage.update_guild(
            interaction.guild.id, SECTION, {"enabled": new_state}
        )
        await interaction.response.send_message(
            "🟢 تم تفعيل الفلتر." if new_state else "🔴 تم إيقاف الفلتر.",
            ephemeral=True,
        )

    @filter_group.command(name="invites", description="تشغيل/إيقاف منع روابط دعوة ديسكورد")
    @app_commands.describe(enabled="true = منع الدعوات")
    @app_commands.checks.has_permissions(administrator=True)
    async def filter_invites(self, interaction: discord.Interaction, enabled: bool):
        await Storage.update_guild(
            interaction.guild.id, SECTION, {"block_invites": enabled}
        )
        await interaction.response.send_message(
            f"{'🟢' if enabled else '🔴'} منع دعوات ديسكورد: **{'مفعّل' if enabled else 'متوقف'}**",
            ephemeral=True,
        )

    @filter_group.command(name="log", description="تحديد قناة لوق الفلتر")
    @app_commands.describe(channel="قناة اللوق")
    @app_commands.checks.has_permissions(administrator=True)
    async def filter_log(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ):
        await Storage.update_guild(
            interaction.guild.id, SECTION, {"log_channel_id": channel.id}
        )
        await interaction.response.send_message(
            f"✅ لوق الفلتر: {channel.mention}", ephemeral=True
        )

    @filter_group.command(name="clear", description="مسح كل الكلمات الممنوعة")
    @app_commands.checks.has_permissions(administrator=True)
    async def filter_clear(self, interaction: discord.Interaction):
        await Storage.update_guild(interaction.guild.id, SECTION, {"words": []})
        await interaction.response.send_message(
            "🗑️ تم مسح كل الكلمات من الفلتر.", ephemeral=True
        )

    # ---------- المراقبة ----------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        if not isinstance(message.author, discord.Member):
            return
        # الأدمن واللي عندهم Manage Messages ما ينفلتروا
        if message.author.guild_permissions.manage_messages:
            return

        cfg = await self._cfg(message.guild.id)
        if not cfg.get("enabled", True):
            return

        content = message.content or ""
        content_l = content.lower()
        hit = None

        # كلمات ممنوعة
        for word in cfg.get("words") or []:
            if word and word in content_l:
                hit = f"كلمة ممنوعة: `{word}`"
                break

        # دعوات
        if not hit and cfg.get("block_invites", True) and _INVITE_RE.search(content):
            hit = "رابط دعوة ديسكورد"

        if not hit:
            return

        try:
            await message.delete()
        except (discord.Forbidden, discord.HTTPException):
            return

        try:
            warn = await message.channel.send(
                f"⚠️ {message.author.mention} رسالتك انحذفت — {hit}.",
                delete_after=6,
            )
        except discord.HTTPException:
            pass

        embed = branded_embed(
            title="🛡️ فلتر — رسالة محذوفة",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="العضو", value=message.author.mention, inline=True)
        embed.add_field(name="القناة", value=message.channel.mention, inline=True)
        embed.add_field(name="السبب", value=hit, inline=False)
        snippet = content[:300] + ("…" if len(content) > 300 else "")
        if snippet:
            embed.add_field(name="المحتوى", value=snippet, inline=False)
        await self._log(message.guild, embed)

    @filter_add.error
    @filter_remove.error
    @filter_list.error
    @filter_toggle.error
    @filter_invites.error
    @filter_log.error
    @filter_clear.error
    async def _err(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            return


async def setup(bot: commands.Bot):
    await bot.add_cog(FilterSystem(bot))
