"""نظام القيف أواي — منقول من مشروع Node."""

from __future__ import annotations

import asyncio
import random
import time
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.embeds import branded_embed
from utils.storage import Storage

SECTION = "giveaways"
JOIN_PREFIX = "giveaway:join:"
DEFAULT_IMAGE = None


def parse_duration(text: str) -> Optional[int]:
    text = (text or "").lower().strip()
    try:
        if text.endswith("s"):
            seconds = int(text[:-1])
        elif text.endswith("m"):
            seconds = int(text[:-1]) * 60
        elif text.endswith("h"):
            seconds = int(text[:-1]) * 3600
        elif text.endswith("d"):
            seconds = int(text[:-1]) * 86400
        else:
            return None
    except ValueError:
        return None
    if seconds < 10:
        return None
    return seconds


def build_active_embed(g: dict) -> discord.Embed:
    end_ts = int(g["end_time"])
    count = len(g.get("participants") or [])
    embed = discord.Embed(
        title=f"🎁 {g['prize']}",
        description=(
            "### ✨ Giveaway Started ✨\n\n"
            "🎊 **اضغط الزر تحت للمشاركة!**\n\n"
            f"⏰ **ينتهي:** <t:{end_ts}:R>\n"
            f"👥 **المشاركون:** `{count}`   |   🏆 **الفائزون:** `{g['winners']}`\n"
            f"📅 **الوقت:** <t:{end_ts}:F>\n\n"
            f"👑 **المنظم:** <@{g['host']}>\n\n"
            "━━━━━━━━━━━━━━━━━━━━"
        ),
        color=0xFF6B00,
    )
    embed.timestamp = discord.utils.utcnow()
    embed.set_footer(text="ROW")
    if g.get("image"):
        embed.set_image(url=g["image"])
    if g.get("thumbnail"):
        embed.set_thumbnail(url=g["thumbnail"])
    return embed


def build_ended_embed(g: dict, winners_mentions: str, count: int) -> discord.Embed:
    embed = discord.Embed(
        title=f"🎁 {g['prize']}",
        description=(
            "### 🏆 Giveaway Ended 🏆\n\n"
            f"🎉 **الفائز/ون:** {winners_mentions}\n\n"
            f"👑 **المنظم:** <@{g['host']}>\n\n"
            "━━━━━━━━━━━━━━━━━━━━"
        ),
        color=0xFF6B00,
    )
    embed.timestamp = discord.utils.utcnow()
    embed.set_footer(text=f"{count} participants  •  ROW")
    return embed


class GiveawayCreateModal(discord.ui.Modal, title="إنشاء قيف أواي"):
    duration = discord.ui.TextInput(
        label="المدة (مثال: 30m / 2h / 1d)",
        placeholder="30m",
        required=True,
        max_length=10,
    )
    winners = discord.ui.TextInput(
        label="عدد الفائزين",
        placeholder="1",
        required=True,
        max_length=3,
    )
    prize = discord.ui.TextInput(
        label="الجائزة",
        required=True,
        max_length=200,
    )
    image = discord.ui.TextInput(
        label="رابط صورة (اختياري)",
        required=False,
        max_length=300,
    )
    thumbnail = discord.ui.TextInput(
        label="رابط صورة مصغّرة (اختياري)",
        required=False,
        max_length=300,
    )

    def __init__(self, cog: "GiveawaySystem"):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        seconds = parse_duration(str(self.duration))
        if not seconds:
            await interaction.response.send_message(
                "❌ صيغة المدة غلط. مثال: `30m` أو `2h` أو `1d` (حد أدنى 10 ثواني).",
                ephemeral=True,
            )
            return
        try:
            winners_count = int(str(self.winners).strip())
            if winners_count < 1:
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                "❌ عدد الفائزين لازم رقم أكبر من 0.", ephemeral=True
            )
            return

        prize = str(self.prize).strip()
        image = (str(self.image).strip() if self.image.value else "") or None
        thumbnail = (str(self.thumbnail).strip() if self.thumbnail.value else "") or None
        end_time = time.time() + seconds

        draft = {
            "prize": prize,
            "channel_id": interaction.channel.id,
            "end_time": end_time,
            "winners": winners_count,
            "participants": [],
            "host": interaction.user.id,
            "image": image,
            "thumbnail": thumbnail,
            "forced_winners": [],
            "guild_id": interaction.guild.id,
        }

        embed = build_active_embed(draft)
        await interaction.response.send_message(embed=embed, view=GiveawayJoinView(self.cog))
        msg = await interaction.original_response()

        draft_id = str(msg.id)
        section = await Storage.get_guild(interaction.guild.id)
        active = dict(section.get(SECTION, {}).get("active", {}))
        active[draft_id] = draft
        await Storage.update_guild(interaction.guild.id, SECTION, {"active": active})


class GiveawayJoinView(discord.ui.View):
    def __init__(self, cog: "GiveawaySystem"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="دخول السحب",
        emoji="🎁",
        style=discord.ButtonStyle.success,
        custom_id="giveaway:join",
    )
    async def join_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        gid = str(interaction.message.id)

        section = await Storage.get_guild(interaction.guild.id)
        active = dict(section.get(SECTION, {}).get("active", {}))
        g = active.get(gid)
        if not g:
            await interaction.response.send_message("❌ هذا القيف أواي منتهي أو غير موجود.", ephemeral=True)
            return
        if time.time() >= g["end_time"]:
            await interaction.response.send_message("❌ القيف أواي خلص.", ephemeral=True)
            return

        uid = interaction.user.id
        parts = list(g.get("participants") or [])
        if uid in parts:
            parts.remove(uid)
            g["participants"] = parts
            active[gid] = g
            await Storage.update_guild(interaction.guild.id, SECTION, {"active": active})
            await interaction.response.send_message("تم سحب مشاركتك.", ephemeral=True)
        else:
            parts.append(uid)
            g["participants"] = parts
            active[gid] = g
            await Storage.update_guild(interaction.guild.id, SECTION, {"active": active})
            await interaction.response.send_message(
                f"✅ تم تسجيلك! المشاركون الآن: **{len(parts)}**", ephemeral=True
            )

        try:
            await interaction.message.edit(embed=build_active_embed(g))
        except discord.HTTPException:
            pass


class GiveawaySystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        # استعادة أزرار القيف أوايات النشطة
        # نضيف view عام يستقبل أي custom_id بالـ prefix عبر Persistent
        self.bot.add_view(GiveawayJoinView(self))
        if not self.end_loop.is_running():
            self.end_loop.start()

    async def cog_unload(self):
        self.end_loop.cancel()

    @tasks.loop(seconds=20)
    async def end_loop(self):
        # نمر على كل السيرفرات في الكاش — نخزن guild_id داخل كل giveaway
        await self.bot.wait_until_ready()
        now = time.time()
        # نجمع من كل guild عبر storage - نحتاج طريقة. نستخدم guilds cache
        for guild in list(self.bot.guilds):
            try:
                section = await Storage.get_guild(guild.id)
                active = dict(section.get(SECTION, {}).get("active", {}))
                to_end = [mid for mid, g in active.items() if now >= g.get("end_time", 0)]
                for mid in to_end:
                    await self.end_giveaway(guild.id, mid)
            except Exception:
                continue

    @end_loop.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

    async def end_giveaway(self, guild_id: int, message_id: str):
        section = await Storage.get_guild(guild_id)
        active = dict(section.get(SECTION, {}).get("active", {}))
        g = active.pop(message_id, None)
        if not g:
            return
        await Storage.update_guild(guild_id, SECTION, {"active": active})

        participants = list(g.get("participants") or [])
        forced = [u for u in (g.get("forced_winners") or []) if u in participants or True]
        winners_count = int(g.get("winners") or 1)

        winners: list[int] = []
        # forced أولاً
        for uid in forced:
            if uid not in winners:
                winners.append(uid)
            if len(winners) >= winners_count:
                break
        pool = [u for u in participants if u not in winners]
        random.shuffle(pool)
        while len(winners) < winners_count and pool:
            winners.append(pool.pop())

        if winners:
            mentions = ", ".join(f"<@{u}>" for u in winners)
        else:
            mentions = "ما في فائز (ما في مشاركين)"

        guild = self.bot.get_guild(guild_id)
        channel = guild.get_channel(g["channel_id"]) if guild else None
        if channel:
            try:
                msg = await channel.fetch_message(int(message_id))
                await msg.edit(
                    embed=build_ended_embed(g, mentions, len(participants)),
                    view=None,
                )
                await channel.send(f"🏆 خلص القيف أواي **{g['prize']}**!\nالفائز/ون: {mentions}")
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass

    @app_commands.command(name="giveaway", description="بدء قيف أواي جديد")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def giveaway(self, interaction: discord.Interaction):
        await interaction.response.send_modal(GiveawayCreateModal(self))

    @app_commands.command(name="gend", description="إنهاء قيف أواي يدوياً")
    @app_commands.describe(message_id="آيدي رسالة القيف أواي")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def gend(self, interaction: discord.Interaction, message_id: str):
        section = await Storage.get_guild(interaction.guild.id)
        active = section.get(SECTION, {}).get("active", {})
        if message_id not in active:
            await interaction.response.send_message(
                "❌ ما لقيت قيف أواي بهذا الآيدي.", ephemeral=True
            )
            return
        await interaction.response.send_message("✅ جاري إنهاء القيف أواي...", ephemeral=True)
        await self.end_giveaway(interaction.guild.id, message_id)

    @app_commands.command(name="mo7_win", description="تعيين فائز سري لقيف أواي")
    @app_commands.describe(
        message_id="آيدي رسالة القيف أواي",
        user="العضو اللي راح يفوز",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def mo7_win(
        self,
        interaction: discord.Interaction,
        message_id: str,
        user: discord.Member,
    ):
        section = await Storage.get_guild(interaction.guild.id)
        active = dict(section.get(SECTION, {}).get("active", {}))
        g = active.get(message_id)
        if not g:
            await interaction.response.send_message("❌ ما لقيت القيف أواي.", ephemeral=True)
            return
        forced = list(g.get("forced_winners") or [])
        if len(forced) >= int(g.get("winners") or 1):
            await interaction.response.send_message(
                f"❌ وصلت للحد الأقصى ({g['winners']} فائزين).", ephemeral=True
            )
            return
        parts = list(g.get("participants") or [])
        if user.id not in parts:
            parts.append(user.id)
        if user.id not in forced:
            forced.append(user.id)
        g["participants"] = parts
        g["forced_winners"] = forced
        active[message_id] = g
        await Storage.update_guild(interaction.guild.id, SECTION, {"active": active})
        await interaction.response.send_message(
            f"✅ تم تعيين {user.mention} كفائز سري ({len(forced)}/{g['winners']}).",
            ephemeral=True,
        )

    @giveaway.error
    @gend.error
    @mo7_win.error
    async def _err(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            return


async def setup(bot: commands.Bot):
    await bot.add_cog(GiveawaySystem(bot))
