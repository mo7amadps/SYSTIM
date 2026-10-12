"""نسخة احتياطية يدوية + استعادة من رابط ملف JSON."""

from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from urllib.parse import urlparse

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import is_owner
from utils.embeds import branded_embed
from utils.storage import Storage

# حد أقصى لحجم ملف الاستعادة (5MB)
_MAX_BACKUP_BYTES = 5 * 1024 * 1024


class BackupSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="backup",
        description="إرسال نسخة JSON من إعدادات هذا السيرفر (لصاحب السيرفر فقط)",
    )
    @app_commands.guild_only()
    async def backup(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member) or not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ هذا الأمر مخصص لصاحب السيرفر فقط.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        raw = await Storage.export_guild_json(interaction.guild.id)
        # نسخة احتياطية محلية فورية أيضاً
        await Storage.backup_now()

        payload = {
            "meta": {
                "guild_id": interaction.guild.id,
                "guild_name": interaction.guild.name,
                "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "exported_by": interaction.user.id,
                "bot_id": self.bot.user.id if self.bot.user else None,
                "note": (
                    "نسخة إعدادات السيرفر. تحتوي توكنات البرودكاست المشفّرة إن وُجدت. "
                    "احفظ الملف بمكان آمن ولا تشاركه."
                ),
            },
            "guild": raw,
        }

        content = json.dumps(payload, ensure_ascii=False, indent=2)
        filename = (
            f"backup_{interaction.guild.id}_"
            f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        )
        file = discord.File(
            io.BytesIO(content.encode("utf-8")),
            filename=filename,
        )

        embed = branded_embed(
            title="📦 نسخة احتياطية",
            description=(
                f"**السيرفر:** {interaction.guild.name}\n"
                f"**الحجم:** `{len(content.encode('utf-8'))}` بايت\n\n"
                "الملف تحت — احفظه عندك. لو الاستضافة انمسحت تقدر تسترجع الإعدادات لاحقاً."
            ),
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow(),
        )

        # نحاول الإرسال بالخاص أولاً، ولو فشل نرجع المرفق هنا (ephemeral)
        dm_ok = False
        try:
            await interaction.user.send(embed=embed, file=file)
            dm_ok = True
        except (discord.Forbidden, discord.HTTPException):
            dm_ok = False

        if dm_ok:
            await interaction.followup.send(
                "✅ تم إرسال ملف النسخة الاحتياطية إلى رسائلك الخاصة.",
                ephemeral=True,
            )
        else:
            # إعادة بناء الملف لأن File يُستهلك بعد الإرسال
            file2 = discord.File(
                io.BytesIO(content.encode("utf-8")),
                filename=filename,
            )
            await interaction.followup.send(
                content=(
                    "⚠️ ما قدرت أرسل لك خاص (الـ DM مقفل؟). "
                    "هذا الملف هنا فقط لك (ephemeral):"
                ),
                embed=embed,
                file=file2,
                ephemeral=True,
            )

    @backup.error
    async def backup_error(self, interaction: discord.Interaction, error):
        if interaction.response.is_done():
            return
        try:
            await interaction.response.send_message(
                "❌ حصل خطأ أثناء إنشاء النسخة الاحتياطية.",
                ephemeral=True,
            )
        except discord.HTTPException:
            pass

    # ------------------------------------------------------------------
    # /back — استعادة من رابط JSON
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_guild_payload(data: dict, current_guild_id: int) -> dict:
        """
        يدعم صيغ النسخ المختلفة:
        1) {"meta": {...}, "guild": {...}}   ← ناتج /backup
        2) {"123456789": {...}, ...}         ← نسخة كاملة من /data/backups
        3) {...sections...}                  ← بيانات السيرفر مباشرة
        """
        if not isinstance(data, dict):
            raise ValueError("الملف ليس JSON object صالح")

        # صيغة /backup
        if "guild" in data and isinstance(data["guild"], dict):
            meta = data.get("meta") or {}
            meta_gid = meta.get("guild_id")
            if meta_gid is not None and int(meta_gid) != int(current_guild_id):
                raise ValueError(
                    f"هالنسخة لسيرفر ثاني (ID: {meta_gid}) مش لهذا السيرفر ({current_guild_id})."
                )
            return data["guild"]

        # نسخة كاملة: مفاتيحها آيديات سيرفرات
        gid = str(current_guild_id)
        if gid in data and isinstance(data[gid], dict):
            return data[gid]

        # إذا كل القيم dict وفي مفاتيح رقمية فقط → نسخة كاملة بدون هذا السيرفر
        keys = list(data.keys())
        if keys and all(str(k).isdigit() for k in keys):
            raise ValueError(
                f"الملف نسخة كاملة لسيرفرات ثانية، وما فيه بيانات لهذا السيرفر ({gid})."
            )

        # نفترض أنها بيانات السيرفر مباشرة (فيها أقسام time/role/...)
        return data

    @app_commands.command(
        name="back",
        description="استعادة إعدادات السيرفر من رابط نسخة JSON احتياطية",
    )
    @app_commands.describe(
        url="رابط مباشر لملف JSON (من /backup أو من /data/backups على الاستضافة)",
    )
    @app_commands.guild_only()
    async def back(self, interaction: discord.Interaction, url: str):
        if not isinstance(interaction.user, discord.Member) or not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ هذا الأمر مخصص لصاحب السيرفر فقط.",
                ephemeral=True,
            )
            return

        url = (url or "").strip().strip("<>")
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            await interaction.response.send_message(
                "❌ رابط غير صالح. لازم يبدأ بـ `https://` ويكون رابط مباشر للملف.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        await interaction.followup.send(
                            f"❌ ما قدرت أحمل الملف (HTTP {resp.status}). "
                            "تأكد إن الرابط مباشر ويعمل بدون تسجيل دخول.",
                            ephemeral=True,
                        )
                        return

                    # حماية من ملفات ضخمة
                    content_length = resp.headers.get("Content-Length")
                    if content_length and int(content_length) > _MAX_BACKUP_BYTES:
                        await interaction.followup.send(
                            "❌ الملف أكبر من المسموح (5MB).",
                            ephemeral=True,
                        )
                        return

                    raw_bytes = await resp.read()
                    if len(raw_bytes) > _MAX_BACKUP_BYTES:
                        await interaction.followup.send(
                            "❌ الملف أكبر من المسموح (5MB).",
                            ephemeral=True,
                        )
                        return

            try:
                text = raw_bytes.decode("utf-8")
                data = json.loads(text)
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                await interaction.followup.send(
                    f"❌ الملف مش JSON صالح: `{e}`",
                    ephemeral=True,
                )
                return

            guild_payload = self._extract_guild_payload(data, interaction.guild.id)
            if not guild_payload:
                await interaction.followup.send(
                    "❌ النسخة فاضية — ما في إعدادات تُسترجع.",
                    ephemeral=True,
                )
                return

            sections = await Storage.restore_guild_data(
                interaction.guild.id, guild_payload
            )

            embed = branded_embed(
                title="✅ تمت الاستعادة",
                description=(
                    f"تم استبدال إعدادات **{interaction.guild.name}** بمحتوى النسخة.\n\n"
                    f"**عدد الأقسام المسترجعة:** `{sections}`\n"
                    f"**المصدر:** `{parsed.netloc}`\n\n"
                    "كل الإعدادات الحالية انمسحت واتبدلت بهالنسخة "
                    "(رتب، تذاكر، برودكاست، XP، أوتو رول...)."
                ),
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except ValueError as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)
        except aiohttp.ClientError as e:
            await interaction.followup.send(
                f"❌ فشل التحميل من الرابط: `{e}`",
                ephemeral=True,
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ خطأ غير متوقع أثناء الاستعادة: `{e}`",
                ephemeral=True,
            )

    @back.error
    async def back_error(self, interaction: discord.Interaction, error):
        if interaction.response.is_done():
            return
        try:
            await interaction.response.send_message(
                "❌ حصل خطأ أثناء الاستعادة.",
                ephemeral=True,
            )
        except discord.HTTPException:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(BackupSystem(bot))
