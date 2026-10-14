import discord
from discord import app_commands
from discord.ext import commands

from utils.storage import Storage
from utils.embeds import branded_embed

VOICE_REGIONS = [
    ("🌐 تلقائي", None),
    ("🇺🇸 أمريكا (شرق)", "us-east"),
    ("🇺🇸 أمريكا (غرب)", "us-west"),
    ("🇺🇸 أمريكا (وسط)", "us-central"),
    ("🇪🇺 أوروبا الغربية", "rotterdam"),
    ("🇩🇪 أوروبا الوسطى", "frankfurt"),
    ("🇮🇳 الهند", "india"),
    ("🇯🇵 اليابان", "japan"),
    ("🇰🇷 كوريا", "south-korea"),
    ("🇸🇬 سنغافورة", "singapore"),
    ("🇦🇺 أستراليا", "sydney"),
    ("🇧🇷 البرازيل", "brazil"),
]


def _room_owner_overwrite() -> discord.PermissionOverwrite:
    return discord.PermissionOverwrite(
        manage_channels=True,
        move_members=True,
        mute_members=True,
        deafen_members=True,
        connect=True,
        speak=True,
        view_channel=True,
        priority_speaker=True,
    )


class RenameModal(discord.ui.Modal, title="✏️ تغيير اسم الروم"):
    name = discord.ui.TextInput(label="الاسم الجديد", max_length=100, required=True)

    def __init__(self, channel: discord.VoiceChannel):
        super().__init__()
        self.channel = channel
        self.name.default = channel.name

    async def on_submit(self, interaction: discord.Interaction):
        await self.channel.edit(name=str(self.name)[:100], reason=f"تسمية بواسطة {interaction.user}")
        await interaction.response.send_message(f"✅ صار اسم الروم: **{str(self.name)[:100]}**", ephemeral=True)


class LimitModal(discord.ui.Modal, title="👥 حد عدد الأعضاء"):
    limit = discord.ui.TextInput(label="أقصى عدد (0 = بدون حد، أقصى 99)", max_length=2, required=True)

    def __init__(self, channel: discord.VoiceChannel):
        super().__init__()
        self.channel = channel
        self.limit.default = str(channel.user_limit or 0)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            value = max(0, min(99, int(str(self.limit))))
        except ValueError:
            await interaction.response.send_message("لازم تكتب رقم صحيح.", ephemeral=True)
            return
        await self.channel.edit(user_limit=value, reason=f"تحديد عدد بواسطة {interaction.user}")
        await interaction.response.send_message(
            f"✅ الحد الأقصى صار: **{value if value else 'بدون حد'}**", ephemeral=True
        )


class RegionSelect(discord.ui.Select):
    def __init__(self, channel: discord.VoiceChannel):
        self.channel = channel
        options = [
            discord.SelectOption(label=label, value=value or "auto")
            for label, value in VOICE_REGIONS
        ]
        super().__init__(placeholder="🌍 اختار منطقة الروم", options=options)

    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]
        region = None if value == "auto" else value
        await self.channel.edit(rtc_region=region, reason=f"تغيير منطقة بواسطة {interaction.user}")
        label = next((l for l, v in VOICE_REGIONS if (v or "auto") == value), value)
        await interaction.response.edit_message(content=f"✅ صارت منطقة الروم: **{label}**", view=None)


class RegionView(discord.ui.View):
    def __init__(self, channel: discord.VoiceChannel):
        super().__init__(timeout=120)
        self.add_item(RegionSelect(channel))


class MemberActionSelect(discord.ui.UserSelect):
    def __init__(self, channel: discord.VoiceChannel, action: str, placeholder: str):
        super().__init__(placeholder=placeholder, min_values=1, max_values=1)
        self.channel = channel
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        target = self.values[0]
        guild = interaction.guild
        member = guild.get_member(target.id) or target

        if self.action == "kick":
            voice_state = getattr(member, "voice", None)
            if not voice_state or not voice_state.channel or voice_state.channel.id != self.channel.id:
                await interaction.response.edit_message(content="هاد الشخص مش موجود بالروم أصلاً.", view=None)
                return
            if member.id == interaction.user.id:
                await interaction.response.edit_message(content="ما فيك تطرد حالك 😅", view=None)
                return
            await member.move_to(None, reason=f"طرد من الروم بواسطة {interaction.user}")
            await interaction.response.edit_message(content=f"✅ تم طرد {member.mention} من الروم.", view=None)

        elif self.action == "block":
            if member.id == interaction.user.id:
                await interaction.response.edit_message(content="ما فيك تحظر حالك 😅", view=None)
                return
            await self.channel.set_permissions(
                member, connect=False, view_channel=None, reason=f"حظر بواسطة {interaction.user}"
            )
            voice_state = getattr(member, "voice", None)
            if voice_state and voice_state.channel and voice_state.channel.id == self.channel.id:
                try:
                    await member.move_to(None, reason="حظر من الروم")
                except discord.HTTPException:
                    pass
            await interaction.response.edit_message(content=f"🚫 تم حظر {member.mention} من الروم.", view=None)

        elif self.action == "invite":
            await self.channel.set_permissions(
                member, connect=True, view_channel=True, reason=f"دعوة بواسطة {interaction.user}"
            )
            await interaction.response.edit_message(content=f"📩 تم منح {member.mention} صلاحية الدخول للروم.", view=None)

        elif self.action == "trust":
            if member.id == interaction.user.id:
                await interaction.response.edit_message(content="إنت أصلاً صاحب الروم.", view=None)
                return
            await self.channel.set_permissions(
                member,
                connect=True,
                view_channel=True,
                speak=True,
                reason=f"ثقة بواسطة {interaction.user}",
            )
            await interaction.response.edit_message(
                content=f"✅ تم منح الثقة لـ {member.mention} (يقدر يدخل ويحكي).", view=None
            )

        elif self.action == "untrust":
            if member.id == interaction.user.id:
                await interaction.response.edit_message(content="ما فيك تشيل الثقة عن حالك.", view=None)
                return
            try:
                await self.channel.set_permissions(member, overwrite=None, reason=f"سحب ثقة بواسطة {interaction.user}")
            except discord.HTTPException:
                pass
            await interaction.response.edit_message(
                content=f"♻️ تم سحب الثقة من {member.mention}.", view=None
            )

        elif self.action == "transfer":
            if member.id == interaction.user.id:
                await interaction.response.edit_message(content="إنت أصلاً صاحب الروم 😅", view=None)
                return
            try:
                await self.channel.set_permissions(interaction.user, overwrite=None, reason="نقل ملكية")
            except discord.HTTPException:
                pass
            await self.channel.set_permissions(
                member, overwrite=_room_owner_overwrite(), reason=f"نقل ملكية من {interaction.user}"
            )
            await Storage.add_auto_voice_room(interaction.guild.id, self.channel.id, member.id)
            await interaction.response.edit_message(content=f"👑 صار {member.mention} صاحب الروم.", view=None)


class MemberActionView(discord.ui.View):
    def __init__(self, channel: discord.VoiceChannel, action: str, placeholder: str):
        super().__init__(timeout=120)
        self.add_item(MemberActionSelect(channel, action, placeholder))


class UnblockSelect(discord.ui.Select):
    def __init__(self, channel: discord.VoiceChannel, blocked: list):
        self.channel = channel
        options = [
            discord.SelectOption(label=m.display_name[:100], value=str(m.id))
            for m in blocked[:25]
        ]
        super().__init__(placeholder="✅ اختار مين ترفع عنه الحظر", options=options)

    async def callback(self, interaction: discord.Interaction):
        member_id = int(self.values[0])
        member = interaction.guild.get_member(member_id)
        await self.channel.set_permissions(
            discord.Object(id=member_id), overwrite=None, reason=f"رفع حظر بواسطة {interaction.user}"
        )
        name = member.mention if member else f"<@{member_id}>"
        await interaction.response.edit_message(content=f"✅ تم رفع الحظر عن {name}.", view=None)


class UnblockView(discord.ui.View):
    def __init__(self, channel: discord.VoiceChannel, blocked: list):
        super().__init__(timeout=120)
        self.add_item(UnblockSelect(channel, blocked))


class DeleteConfirmView(discord.ui.View):
    def __init__(self, channel: discord.VoiceChannel):
        super().__init__(timeout=60)
        self.channel = channel

    @discord.ui.button(label="تأكيد الحذف", emoji="⚠️", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="⏳ جاري حذف الروم...", view=None)
        try:
            await self.channel.delete(reason=f"حذف بواسطة {interaction.user}")
        except discord.HTTPException:
            pass
        await Storage.remove_auto_voice_room(interaction.guild.id, self.channel.id)

    @discord.ui.button(label="إلغاء", emoji="✖️", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="تم الإلغاء.", view=None)


class RoomControlView(discord.ui.View):
    """
    لوحة تحكم TempVoice Interface — أزرار ثابتة داخل الروم الصوتي المؤقت.
    """

    def __init__(self):
        super().__init__(timeout=None)

    async def _resolve(self, interaction: discord.Interaction):
        """
        يجد روم الفويس الخاص بالضاغط على الزر (مو شرط يكون الزر جوا الروم نفسه).
        - لازم يكون صاحب روم auto-voice
        - يفضّل الروم اللي هو فيه حالياً، وإلا أي روم يملكه
        """
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("❌ الأمر للسيرفرات فقط.", ephemeral=True)
            return None, None

        conf = await Storage.get_guild(interaction.guild.id)
        rooms = conf.get("auto_voice", {}).get("rooms", {}) or {}
        member = interaction.user

        # 1) إذا هو جوا روم صوتي من إنشائه
        if member.voice and member.voice.channel:
            ch = member.voice.channel
            room = rooms.get(str(ch.id))
            if room and room.get("owner_id") == member.id:
                return ch, room

        # 2) أي روم auto-voice يملكه (حتى لو مش جواه هاللحظة)
        owned = []
        for cid, room in rooms.items():
            if room.get("owner_id") == member.id:
                ch = interaction.guild.get_channel(int(cid))
                if isinstance(ch, discord.VoiceChannel):
                    owned.append((ch, room))
        if len(owned) == 1:
            return owned[0]
        if len(owned) > 1:
            # أكثر من روم — خذ اللي هو فيه أو الأول
            await interaction.response.send_message(
                "❌ عندك أكثر من روم. ادخل الروم اللي بدك تعدّل عليه بعدين اضغط الزر.",
                ephemeral=True,
            )
            return None, None

        await interaction.response.send_message(
            "❌ ما عندك روم صوتي نشط من النظام. ادخل روم «اعمل روم» أولاً.",
            ephemeral=True,
        )
        return None, None

    @discord.ui.button(label="تغيير اسم", emoji="✏️", style=discord.ButtonStyle.secondary, custom_id="av:rename", row=0)
    async def rename(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel, room = await self._resolve(interaction)
        if not channel:
            return
        await interaction.response.send_modal(RenameModal(channel))

    @discord.ui.button(label="حد عدد الأعضاء", emoji="👥", style=discord.ButtonStyle.secondary, custom_id="av:limit", row=0)
    async def limit(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel, room = await self._resolve(interaction)
        if not channel:
            return
        await interaction.response.send_modal(LimitModal(channel))

    @discord.ui.button(label="قفل الروم", emoji="🔒", style=discord.ButtonStyle.secondary, custom_id="av:lock", row=0)
    async def toggle_lock(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel, room = await self._resolve(interaction)
        if not channel:
            return
        everyone = interaction.guild.default_role
        currently_locked = channel.overwrites_for(everyone).connect is False
        await channel.set_permissions(
            everyone, connect=(None if currently_locked else False), reason=f"تبديل القفل بواسطة {interaction.user}"
        )
        await interaction.response.send_message(
            "🔓 تم فتح الروم." if currently_locked else "🔒 تم قفل الروم.", ephemeral=True
        )

    @discord.ui.button(label="الدردشة", emoji="💬", style=discord.ButtonStyle.secondary, custom_id="av:chat", row=0)
    async def chat(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel, room = await self._resolve(interaction)
        if not channel:
            return
        everyone = interaction.guild.default_role
        currently_muted = channel.overwrites_for(everyone).send_messages is False
        await channel.set_permissions(
            everyone, send_messages=(None if currently_muted else False),
            reason=f"تبديل الدردشة بواسطة {interaction.user}",
        )
        await interaction.response.send_message(
            "💬 تم فتح الدردشة للكل." if currently_muted else "🔇 تم قفل الدردشة عن غير الصاحب.", ephemeral=True
        )

    @discord.ui.button(label="الثقة", emoji="🤝", style=discord.ButtonStyle.secondary, custom_id="av:trust", row=0)
    async def trust(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel, room = await self._resolve(interaction)
        if not channel:
            return
        view = MemberActionView(channel, "trust", "🤝 اختار مين تعطيه ثقة")
        await interaction.response.send_message(view=view, ephemeral=True)

    @discord.ui.button(label="عدم الثقة", emoji="🚫", style=discord.ButtonStyle.secondary, custom_id="av:untrust", row=1)
    async def untrust(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel, room = await self._resolve(interaction)
        if not channel:
            return
        view = MemberActionView(channel, "untrust", "🚫 اختار مين تشيل منه الثقة")
        await interaction.response.send_message(view=view, ephemeral=True)

    @discord.ui.button(label="دعوة", emoji="📩", style=discord.ButtonStyle.secondary, custom_id="av:invite", row=1)
    async def invite(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel, room = await self._resolve(interaction)
        if not channel:
            return
        view = MemberActionView(channel, "invite", "📩 اختار مين تدعي")
        await interaction.response.send_message(view=view, ephemeral=True)

    @discord.ui.button(label="طرد", emoji="👢", style=discord.ButtonStyle.secondary, custom_id="av:kick", row=1)
    async def kick(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel, room = await self._resolve(interaction)
        if not channel:
            return
        view = MemberActionView(channel, "kick", "👢 اختار مين تطرد")
        await interaction.response.send_message(view=view, ephemeral=True)

    @discord.ui.button(label="تغيير منطقة", emoji="🌍", style=discord.ButtonStyle.secondary, custom_id="av:region", row=1)
    async def region(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel, room = await self._resolve(interaction)
        if not channel:
            return
        await interaction.response.send_message(view=RegionView(channel), ephemeral=True)

    @discord.ui.button(label="حظر", emoji="⛔", style=discord.ButtonStyle.secondary, custom_id="av:block", row=1)
    async def block(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel, room = await self._resolve(interaction)
        if not channel:
            return
        view = MemberActionView(channel, "block", "⛔ اختار مين تحظر")
        await interaction.response.send_message(view=view, ephemeral=True)

    @discord.ui.button(label="رفع الحظر", emoji="♻️", style=discord.ButtonStyle.success, custom_id="av:unblock", row=2)
    async def unblock(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel, room = await self._resolve(interaction)
        if not channel:
            return
        blocked = [
            target for target, ow in channel.overwrites.items()
            if isinstance(target, discord.Member) and ow.connect is False
        ]
        if not blocked:
            await interaction.response.send_message("ما في حدا محظور بهاد الروم حالياً.", ephemeral=True)
            return
        await interaction.response.send_message(view=UnblockView(channel, blocked), ephemeral=True)

    @discord.ui.button(label="نقل ملكية", emoji="👑", style=discord.ButtonStyle.primary, custom_id="av:transfer", row=2)
    async def transfer(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel, room = await self._resolve(interaction)
        if not channel:
            return
        view = MemberActionView(channel, "transfer", "👑 اختار مين تنقله الملكية")
        await interaction.response.send_message(view=view, ephemeral=True)

    @discord.ui.button(label="حذف", emoji="🗑️", style=discord.ButtonStyle.danger, custom_id="av:delete", row=2)
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel, room = await self._resolve(interaction)
        if not channel:
            return
        await interaction.response.send_message(
            f"متأكد بدك تحذف **{channel.name}**؟", view=DeleteConfirmView(channel), ephemeral=True
        )

    @discord.ui.button(label="خصوصية قناتك", emoji="🔐", style=discord.ButtonStyle.secondary, custom_id="av:privacy", row=2)
    async def privacy(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel, room = await self._resolve(interaction)
        if not channel:
            return
        everyone = interaction.guild.default_role
        currently_hidden = channel.overwrites_for(everyone).view_channel is False
        await channel.set_permissions(
            everyone, view_channel=(None if currently_hidden else False),
            reason=f"تبديل الخصوصية بواسطة {interaction.user}",
        )
        await interaction.response.send_message(
            "👁️ صار الروم ظاهر للكل." if currently_hidden else "🙈 صار الروم مخفي عن الكل.", ephemeral=True
        )


class AutoVoiceSystem(commands.Cog):
    """
    نظام الرومات الصوتية التلقائية:
    - عضو يدخل روم "الزرار" (➕ اعمل روم) → البوت ينشئله روم خاص وينقله فيه.
    - بتنبعث جوا الروم لوحة تحكم كاملة بأزرار (قفل، تسمية، حد أعضاء، منطقة، طرد،
      حظر/رفع حظر، دعوة، خصوصية، قفل الدردشة، نقل ملكية، حذف).
    - الروم بينحذف تلقائياً لما يفضى تماماً.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        # نسجل اللوحة كـ persistent view حتى تضل الأزرار شغالة حتى لو البوت عمل ريستارت
        self.bot.add_view(RoomControlView())


    # ---------------- /set-up-auto-voice ----------------

    @app_commands.command(name="set-up-auto-voice", description="إعداد نظام الرومات الصوتية التلقائية")
    @app_commands.describe(
        trigger_channel="الروم الصوتي يلي لما حدا يدخله بينعملّه روم خاص (مثلاً: ➕ اعمل روم)",
        category="الكاتيغوري يلي رح تتعمل فيه الرومات المؤقتة",
        log_channel="قناة اللوق (اختياري)",
        name_template="شكل اسم الروم - استخدم {user} حتى ينحط مكانها اسم الشخص",
        user_limit="أقصى عدد أشخاص بالروم افتراضياً (0 = بدون حد)",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_auto_voice(
        self,
        interaction: discord.Interaction,
        trigger_channel: discord.VoiceChannel,
        category: discord.CategoryChannel,
        log_channel: discord.TextChannel = None,
        name_template: str = "🔊 روم {user}",
        user_limit: app_commands.Range[int, 0, 99] = 0,
    ):
        if "{user}" not in name_template:
            name_template = name_template.strip() + " {user}"

        await Storage.update_guild(interaction.guild.id, "auto_voice", {
            "trigger_channel_id": trigger_channel.id,
            "category_id": category.id,
            "log_channel_id": log_channel.id if log_channel else None,
            "name_template": name_template,
            "user_limit": user_limit,
        })

        embed = branded_embed(title="✅ تم إعداد الرومات الصوتية التلقائية", color=discord.Color.green())
        embed.add_field(name="🚪 روم الدخول", value=trigger_channel.mention, inline=True)
        embed.add_field(name="📁 الكاتيغوري", value=category.mention, inline=True)
        embed.add_field(name="📝 اللوق", value=log_channel.mention if log_channel else "❌ غير مفعّل", inline=True)
        embed.add_field(name="🏷️ شكل الاسم", value=f"`{name_template}`", inline=True)
        embed.add_field(name="👥 الحد الافتراضي", value=str(user_limit) if user_limit else "بدون حد", inline=True)
        embed.add_field(
            name="ℹ️ طريقة الشغل",
            value=(
                f"أي حدا يدخل {trigger_channel.mention} بينعملّه روم خاص جواته وينقل فيه تلقائياً، "
                "وبتنبعثله جوا الروم لوحة تحكم كاملة بأزرار. الروم بينحذف لحاله لما يفضى تماماً."
            ),
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @setup_auto_voice.error
    async def setup_auto_voice_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            return

    # ---------------- إنشاء / حذف الرومات ----------------

    async def _create_room(self, member: discord.Member, av: dict):
        guild = member.guild
        category = guild.get_channel(av["category_id"])
        if not isinstance(category, discord.CategoryChannel):
            return

        me = guild.me
        if not category.permissions_for(me).manage_channels or not me.guild_permissions.move_members:
            return  # البوت ما عنده صلاحيات كافية، ما لازم يحاول

        name = av.get("name_template", "🔊 روم {user}").format(user=member.display_name)[:100]
        user_limit = av.get("user_limit", 0) or 0

        overwrites = dict(category.overwrites)
        overwrites[member] = _room_owner_overwrite()

        try:
            new_channel = await guild.create_voice_channel(
                name=name,
                category=category,
                user_limit=user_limit,
                overwrites=overwrites,
                reason=f"روم صوتي تلقائي لـ {member}",
            )
            await member.move_to(new_channel, reason="نقل لرومه الخاص")
        except discord.Forbidden:
            return
        except discord.HTTPException:
            return

        await Storage.add_auto_voice_room(guild.id, new_channel.id, member.id)

        try:
            welcome_embed = branded_embed(
                title="TempVoice Interface",
                color=discord.Color.from_rgb(237, 66, 69),
                description=(
                    f"يمكنك استخدام الأوامر للتحكم في الروم الصوتي الخاص بك المؤقت. "
                    f"المزيد من الخيارات متاحة من خلال هذه الواجهة.\n\n"
                    f"صاحب الروم: {member.mention}\n"
                    "الروم يُحذف تلقائياً عند فراغه.\n\n"
                    "**يمكن استخدام هذه الواجهة بالنص فوق الأزرار أدناه**"
                ),
            )
            await new_channel.send(embed=welcome_embed, view=RoomControlView())
        except discord.Forbidden:
            pass

        conf = await Storage.get_guild(guild.id)
        log_channel_id = conf["auto_voice"].get("log_channel_id")
        if log_channel_id:
            log_channel = guild.get_channel(log_channel_id)
            if log_channel:
                log_embed = branded_embed(title="🔊 روم صوتي جديد", color=discord.Color.blurple())
                log_embed.add_field(name="الصاحب", value=member.mention, inline=True)
                log_embed.add_field(name="الروم", value=new_channel.mention, inline=True)
                try:
                    await log_channel.send(embed=log_embed)
                except discord.Forbidden:
                    pass

    async def _maybe_delete_room(self, channel: discord.VoiceChannel, av: dict):
        if str(channel.id) not in av.get("rooms", {}):
            return
        if len(channel.members) > 0:
            return

        guild = channel.guild
        try:
            await channel.delete(reason="روم صوتي فضي - حذف تلقائي")
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            pass

        await Storage.remove_auto_voice_room(guild.id, channel.id)

        conf = await Storage.get_guild(guild.id)
        log_channel_id = conf["auto_voice"].get("log_channel_id")
        if log_channel_id:
            log_channel = guild.get_channel(log_channel_id)
            if log_channel:
                log_embed = branded_embed(title="🗑️ روم صوتي انحذف (فضي)", color=discord.Color.dark_grey())
                log_embed.add_field(name="اسم الروم", value=channel.name, inline=False)
                try:
                    await log_channel.send(embed=log_embed)
                except discord.Forbidden:
                    pass

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ):
        conf = await Storage.get_guild(member.guild.id)
        av = conf["auto_voice"]

        # دخل على روم الزرار -> ننشئله روم خاص
        trigger_id = av.get("trigger_channel_id")
        if trigger_id and after.channel and after.channel.id == trigger_id:
            await self._create_room(member, av)

        # طلع من روم مؤقت -> لو فضي، نحذفه
        if before.channel and before.channel != after.channel:
            await self._maybe_delete_room(before.channel, av)

    # ---------------- /room-voice ----------------

    @app_commands.command(
        name="room-voice",
        description="إرسال بانل التحكم بالفويس هنا (وفي شات الروم إن وُجد)",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def room_voice(self, interaction: discord.Interaction):
        """
        يرسل بانل TempVoice في الروم النصي الحالي.
        الأعضاء أصحاب الرومات يضغطون الأزرار من هون للتحكم بروماتهم
        (قفل، اسم، طرد...) — حتى لو الروم الصوتي مقفول عن الكتابة.
        """
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("الأمر للسيرفرات فقط.", ephemeral=True)
            return

        is_streater = (
            interaction.user.guild_permissions.administrator
            or interaction.user.id == interaction.guild.owner_id
        )
        if not is_streater:
            await interaction.response.send_message(
                "❌ بس الستريتر (أدمن / أونر) يقدر يرسل بانل التحكم.",
                ephemeral=True,
            )
            return

        if not isinstance(interaction.channel, (discord.TextChannel, discord.Thread)):
            await interaction.response.send_message(
                "❌ استخدم الأمر بروم نصي.",
                ephemeral=True,
            )
            return

        embed = branded_embed(
            title="TempVoice Interface",
            color=discord.Color.from_rgb(237, 66, 69),
            description=(
                "يمكنك استخدام هذه الواجهة للتحكم في **رومك الصوتي المؤقت**." + chr(10)*2
                + "**كيف تستخدمها؟**" + chr(10)
                + "1️⃣ ادخل روم «اعمل روم» عشان ينعمل لك فويس خاص" + chr(10)
                + "2️⃣ ارجع لهالرسالة واضغط الأزرار تحت" + chr(10)
                + "3️⃣ التعديل يصير على رومك حتى لو كان مقفول" + chr(10)*2
                + "────────────────────" + chr(10)
                + "قفل · تغيير اسم · حد أعضاء · طرد · حظر · دعوة · ملكية · حذف..."
            ),
        )

        view = RoomControlView()
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message(
            f"✅ تم إرسال بانل الفويس هنا في {interaction.channel.mention}" + chr(10)
            + "أصحاب الرومات يقدرون يتحكمون بروماتهم من الأزرار.",
            ephemeral=True,
        )

        # إذا الأمر مستخدم وهو جوا روم auto-voice — أرسل نسخة كمان بشات الفويس
        member = interaction.user
        if member.voice and member.voice.channel:
            conf = await Storage.get_guild(interaction.guild.id)
            ch = member.voice.channel
            room = conf.get("auto_voice", {}).get("rooms", {}).get(str(ch.id))
            if room:
                try:
                    await ch.send(embed=embed, view=RoomControlView())
                except discord.Forbidden:
                    pass
                except discord.HTTPException:
                    pass


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoVoiceSystem(bot))
