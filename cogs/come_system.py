"""
نظام الاستدعاء — /set-up-come + أمر استدعاء
"""
from __future__ import annotations

import time

import discord
from discord import app_commands
from discord.ext import commands

from utils.storage import Storage
from utils.embeds import branded_embed
from utils.checks import has_any_role

SECTION = "come"
COOLDOWN_SECONDS = 5 * 60  # 5 دقائق بين نفس المستدعي والمستدعى

# (guild_id, caller_id, target_id) -> monotonic expiry
_cooldowns: dict[tuple[int, int, int], float] = {}


class ComeSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _cfg(self, guild_id: int) -> dict:
        conf = await Storage.get_guild(guild_id)
        return conf.get(SECTION) or {}

    def _on_cooldown(self, guild_id: int, caller_id: int, target_id: int) -> int:
        key = (guild_id, caller_id, target_id)
        exp = _cooldowns.get(key, 0)
        now = time.monotonic()
        if exp > now:
            return int(exp - now)
        return 0

    def _set_cooldown(self, guild_id: int, caller_id: int, target_id: int):
        _cooldowns[(guild_id, caller_id, target_id)] = time.monotonic() + COOLDOWN_SECONDS

    @app_commands.command(
        name="set-up-come",
        description="إعداد نظام الاستدعاء (الرتب المسموحة + قناة اللوق)",
    )
    @app_commands.describe(
        allowed_role="رتبة تقدر تستخدم أمر الاستدعاء (تقدر تعيد الأمر لزيادة رتب)",
        log_channel="قناة لوق الاستدعاء",
        allowed_role_2="رتبة إضافية",
        allowed_role_3="رتبة إضافية",
        allowed_role_4="رتبة إضافية",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_come(
        self,
        interaction: discord.Interaction,
        allowed_role: discord.Role,
        log_channel: discord.TextChannel,
        allowed_role_2: discord.Role = None,
        allowed_role_3: discord.Role = None,
        allowed_role_4: discord.Role = None,
    ):
        roles = [allowed_role]
        for r in (allowed_role_2, allowed_role_3, allowed_role_4):
            if r and r not in roles:
                roles.append(r)
        role_ids = [r.id for r in roles]
        await Storage.update_guild(
            interaction.guild.id,
            SECTION,
            {"allowed_role_ids": role_ids, "log_channel_id": log_channel.id},
        )
        emb = branded_embed(title="✅ تم إعداد الاستدعاء", color=discord.Color.green())
        emb.add_field(
            name="الرتب المسموحة",
            value=", ".join(r.mention for r in roles),
            inline=False,
        )
        emb.add_field(name="اللوق", value=log_channel.mention, inline=True)
        emb.add_field(
            name="الاستخدام",
            value="`استدعاء @العضو` أو `/come @العضو`",
            inline=False,
        )
        emb.set_footer(text="كولداون 5 دقائق لنفس الشخص")
        await interaction.response.send_message(embed=emb, ephemeral=True)

    async def _do_come(
        self,
        guild: discord.Guild,
        channel: discord.abc.Messageable,
        caller: discord.Member,
        target: discord.Member,
        respond,
    ):
        cfg = await self._cfg(guild.id)
        role_ids = cfg.get("allowed_role_ids") or []
        if not role_ids:
            await respond("❌ نظام الاستدعاء مو مضبوط. استخدم `/set-up-come` أول.", ephemeral=True)
            return
        if not has_any_role(caller, role_ids) and not caller.guild_permissions.administrator:
            await respond("❌ ما عندك صلاحية الاستدعاء.", ephemeral=True)
            return
        if target.bot:
            await respond("❌ ما تقدر تستدعي بوت.", ephemeral=True)
            return
        if target.id == caller.id:
            await respond("❌ ما تقدر تستدعي نفسك.", ephemeral=True)
            return

        left = self._on_cooldown(guild.id, caller.id, target.id)
        if left > 0:
            m, s = divmod(left, 60)
            await respond(
                f"⏳ استدعيت {target.mention} قبل شوي. باقي **{m}د {s}ث**.",
                ephemeral=True,
            )
            return

        room = getattr(channel, "mention", str(channel))
        try:
            dm = discord.Embed(
                title="📢 تم استدعاؤك",
                description=(
                    f"تم استدعاؤك من قبل {caller.mention}\n"
                    f"**السيرفر:** {guild.name}\n"
                    f"**الروم:** {room}"
                ),
                color=discord.Color.orange(),
                timestamp=discord.utils.utcnow(),
            )
            dm.set_footer(text=str(guild.name))
            if guild.icon:
                dm.set_thumbnail(url=guild.icon.url)
            await target.send(embed=dm)
            dm_ok = True
        except (discord.Forbidden, discord.HTTPException):
            dm_ok = False

        self._set_cooldown(guild.id, caller.id, target.id)

        if dm_ok:
            await respond(f"✅ تم استدعاء {target.mention} (انرسلت له رسالة خاص).", ephemeral=True)
        else:
            await respond(
                f"⚠️ ما قدرت أرسل خاص لـ {target.mention} (الخاص مقفول).",
                ephemeral=True,
            )

        log_id = cfg.get("log_channel_id")
        if log_id:
            log_ch = guild.get_channel(int(log_id))
            if log_ch:
                emb = branded_embed(
                    title="📢 استدعاء",
                    color=discord.Color.orange(),
                    timestamp=discord.utils.utcnow(),
                )
                emb.add_field(name="المستدعي", value=f"{caller.mention} (`{caller.id}`)", inline=True)
                emb.add_field(name="المستدعى", value=f"{target.mention} (`{target.id}`)", inline=True)
                emb.add_field(name="الروم", value=room, inline=True)
                emb.add_field(name="الخاص", value="تم ✅" if dm_ok else "فشل ❌", inline=True)
                try:
                    await log_ch.send(embed=emb)
                except discord.HTTPException:
                    pass

    @app_commands.command(name="come", description="استدعاء عضو (يرسل له خاص)")
    @app_commands.describe(member="العضو المراد استدعاؤه")
    @app_commands.guild_only()
    async def come_slash(self, interaction: discord.Interaction, member: discord.Member):
        async def resp(content=None, *, ephemeral=False, embed=None):
            if interaction.response.is_done():
                await interaction.followup.send(content=content, ephemeral=ephemeral, embed=embed)
            else:
                await interaction.response.send_message(content=content, ephemeral=ephemeral, embed=embed)

        await self._do_come(
            interaction.guild,
            interaction.channel,
            interaction.user,
            member,
            resp,
        )

    @commands.command(name="استدعاء")
    @commands.guild_only()
    async def come_prefix(self, ctx: commands.Context, member: discord.Member = None):
        if member is None:
            await ctx.reply("استخدم: `استدعاء @العضو`", mention_author=False)
            return

        async def resp(content=None, *, ephemeral=False, embed=None):
            # prefix: ephemeral ignored
            await ctx.reply(content or "", embed=embed, mention_author=False)

        await self._do_come(ctx.guild, ctx.channel, ctx.author, member, resp)

    @setup_come.error
    @come_slash.error
    async def _err(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("لازم صلاحية Administrator.", ephemeral=True)
            return
        if not interaction.response.is_done():
            await interaction.response.send_message(f"خطأ: {error}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ComeSystem(bot))
