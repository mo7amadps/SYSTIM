"""
نظام الألعاب — أوامر بـ !
كت · اسرع · لاعب · تفكيك · تجميع · سلسلة · ريبلكا · روليت · مافيا
"""
from __future__ import annotations

import asyncio
import random
import re
import time
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.storage import Storage
from utils.embeds import branded_embed
from cogs.games_data import (
    RACE_QUESTIONS, RIDDLES, PLURAL_TO_SING, SING_TO_PLURAL,
    HIDE_PLACES, GUESS_PLACES,
)
from cogs.games_replica_words import word_in_category

SECTION = "games"

# ───────────── بيانات ─────────────

WORDS = [
    "دجاج مقلي", "بيتزا", "شاي أخضر", "قهوة تركية", "مندوب", "مدرسة", "كتاب",
    "سيارة حمراء", "هاتف ذكي", "بحر هادئ", "جبل عالي", "قمر منير", "شمس حارة",
    "ورد أحمر", "تفاح أخضر", "موز أصفر", "عنب أسود", "حليب طازج", "خبز ساخن",
    "كمبيوتر", "لوحة مفاتيح", "ماوس", "شاشة كبيرة", "سماعة", "ميكروفون",
    "كرة قدم", "ملعب", "حكم", "جمهور", "هدف", "ركلة جزاء", "تسلل",
    "قطة بيضاء", "كلب أسود", "عصفور", "سمكة", "أسد", "نمر", "فيل",
    "مدينة", "قرية", "شارع", "جسر", "قطار", "طائرة", "سفينة",
    "شتاء بارد", "صيف حار", "ربيع جميل", "خريف ذهبي", "مطر غزير", "ثلج أبيض",
    "صديق وفي", "عائلة", "أخ كبير", "أخت صغيرة", "جد طيب", "جدة حنونة",
    "مطبخ", "غرفة نوم", "صالون", "حديقة", "سطح البيت", "باب خشبي",
    "قلم رصاص", "دفتر", "ممحاة", "مسطرة", "حقيبة مدرسية", "سبورة",
    "فيلم رعب", "مسلسل", "أغنية", "رقصة", "حفلة", "عيد ميلاد",
    "ذهب", "فضة", "ماس", "لؤلؤ", "كنز مدفون", "خريطة قديمة",
]

PLAYERS = [
    "ميسي", "رونالدو", "نيمار", "مبابي", "هالاند", "بنزيما", "صلاح",
    "محرز", "بونو", "حكيمي", "يوسف النصيري", "أشرف حكيمي", "كريم بنزيما",
    "زيدان", "رونالدينيو", "خافي", "إينييستا", "كاسياس", "بوفون",
    "ليفاندوفسكي", "مودريتش", "كروس", "دي بروين", "ستيرلينغ", "سون",
    "فينيسيوس", "بيدري", "غافي", "يامال", "بellingham".replace("bellingham", "بيلينغهام"),
]

QUESTIONS = [
    # أسئلة نقاش مفتوحة — أي جواب يُحسب (أول واحد يفوز)
    ("شو أكثر موقف خلاك ندمان؟", ["*"]),
    ("لو يرجع فيك الزمن، أي قرار تغيّره؟", ["*"]),
    ("وش أجمل ذكرى عندك؟", ["*"]),
    ("لو عندك يوم واحد فقط، وش تسوي فيه؟", ["*"]),
    ("وش الشي اللي ما تقدر تعيش بدونه؟", ["*"]),
    ("تصف يومك المثالي بكلمتين؟", ["*"]),
    ("مين الشخص اللي أثّر فيك أكثر شي؟", ["*"]),
    ("وش أكبر درس تعلمته هالسنة؟", ["*"]),
    ("لو تسافر الحين لمكان واحد، وين؟", ["*"]),
    ("وش أكتر صفة تحبها بنفسك؟", ["*"]),
    ("لو تكتب رسالة لنسخة أصغر منك، وش تقول؟", ["*"]),
    ("وش الموقف اللي ضحكت فيه لين دمعت؟", ["*"]),
    ("تفضّل البحر ولا الجبل؟ وليش؟", ["*"]),
    ("وش عاداتك اليومية اللي ما تفرّط فيها؟", ["*"]),
    ("لو تصير مشهور، بشو؟", ["*"]),
    ("وش أكثر أغنية تمثّلك الحين؟", ["*"]),
    ("لو عندك قوة خارقة واحدة، وش تختار؟", ["*"]),
    ("تصف نفسك بثلاث كلمات؟", ["*"]),
    ("وش الشي اللي الناس ما تعرفه عنك؟", ["*"]),
    ("لو تعيد اختيار تخصصك/شغلك، تختار نفس الشي؟", ["*"]),
    ("وش أسوأ نصيحة سمعتها؟", ["*"]),
    ("متى آخر مرة جربت شي جديد؟", ["*"]),
    ("وش يخليك سعيد بسرعة؟", ["*"]),
    ("لو تتعشى مع شخصية مشهورة، مين؟", ["*"]),
    ("وش أكثر خوف تبغى تتغلب عليه؟", ["*"]),
    ("تحب الصباح ولا الليل؟", ["*"]),
    ("وش كتاب أو فيلم غيّر نظرتك؟", ["*"]),
    ("لو تخترع تطبيق، عن أيش؟", ["*"]),
    ("وش أكتر مكان ترتاح فيه؟", ["*"]),
    ("لو تقول نصيحة لشخص غريب، وش تقول؟", ["*"]),
]

# وسّع الأسئلة بتكرار أنماط بسيطة إلى ~120+
for i in range(2, 51):
    QUESTIONS.append((f"ما ناتج {i}+{i}؟", [str(i * 2)]))
for i in range(2, 21):
    QUESTIONS.append((f"ما ناتج {i}×{i}؟", [str(i * i)]))

REPLICA_CATS = ["اسم", "حيوان", "جماد", "نبات", "بلاد"]
ARABIC_LETTERS = list("أاببتثجحخدذرزسشصضطظعغفقكلمنهوية")


def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
    s = re.sub(r"\s+", " ", s)
    return s


def _norm_spaces(s: str) -> str:
    """يتجاهل كل المسافات للمقارنة (تفكيك/تجميع)."""
    return re.sub(r"\s+", "", _norm(s))


def _last_letter(word: str) -> str:
    w = (word or "").strip()
    if not w:
        return ""
    ch = w[-1]
    if ch == "ة":
        return "ت"
    if ch in "ىي":
        return "ي"
    if ch in "أإآا":
        return "ا"
    return ch


def _split_word(word: str) -> str:
    chars = [c for c in word if not c.isspace()]
    return " ".join(chars)


# ───────────── حالة القنوات ─────────────
# channel_id -> game state dict
_ACTIVE: dict[int, dict] = {}


async def _cfg(guild_id: int) -> dict:
    conf = await Storage.get_guild(guild_id)
    return conf.get(SECTION) or {}


async def _timeout(guild_id: int, key: str, default: int = 30) -> int:
    cfg = await _cfg(guild_id)
    t = (cfg.get("timeouts") or {}).get(key, default)
    try:
        return max(5, min(100, int(t)))
    except Exception:
        return default


async def _can_start(member: discord.Member, game_key: str) -> bool:
    """رتب مسموحة + أي رتبة أعلى منها بالهرمية تشتغل."""
    if member.guild_permissions.administrator or member.guild_permissions.manage_guild:
        return True
    if member.guild.owner_id == member.id:
        return True
    cfg = await _cfg(member.guild.id)
    roles_map = cfg.get("starter_roles") or {}
    allowed = roles_map.get(game_key) or roles_map.get("all") or []
    if not allowed:
        return True
    guild = member.guild
    allowed_roles = []
    for rid in allowed:
        try:
            r = guild.get_role(int(rid))
        except Exception:
            r = None
        if r is not None:
            allowed_roles.append(r)
    if not allowed_roles:
        return True
    # يملك إحدى الرتب أو رتبة بموضع >= أقل موضع مسموح (يعني الأعلى كمان)
    threshold = min(r.position for r in allowed_roles)
    for r in member.roles:
        if r.is_default():
            continue
        if r in allowed_roles or r.position >= threshold:
            return True
    return False


async def _can_stop(member: discord.Member, game_key: str | None = None) -> bool:
    """من يقدر يوقف اللعبة: أدمن أو رتب الإيقاف أو رتب البدء (إن ما تحدد إيقاف)."""
    if member.guild_permissions.administrator or member.guild_permissions.manage_guild:
        return True
    if member.guild.owner_id == member.id:
        return True
    cfg = await _cfg(member.guild.id)
    roles_map = cfg.get("stopper_roles") or {}
    allowed = []
    if game_key:
        allowed = roles_map.get(game_key) or []
    if not allowed:
        allowed = roles_map.get("all") or []
    # إذا ما في رتب إيقاف، استخدم رتب البدء
    if not allowed:
        sm = cfg.get("starter_roles") or {}
        if game_key:
            allowed = sm.get(game_key) or []
        if not allowed:
            allowed = sm.get("all") or []
    if not allowed:
        return member.guild_permissions.manage_messages
    guild = member.guild
    allowed_roles = []
    for rid in allowed:
        try:
            r = guild.get_role(int(rid))
        except Exception:
            r = None
        if r is not None:
            allowed_roles.append(r)
    if not allowed_roles:
        return True
    threshold = min(r.position for r in allowed_roles)
    for r in member.roles:
        if r.is_default():
            continue
        if r in allowed_roles or r.position >= threshold:
            return True
    return False


async def _log_game(guild: discord.Guild, text: str):
    try:
        cfg = await _cfg(guild.id)
        cid = cfg.get("log_channel_id")
        if not cid:
            return
        ch = guild.get_channel(int(cid))
        if ch:
            await ch.send(text)
    except Exception:
        pass


async def _channel_allowed(guild_id: int, channel_id: int) -> bool:
    cfg = await _cfg(guild_id)
    chans = cfg.get("allowed_channels") or []
    if not chans:
        return True
    try:
        return int(channel_id) in {int(x) for x in chans}
    except Exception:
        return True


async def _add_point(guild_id: int, user_id: int, amount: int = 1) -> int:
    cfg = await _cfg(guild_id)
    pts = dict(cfg.get("points") or {})
    pts[str(user_id)] = int(pts.get(str(user_id), 0)) + amount
    await Storage.update_guild(guild_id, SECTION, {"points": pts})
    return pts[str(user_id)]


def _game_embed(title: str, desc: str = "", color: discord.Color | None = None) -> discord.Embed:
    return branded_embed(title=title, description=desc, color=color or discord.Color.blurple())


# ───────────── Views مشتركة ─────────────

class PlayAgainView(discord.ui.View):
    def __init__(self, cog: "GamesSystem", game_key: str, starter_id: int):
        super().__init__(timeout=120)
        self.cog = cog
        self.game_key = game_key
        self.starter_id = starter_id

    @discord.ui.button(label="العب مرة أخرى", style=discord.ButtonStyle.primary, emoji="🔄")
    async def again(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.starter_id:
            await interaction.response.send_message("فقط من بدأ الجولة السابقة.", ephemeral=True)
            return
        await interaction.response.defer()
        cmd = {
            "kat": self.cog.start_kat,
            "asra": self.cog.start_asra,
            "player": self.cog.start_player,
            "tafkik": self.cog.start_tafkik,
            "tajmee": self.cog.start_tajmee,
        }.get(self.game_key)
        if cmd:
            await cmd(interaction.channel, interaction.user)



class LobbyView(discord.ui.View):
    """دخول / خروج — العداد يبدأ اللعبة تلقائي."""

    def __init__(self, cog: "GamesSystem", channel_id: int, game_type: str):
        super().__init__(timeout=600)
        self.cog = cog
        self.channel_id = channel_id
        self.game_type = game_type

    @discord.ui.button(label="دخول", style=discord.ButtonStyle.success, emoji="✅")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        st = _ACTIVE.get(self.channel_id)
        if not st or st.get("phase") != "lobby" or st.get("type") != self.game_type:
            await interaction.response.send_message("ما في لوبي مفتوح.", ephemeral=True)
            return
        max_p = int(st.get("max_players") or 300)
        if interaction.user.id not in st["players"] and len(st["players"]) >= max_p:
            await interaction.response.send_message(f"اللعبة ممتلئة (حد أقصى {max_p}).", ephemeral=True)
            return
        st["players"][interaction.user.id] = interaction.user.display_name
        await interaction.response.send_message("تم دخولك ✅", ephemeral=True)
        await self.cog._lobby_refresh(st)

    @discord.ui.button(label="خروج", style=discord.ButtonStyle.danger, emoji="🚪")
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        st = _ACTIVE.get(self.channel_id)
        if not st or st.get("phase") != "lobby":
            await interaction.response.send_message("ما في لوبي.", ephemeral=True)
            return
        uid = interaction.user.id
        if uid == st.get("host_id") and len(st.get("players") or {}) > 1:
            await interaction.response.send_message("المضيف يطلع لما يبقى لحاله أو ينتهي العداد.", ephemeral=True)
            return
        st["players"].pop(uid, None)
        if not st["players"]:
            await interaction.response.send_message("خرجت · اللوبي انلغى.", ephemeral=True)
            await self.cog._clear(self.channel_id)
            try:
                await interaction.message.edit(view=None)
            except Exception:
                pass
            return
        await interaction.response.send_message("خرجت.", ephemeral=True)
        await self.cog._lobby_refresh(st)



def smart_eliminate_quota(n: int, fixed: int = 0) -> int:
    """كم لاعب يُستبعد كهدف لكل جولة. fixed>0 من الداشبورد يلغي التلقائي."""
    if fixed and fixed > 0:
        return max(1, min(int(fixed), max(1, n - 1)))
    if n <= 2:
        return 1
    if n <= 5:
        return 1
    if n <= 10:
        return max(1, n // 4)
    if n <= 15:
        return max(2, n // 5)
    if n <= 25:
        return max(3, n // 5)
    if n <= 40:
        return max(4, n // 5)
    return max(5, n // 6)



async def _player_limits(guild_id: int, game_key: str, default_min: int = 1, default_max: int = 300) -> tuple[int, int]:
    cfg = await _cfg(guild_id)
    hard_max = 1000 if game_key == "roulette" else 300
    try:
        mn = int((cfg.get("min_players") or {}).get(game_key, default_min))
    except Exception:
        mn = default_min
    try:
        mx = int((cfg.get("max_players") or {}).get(game_key, default_max if game_key != "roulette" else 1000))
    except Exception:
        mx = default_max if game_key != "roulette" else 1000
    mn = max(1, min(hard_max, mn))
    mx = max(mn, min(hard_max, mx))
    return mn, mx

async def _eliminate_setting(guild_id: int, game_key: str) -> int:
    """0 = تلقائي."""
    cfg = await _cfg(guild_id)
    try:
        return int((cfg.get("eliminate") or {}).get(game_key) or 0)
    except Exception:
        return 0


class RouletteJoinView(discord.ui.View):
    def __init__(self, cog: "GamesSystem", channel_id: int):
        super().__init__(timeout=600)
        self.cog = cog
        self.channel_id = channel_id

    @discord.ui.button(label="دخول", style=discord.ButtonStyle.success, emoji="✅")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        st = _ACTIVE.get(self.channel_id)
        if not st or st.get("type") != "roulette" or st.get("phase") != "join":
            await interaction.response.send_message("ما في روليت مفتوحة هنا.", ephemeral=True)
            return
        uid = interaction.user.id
        if uid in st["players"]:
            await interaction.response.send_message("أنت داخل أصلاً.", ephemeral=True)
            return
        max_p = int(st.get("max_players") or 1000)
        if len(st["players"]) >= max_p:
            await interaction.response.send_message(f"ممتلئة (حد {max_p}).", ephemeral=True)
            return
        st["players"][uid] = interaction.user.display_name
        await interaction.response.send_message("تم دخولك للروليت ✅", ephemeral=True)
        await self.cog._roulette_refresh(st)

    @discord.ui.button(label="خروج", style=discord.ButtonStyle.danger, emoji="🚪")
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        st = _ACTIVE.get(self.channel_id)
        if not st or st.get("type") != "roulette" or st.get("phase") != "join":
            await interaction.response.send_message("ما في روليت مفتوحة.", ephemeral=True)
            return
        uid = interaction.user.id
        if uid not in st["players"]:
            await interaction.response.send_message("أنت مو داخل.", ephemeral=True)
            return
        if uid == st.get("host_id") and len(st["players"]) > 1:
            await interaction.response.send_message("المضيف ما يطلع إلا إذا فك اللعبة أو باقي لحاله.", ephemeral=True)
            return
        st["players"].pop(uid, None)
        await interaction.response.send_message("خرجت من الروليت.", ephemeral=True)
        await self.cog._roulette_refresh(st)

    @discord.ui.button(label="بدء", style=discord.ButtonStyle.primary, emoji="▶️")
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        st = _ACTIVE.get(self.channel_id)
        if not st or st.get("type") != "roulette" or st.get("phase") != "join":
            await interaction.response.send_message("ما في روليت.", ephemeral=True)
            return
        if interaction.user.id != st.get("host_id"):
            await interaction.response.send_message("فقط المضيف يبدأ.", ephemeral=True)
            return
        if len(st["players"]) < 2:
            await interaction.response.send_message("لازم لاعبين على الأقل.", ephemeral=True)
            return
        await interaction.response.defer()
        await self.cog._roulette_begin(st)


class RoulettePickView(discord.ui.View):
    def __init__(self, cog: "GamesSystem", channel_id: int, chooser_id: int, page: int = 0):
        super().__init__(timeout=None)
        self.cog = cog
        self.channel_id = channel_id
        self.chooser_id = chooser_id
        self.page = page
        self._build()

    def _build(self):
        self.clear_items()
        st = _ACTIVE.get(self.channel_id)
        if not st:
            return
        players = [(uid, name) for uid, name in st["players"].items() if uid != self.chooser_id]
        per = int(st.get("per_page") or 20)
        pages = max(1, (len(players) + per - 1) // per)
        self.page = max(0, min(self.page, pages - 1))
        chunk = players[self.page * per : (self.page + 1) * per]

        for i, (uid, name) in enumerate(chunk):
            label = f"{name}"[:70]
            btn = discord.ui.Button(
                label=label,
                style=discord.ButtonStyle.secondary,
                custom_id=f"rl:pick:{uid}",
                row=i // 5,
            )

            async def _cb(interaction: discord.Interaction, target_id=uid):
                await self.cog._roulette_kick(interaction, self.channel_id, self.chooser_id, target_id)

            btn.callback = _cb
            self.add_item(btn)

        # صف أخير: صفحات + انسحب
        if pages > 1:
            prev = discord.ui.Button(label="◀", style=discord.ButtonStyle.primary, row=4, disabled=self.page <= 0)

            async def _prev(interaction: discord.Interaction):
                if interaction.user.id != self.chooser_id:
                    await interaction.response.send_message("مو دورك.", ephemeral=True)
                    return
                v = RoulettePickView(self.cog, self.channel_id, self.chooser_id, self.page - 1)
                await interaction.response.edit_message(view=v)

            prev.callback = _prev
            self.add_item(prev)

            nxt = discord.ui.Button(label="▶", style=discord.ButtonStyle.primary, row=4, disabled=self.page >= pages - 1)

            async def _nxt(interaction: discord.Interaction):
                if interaction.user.id != self.chooser_id:
                    await interaction.response.send_message("مو دورك.", ephemeral=True)
                    return
                v = RoulettePickView(self.cog, self.channel_id, self.chooser_id, self.page + 1)
                await interaction.response.edit_message(view=v)

            nxt.callback = _nxt
            self.add_item(nxt)

        withdraw = discord.ui.Button(label="انسحب", style=discord.ButtonStyle.danger, row=4)

        async def _wd(interaction: discord.Interaction):
            if interaction.user.id != self.chooser_id:
                await interaction.response.send_message("مو دورك.", ephemeral=True)
                return
            await self.cog._roulette_self_out(interaction, self.channel_id, self.chooser_id)

        withdraw.callback = _wd
        self.add_item(withdraw)


class MafiaJoinView(discord.ui.View):
    def __init__(self, cog: "GamesSystem", channel_id: int):
        super().__init__(timeout=600)
        self.cog = cog
        self.channel_id = channel_id

    @discord.ui.button(label="دخول", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        st = _ACTIVE.get(self.channel_id)
        if not st or st.get("type") != "mafia" or st.get("phase") != "join":
            await interaction.response.send_message("ما في مافيا مفتوحة.", ephemeral=True)
            return
        max_p = int(st.get("max_players") or 300)
        if interaction.user.id not in st["players"] and len(st["players"]) >= max_p:
            await interaction.response.send_message(f"ممتلئة (حد {max_p}).", ephemeral=True)
            return
        st["players"][interaction.user.id] = interaction.user.display_name
        await interaction.response.send_message("دخلت المافيا ✅", ephemeral=True)
        await self.cog._mafia_refresh(st)

    @discord.ui.button(label="خروج", style=discord.ButtonStyle.danger)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        st = _ACTIVE.get(self.channel_id)
        if not st or st.get("type") != "mafia" or st.get("phase") != "join":
            await interaction.response.send_message("ما في مافيا.", ephemeral=True)
            return
        st["players"].pop(interaction.user.id, None)
        await interaction.response.send_message("خرجت.", ephemeral=True)
        await self.cog._mafia_refresh(st)

    @discord.ui.button(label="بدء", style=discord.ButtonStyle.primary)
    async def start_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        st = _ACTIVE.get(self.channel_id)
        if not st or st.get("type") != "mafia":
            await interaction.response.send_message("ما في مافيا.", ephemeral=True)
            return
        if interaction.user.id != st.get("host_id"):
            await interaction.response.send_message("فقط المضيف.", ephemeral=True)
            return
        cfg = await _cfg(interaction.guild.id)
        min_p = int((cfg.get("mafia") or {}).get("min_players") or 5)
        if len(st["players"]) < min_p:
            await interaction.response.send_message(f"أقل عدد: {min_p}", ephemeral=True)
            return
        await interaction.response.defer()
        await self.cog._mafia_begin(st, interaction.channel)


# ───────────── الكوج ─────────────


class RaceAnswerView(discord.ui.View):
    def __init__(self, cog: "GamesSystem", channel_id: int, options: list[str]):
        super().__init__(timeout=120)
        self.cog = cog
        self.channel_id = channel_id
        for i, label in enumerate(options[:4]):
            style = discord.ButtonStyle.secondary
            btn = discord.ui.Button(label=f"{i+1} {label}"[:80], style=style, custom_id=f"race:{i}")

            async def cb(interaction: discord.Interaction, idx=i, lab=label):
                await self.cog._sabaq_answer(interaction, self.channel_id, idx, lab)

            btn.callback = cb
            self.add_item(btn)


class XOView(discord.ui.View):
    def __init__(self, cog: "GamesSystem", channel_id: int):
        super().__init__(timeout=300)
        self.cog = cog
        self.channel_id = channel_id
        for i in range(9):
            btn = discord.ui.Button(label="·", style=discord.ButtonStyle.secondary, row=i // 3, custom_id=f"xo:{i}")

            async def cb(interaction: discord.Interaction, idx=i):
                await self.cog._xo_click(interaction, self.channel_id, idx)

            btn.callback = cb
            self.add_item(btn)


class GamesSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _busy(self, channel_id: int) -> bool:
        return channel_id in _ACTIVE

    async def _guard(self, ctx: commands.Context, game_key: str) -> bool:
        if not await _channel_allowed(ctx.guild.id, ctx.channel.id):
            await ctx.reply("الألعاب مقفولة بهالروم. الأدمن يضبط الرومات بـ `/games`.")
            return False
        if not await _can_start(ctx.author, game_key):
            await ctx.reply("ما عندك صلاحية استخدام هاللعبة.")
            return False
        if self._busy(ctx.channel.id):
            await ctx.reply("في لعبة شغّالة هنا.")
            return False
        return True

    async def _start_solo(self, ctx: commands.Context, game_type: str, title: str):
        """ألعاب فردية بدون لوبي."""
        if not await self._guard(ctx, game_type):
            return None
        st = {
            "type": game_type,
            "phase": "play",
            "players": {ctx.author.id: ctx.author.display_name},
            "host_id": ctx.author.id,
            "channel_id": ctx.channel.id,
            "min_players": 1,
            "max_players": 300,
        }
        _ACTIVE[ctx.channel.id] = st
        return st


    async def _clear(self, channel_id: int):
        _ACTIVE.pop(channel_id, None)

    async def _open_lobby(
        self,
        channel: discord.TextChannel,
        host: discord.Member | discord.User,
        game_type: str,
        title: str,
        desc: str,
        min_players: int = 1,
        extra: dict | None = None,
    ):
        if self._busy(channel.id):
            await channel.send("في لعبة شغّالة هنا.")
            return
        if not await _channel_allowed(channel.guild.id, channel.id):
            await channel.send("الألعاب مقفولة بهالروم. الأدمن يضبط الرومات بـ `/games`.")
            return
        if isinstance(host, discord.Member) and not await _can_start(host, game_type):
            await channel.send("ما عندك صلاحية بدء هاللعبة.")
            return
        cfg_min, cfg_max = await _player_limits(channel.guild.id, game_type, min_players, 300)
        lobby_secs = await _timeout(channel.guild.id, "lobby", 30)
        lobby_secs = max(10, min(120, int(lobby_secs)))
        emb = _game_embed(
            title,
            desc
            + f"\n\n**اللاعبون (1):** {host.mention}"
            + f"\n⏱️ يبدأ خلال **{lobby_secs}** ثانية · الي يلحق يدخل",
        )
        view = LobbyView(self, channel.id, game_type)
        msg = await channel.send(embed=emb, view=view)
        st = {
            "type": game_type,
            "phase": "lobby",
            "players": {host.id: host.display_name},
            "host_id": host.id,
            "msg_id": msg.id,
            "channel_id": channel.id,
            "min_players": cfg_min,
            "max_players": cfg_max,
            "lobby_secs": lobby_secs,
            "lobby_ends": time.monotonic() + lobby_secs,
            "title": title,
            "desc": desc,
        }
        if extra:
            st.update(extra)
        _ACTIVE[channel.id] = st
        await self._lobby_refresh(st)
        asyncio.create_task(self._lobby_countdown(channel.id))

    async def _lobby_refresh(self, st: dict):
        ch = self.bot.get_channel(st["channel_id"])
        if not ch:
            return
        try:
            msg = await ch.fetch_message(st["msg_id"])
        except Exception:
            return
        players = list((st.get("players") or {}).items())
        lines = [f"**{i}.** <@{uid}>" for i, (uid, _) in enumerate(players, 1)]
        body = "\n".join(lines) if lines else "لا أحد"
        title_map = {
            "kat": "❓ كت", "asra": "⚡ أسرع", "player": "⚽ لاعب",
            "tafkik": "🔤 تفكيك", "tajmee": "🧩 تجميع",
            "silsila": "🔗 سلسلة", "replica": "📋 ريبلكا",
            "sabaq": "🏁 سباق", "lughz": "🧩 لغز", "arqam": "🔢 أرقام",
            "mufrad": "📘 مفرد", "jam": "📚 جمع", "harf": "🔤 حرف مفقود",
            "xo": "⭕ XO", "ghmida": "🙈 غميضة", "khammen": "📍 خمن",
            "aks": "🔄 عكس",
        }
        title = title_map.get(st.get("type"), "🎮 لوبي")
        n = len(players)
        quota = 0
        if st.get("type") == "silsila" and n >= 2:
            fixed = int(st.get("elim_fixed") or 0)
            quota = smart_eliminate_quota(n, fixed)
        extra = ""
        if st.get("type") == "silsila" and n >= 2:
            extra = f"\n📊 هدف الاستبعاد التقريبي لكل جولة: **{quota}** (من {n})"
        mn = int(st.get("min_players") or 1)
        mx = int(st.get("max_players") or 300)
        left = 0
        if st.get("lobby_ends"):
            left = max(0, int(st["lobby_ends"] - time.monotonic()))
        emb = _game_embed(
            f"{title} — انتظار",
            f"**{n}/{mx}** لاعب (الحد الأدنى: {mn}){extra}\n\n{body}\n\n⏱️ باقي **{left}** ثانية · الي يلحق يدخل",
        )
        try:
            await msg.edit(embed=emb, view=LobbyView(self, st["channel_id"], st["type"]))
        except Exception:
            pass


    async def _lobby_countdown(self, channel_id: int):
        """عداد تنازلي ثم بدء تلقائي لمن دخل."""
        while True:
            st = _ACTIVE.get(channel_id)
            if not st or st.get("phase") != "lobby":
                return
            left = int(st.get("lobby_ends", 0) - time.monotonic())
            if left <= 0:
                break
            try:
                await self._lobby_refresh(st)
            except Exception:
                pass
            # كل ثانية لما قرب، وإلا كل 3 ثواني
            await asyncio.sleep(1 if left <= 10 else 3)
        st = _ACTIVE.get(channel_id)
        if not st or st.get("phase") != "lobby":
            return
        ch = self.bot.get_channel(channel_id)
        if not ch:
            await self._clear(channel_id)
            return
        n = len(st.get("players") or {})
        mn = int(st.get("min_players") or 1)
        if n < mn:
            try:
                msg = await ch.fetch_message(st["msg_id"])
                await msg.edit(view=None)
            except Exception:
                pass
            await ch.send(f"⏱️ انتهى الوقت · ما اكتمل العدد ({n}/{mn}).")
            await self._clear(channel_id)
            return
        await self._lobby_start(st, ch)

    async def _lobby_start(self, st: dict, channel):
        gtype = st.get("type")
        st["phase"] = "play"
        # عطّل أزرار اللوبي
        try:
            msg = await channel.fetch_message(st["msg_id"])
            await msg.edit(view=None)
        except Exception:
            pass
        if gtype == "kat":
            await self._run_kat(channel, st)
        elif gtype == "asra":
            await self._run_asra(channel, st)
        elif gtype == "player":
            await self._run_player(channel, st)
        elif gtype == "tafkik":
            await self._run_tafkik(channel, st)
        elif gtype == "tajmee":
            await self._run_tajmee(channel, st)
        elif gtype == "silsila":
            await self._run_silsila(channel, st)
        elif gtype == "replica":
            await self._run_replica(channel, st)
        elif gtype == "sabaq":
            await self._run_sabaq(channel, st)
        elif gtype == "lughz":
            await self._run_lughz(channel, st)
        elif gtype == "arqam":
            await self._run_arqam(channel, st)
        elif gtype == "mufrad":
            await self._run_mufrad(channel, st)
        elif gtype == "jam":
            await self._run_jam(channel, st)
        elif gtype == "harf":
            await self._run_harf(channel, st)
        elif gtype == "xo":
            await self._run_xo(channel, st)
        elif gtype == "ghmida":
            await self._run_ghmida(channel, st)
        elif gtype == "khammen":
            await self._run_khammen(channel, st)
        elif gtype == "aks":
            await self._run_aks(channel, st)



    # ===== كت =====
    @commands.command(name="كت")
    async def cmd_kat(self, ctx: commands.Context):
        st = await self._start_solo(ctx, "kat", "❓ كت")
        if not st:
            return
        await self._run_kat(ctx.channel, st)

    async def _run_kat(self, channel, st):
        q, answers = random.choice(QUESTIONS)
        timeout = await _timeout(channel.guild.id, "kat", 30)
        emb = _game_embed("❓ كت", f"**{q}**\n\nأول واحد يجاوب · {timeout}ث")
        await channel.send(embed=emb)
        st.update({
            "answer": answers if answers == ["*"] else [_norm(a) for a in answers],
            "start": time.monotonic(),
            "host": st["host_id"],
            "allowed": None,  # الكل بالروم
            "type": "kat",
        })
        try:
            await asyncio.wait_for(self._wait_answer(channel.id), timeout=timeout)
        except asyncio.TimeoutError:
            if channel.id in _ACTIVE and _ACTIVE[channel.id].get("type") == "kat":
                await channel.send("⏰ انتهى الوقت — ما في فائز.")
                await self._clear(channel.id)

    # ===== اسرع =====
    @commands.command(name="اسرع")
    async def cmd_asra(self, ctx: commands.Context):
        st = await self._start_solo(ctx, "asra", "asra")
        if st:
            await self._run_asra(ctx.channel, st)


    async def _run_asra(self, channel, st):
        word = random.choice(WORDS)
        timeout = await _timeout(channel.guild.id, "asra", 20)
        emb = _game_embed(
            "⚡ لعبة أسرع",
            f"اكتب الكلمات التالية قبل انتهاء الوقت\n\n# {word}\n\n"
            f"الداخلون فقط · {timeout}ث",
        )
        await channel.send(embed=emb)
        st.update({
            "answer": _norm(word),
            "raw": word,
            "start": time.monotonic(),
            "host": st["host_id"],
            "allowed": None,
        })
        try:
            await asyncio.wait_for(self._wait_answer(channel.id), timeout=timeout)
        except asyncio.TimeoutError:
            if channel.id in _ACTIVE and _ACTIVE[channel.id].get("type") == "asra":
                await channel.send("⏰ انتهى الوقت.")
                await self._clear(channel.id)

    # ===== لاعب =====
    @commands.command(name="لاعب")
    async def cmd_player(self, ctx: commands.Context):
        st = await self._start_solo(ctx, "player", "player")
        if st:
            await self._run_player(ctx.channel, st)


    async def _run_player(self, channel, st):
        name = random.choice(PLAYERS)
        timeout = await _timeout(channel.guild.id, "player", 25)
        emb = _game_embed(
            "⚽ خمّن اللاعب",
            f"من هو اللاعب؟\n\n**تلميح:** `{name[0]}` · حروف: `{len(name)}`\n{timeout}ث",
        )
        await channel.send(embed=emb)
        st.update({
            "answer": _norm(name),
            "raw": name,
            "start": time.monotonic(),
            "host": st["host_id"],
            "allowed": None,
        })
        try:
            await asyncio.wait_for(self._wait_answer(channel.id), timeout=timeout)
        except asyncio.TimeoutError:
            if channel.id in _ACTIVE and _ACTIVE[channel.id].get("type") == "player":
                await channel.send(f"⏰ الجواب: **{name}**")
                await self._clear(channel.id)

    # ===== تفكيك =====
    @commands.command(name="تفكيك")
    async def cmd_tafkik(self, ctx: commands.Context):
        st = await self._start_solo(ctx, "tafkik", "tafkik")
        if st:
            await self._run_tafkik(ctx.channel, st)


    async def _run_tafkik(self, channel, st):
        word = random.choice([w for w in WORDS if " " not in w and 3 <= len(w) <= 10] or WORDS)
        word = word.replace(" ", "")
        shown = _split_word(word)
        timeout = await _timeout(channel.guild.id, "tafkik", 20)
        emb = _game_embed("🔤 تفكيك", f"ركّب الكلمة:\n\n# {shown}\n\n{timeout}ث")
        await channel.send(embed=emb)
        st.update({
            "answer": _norm_spaces(word),
            "raw": word,
            "start": time.monotonic(),
            "host": st["host_id"],
            "space_insensitive": True,
            "allowed": None,
        })
        try:
            await asyncio.wait_for(self._wait_answer(channel.id), timeout=timeout)
        except asyncio.TimeoutError:
            if channel.id in _ACTIVE and _ACTIVE[channel.id].get("type") == "tafkik":
                await channel.send(f"⏰ الجواب: **{word}**")
                await self._clear(channel.id)

    # ===== تجميع =====
    @commands.command(name="تجميع")
    async def cmd_tajmee(self, ctx: commands.Context):
        st = await self._start_solo(ctx, "tajmee", "tajmee")
        if st:
            await self._run_tajmee(ctx.channel, st)


    async def _run_tajmee(self, channel, st):
        word = random.choice([w for w in WORDS if " " not in w and 3 <= len(w) <= 10] or WORDS)
        word = word.replace(" ", "")
        letters = list(word)
        random.shuffle(letters)
        shown = " ".join(letters)
        timeout = await _timeout(channel.guild.id, "tajmee", 20)
        emb = _game_embed("🧩 تجميع", f"رتّب الحروف:\n\n# {shown}\n\n{timeout}ث")
        await channel.send(embed=emb)
        st.update({
            "answer": _norm_spaces(word),
            "raw": word,
            "start": time.monotonic(),
            "host": st["host_id"],
            "space_insensitive": True,
            "allowed": None,
        })
        try:
            await asyncio.wait_for(self._wait_answer(channel.id), timeout=timeout)
        except asyncio.TimeoutError:
            if channel.id in _ACTIVE and _ACTIVE[channel.id].get("type") == "tajmee":
                await channel.send(f"⏰ الجواب: **{word}**")
                await self._clear(channel.id)


    # ===== سلسلة =====
    @commands.command(name="سلسلة")
    async def cmd_silsila(self, ctx: commands.Context, *, start_word: str = None):
        extra = {}
        if start_word:
            extra["seed_word"] = start_word.strip().split()[0]
        await self._open_lobby(
            ctx.channel, ctx.author, "silsila", "🔗 سلسلة",
            "كلمة وراء كلمة حسب آخر حرف · بالترتيب · الغلط أو الوقت = خروج",
            min_players=2,
            extra=extra,
        )

    async def _run_silsila(self, channel, st):
        """جولات مرتبة · الوقت ينقص كل جولة · كلمة واحدة بدون تكرار."""
        base_timeout = await _timeout(channel.guild.id, "silsila", 30)
        st["elim_fixed"] = await _eliminate_setting(channel.guild.id, "silsila")
        word = st.get("seed_word") or random.choice([w for w in WORDS if " " not in w])
        word = word.split()[0]
        order = list(st["players"].keys())
        random.shuffle(order)
        alive = list(order)
        used = {_norm(word)}
        need = _last_letter(word)
        round_no = 1
        # نقص الوقت حسب عدد اللاعبين (كل جولة)
        def _round_timeout(rn: int, nplayers: int) -> int:
            # كل جولة -5ث، مع لاعبين أكثر ينقص أسرع شوي
            step = 5 if nplayers <= 10 else (6 if nplayers <= 20 else 7)
            return max(5, int(base_timeout) - (rn - 1) * step)
        timeout = _round_timeout(1, len(alive))

        await channel.send(
            embed=_game_embed(
                "🔗 بدأت السلسلة",
                f"الكلمة: **{word}** → حرف **{need}**\n"
                f"الترتيب: {', '.join(f'<@{u}>' for u in alive)}\n"
                f"وقت كل لاعب: **{timeout}**ث",
            )
        )

        while len(alive) > 1:
            n = len(alive)
            fixed = int(st.get("elim_fixed") or 0)
            quota = smart_eliminate_quota(n, fixed)
            eliminated_this_round = 0
            timeout = _round_timeout(round_no, n)
            await channel.send(
                f"🔄 **جولة {round_no}** · باقي **{n}** · وقت الدور **{timeout}**ث · هدف استبعاد ~**{quota}**"
            )

            # نسخة من القائمة لأننا نعدّل alive
            turn_list = list(alive)
            for uid in turn_list:
                if uid not in alive:
                    continue
                if len(alive) <= 1:
                    break

                await channel.send(
                    f"🔗 دور <@{uid}> — كلمة تبدأ بـ **{need}** · **{timeout}**ث"
                )
                st.update({
                    "type": "silsila",
                    "phase": "play",
                    "expect_user": uid,
                    "need": need,
                    "used": used,
                    "answered": False,
                    "answer_word": None,
                    "alive": alive,
                    "timeout": timeout,
                    "deadline": time.monotonic() + timeout,
                })

                end_t = time.monotonic() + timeout
                while time.monotonic() < end_t and not st.get("answered"):
                    await asyncio.sleep(0.35)
                    if _ACTIVE.get(channel.id) is not st:
                        return

                if not st.get("answered"):
                    alive = [x for x in alive if x != uid]
                    eliminated_this_round += 1
                    await channel.send(f"⏰ <@{uid}> طلع من السلسلة.")
                else:
                    w = st.get("answer_word") or ""
                    used.add(_norm(w))
                    need = _last_letter(w)
                    await channel.send(f"✅ **{w}** → التالي **{need}**")

                st["alive"] = alive
                st["need"] = need
                st["used"] = used

            # إذا الجولة خلصت وما انقص أحد كفاية والنقص أقل من الهدف: ما نجبر طرد الصح
            # نكمل جولة جديدة طبيعي
            round_no += 1
            if round_no > 40:
                break

        if len(alive) == 1:
            w = alive[0]
            pts = await _add_point(channel.guild.id, w)
            await channel.send(f"🏆 فائز السلسلة: <@{w}> · ⭐ **{pts}**")
            await _log_game(channel.guild, f"🏆 **سلسلة** — فوز <@{w}> · ⭐ {pts} · {channel.mention}")
        else:
            await channel.send("انتهت السلسلة بدون فائز واضح.")
        await self._clear(channel.id)


    # ===== ريبلكا =====
    @commands.command(name="ريبلكا")
    async def cmd_replica(self, ctx: commands.Context):
        await self._open_lobby(
            ctx.channel, ctx.author, "replica", "📋 ريبلكا",
            "فئات بالدور · آخر واحد يبقى = **يخسر**",
            min_players=2,
        )

    async def _run_replica(self, channel, st):
        timeout = await _timeout(channel.guild.id, "replica", 30)
        st["timeout"] = timeout
        st["players"] = dict(st["players"])
        await self._replica_round(channel, st)


    # ===== سباق =====
    @commands.command(name="سباق")
    async def cmd_sabaq(self, ctx: commands.Context):
        if not await _can_start(ctx.author, "sabaq"):
            return await ctx.reply("ما عندك صلاحية بدء هاللعبة.")
        cfg = await _cfg(ctx.guild.id)
        target = int(cfg.get("race_target") or 10)
        await self._open_lobby(
            ctx.channel, ctx.author, "sabaq", "🏁 سباق",
            f"أسئلة اختيار من متعدد · أول من يصل **{target}** نقاط يفوز",
            min_players=1,
        )

    async def _run_sabaq(self, channel, st):
        cfg = await _cfg(channel.guild.id)
        target = int(cfg.get("race_target") or 10)
        timeout = await _timeout(channel.guild.id, "sabaq", 20)
        scores = {uid: 0 for uid in st["players"]}
        st.update({"scores": scores, "target": target, "timeout": timeout, "phase": "play", "answered_round": set()})
        await channel.send(embed=_game_embed("🏁 بدأ السباق", f"الهدف: **{target}** نقطة · وقت السؤال: **{timeout}**ث"))
        await self._sabaq_round(channel, st)

    async def _sabaq_round(self, channel, st):
        if channel.id not in _ACTIVE:
            return
        q, opts, ans = random.choice(RACE_QUESTIONS)
        st["race_ans"] = ans
        st["answered_round"] = set()
        timeout = int(st.get("timeout") or 20)
        scores = st["scores"]
        # لوحة ترتيب
        board = sorted(scores.items(), key=lambda x: -x[1])
        lines = []
        for i in range(max(st["target"], 10), 0, -1):
            holders = [f"<@{u}>" for u, s in board if s == i]
            if holders:
                lines.append(f"**{i}** — {' '.join(holders[:8])}")
        board_txt = "\n".join(lines) if lines else "لا نقاط بعد"
        emb = _game_embed("🏁 سباق", f"{board_txt}\n\n**{q}**")
        view = RaceAnswerView(self, channel.id, opts)
        msg = await channel.send(embed=emb, view=view)
        st["race_msg"] = msg.id
        await asyncio.sleep(timeout)
        if _ACTIVE.get(channel.id) is not st:
            return
        try:
            await msg.edit(view=None)
        except Exception:
            pass
        # فائز؟
        for uid, sc in st["scores"].items():
            if sc >= st["target"]:
                pts = await _add_point(channel.guild.id, uid)
                await channel.send(f"🏆 فائز السباق: <@{uid}> · ⭐ **{pts}**")
                await self._clear(channel.id)
                return
        await self._sabaq_round(channel, st)

    # ===== لغز =====
    @commands.command(name="لغز")
    async def cmd_lughz(self, ctx):
        st = await self._start_solo(ctx, "lughz", "🧩 لغز")
        if st:
            await self._run_lughz(ctx.channel, st)

    async def _run_lughz(self, channel, st):
        q, answers = random.choice(RIDDLES)
        timeout = await _timeout(channel.guild.id, "lughz", 30)
        emb = _game_embed("🧩 لعبة لغز", f"أجب على اللغز التالي قبل انتهاء الوقت\n\n# {q}\n\nبواسطة <@{st['host_id']}>")
        emb.set_footer(text=f"{timeout} ثانية")
        await channel.send(embed=emb)
        st.update({
            "answer": [_norm(a) for a in answers],
            "start": time.monotonic(),
            "host": st["host_id"],
            "allowed": None,
            "type": "lughz",
        })
        try:
            await asyncio.wait_for(self._wait_answer(channel.id), timeout=timeout)
        except asyncio.TimeoutError:
            if channel.id in _ACTIVE and _ACTIVE[channel.id].get("type") == "lughz":
                await channel.send(f"⏰ انتهى الوقت. الجواب: **{answers[0]}**")
                await self._clear(channel.id)

    # ===== أرقام =====
    @commands.command(name="ارقام", aliases=["أرقام"])
    async def cmd_arqam(self, ctx):
        st = await self._start_solo(ctx, "arqam", "🔢 أرقام")
        if st:
            await self._run_arqam(ctx.channel, st)

    async def _run_arqam(self, channel, st):
        num = str(random.randint(100000, 9999999))
        timeout = await _timeout(channel.guild.id, "arqam", 15)
        emb = _game_embed("🔢 لعبة أرقام", f"اكتب الأرقام التالية قبل انتهاء الوقت\n\n# {num}\n\nبواسطة <@{st['host_id']}>")
        emb.set_footer(text=f"{timeout}ث")
        await channel.send(embed=emb)
        st.update({
            "answer": num,
            "start": time.monotonic(),
            "host": st["host_id"],
            "allowed": None,
            "type": "arqam",
            "exact": True,
        })
        try:
            await asyncio.wait_for(self._wait_answer(channel.id), timeout=timeout)
        except asyncio.TimeoutError:
            if channel.id in _ACTIVE and _ACTIVE[channel.id].get("type") == "arqam":
                await channel.send("⏰ انتهى الوقت.")
                await self._clear(channel.id)

    # ===== مفرد =====
    @commands.command(name="مفرد")
    async def cmd_mufrad(self, ctx):
        st = await self._start_solo(ctx, "mufrad", "📘 مفرد")
        if st:
            await self._run_mufrad(ctx.channel, st)

    async def _run_mufrad(self, channel, st):
        plural, singular = random.choice(list(PLURAL_TO_SING.items()))
        timeout = await _timeout(channel.guild.id, "mufrad", 15)
        emb = _game_embed("📘 لعبة مفرد", f"اكتب مفرد الكلمة التالية قبل انتهاء الوقت\n\n# {plural}\n\nبواسطة <@{st['host_id']}>")
        emb.set_footer(text=f"{timeout}ث")
        await channel.send(embed=emb)
        st.update({
            "answer": _norm(singular),
            "start": time.monotonic(),
            "host": st["host_id"],
            "allowed": None,
            "type": "mufrad",
        })
        try:
            await asyncio.wait_for(self._wait_answer(channel.id), timeout=timeout)
        except asyncio.TimeoutError:
            if channel.id in _ACTIVE and _ACTIVE[channel.id].get("type") == "mufrad":
                await channel.send(f"⏰ الجواب: **{singular}**")
                await self._clear(channel.id)

    # ===== جمع =====
    @commands.command(name="جمع")
    async def cmd_jam(self, ctx):
        st = await self._start_solo(ctx, "jam", "📚 جمع")
        if st:
            await self._run_jam(ctx.channel, st)

    async def _run_jam(self, channel, st):
        singular, plural = random.choice(list(SING_TO_PLURAL.items()))
        timeout = await _timeout(channel.guild.id, "jam", 15)
        emb = _game_embed("📚 لعبة جمع", f"اكتب جمع الكلمة التالية قبل انتهاء الوقت\n\n# {singular}\n\nبواسطة <@{st['host_id']}>")
        emb.set_footer(text=f"{timeout}ث")
        await channel.send(embed=emb)
        st.update({
            "answer": _norm(plural),
            "start": time.monotonic(),
            "host": st["host_id"],
            "allowed": None,
            "type": "jam",
        })
        try:
            await asyncio.wait_for(self._wait_answer(channel.id), timeout=timeout)
        except asyncio.TimeoutError:
            if channel.id in _ACTIVE and _ACTIVE[channel.id].get("type") == "jam":
                await channel.send(f"⏰ الجواب: **{plural}**")
                await self._clear(channel.id)

    # ===== حرف مفقود =====
    @commands.command(name="حرف")
    async def cmd_harf(self, ctx):
        st = await self._start_solo(ctx, "harf", "🔤 حرف مفقود")
        if st:
            await self._run_harf(ctx.channel, st)

    async def _run_harf(self, channel, st):
        word = random.choice([w for w in WORDS if " " not in w and 3 <= len(w) <= 8] or ["قلب", "كتاب", "باب"])
        word = word.replace(" ", "")
        idx = random.randrange(len(word))
        shown = word[:idx] + "ـ" + word[idx + 1:]
        timeout = await _timeout(channel.guild.id, "harf", 15)
        emb = _game_embed("🔤 لعبة حرف مفقود", f"اكتشف الحرف المفقود واكتب الكلمة كاملة قبل انتهاء الوقت\n\n# {shown}\n\nبواسطة <@{st['host_id']}>")
        emb.set_footer(text=f"{timeout}ث")
        await channel.send(embed=emb)
        st.update({
            "answer": _norm(word),
            "start": time.monotonic(),
            "host": st["host_id"],
            "allowed": None,
            "type": "harf",
        })
        try:
            await asyncio.wait_for(self._wait_answer(channel.id), timeout=timeout)
        except asyncio.TimeoutError:
            if channel.id in _ACTIVE and _ACTIVE[channel.id].get("type") == "harf":
                await channel.send(f"⏰ الجواب: **{word}**")
                await self._clear(channel.id)

    # ===== XO =====
    @commands.command(name="xo", aliases=["XO", "اكس"])
    async def cmd_xo(self, ctx):
        if not await _can_start(ctx.author, "xo"):
            return await ctx.reply("ما عندك صلاحية بدء هاللعبة.")
        await self._open_lobby(ctx.channel, ctx.author, "xo", "⭕ XO", "لعبة إكس أو · لاعبان", 2)

    async def _run_xo(self, channel, st):
        players = list(st["players"].keys())
        if len(players) < 2:
            await channel.send("لازم لاعبين.")
            await self._clear(channel.id)
            return
        random.shuffle(players)
        p1, p2 = players[0], players[1]
        board = [" "] * 9
        st.update({"board": board, "p1": p1, "p2": p2, "turn": p1, "phase": "play", "type": "xo"})
        view = XOView(self, channel.id)
        emb = _game_embed("⭕ XO", f"❌ <@{p1}> ضد ⭕ <@{p2}>\nالدور: <@{p1}>")
        msg = await channel.send(embed=emb, view=view)
        st["msg_id"] = msg.id

    # ===== غميضة =====
    @commands.command(name="غميضة")
    async def cmd_ghmida(self, ctx):
        if not await _can_start(ctx.author, "ghmida"):
            return await ctx.reply("ما عندك صلاحية بدء هاللعبة.")
        await self._open_lobby(
            ctx.channel, ctx.author, "ghmida", "🙈 غميضة",
            "اختبئوا في الأماكن · كل جولة ينكشف بعض الأماكن حتى يبقى آخر واحد",
            2,
        )

    async def _run_ghmida(self, channel, st):
        players = list(st["players"].keys())
        n = len(players)
        # أماكن أكثر من اللاعبين (~1.4x)
        need = min(len(HIDE_PLACES), max(n + 5, int(n * 1.4)))
        places = random.sample(HIDE_PLACES, need)
        timeout = await _timeout(channel.guild.id, "ghmida", 30)
        st["elim_fixed"] = await _eliminate_setting(channel.guild.id, "ghmida")
        # توزيع عشوائي أولي
        random.shuffle(places)
        assignment = {}
        for i, uid in enumerate(players):
            assignment[uid] = places[i]
        free = places[n:]
        st.update({
            "assignment": assignment,
            "places": places,
            "free": free,
            "timeout": timeout,
            "phase": "play",
            "type": "ghmida",
        })
        # DM each player their place
        for uid, place in assignment.items():
            m = channel.guild.get_member(uid)
            if m:
                try:
                    await m.send(f"🙈 مكانك في الغميضة: **{place}**\nالسيرفر: {channel.guild.name}")
                except Exception:
                    pass
        await channel.send(
            embed=_game_embed(
                "🙈 بدأت الغميضة",
                f"**{n}** لاعب · **{need}** مكان\nالأماكن انرسلت بالخاص.\nكل جولة ينكشف بعض الأماكن!",
            )
        )
        await asyncio.sleep(3)
        while len(st["assignment"]) > 1:
            alive = list(st["assignment"].items())
            # استبعاد ذكي
            quota = smart_eliminate_quota(len(alive), int(st.get("elim_fixed") or 0))
            quota = min(quota, len(alive) - 1)
            victims = random.sample(alive, quota)
            for uid, place in victims:
                st["assignment"].pop(uid, None)
                await channel.send(f"🔦 انكشف **{place}** — <@{uid}> طلع!")
            if len(st["assignment"]) <= 1:
                break
            await channel.send(f"باقي **{len(st['assignment'])}** مختبئين… الجولة الجاية بعد {timeout}ث")
            await asyncio.sleep(timeout)
        if st["assignment"]:
            uid = next(iter(st["assignment"]))
            pts = await _add_point(channel.guild.id, uid)
            await channel.send(f"🏆 آخر مختبئ: <@{uid}> · ⭐ **{pts}**")
        await self._clear(channel.id)

    # ===== خمن =====
    @commands.command(name="خمن")
    async def cmd_khammen(self, ctx):
        st = await self._start_solo(ctx, "khammen", "📍 خمن")
        if st:
            await self._run_khammen(ctx.channel, st)

    async def _run_khammen(self, channel, st):
        name, hint = random.choice(GUESS_PLACES)
        timeout = await _timeout(channel.guild.id, "khammen", 40)
        emb = _game_embed("📍 خمن المكان", f"**تلميح:** {hint}\n\nما هو اسم المكان؟\nبواسطة <@{st['host_id']}>")
        emb.set_footer(text=f"{timeout}ث")
        await channel.send(embed=emb)
        st.update({
            "answer": _norm(name),
            "raw": name,
            "start": time.monotonic(),
            "host": st["host_id"],
            "allowed": None,
            "type": "khammen",
        })
        try:
            await asyncio.wait_for(self._wait_answer(channel.id), timeout=timeout)
        except asyncio.TimeoutError:
            if channel.id in _ACTIVE and _ACTIVE[channel.id].get("type") == "khammen":
                await channel.send(f"⏰ الجواب: **{name}**")
                await self._clear(channel.id)



    # ===== عكس =====
    @commands.command(name="عكس")
    async def cmd_aks(self, ctx: commands.Context):
        st = await self._start_solo(ctx, "aks", "aks")
        if st:
            await self._run_aks(ctx.channel, st)


    async def _run_aks(self, channel, st):
        pool = [w for w in WORDS if " " not in w and 3 <= len(w) <= 12] or list(WORDS)
        word = random.choice(pool).replace(" ", "")
        reversed_word = word[::-1]
        if reversed_word == word:
            word = random.choice([w for w in pool if len(w) >= 4] or ["كتاب"]).replace(" ", "")
            reversed_word = word[::-1]
        timeout = await _timeout(channel.guild.id, "aks", 15)
        desc = (
            "اكتب الكلمة بالاتجاه الصحيح قبل انتهاء الوقت"
            + chr(10) + chr(10)
            + f"# {reversed_word}"
            + chr(10) + chr(10)
            + f"بواسطة <@{st['host_id']}>"
        )
        emb = _game_embed("🔄 لعبة عكس", desc)
        emb.set_footer(text=f"{timeout}ث")
        await channel.send(embed=emb)
        st.update({
            "answer": _norm(word),
            "raw": word,
            "start": time.monotonic(),
            "host": st["host_id"],
            "allowed": None,
            "type": "aks",
        })
        try:
            await asyncio.wait_for(self._wait_answer(channel.id), timeout=timeout)
        except asyncio.TimeoutError:
            if channel.id in _ACTIVE and _ACTIVE[channel.id].get("type") == "aks":
                await channel.send(f"⏰ انتهى الوقت. الجواب: **{word}**")
                await self._clear(channel.id)

    # ===== روليت =====
    @commands.command(name="روليت")
    async def cmd_roulette(self, ctx: commands.Context):
        if self._busy(ctx.channel.id):
            return await ctx.reply("في لعبة شغّالة هنا.")
        cfg = await _cfg(ctx.guild.id)
        per = int(cfg.get("roulette_max_per_page") or 20)
        timeout = await _timeout(ctx.guild.id, "roulette", 30)
        emb = _game_embed(
            "🎡 روليت",
            "**طريقة اللعب:**\n"
            "1- اضغط دخول\n"
            "2- عند البدء يُختار لاعب عشوائي\n"
            "3- المختار يطرد لاعب خلال الوقت\n"
            "4- آخر لاعب يبقى = الفائز\n\n"
            f"**اللاعبون (0):** لا أحد بعد\n"
            f"وقت الاختيار: {timeout}ث",
        )
        view = RouletteJoinView(self, ctx.channel.id)
        msg = await ctx.send(embed=emb, view=view)
        _mn, _mx = await _player_limits(ctx.guild.id, "roulette", 2, 1000)
        _ACTIVE[ctx.channel.id] = {
            "type": "roulette",
            "phase": "join",
            "players": {ctx.author.id: ctx.author.display_name},
            "host_id": ctx.author.id,
            "msg_id": msg.id,
            "per_page": per,
            "timeout": timeout,
            "channel_id": ctx.channel.id,
            "min_players": _mn,
            "max_players": _mx,
        }
        await self._roulette_refresh(_ACTIVE[ctx.channel.id])

    async def _roulette_refresh(self, st: dict):
        ch = self.bot.get_channel(st["channel_id"])
        if not ch:
            return
        try:
            msg = await ch.fetch_message(st["msg_id"])
        except Exception:
            return
        players = list(st["players"].items())
        lines = []
        for i, (uid, name) in enumerate(players, 1):
            lines.append(f"**{i}:** <@{uid}>")
        body = "\n".join(lines) if lines else "لا أحد"
        emb = _game_embed(
            "🎡 روليت",
            "**طريقة اللعب:**\n"
            "1- دخول  2- بدء  3- المختار يطرد  4- آخر واحد يفوز\n\n"
            f"**اللاعبون ({len(players)}):**\n{body}",
        )
        try:
            await msg.edit(embed=emb, view=RouletteJoinView(self, st["channel_id"]))
        except Exception:
            pass

    async def _roulette_begin(self, st: dict):
        st["phase"] = "play"
        ch = self.bot.get_channel(st["channel_id"])
        await self._roulette_turn(ch, st)

    async def _roulette_turn(self, channel, st: dict):
        players = list(st["players"].keys())
        if len(players) <= 1:
            winner = players[0] if players else None
            if winner:
                pts = await _add_point(channel.guild.id, winner)
                await channel.send(f"🏆 الفائز بالروليت: <@{winner}> · نجوم: **{pts}**")
            else:
                await channel.send("انتهت الروليت بدون فائز.")
            await self._clear(channel.id)
            return

        chooser = random.choice(players)
        st["chooser"] = chooser
        timeout = int(st.get("timeout") or 30)
        emb = _game_embed(
            "🎡 اختيار للطرد",
            f"<@{chooser}> عندك **{timeout}** ثانية تختار مين تطرد.\n"
            f"الباقي: **{len(players)}** لاعب",
        )
        view = RoulettePickView(self, channel.id, chooser, 0)
        msg = await channel.send(embed=emb, view=view)
        st["pick_msg"] = msg.id
        st["deadline"] = time.monotonic() + timeout

        async def _timer():
            await asyncio.sleep(timeout)
            cur = _ACTIVE.get(channel.id)
            if not cur or cur.get("chooser") != chooser or cur.get("phase") != "play":
                return
            # انتهى الوقت → المختار ينطرد
            cur["players"].pop(chooser, None)
            await channel.send(f"⏰ <@{chooser}> ما اختار — انطرد.")
            await self._roulette_turn(channel, cur)

        asyncio.create_task(_timer())

    async def _roulette_kick(self, interaction: discord.Interaction, channel_id: int, chooser_id: int, target_id: int):
        st = _ACTIVE.get(channel_id)
        if not st or st.get("type") != "roulette" or st.get("phase") != "play":
            await interaction.response.send_message("اللعبة خلصت.", ephemeral=True)
            return
        if interaction.user.id != chooser_id or st.get("chooser") != chooser_id:
            await interaction.response.send_message("مو دورك.", ephemeral=True)
            return
        if target_id not in st["players"] or target_id == chooser_id:
            await interaction.response.send_message("هدف غير صالح.", ephemeral=True)
            return
        name = st["players"].pop(target_id)
        await interaction.response.send_message(f"تم طرد **{name}**", ephemeral=True)
        ch = interaction.channel
        await ch.send(f"🚪 <@{target_id}> انطرد بواسطة <@{chooser_id}>")
        st["chooser"] = None
        await self._roulette_turn(ch, st)

    async def _roulette_self_out(self, interaction: discord.Interaction, channel_id: int, chooser_id: int):
        st = _ACTIVE.get(channel_id)
        if not st or st.get("chooser") != chooser_id:
            await interaction.response.send_message("ما عاد دورك.", ephemeral=True)
            return
        st["players"].pop(chooser_id, None)
        st["chooser"] = None
        await interaction.response.send_message("انسحبت.", ephemeral=True)
        await interaction.channel.send(f"🚪 <@{chooser_id}> انسحب.")
        await self._roulette_turn(interaction.channel, st)

    # ===== مافيا =====
    @commands.command(name="مافيا")
    async def cmd_mafia(self, ctx: commands.Context):
        if self._busy(ctx.channel.id):
            return await ctx.reply("في لعبة شغّالة هنا.")
        cfg = await _cfg(ctx.guild.id)
        mcfg = cfg.get("mafia") or {}
        min_p = int(mcfg.get("min_players") or 5)
        max_p = int(mcfg.get("max_players") or 300)
        max_p = max(min_p, min(300, max_p))
        timeout = await _timeout(ctx.guild.id, "mafia", 30)
        emb = _game_embed(
            "🔪 مافيا",
            f"أقل عدد: **{min_p}**\nوقت الجولات: **{timeout}**ث\n"
            "الأدوار تُرسل بالخاص.\nاضغط دخول ثم يبدأ المضيف.",
        )
        view = MafiaJoinView(self, ctx.channel.id)
        msg = await ctx.send(embed=emb, view=view)
        _ACTIVE[ctx.channel.id] = {
            "type": "mafia",
            "phase": "join",
            "players": {ctx.author.id: ctx.author.display_name},
            "host_id": ctx.author.id,
            "msg_id": msg.id,
            "channel_id": ctx.channel.id,
            "timeout": timeout,
            "min_players": min_p,
            "max_players": max_p,
        }
        await self._mafia_refresh(_ACTIVE[ctx.channel.id])

    async def _mafia_refresh(self, st: dict):
        ch = self.bot.get_channel(st["channel_id"])
        if not ch:
            return
        try:
            msg = await ch.fetch_message(st["msg_id"])
        except Exception:
            return
        names = ", ".join(f"<@{u}>" for u in st["players"])
        emb = _game_embed("🔪 مافيا — انتظار", f"**{len(st['players'])}** لاعب:\n{names}")
        try:
            await msg.edit(embed=emb, view=MafiaJoinView(self, st["channel_id"]))
        except Exception:
            pass

    def _mafia_roles(self, n: int, mafia_fixed: int, doctor_fixed: int) -> dict:
        """توزيع منطقي حتى 100 لاعب."""
        n = max(3, min(300, int(n)))
        if mafia_fixed > 0:
            mafia = min(mafia_fixed, n - 2)
        else:
            # ~20-25% مافيا، يتدرج مع العدد
            if n <= 6:
                mafia = 1
            elif n <= 10:
                mafia = 2
            elif n <= 16:
                mafia = 3
            elif n <= 24:
                mafia = max(4, n // 5)
            elif n <= 40:
                mafia = max(6, n // 5)
            elif n <= 70:
                mafia = max(10, n // 5)
            else:
                mafia = max(15, n // 5)
            mafia = min(mafia, n // 3)  # ما تتجاوز ثلث تقريباً
        if doctor_fixed > 0:
            doctor = min(doctor_fixed, n - mafia - 1)
        else:
            if n < 5:
                doctor = 0
            elif n <= 12:
                doctor = 1
            elif n <= 25:
                doctor = 2
            elif n <= 50:
                doctor = 3
            else:
                doctor = 4
        if mafia + doctor >= n:
            mafia = max(1, n // 4)
            doctor = 1 if n - mafia >= 2 else 0
        villagers = n - mafia - doctor
        return {"mafia": mafia, "doctor": doctor, "villager": max(0, villagers)}

    async def _mafia_begin(self, st: dict, channel):
        cfg = await _cfg(channel.guild.id)
        mcfg = cfg.get("mafia") or {}
        ids = list(st["players"].keys())
        random.shuffle(ids)
        counts = self._mafia_roles(
            len(ids),
            int(mcfg.get("mafia_count") or 0),
            int(mcfg.get("doctor_count") or 0),
        )
        roles = {}
        idx = 0
        for _ in range(counts["mafia"]):
            roles[ids[idx]] = "مافيا"
            idx += 1
        for _ in range(counts["doctor"]):
            roles[ids[idx]] = "طبيب"
            idx += 1
        for u in ids[idx:]:
            roles[u] = "مواطن"

        st["roles"] = roles
        st["alive"] = set(ids)
        st["phase"] = "night"
        st["night"] = 1

        for uid, role in roles.items():
            member = channel.guild.get_member(uid)
            if not member:
                continue
            try:
                await member.send(f"🎭 دورك في المافيا: **{role}**\nالسيرفر: {channel.guild.name}")
            except Exception:
                pass

        await channel.send(
            embed=_game_embed(
                "🔪 بدأت المافيا",
                f"مافيا: **{counts['mafia']}** · طبيب: **{counts['doctor']}** · مواطنين: **{counts['villager']}**\n"
                "الأدوار انرسلت بالخاص. الليل يبدأ…",
            )
        )
        await self._mafia_night(channel, st)

    async def _mafia_night(self, channel, st: dict):
        timeout = int(st.get("timeout") or 30)
        alive = st["alive"]
        mafia = [u for u in alive if st["roles"].get(u) == "مافيا"]
        doctor = [u for u in alive if st["roles"].get(u) == "طبيب"]

        await channel.send(f"🌙 ليل {st['night']} — المافيا تختار ضحية والطبيب يحمي ({timeout}ث)…")

        # تصويت المافيا بالخاص مبسّط: اختيار عشوائي ذكي إن ما ردوا — للتبسيط نطلب من أول مافيا في الشات
        st["phase"] = "night_kill"
        st["kill_votes"] = {}
        st["save"] = None
        st["deadline"] = time.monotonic() + timeout

        alive_mentions = ", ".join(f"<@{u}>" for u in alive)
        if mafia:
            await channel.send(
                f"🔪 مافيا ({', '.join(f'<@{u}>' for u in mafia)}): اكتبوا `قتل @شخص` خلال {timeout}ث\nالأحياء: {alive_mentions}"
            )
        if doctor:
            await channel.send(
                f"💉 طبيب ({', '.join(f'<@{u}>' for u in doctor)}): اكتبوا `حمي @شخص` خلال {timeout}ث"
            )

        await asyncio.sleep(timeout)
        if _ACTIVE.get(channel.id) is not st:
            return

        # تنفيذ القتل
        votes = st.get("kill_votes") or {}
        target = None
        if votes:
            target = max(votes, key=lambda k: votes[k])
        elif mafia:
            target = random.choice(list(alive - set(mafia))) if len(alive) > len(mafia) else random.choice(list(alive))

        saved = st.get("save")
        killed = None
        if target and target != saved and target in st["alive"]:
            st["alive"].discard(target)
            killed = target

        if killed:
            await channel.send(f"☠️ قُتل <@{killed}> هذه الليلة.")
        else:
            await channel.send("✨ ما مات أحد هذه الليلة.")

        if await self._mafia_check_end(channel, st):
            return
        await self._mafia_day(channel, st)

    async def _mafia_day(self, channel, st: dict):
        timeout = int(st.get("timeout") or 30)
        st["phase"] = "day"
        st["day_votes"] = {}
        alive = list(st["alive"])
        await channel.send(
            f"☀️ نهار {st['night']} — صوّتوا للطرد: `طرد @شخص` خلال {timeout}ث\n"
            f"الأحياء: {', '.join(f'<@{u}>' for u in alive)}"
        )
        await asyncio.sleep(timeout)
        if _ACTIVE.get(channel.id) is not st:
            return

        votes = st.get("day_votes") or {}
        if votes:
            target = max(votes, key=lambda k: votes[k])
            if target in st["alive"]:
                st["alive"].discard(target)
                role = st["roles"].get(target, "?")
                await channel.send(f"⚖️ الطرد: <@{target}> كان **{role}**")
        else:
            await channel.send("ما تم طرد أحد.")

        if await self._mafia_check_end(channel, st):
            return
        st["night"] += 1
        await self._mafia_night(channel, st)

    async def _mafia_check_end(self, channel, st: dict) -> bool:
        alive = st["alive"]
        mafia_alive = [u for u in alive if st["roles"].get(u) == "مافيا"]
        village = [u for u in alive if st["roles"].get(u) != "مافيا"]
        if not mafia_alive:
            await channel.send("🏆 فاز **المواطنون** — المافيا انقرضت!")
            for u in village:
                await _add_point(channel.guild.id, u)
            await self._clear(channel.id)
            return True
        if len(mafia_alive) >= len(village):
            await channel.send("💀 فازت **المافيا**!")
            for u in mafia_alive:
                await _add_point(channel.guild.id, u)
            await self._clear(channel.id)
            return True
        return False

    # ===== انتظار جواب أسرع/كت/… =====

    async def _sabaq_answer(self, interaction: discord.Interaction, channel_id: int, idx: int, label: str):
        st = _ACTIVE.get(channel_id)
        if not st or st.get("type") != "sabaq":
            await interaction.response.send_message("ما في سباق.", ephemeral=True)
            return
        uid = interaction.user.id
        if uid not in st.get("scores", {}):
            await interaction.response.send_message("أنت مو داخل السباق.", ephemeral=True)
            return
        if uid in st.get("answered_round", set()):
            await interaction.response.send_message("جاوبت بهالجولة.", ephemeral=True)
            return
        st.setdefault("answered_round", set()).add(uid)
        if idx == st.get("race_ans"):
            st["scores"][uid] = st["scores"].get(uid, 0) + 1
            await interaction.response.send_message(
                f"✅ صحيح! نقاطك: **{st['scores'][uid]}**", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ خطأ. اخترت {label}. ما زادت نقاطك.", ephemeral=True
            )

    async def _xo_click(self, interaction: discord.Interaction, channel_id: int, idx: int):
        st = _ACTIVE.get(channel_id)
        if not st or st.get("type") != "xo":
            await interaction.response.send_message("ما في XO.", ephemeral=True)
            return
        uid = interaction.user.id
        if uid != st.get("turn"):
            await interaction.response.send_message("مو دورك.", ephemeral=True)
            return
        board = st["board"]
        if board[idx] != " ":
            await interaction.response.send_message("مأخوذة.", ephemeral=True)
            return
        mark = "X" if uid == st["p1"] else "O"
        board[idx] = mark
        # win check
        wins = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
        won = any(board[a] == board[b] == board[c] == mark for a,b,c in wins)
        draw = all(c != " " for c in board)
        st["turn"] = st["p2"] if uid == st["p1"] else st["p1"]
        # rebuild view labels
        view = XOView(self, channel_id)
        for i, item in enumerate(view.children):
            if isinstance(item, discord.ui.Button) and i < 9:
                item.label = board[i] if board[i] != " " else "·"
                item.disabled = board[i] != " " or won or draw
        if won:
            pts = await _add_point(interaction.guild.id, uid)
            emb = _game_embed("⭕ XO", f"🏆 فاز <@{uid}> ({mark}) · ⭐ **{pts}**")
            await interaction.response.edit_message(embed=emb, view=view)
            await self._clear(channel_id)
            return
        if draw:
            emb = _game_embed("⭕ XO", "تعادل!")
            await interaction.response.edit_message(embed=emb, view=view)
            await self._clear(channel_id)
            return
        emb = _game_embed(
            "⭕ XO",
            f"❌ <@{st['p1']}> ضد ⭕ <@{st['p2']}>\nالدور: <@{st['turn']}>",
        )
        await interaction.response.edit_message(embed=emb, view=view)

    async def _wait_answer(self, channel_id: int):
        """يُلغى من on_message عند الفوز."""
        while channel_id in _ACTIVE:
            await asyncio.sleep(0.5)

    async def _win(self, message: discord.Message, st: dict):
        elapsed = time.monotonic() - st.get("start", time.monotonic())
        pts = await _add_point(message.guild.id, message.author.id)
        game = st.get("type", "")
        emb = _game_embed(
            "✅ فوز!",
            f"{message.author.mention} جاوب خلال **{elapsed:.2f}** ثانية\n"
            f"⭐ نقاطه: **{pts}** (+1)",
            color=discord.Color.green(),
        )
        view = PlayAgainView(self, game if game in ("kat", "asra", "player", "tafkik", "tajmee") else "asra", st.get("host") or message.author.id)
        await message.channel.send(embed=emb, view=view)
        await self._clear(message.channel.id)

    # ===== مستمع الرسائل =====
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        st = _ACTIVE.get(message.channel.id)
        if not st:
            return
        content = message.content or ""
        typ = st.get("type")

        # لوبي — تجاهل الرسائل
        if st.get("phase") == "lobby":
            return

        # ألعاب الجواب السريع
        if typ in ("kat", "asra", "player", "tafkik", "tajmee", "lughz", "arqam", "mufrad", "jam", "harf", "khammen", "aks"):
            allowed = st.get("allowed")
            if allowed is not None and message.author.id not in allowed:
                return
            if st.get("space_insensitive"):
                ok = _norm_spaces(content) == st.get("answer")
            elif typ == "kat":
                # أسئلة نقاش: أي جواب غير فاضي يفوز
                ans = st.get("answer") or []
                if ans == ["*"] or (isinstance(ans, list) and "*" in ans):
                    ok = bool(content.strip())
                else:
                    ok = _norm(content) in [_norm(a) for a in ans]
            elif typ in ("lughz",) or isinstance(st.get("answer"), list):
                ans = st.get("answer") or []
                ok = _norm(content) in ans if isinstance(ans, list) else _norm(content) == ans
            elif st.get("exact"):
                ok = content.strip() == st.get("answer")
            else:
                ok = _norm(content) == st.get("answer")
            if ok:
                await self._win(message, st)
            return

        # سلسلة — دور مرتب
        if typ == "silsila" and st.get("phase") == "play":
            if message.author.id != st.get("expect_user"):
                return
            parts = content.strip().split()
            # كلمة واحدة فقط — "احمد حميدو" مرفوض
            if len(parts) != 1:
                await message.add_reaction("❌")
                try:
                    await message.reply("كلمة **واحدة** فقط (بدون مسافات).", mention_author=False, delete_after=5)
                except Exception:
                    pass
                return
            word = parts[0]
            if not word:
                return
            used = st.get("used") or set()
            if _norm(word) in used:
                await message.add_reaction("🔁")
                try:
                    await message.reply("الكلمة مكررة.", mention_author=False, delete_after=5)
                except Exception:
                    pass
                return
            need = st.get("need", "")
            first = word[0]
            if first in "أإآا":
                first = "ا"
            need_cmp = "ا" if need in "أإآا" else need
            if first != need_cmp:
                await message.add_reaction("❌")
                return
            st["answered"] = True
            st["answer_word"] = word
            await message.add_reaction("✅")
            return

        # ريبلكا انضمام قديم — ملغي (صار بالزرار)

        # ريبلكا دور
        if typ == "replica_turn":
            if message.author.id != st.get("expect_user"):
                return
            word = content.strip().split()[0] if content.strip() else ""
            if not word:
                return
            letter = st.get("expect_letter", "")
            cat = st.get("expect_cat", "")
            first = word[0]
            if first in "أإآا":
                first = "ا"
            need = letter
            if need in "أإآا":
                need = "ا"
            letter_ok = first == need or _norm(word).startswith(_norm(letter)[:1] if letter else "")
            cat_ok = word_in_category(word, cat) or word_in_category(_norm(word), cat)
            # أيضاً جرب بدون أل
            if not cat_ok and word.startswith("ال"):
                cat_ok = word_in_category(word[2:], cat)
            if letter_ok and cat_ok:
                st["answered"] = True
                await message.add_reaction("✅")
            else:
                # توضيح سبب الرفض بشكل خفيف
                if not letter_ok:
                    await message.add_reaction("❌")
                elif not cat_ok:
                    await message.add_reaction("❓")  # الحرف صح بس الكلمة مش من الفئة / مو بالقائمة
                else:
                    await message.add_reaction("❌")
            return

        # مافيا أوامر ليل/نهار
        if typ == "mafia":
            phase = st.get("phase")
            if message.author.id not in st.get("alive", set()):
                return
            if phase == "night_kill" and content.startswith("قتل") and st["roles"].get(message.author.id) == "مافيا":
                if message.mentions:
                    t = message.mentions[0].id
                    if t in st["alive"]:
                        st.setdefault("kill_votes", {})[t] = st.get("kill_votes", {}).get(t, 0) + 1
                        await message.add_reaction("🔪")
            elif phase == "night_kill" and content.startswith("حمي") and st["roles"].get(message.author.id) == "طبيب":
                if message.mentions:
                    st["save"] = message.mentions[0].id
                    await message.add_reaction("💉")
            elif phase == "day" and content.startswith("طرد"):
                if message.mentions:
                    t = message.mentions[0].id
                    if t in st["alive"]:
                        st.setdefault("day_votes", {})[t] = st.get("day_votes", {}).get(t, 0) + 1
                        await message.add_reaction("⚖️")
            return

    async def _replica_round(self, channel, st: dict):
        timeout = st.get("timeout", 30)
        players = list(st["players"].keys())
        if len(players) <= 1:
            loser = players[0] if players else None
            if loser:
                await channel.send(f"💀 آخر واحد: <@{loser}> — **خسر الريبلكا**")
            await self._clear(channel.id)
            return

        random.shuffle(players)
        letter = random.choice(ARABIC_LETTERS)
        for uid in list(players):
            if uid not in st["players"]:
                continue
            cat = random.choice(REPLICA_CATS)
            await channel.send(f"📋 <@{uid}> — **{cat}** يبدأ بـ **{letter}** · {timeout}ث")
            st["type"] = "replica_turn"
            st["expect_user"] = uid
            st["expect_letter"] = letter
            st["expect_cat"] = cat
            st["answered"] = False
            st["deadline"] = time.monotonic() + timeout

            # انتظر جواب أو انتهى الوقت
            end = time.monotonic() + timeout
            while time.monotonic() < end and not st.get("answered"):
                await asyncio.sleep(0.4)
                if _ACTIVE.get(channel.id) is not st:
                    return

            if not st.get("answered"):
                st["players"].pop(uid, None)
                await channel.send(f"⏰ <@{uid}> طلع من الريبلكا.")
                if len(st["players"]) <= 1:
                    break
            else:
                # الجواب ينحسب في on_message — نحتاج معالج
                pass

        # إعادة تعيين للفحص
        # تبسيط: كل من ما جاوب خلال دوره طلع — نعيد جولة
        st["type"] = "replica_join_done"
        await self._replica_round(channel, st)


    @app_commands.command(name="games", description="تحديد رومات الألعاب المسموحة (فارغ = الكل)")
    @app_commands.describe(
        channel1="روم ألعاب",
        channel2="روم إضافي",
        channel3="روم إضافي",
        channel4="روم إضافي",
        channel5="روم إضافي",
        clear="امسح القائمة واسمح لكل الرومات",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def games_channels(
        self,
        interaction: discord.Interaction,
        channel1: discord.TextChannel = None,
        channel2: discord.TextChannel = None,
        channel3: discord.TextChannel = None,
        channel4: discord.TextChannel = None,
        channel5: discord.TextChannel = None,
        clear: bool = False,
    ):
        if clear:
            await Storage.update_guild(interaction.guild.id, SECTION, {"allowed_channels": []})
            await interaction.response.send_message("✅ الألعاب مسموحة **بكل** الرومات.", ephemeral=True)
            return
        chans = []
        for ch in (channel1, channel2, channel3, channel4, channel5):
            if ch and ch.id not in chans:
                chans.append(ch.id)
        if not chans:
            cfg = await _cfg(interaction.guild.id)
            cur = cfg.get("allowed_channels") or []
            if not cur:
                msg = "حالياً: **كل الرومات** مسموحة. حدد رومات أو clear:True."
            else:
                mentions = ", ".join(f"<#{c}>" for c in cur)
                msg = f"الرومات الحالية: {mentions}"
            await interaction.response.send_message(msg, ephemeral=True)
            return
        await Storage.update_guild(interaction.guild.id, SECTION, {"allowed_channels": chans})
        await interaction.response.send_message(
            "✅ الألعاب تشتغل فقط في: " + ", ".join(f"<#{c}>" for c in chans),
            ephemeral=True,
        )


    @commands.command(name="توب-العاب", aliases=["متصدرين", "توبالعاب", "gametop"])
    async def cmd_top(self, ctx: commands.Context):
        cfg = await _cfg(ctx.guild.id)
        pts = cfg.get("points") or {}
        if not pts:
            return await ctx.reply("ما في نقاط بعد. العبوا عشان تدخلوا اللوحة!")
        ranked = sorted(((int(uid), int(v)) for uid, v in pts.items()), key=lambda x: -x[1])[:15]
        lines = []
        medals = ["🥇", "🥈", "🥉"]
        for i, (uid, score) in enumerate(ranked):
            pre = medals[i] if i < 3 else f"**{i+1}.**"
            lines.append(f"{pre} <@{uid}> — ⭐ **{score}**")
        emb = _game_embed("🏆 متصدرين الألعاب", "\n".join(lines))
        emb = _game_embed("🏆 متصدرين الألعاب", chr(10).join(lines))
        await ctx.reply(embed=emb, mention_author=False)

    @commands.command(name="وقف", aliases=["ايقاف", "stop"])
    async def cmd_stop(self, ctx: commands.Context):
        st = _ACTIVE.get(ctx.channel.id)
        if not st:
            return await ctx.reply("ما في لعبة شغّالة هنا.")
        gtype = st.get("type") or ""
        host = st.get("host_id")
        if ctx.author.id != host and not await _can_stop(ctx.author, gtype):
            return await ctx.reply("ما عندك صلاحية إيقاف اللعبة.")
        await self._clear(ctx.channel.id)
        await ctx.reply(f"⏹️ تم إيقاف اللعبة ({gtype}).")
        await _log_game(ctx.guild, f"⏹️ أوقف {ctx.author.mention} لعبة **{gtype}** في {ctx.channel.mention}")

    @commands.command(name="العاب", aliases=["ألعاب"])
    async def list_games(self, ctx: commands.Context):
        desc = (
            "**فردية:**"
            + chr(10) + "`!كت` `!اسرع` `!لاعب` `!تفكيك` `!تجميع` `!لغز` `!ارقام` `!مفرد` `!جمع` `!حرف` `!عكس` `!خمن`"
            + chr(10) + chr(10) + "**جماعية:**"
            + chr(10) + "`!سلسلة` `!ريبلكا` `!سباق` `!xo` `!غميضة` `!روليت` `!مافيا`"
        )
        await ctx.reply(embed=_game_embed("🎮 قائمة الألعاب", desc), mention_author=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(GamesSystem(bot))
