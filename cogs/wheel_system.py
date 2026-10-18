"""عجلة الحظ + نقاط الدعوات — منقول من مشروع Node."""

from __future__ import annotations

import random

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import branded_embed
from utils.storage import Storage

SECTION = "wheel"

PRIZES = {
    "normal": [
        {"prize": "1 rob ", "chance": 40},
        {"prize": "3 rob ", "chance": 30},
        {"prize": "5 rob ", "chance": 1},
        {"prize": "1 rob ", "chance": 0.1},
        {"prize": "20 rob ", "chance": 0.00001},
    ],
    "super": [
        {"prize": "5 rob ", "chance": 40},
        {"prize": "5 rob ", "chance": 30},
        {"prize": "10 rob ", "chance": 7},
        {"prize": "5 rob ", "chance": 0.01},
        {"prize": "25 rob ", "chance": 0.00001},
        {"prize": "25 rob ", "chance": 0.00001},
        {"prize": "25 rob ", "chance": 0.00001},
    ],
}


def get_random_prize(kind: str) -> str:
    listing = PRIZES.get(kind) or PRIZES["normal"]
    total = sum(item["chance"] for item in listing)
    r = random.random() * total
    cumulative = 0.0
    for item in listing:
        cumulative += item["chance"]
        if r <= cumulative:
            return item["prize"]
    return listing[-1]["prize"]


class WheelSpinView(discord.ui.View):
    def __init__(self, cog: "WheelSystem"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="عجلة عادية",
        emoji="🎡",
        style=discord.ButtonStyle.primary,
        custom_id="wheel:normal_spin",
    )
    async def normal_spin(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_spin(interaction, "normal", cost=1)

    @discord.ui.button(
        label="عجلة سوبر",
        emoji="💫",
        style=discord.ButtonStyle.danger,
        custom_id="wheel:super_spin",
    )
    async def super_spin(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_spin(interaction, "super", cost=2)


class WheelSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._invite_cache: dict[int, dict[str, int]] = {}  # guild_id -> {code: uses}

    async def cog_load(self):
        self.bot.add_view(WheelSpinView(self))
        # تحميل كاش الدعوات
        self.bot.loop.create_task(self._warmup_invites())

    async def _warmup_invites(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            try:
                invites = await guild.invites()
                self._invite_cache[guild.id] = {i.code: i.uses or 0 for i in invites}
            except discord.Forbidden:
                self._invite_cache[guild.id] = {}

    async def _section(self, guild_id: int) -> dict:
        conf = await Storage.get_guild(guild_id)
        return conf.get(SECTION, {})

    async def _get_points(self, guild_id: int, user_id: int) -> int:
        section = await self._section(guild_id)
        return int((section.get("points") or {}).get(str(user_id), 0))

    async def _set_points(self, guild_id: int, user_id: int, value: int):
        section = await self._section(guild_id)
        points = dict(section.get("points") or {})
        points[str(user_id)] = max(0, int(value))
        await Storage.update_guild(guild_id, SECTION, {"points": points})

    async def handle_spin(self, interaction: discord.Interaction, kind: str, cost: int):
        pts = await self._get_points(interaction.guild.id, interaction.user.id)
        if pts < cost:
            await interaction.response.send_message(
                f"❌ ما عندك نقاط كافية (تحتاج {cost}، عندك {pts}).",
                ephemeral=True,
            )
            return
        await self._set_points(interaction.guild.id, interaction.user.id, pts - cost)
        prize = get_random_prize(kind)

        section = await self._section(interaction.guild.id)
        prize_room_id = section.get("prize_room_id")
        announce = f"> 🥳 مبروك {interaction.user.mention}! لقد فزت بـ **{prize}** 🏆"

        await interaction.response.send_message(
            f"🎉 مبروك {interaction.user.mention}! فزت بـ **{prize}**! 🏆"
        )
        if prize_room_id:
            ch = interaction.guild.get_channel(prize_room_id)
            if ch:
                try:
                    await ch.send(announce)
                except discord.HTTPException:
                    pass

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """نقطة دعوة عند انضمام عضو جديد عبر إنفايت."""
        if member.bot:
            return
        guild = member.guild
        section = await self._section(guild.id)
        seen = dict(section.get("seen_members") or {})
        if seen.get(str(member.id)):
            return

        inviter_id = None
        try:
            invites = await guild.invites()
            current = {i.code: i.uses or 0 for i in invites}
            previous = self._invite_cache.get(guild.id, {})
            for code, uses in current.items():
                if uses > previous.get(code, 0):
                    inv = next((i for i in invites if i.code == code), None)
                    if inv and inv.inviter:
                        inviter_id = inv.inviter.id
                    break
            self._invite_cache[guild.id] = current
        except discord.Forbidden:
            return

        seen[str(member.id)] = True
        await Storage.update_guild(guild.id, SECTION, {"seen_members": seen})

        if not inviter_id or inviter_id == member.id:
            return

        pts = await self._get_points(guild.id, inviter_id)
        await self._set_points(guild.id, inviter_id, pts + 1)

        invite_room_id = section.get("invite_room_id")
        if invite_room_id:
            ch = guild.get_channel(invite_room_id)
            if ch:
                try:
                    await ch.send(
                        f"📨 {member.mention} انضم عبر دعوة <@{inviter_id}> "
                        f"— نقاطه الآن: **{pts + 1}**"
                    )
                except discord.HTTPException:
                    pass

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        if invite.guild:
            cache = self._invite_cache.setdefault(invite.guild.id, {})
            cache[invite.code] = invite.uses or 0

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        if invite.guild:
            cache = self._invite_cache.get(invite.guild.id, {})
            cache.pop(invite.code, None)

    # ─── Commands ───

    @app_commands.command(name="rooms", description="ضبط روم الجوائز وروم تسجيل الدعوات")
    @app_commands.describe(
        prize_room="روم إعلان جوائز العجلة",
        invite_room="روم تسجيل الدعوات",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def rooms(
        self,
        interaction: discord.Interaction,
        prize_room: discord.TextChannel | None = None,
        invite_room: discord.TextChannel | None = None,
    ):
        section = await self._section(interaction.guild.id)
        updates = {}
        if prize_room:
            updates["prize_room_id"] = prize_room.id
        if invite_room:
            updates["invite_room_id"] = invite_room.id
        if updates:
            await Storage.update_guild(interaction.guild.id, SECTION, updates)
            section = {**section, **updates}

        embed = branded_embed(title="🏠 إعدادات الرومات", color=discord.Color.blurple())
        embed.add_field(
            name="🏆 روم الجوائز",
            value=f"<#{section['prize_room_id']}>" if section.get("prize_room_id") else "غير محدد",
            inline=False,
        )
        embed.add_field(
            name="📨 روم الدعوات",
            value=f"<#{section['invite_room_id']}>" if section.get("invite_room_id") else "غير محدد",
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="add-points", description="إضافة نقاط عجلة لعضو")
    @app_commands.describe(user="العضو", amount="الكمية")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def add_points(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        amount: app_commands.Range[int, 1, 10000],
    ):
        pts = await self._get_points(interaction.guild.id, user.id)
        await self._set_points(interaction.guild.id, user.id, pts + amount)
        await interaction.response.send_message(
            f"✅ تمت إضافة **{amount}** نقطة لـ {user.mention} (المجموع: {pts + amount}).",
            ephemeral=True,
        )

    @app_commands.command(name="reset-points", description="تصفير نقاط عضو")
    @app_commands.describe(user="العضو")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_points(self, interaction: discord.Interaction, user: discord.Member):
        await self._set_points(interaction.guild.id, user.id, 0)
        await interaction.response.send_message(
            f"✅ تم تصفير نقاط {user.mention}.", ephemeral=True
        )

    @app_commands.command(name="reset-all-points", description="تصفير نقاط كل الأعضاء")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_all_points(self, interaction: discord.Interaction):
        await Storage.update_guild(interaction.guild.id, SECTION, {"points": {}})
        await interaction.response.send_message("✅ تم تصفير كل النقاط.", ephemeral=True)

    @app_commands.command(name="points", description="عرض نقاطك أو نقاط عضو")
    @app_commands.describe(user="عضو (اختياري)")
    @app_commands.guild_only()
    async def points(self, interaction: discord.Interaction, user: discord.Member | None = None):
        target = user or interaction.user
        pts = await self._get_points(interaction.guild.id, target.id)
        await interaction.response.send_message(
            f"🎯 نقاط {target.mention}: **{pts}**",
            ephemeral=True,
        )

    @app_commands.command(name="wheel-panel", description="إرسال بانل عجلة الحظ")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def wheel_panel(self, interaction: discord.Interaction):
        embed = branded_embed(
            title="🎰 عجلة الحظ",
            description=(
                "لف العجلة واستخدم نقاط الدعوات!\n\n"
                "🔹 **العادية** = نقطة واحدة\n"
                "💎 **السوبر** = نقطتين\n\n"
                "تكسب نقاط لما الناس تدخل السيرفر بدعوتك."
            ),
            color=discord.Color.gold(),
        )
        await interaction.response.send_message("✅ تم إرسال البانل.", ephemeral=True)
        await interaction.channel.send(embed=embed, view=WheelSpinView(self))

    def _panel_embed(self) -> discord.Embed:
        return branded_embed(
            title="🎰 عجلة الحظ",
            description=(
                "لف العجلة واستخدم نقاط الدعوات!"
                + chr(10) + chr(10)
                + "🔹 **العادية** = نقطة واحدة"
                + chr(10)
                + "💎 **السوبر** = نقطتين"
                + chr(10) + chr(10)
                + "تكسب نقاط لما الناس تدخل السيرفر بدعوتك."
            ),
            color=discord.Color.gold(),
        )

    @commands.command(name="spin", aliases=["عجلة"])
    @commands.guild_only()
    async def spin_prefix(self, ctx: commands.Context):
        """+spin — بانل العجلة للكل."""
        await ctx.send(embed=self._panel_embed(), view=WheelSpinView(self))

    @commands.command(name="points", aliases=["نقاط"])
    @commands.guild_only()
    async def points_prefix(self, ctx: commands.Context, member: discord.Member | None = None):
        """+points — نقاطك أو نقاط عضو."""
        target = member or ctx.author
        pts = await self._get_points(ctx.guild.id, target.id)
        if target.id == ctx.author.id:
            await ctx.reply(f"🎯 نقاطك: **{pts}**", mention_author=False)
        else:
            await ctx.reply(f"🎯 نقاط {target.mention}: **{pts}**", mention_author=False)

    @rooms.error
    @add_points.error
    @reset_points.error
    @reset_all_points.error
    @wheel_panel.error
    async def _err(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            return


async def setup(bot: commands.Bot):
    await bot.add_cog(WheelSystem(bot))
