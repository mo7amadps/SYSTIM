"""نظام اقتراحات: /suggest + تصويت + موافقة/رفض من الستاف."""

from __future__ import annotations

from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import is_owner
from utils.embeds import branded_embed
from utils.storage import Storage

SECTION = "suggestions"
STATUS_COLORS = {
    "pending": discord.Color.blurple(),
    "approved": discord.Color.green(),
    "rejected": discord.Color.red(),
}
STATUS_LABELS = {
    "pending": "⏳ قيد المراجعة",
    "approved": "✅ تمت الموافقة",
    "rejected": "❌ مرفوض",
}


def _suggestion_embed(
    guild: discord.Guild,
    item: dict,
    suggestion_id: str,
    author: discord.abc.User | None = None,
) -> discord.Embed:
    status = item.get("status", "pending")
    up = len(item.get("up_voters", []))
    down = len(item.get("down_voters", []))
    author_mention = f"<@{item['author_id']}>"
    if author:
        author_mention = author.mention

    embed = branded_embed(
        title=f"📝 اقتراح #{suggestion_id}",
        description=item.get("content", "—"),
        color=STATUS_COLORS.get(status, discord.Color.blurple()),
        timestamp=discord.utils.utcnow(),
    )
    embed.add_field(name="من", value=author_mention, inline=True)
    embed.add_field(name="الحالة", value=STATUS_LABELS.get(status, status), inline=True)
    embed.add_field(
        name="التصويت",
        value=f"👍 `{up}` 👎 `{down}`",
        inline=True,
    )
    if item.get("staff_note"):
        embed.add_field(name="ملاحظة الإدارة", value=item["staff_note"], inline=False)
    if item.get("reviewed_by"):
        embed.add_field(
            name="راجعه",
            value=f"<@{item['reviewed_by']}>",
            inline=True,
        )
    embed.set_footer(text=f"ID: {suggestion_id} • discord.gg/row")
    return embed


class SuggestionVoteView(discord.ui.View):
    """أزرار دائمة للتصويت والمراجعة."""

    def __init__(self, cog: "SuggestionSystem"):
        super().__init__(timeout=None)
        self.cog = cog

    async def _get_item(
        self, interaction: discord.Interaction
    ) -> tuple[str | None, dict | None]:
        conf = await Storage.get_guild(interaction.guild.id)
        items = conf.get(SECTION, {}).get("items", {})
        # نبحث عن الاقتراح المرتبط برسالة الزر
        message_id = interaction.message.id if interaction.message else None
        for sid, item in items.items():
            if item.get("message_id") == message_id:
                return sid, item
        return None, None

    async def _save_item(self, guild_id: int, suggestion_id: str, item: dict):
        conf = await Storage.get_guild(guild_id)
        items = dict(conf.get(SECTION, {}).get("items", {}))
        items[suggestion_id] = item
        await Storage.update_guild(guild_id, SECTION, {"items": items})

    async def _refresh_message(
        self, interaction: discord.Interaction, suggestion_id: str, item: dict
    ):
        embed = _suggestion_embed(interaction.guild, item, suggestion_id)
        try:
            await interaction.message.edit(embed=embed, view=self)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass

    @discord.ui.button(
        label="تأييد",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="suggest:up",
    )
    async def upvote(self, interaction: discord.Interaction, button: discord.ui.Button):
        sid, item = await self._get_item(interaction)
        if not item:
            await interaction.response.send_message("❌ ما لقيت هذا الاقتراح.", ephemeral=True)
            return
        if item.get("status") != "pending":
            await interaction.response.send_message(
                "هذا الاقتراح مُغلق وما عاد فيه تصويت.", ephemeral=True
            )
            return

        uid = interaction.user.id
        up = set(item.get("up_voters", []))
        down = set(item.get("down_voters", []))
        if uid in up:
            up.discard(uid)
            msg = "تم سحب تأييدك."
        else:
            up.add(uid)
            down.discard(uid)
            msg = "تم تسجيل تأييدك 👍"
        item["up_voters"] = list(up)
        item["down_voters"] = list(down)
        await self._save_item(interaction.guild.id, sid, item)
        await interaction.response.send_message(msg, ephemeral=True)
        await self._refresh_message(interaction, sid, item)

    @discord.ui.button(
        label="تصويت ضد",
        emoji="❎",
        style=discord.ButtonStyle.secondary,
        custom_id="suggest:down",
    )
    async def downvote(self, interaction: discord.Interaction, button: discord.ui.Button):
        sid, item = await self._get_item(interaction)
        if not item:
            await interaction.response.send_message("❌ ما لقيت هذا الاقتراح.", ephemeral=True)
            return
        if item.get("status") != "pending":
            await interaction.response.send_message(
                "هذا الاقتراح مُغلق وما عاد فيه تصويت.", ephemeral=True
            )
            return

        uid = interaction.user.id
        up = set(item.get("up_voters", []))
        down = set(item.get("down_voters", []))
        if uid in down:
            down.discard(uid)
            msg = "تم سحب تصويتك."
        else:
            down.add(uid)
            up.discard(uid)
            msg = "تم تسجيل رفضك 👎"
        item["up_voters"] = list(up)
        item["down_voters"] = list(down)
        await self._save_item(interaction.guild.id, sid, item)
        await interaction.response.send_message(msg, ephemeral=True)
        await self._refresh_message(interaction, sid, item)

    @discord.ui.button(
        label="قبول",
        emoji="🟢",
        style=discord.ButtonStyle.primary,
        custom_id="suggest:approve",
    )
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.cog._can_moderate(interaction):
            await interaction.response.send_message(
                "❌ ما عندك صلاحية مراجعة الاقتراحات.", ephemeral=True
            )
            return
        sid, item = await self._get_item(interaction)
        if not item:
            await interaction.response.send_message("❌ ما لقيت هذا الاقتراح.", ephemeral=True)
            return
        if item.get("status") != "pending":
            await interaction.response.send_message("هذا الاقتراح مُغلق مسبقاً.", ephemeral=True)
            return

        item["status"] = "approved"
        item["reviewed_by"] = interaction.user.id
        item["reviewed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        await self._save_item(interaction.guild.id, sid, item)
        await interaction.response.send_message("✅ تمت الموافقة على الاقتراح.", ephemeral=True)
        await self._refresh_message(interaction, sid, item)

    @discord.ui.button(
        label="رفض",
        emoji="🔴",
        style=discord.ButtonStyle.danger,
        custom_id="suggest:reject",
    )
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.cog._can_moderate(interaction):
            await interaction.response.send_message(
                "❌ ما عندك صلاحية مراجعة الاقتراحات.", ephemeral=True
            )
            return
        sid, item = await self._get_item(interaction)
        if not item:
            await interaction.response.send_message("❌ ما لقيت هذا الاقتراح.", ephemeral=True)
            return
        if item.get("status") != "pending":
            await interaction.response.send_message("هذا الاقتراح مُغلق مسبقاً.", ephemeral=True)
            return

        item["status"] = "rejected"
        item["reviewed_by"] = interaction.user.id
        item["reviewed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        await self._save_item(interaction.guild.id, sid, item)
        await interaction.response.send_message("🛑 تم رفض الاقتراح.", ephemeral=True)
        await self._refresh_message(interaction, sid, item)


class SuggestionSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(SuggestionVoteView(self))

    async def _can_moderate(self, interaction: discord.Interaction) -> bool:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return False
        member = interaction.user
        if is_owner(member) or member.guild_permissions.administrator:
            return True
        conf = await Storage.get_guild(interaction.guild.id)
        staff_role_id = conf.get(SECTION, {}).get("staff_role_id")
        if staff_role_id and any(r.id == staff_role_id for r in member.roles):
            return True
        return False

    @app_commands.command(
        name="set-up-suggestions",
        description="إعداد نظام الاقتراحات (قناة النشر + رتبة المراجعة)",
    )
    @app_commands.describe(
        channel="القناة اللي بتننشر فيها الاقتراحات",
        staff_role="رتبة تقدر توافق/ترفض (اختياري — الأدمن والأونر دائماً يقدرون)",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def set_up_suggestions(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        staff_role: discord.Role | None = None,
    ):
        await Storage.update_guild(
            interaction.guild.id,
            SECTION,
            {
                "channel_id": channel.id,
                "staff_role_id": staff_role.id if staff_role else None,
            },
        )
        embed = branded_embed(
            title="💡 نظام الاقتراحات",
            color=discord.Color.green(),
        )
        embed.add_field(name="قناة الاقتراحات", value=channel.mention, inline=False)
        embed.add_field(
            name="رتبة المراجعة",
            value=staff_role.mention if staff_role else "الأدمن + صاحب السيرفر فقط",
            inline=False,
        )
        embed.add_field(
            name="الاستخدام",
            value="`/suggest` أو `اقتراح نص الاقتراح`",
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @set_up_suggestions.error
    async def set_up_suggestions_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            return

    @app_commands.command(name="suggest", description="أرسل اقتراحاً لإدارة السيرفر")
    @app_commands.describe(text="نص الاقتراح")
    @app_commands.guild_only()
    async def suggest_slash(self, interaction: discord.Interaction, text: str):
        await interaction.response.defer(ephemeral=True)
        ok, msg = await self._create_suggestion(
            interaction.guild, interaction.user, text.strip()
        )
        await interaction.followup.send(msg, ephemeral=True)

    @commands.command(name="اقتراح")
    @commands.guild_only()
    async def suggest_prefix(self, ctx: commands.Context, *, text: str = None):
        if not text or not text.strip():
            await ctx.reply("❌ اكتب نص الاقتراح بعد الأمر.\nمثال: `اقتراح نضيف روم أفلام`")
            return
        ok, msg = await self._create_suggestion(ctx.guild, ctx.author, text.strip())
        await ctx.reply(msg)

    async def _create_suggestion(
        self,
        guild: discord.Guild,
        author: discord.abc.User,
        content: str,
    ) -> tuple[bool, str]:
        content = content.strip()
        if len(content) < 5:
            return False, "❌ الاقتراح قصير جداً (حد أدنى 5 أحرف)."
        if len(content) > 1500:
            return False, "❌ الاقتراح طويل جداً (حد أقصى 1500 حرف)."

        conf = await Storage.get_guild(guild.id)
        section = conf.get(SECTION, {})
        channel_id = section.get("channel_id")
        if not channel_id:
            return (
                False,
                "❌ نظام الاقتراحات مش معدّ لسا. الأدمن يستخدم `/set-up-suggestions`.",
            )

        channel = guild.get_channel(channel_id)
        if not channel:
            return False, "❌ قناة الاقتراحات مش موجودة أو انمسحت. أعيد الإعداد."

        next_id = int(section.get("next_id") or 1)
        suggestion_id = str(next_id)
        item = {
            "author_id": author.id,
            "content": content,
            "status": "pending",
            "up_voters": [],
            "down_voters": [],
            "message_id": None,
            "channel_id": channel.id,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "staff_note": None,
            "reviewed_by": None,
        }

        embed = _suggestion_embed(guild, item, suggestion_id, author=author)
        view = SuggestionVoteView(self)
        try:
            message = await channel.send(embed=embed, view=view)
        except discord.Forbidden:
            return False, "❌ البوت ما معه صلاحية يرسل بقناة الاقتراحات."
        except discord.HTTPException:
            return False, "❌ فشل إرسال الاقتراح. حاول مرة ثانية."

        item["message_id"] = message.id
        items = dict(section.get("items", {}))
        items[suggestion_id] = item
        await Storage.update_guild(
            guild.id,
            SECTION,
            {"items": items, "next_id": next_id + 1},
        )
        return True, f"✅ تم نشر اقتراحك برقم **#{suggestion_id}** في {channel.mention}"


async def setup(bot: commands.Bot):
    await bot.add_cog(SuggestionSystem(bot))
