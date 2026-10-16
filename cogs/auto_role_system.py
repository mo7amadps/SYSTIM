"""رتب تلقائية عند دخول الأعضاء (وإختيارياً البوتات)."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import branded_embed
from utils.storage import Storage

SECTION = "auto_role"


class AutoRoleSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _get_config(self, guild_id: int) -> dict:
        conf = await Storage.get_guild(guild_id)
        return conf.get(SECTION, {})

    async def _log(
        self,
        guild: discord.Guild,
        member: discord.Member,
        given: list[discord.Role],
        failed: list[str],
    ):
        conf = await self._get_config(guild.id)
        channel_id = conf.get("log_channel_id")
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if not channel:
            return
        embed = branded_embed(
            title="🎭 Auto Role",
            color=discord.Color.green() if given else discord.Color.orange(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(
            name=str(member),
            icon_url=member.display_avatar.url if member.display_avatar else None,
        )
        embed.add_field(name="العضو", value=member.mention, inline=True)
        embed.add_field(
            name="الرتب المعطاة",
            value=", ".join(r.mention for r in given) if given else "لا شيء",
            inline=False,
        )
        if failed:
            embed.add_field(
                name="فشل",
                value="\n".join(failed[:5]),
                inline=False,
            )
        try:
            await channel.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            pass

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        conf = await self._get_config(member.guild.id)
        if not conf.get("enabled"):
            return

        role_ids = conf.get("bot_role_ids") if member.bot else conf.get("role_ids")
        role_ids = list(role_ids or [])
        if not role_ids:
            return

        me = member.guild.me
        if not me or not me.guild_permissions.manage_roles:
            return

        given: list[discord.Role] = []
        failed: list[str] = []
        for rid in role_ids:
            role = member.guild.get_role(int(rid))
            if not role:
                failed.append(f"رتبة غير موجودة (`{rid}`)")
                continue
            if role.managed:
                failed.append(f"{role.mention} مُدارة من تكامل — ما بتنعطى")
                continue
            if role >= me.top_role:
                failed.append(f"{role.mention} أعلى من رتبة البوت أو تساويها")
                continue
            if role in member.roles:
                continue
            try:
                await member.add_roles(role, reason="Auto-role عند الدخول")
                given.append(role)
            except discord.Forbidden:
                failed.append(f"ما في صلاحية لإعطاء {role.mention}")
            except discord.HTTPException:
                failed.append(f"فشل HTTP مع {role.mention}")

        if given or failed:
            await self._log(member.guild, member, given, failed)

    # ---------- /auto-role ----------

    auto_role = app_commands.Group(
        name="auto-role",
        description="إدارة الرتب التلقائية عند دخول الأعضاء",
        guild_only=True,
    )

    @auto_role.command(name="setup", description="تفعيل الرتب التلقائية وتحديدها")
    @app_commands.describe(
        role="رتبة تُعطى للأعضاء الجدد (تقدر تعيد الأمر لإضافة أكثر من رتبة)",
        bot_role="رتبة اختيارية للبوتات عند دخولها",
        log_channel="قناة لوق اختيارية",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def setup(
        self,
        interaction: discord.Interaction,
        role: discord.Role | None = None,
        bot_role: discord.Role | None = None,
        log_channel: discord.TextChannel | None = None,
    ):
        conf = await self._get_config(interaction.guild.id)
        role_ids = list(conf.get("role_ids") or [])
        bot_role_ids = list(conf.get("bot_role_ids") or [])

        if role:
            if role.is_default():
                await interaction.response.send_message(
                    "❌ ما فيك تستخدم @everyone.", ephemeral=True
                )
                return
            if role.managed:
                await interaction.response.send_message(
                    "❌ الرتبة مُدارة من بوت/تكامل وما بتنعطى يدوياً.", ephemeral=True
                )
                return
            if role.id not in role_ids:
                role_ids.append(role.id)

        if bot_role:
            if bot_role.is_default() or bot_role.managed:
                await interaction.response.send_message(
                    "❌ رتبة البوتات غير صالحة.", ephemeral=True
                )
                return
            if bot_role.id not in bot_role_ids:
                bot_role_ids.append(bot_role.id)

        updates = {
            "enabled": True,
            "role_ids": role_ids,
            "bot_role_ids": bot_role_ids,
        }
        if log_channel:
            updates["log_channel_id"] = log_channel.id

        await Storage.update_guild(interaction.guild.id, SECTION, updates)

        embed = branded_embed(
            title="✅ الرتب التلقائية",
            color=discord.Color.green(),
        )
        embed.add_field(
            name="رتب الأعضاء",
            value=", ".join(f"<@&{i}>" for i in role_ids) if role_ids else "لا شيء بعد",
            inline=False,
        )
        embed.add_field(
            name="رتب البوتات",
            value=", ".join(f"<@&{i}>" for i in bot_role_ids) if bot_role_ids else "لا شيء",
            inline=False,
        )
        if log_channel or conf.get("log_channel_id"):
            cid = log_channel.id if log_channel else conf.get("log_channel_id")
            embed.add_field(name="اللوق", value=f"<#{cid}>", inline=False)
        embed.add_field(
            name="أوامر مفيدة",
            value=(
                "`/auto-role add` إضافة رتبة\n"
                "`/auto-role remove` إزالة رتبة\n"
                "`/auto-role list` عرض الحالي\n"
                "`/auto-role disable` إيقاف النظام"
            ),
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @auto_role.command(name="add", description="إضافة رتبة للقائمة التلقائية")
    @app_commands.describe(
        role="الرتبة",
        for_bots="هل الرتبة للبوتات؟ (افتراضي: للأعضاء)",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def add(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        for_bots: bool = False,
    ):
        if role.is_default() or role.managed:
            await interaction.response.send_message(
                "❌ رتبة غير صالحة (@everyone أو مُدارة).", ephemeral=True
            )
            return
        conf = await self._get_config(interaction.guild.id)
        key = "bot_role_ids" if for_bots else "role_ids"
        ids = list(conf.get(key) or [])
        if role.id in ids:
            await interaction.response.send_message(
                f"⚠️ {role.mention} موجودة أصلاً بالقائمة.", ephemeral=True
            )
            return
        ids.append(role.id)
        await Storage.update_guild(
            interaction.guild.id,
            SECTION,
            {key: ids, "enabled": True},
        )
        await interaction.response.send_message(
            f"✅ تمت إضافة {role.mention} "
            f"{'(للبوتات)' if for_bots else '(للأعضاء)'}.",
            ephemeral=True,
        )

    @auto_role.command(name="remove", description="إزالة رتبة من القائمة التلقائية")
    @app_commands.describe(
        role="الرتبة",
        for_bots="هل الرتبة من قائمة البوتات؟",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def remove(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        for_bots: bool = False,
    ):
        conf = await self._get_config(interaction.guild.id)
        key = "bot_role_ids" if for_bots else "role_ids"
        ids = list(conf.get(key) or [])
        if role.id not in ids:
            await interaction.response.send_message(
                f"⚠️ {role.mention} مش موجودة بالقائمة.", ephemeral=True
            )
            return
        ids = [i for i in ids if i != role.id]
        await Storage.update_guild(interaction.guild.id, SECTION, {key: ids})
        await interaction.response.send_message(
            f"✅ تمت إزالة {role.mention} من القائمة.", ephemeral=True
        )

    @auto_role.command(name="list", description="عرض إعدادات الرتب التلقائية")
    @app_commands.checks.has_permissions(administrator=True)
    async def list_roles(self, interaction: discord.Interaction):
        conf = await self._get_config(interaction.guild.id)
        enabled = conf.get("enabled")
        role_ids = conf.get("role_ids") or []
        bot_role_ids = conf.get("bot_role_ids") or []
        log_id = conf.get("log_channel_id")

        embed = branded_embed(
            title="🎭 الرتب التلقائية",
            color=discord.Color.green() if enabled else discord.Color.greyple(),
        )
        embed.add_field(
            name="الحالة",
            value="🟢 مفعّل" if enabled else "🔴 متوقف",
            inline=True,
        )
        embed.add_field(
            name="رتب الأعضاء",
            value=", ".join(f"<@&{i}>" for i in role_ids) if role_ids else "—",
            inline=False,
        )
        embed.add_field(
            name="رتب البوتات",
            value=", ".join(f"<@&{i}>" for i in bot_role_ids) if bot_role_ids else "—",
            inline=False,
        )
        embed.add_field(
            name="اللوق",
            value=f"<#{log_id}>" if log_id else "—",
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @auto_role.command(name="disable", description="إيقاف الرتب التلقائية")
    @app_commands.checks.has_permissions(administrator=True)
    async def disable(self, interaction: discord.Interaction):
        await Storage.update_guild(interaction.guild.id, SECTION, {"enabled": False})
        await interaction.response.send_message(
            "🛑 تم إيقاف الرتب التلقائية. القوائم محفوظة — فعّلها من `/auto-role setup`.",
            ephemeral=True,
        )

    @auto_role.command(name="enable", description="تشغيل الرتب التلقائية")
    @app_commands.checks.has_permissions(administrator=True)
    async def enable(self, interaction: discord.Interaction):
        conf = await self._get_config(interaction.guild.id)
        if not (conf.get("role_ids") or conf.get("bot_role_ids")):
            await interaction.response.send_message(
                "❌ ما في رتب محفوظة. استخدم `/auto-role setup` أو `/auto-role add` أولاً.",
                ephemeral=True,
            )
            return
        await Storage.update_guild(interaction.guild.id, SECTION, {"enabled": True})
        await interaction.response.send_message(
            "🟢 تم تفعيل الرتب التلقائية.", ephemeral=True
        )

    # أمر مباشر أسهل: /autorole @رتبة
    @app_commands.command(
        name="autorole",
        description="تعيين رتبة تلقائية للأعضاء الجدد (اختصار سريع)",
    )
    @app_commands.describe(
        role="الرتبة اللي بتنعطى تلقائياً لما حد يدخل",
        log_channel="قناة لوق اختيارية",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def autorole_quick(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        log_channel: discord.TextChannel | None = None,
    ):
        if role.is_default():
            await interaction.response.send_message(
                "❌ ما فيك تستخدم @everyone.", ephemeral=True
            )
            return
        if role.managed:
            await interaction.response.send_message(
                "❌ الرتبة مُدارة من بوت/تكامل.", ephemeral=True
            )
            return

        me = interaction.guild.me
        if me and role >= me.top_role:
            await interaction.response.send_message(
                "❌ رتبة البوت لازم تكون **أعلى** من الرتبة التلقائية بترتيب الرتب.",
                ephemeral=True,
            )
            return

        updates = {
            "enabled": True,
            "role_ids": [role.id],
        }
        if log_channel:
            updates["log_channel_id"] = log_channel.id
        await Storage.update_guild(interaction.guild.id, SECTION, updates)

        embed = branded_embed(
            title="✅ تم تفعيل Auto Role",
            description=(
                f"**الرتبة:** {role.mention}\n"
                "────────────────────\n"
                "كل عضو جديد رح ياخذ هالرتبة تلقائياً.\n\n"
                "**تأكد من:**\n"
                "• رتبة البوت أعلى من هالرتبة\n"
                "• صلاحية Manage Roles للبوت\n"
                "• Members Intent مفعّل"
            ),
            color=discord.Color.green(),
            timestamp=True,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @setup.error
    @add.error
    @remove.error
    @list_roles.error
    @disable.error
    @enable.error
    @autorole_quick.error
    async def _perm_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            return


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoRoleSystem(bot))
