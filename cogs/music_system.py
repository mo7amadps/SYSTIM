"""نظام موسيقى بسيط: !شغل · !وقف · بانل تحكم."""
from __future__ import annotations

import asyncio
import logging
import re
from collections import deque
from typing import Optional

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)

# yt-dlp اختياري — إذا ما انثبت يطلع تنبيه
try:
    import yt_dlp
    HAS_YTDL = True
except ImportError:
    HAS_YTDL = False

YTDL_OPTS = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch1",
    "noplaylist": True,
    "source_address": "0.0.0.0",
}
FFMPEG_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


class GuildPlayer:
    def __init__(self, guild_id: int):
        self.guild_id = guild_id
        self.queue: deque = deque()
        self.voice: Optional[discord.VoiceClient] = None
        self.current: Optional[dict] = None
        self.channel: Optional[discord.TextChannel] = None
        self.panel_message: Optional[discord.Message] = None
        self.loop_one = False


class MusicControlView(discord.ui.View):
    def __init__(self, cog: "MusicSystem", guild_id: int):
        super().__init__(timeout=600)
        self.cog = cog
        self.guild_id = guild_id

    async def _player(self, interaction: discord.Interaction) -> GuildPlayer:
        gid = interaction.guild.id if interaction.guild else self.guild_id
        return self.cog.get_player(gid)

    @discord.ui.button(emoji="⏸️", style=discord.ButtonStyle.secondary, custom_id="music:pause")
    async def pause_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        p = await self._player(interaction)
        if not p.voice or not p.voice.is_connected():
            return await interaction.response.send_message("البوت مو بالفويس.", ephemeral=True)
        if p.voice.is_playing():
            p.voice.pause()
            await interaction.response.send_message("⏸️ تم الإيقاف المؤقت.", ephemeral=True)
        elif p.voice.is_paused():
            p.voice.resume()
            await interaction.response.send_message("▶️ تم الاستكمال.", ephemeral=True)
        else:
            await interaction.response.send_message("ما في شي شغال.", ephemeral=True)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.primary, custom_id="music:skip")
    async def skip_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        p = await self._player(interaction)
        if p.voice and (p.voice.is_playing() or p.voice.is_paused()):
            p.voice.stop()
            await interaction.response.send_message("⏭️ تخطي.", ephemeral=True)
        else:
            await interaction.response.send_message("ما في أغنية للتخطي.", ephemeral=True)

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, custom_id="music:stop")
    async def stop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        p = await self._player(interaction)
        p.queue.clear()
        if p.voice and (p.voice.is_playing() or p.voice.is_paused()):
            p.voice.stop()
        await interaction.response.send_message("⏹️ توقف ومسحت القائمة.", ephemeral=True)

    @discord.ui.button(emoji="📃", style=discord.ButtonStyle.secondary, custom_id="music:queue")
    async def queue_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        p = await self._player(interaction)
        lines = []
        if p.current:
            lines.append(f"**الآن:** {p.current.get('title', '?')}")
        for i, item in enumerate(list(p.queue)[:10], 1):
            lines.append(f"`{i}.` {item.get('title', '?')}")
        if not lines:
            lines = ["القائمة فاضية."]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)


class MusicSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.players: dict[int, GuildPlayer] = {}

    def get_player(self, guild_id: int) -> GuildPlayer:
        if guild_id not in self.players:
            self.players[guild_id] = GuildPlayer(guild_id)
        return self.players[guild_id]

    async def _extract(self, query: str) -> Optional[dict]:
        if not HAS_YTDL:
            return None
        loop = asyncio.get_event_loop()

        def run():
            with yt_dlp.YoutubeDL(YTDL_OPTS) as ydl:
                info = ydl.extract_info(query, download=False)
                if info is None:
                    return None
                if "entries" in info:
                    info = next((e for e in info["entries"] if e), None)
                if not info:
                    return None
                url = info.get("url")
                title = info.get("title") or query
                duration = info.get("duration")
                webpage = info.get("webpage_url") or info.get("original_url") or query
                return {
                    "url": url,
                    "title": title,
                    "duration": duration,
                    "webpage": webpage,
                }

        try:
            return await loop.run_in_executor(None, run)
        except Exception:
            logger.exception("yt-dlp extract failed")
            return None

    def _fmt_dur(self, sec) -> str:
        try:
            sec = int(sec)
            return f"{sec // 60:02d}:{sec % 60:02d}"
        except Exception:
            return "??:??"

    def _panel_embed(self, p: GuildPlayer) -> discord.Embed:
        if p.current:
            title = p.current.get("title", "—")
            dur = self._fmt_dur(p.current.get("duration"))
            req = p.current.get("requester", "?")
            desc = (
                f"**{title}**" + chr(10)
                + f"`[{dur}]` · Requested by {req}" + chr(10)
                + f"القائمة: **{len(p.queue)}** أغنية"
            )
        else:
            desc = "ما في أغنية حالياً. اكتب `!شغل اسم الأغنية`"
        emb = discord.Embed(
            title="🎵 مشغّل الموسيقى",
            description=desc,
            color=discord.Color.from_rgb(88, 101, 242),
        )
        emb.set_footer(text="⏸️ إيقاف مؤقت · ⏭️ تخطي · ⏹️ وقف · 📃 القائمة")
        return emb

    async def _ensure_voice(self, ctx: commands.Context) -> Optional[discord.VoiceClient]:
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.reply("ادخل فويس أولاً.")
            return None
        channel = ctx.author.voice.channel
        p = self.get_player(ctx.guild.id)
        if p.voice and p.voice.is_connected():
            if p.voice.channel.id != channel.id:
                await p.voice.move_to(channel)
            return p.voice
        try:
            p.voice = await channel.connect(reconnect=True, timeout=15)
        except Exception as e:
            await ctx.reply(f"ما قدرت أدخل الفويس: `{e}`")
            return None
        return p.voice

    async def _play_next(self, guild_id: int):
        p = self.get_player(guild_id)
        if not p.voice or not p.voice.is_connected():
            p.current = None
            return
        if p.loop_one and p.current:
            item = p.current
        elif p.queue:
            item = p.queue.popleft()
        else:
            p.current = None
            try:
                if p.panel_message:
                    await p.panel_message.edit(embed=self._panel_embed(p), view=MusicControlView(self, guild_id))
            except Exception:
                pass
            return
        p.current = item
        try:
            source = discord.FFmpegPCMAudio(item["url"], **FFMPEG_OPTS)
            # Volume can be wrapped if needed
            def after_play(err):
                if err:
                    logger.warning("player error: %s", err)
                fut = asyncio.run_coroutine_threadsafe(self._play_next(guild_id), self.bot.loop)
                try:
                    fut.result(timeout=30)
                except Exception:
                    pass

            p.voice.play(source, after=after_play)
        except Exception:
            logger.exception("play failed")
            await self._play_next(guild_id)
            return
        try:
            if p.panel_message:
                await p.panel_message.edit(embed=self._panel_embed(p), view=MusicControlView(self, guild_id))
            elif p.channel:
                p.panel_message = await p.channel.send(
                    embed=self._panel_embed(p), view=MusicControlView(self, guild_id)
                )
        except Exception:
            pass

    @commands.command(name="شغل", aliases=["play", "p"])
    async def play_cmd(self, ctx: commands.Context, *, query: str = None):
        if not HAS_YTDL:
            return await ctx.reply(
                "نظام الأغاني يحتاج تثبيت `yt-dlp` و `PyNaCl` ووجود **ffmpeg** على الاستضافة."
            )
        if not query:
            return await ctx.reply("اكتب: `!شغل اسم الأغنية`")
        vc = await self._ensure_voice(ctx)
        if not vc:
            return
        msg = await ctx.reply(f"🔎 جاري البحث عن: **{query[:80]}** …")
        info = await self._extract(query)
        if not info or not info.get("url"):
            return await msg.edit(content="❌ ما لقيت نتيجة.")
        p = self.get_player(ctx.guild.id)
        p.channel = ctx.channel
        item = {
            **info,
            "requester": ctx.author.mention,
        }
        p.queue.append(item)
        if not p.voice.is_playing() and not p.voice.is_paused():
            await msg.edit(content=f"✅ تشغيل: **{info['title']}**")
            await self._play_next(ctx.guild.id)
        else:
            await msg.edit(
                content=f"✅ انضافت للطابور: **{info['title']}** (#{len(p.queue)})"
            )
            try:
                if p.panel_message:
                    await p.panel_message.edit(
                        embed=self._panel_embed(p), view=MusicControlView(self, ctx.guild.id)
                    )
            except Exception:
                pass

    @commands.command(name="وقف", aliases=["stop"])
    async def stop_cmd(self, ctx: commands.Context):
        p = self.get_player(ctx.guild.id)
        p.queue.clear()
        if p.voice and p.voice.is_connected():
            if p.voice.is_playing() or p.voice.is_paused():
                p.voice.stop()
            await p.voice.disconnect()
            p.voice = None
        p.current = None
        await ctx.reply("⏹️ تم الإيقاف ومغادرة الفويس.")

    @commands.command(name="تخطي", aliases=["skip", "s"])
    async def skip_cmd(self, ctx: commands.Context):
        p = self.get_player(ctx.guild.id)
        if p.voice and (p.voice.is_playing() or p.voice.is_paused()):
            p.voice.stop()
            await ctx.reply("⏭️ تخطي.")
        else:
            await ctx.reply("ما في أغنية.")

    @commands.command(name="موسيقى", aliases=["music", "np"])
    async def panel_cmd(self, ctx: commands.Context):
        p = self.get_player(ctx.guild.id)
        p.channel = ctx.channel
        p.panel_message = await ctx.send(
            embed=self._panel_embed(p), view=MusicControlView(self, ctx.guild.id)
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(MusicSystem(bot))
