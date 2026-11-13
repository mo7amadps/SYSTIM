"""
نظام الألعاب — أوامر بـ !
كت · اسرع · لاعب · تفكيك · تجميع · سلسلة · ريبلكا · روليت · مافيا
"""
from __future__ import annotations

import asyncio
import logging
import random
import re
import time
from typing import Optional
from pathlib import Path

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

def _roulette_image_path() -> Path | None:
    """صورة الروليت المخصصة (assets/roulette.jpg)."""
    candidates = [
        Path(__file__).resolve().parent.parent / "assets" / "roulette.jpg",
        Path("assets/roulette.jpg"),
        Path("/app/assets/roulette.jpg"),
    ]
    for c in candidates:
        try:
            if c.is_file():
                return c
        except Exception:
            continue
    return None


def _roulette_file() -> discord.File | None:
    path = _roulette_image_path()
    if not path:
        return None
    try:
        return discord.File(path, filename="roulette.jpg")
    except Exception:
        return None

logger = logging.getLogger(__name__)

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

# اسم اللاعب + صورة (روابط عامة) + أسماء بديلة مقبولة
PLAYER_POOL = [
    {"name": "ميسي", "aliases": ["ليونيل ميسي", "messi", "ليونيل"], "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/Lionel-Messi-Argentina-2022-FIFA-World-Cup_%28cropped%29.jpg/440px-Lionel-Messi-Argentina-2022-FIFA-World-Cup_%28cropped%29.jpg"},
    {"name": "رونالدو", "aliases": ["كريستيانو", "cristiano", "cr7", "كريستيانو رونالدو"], "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/Cristiano_Ronaldo_2018.jpg/440px-Cristiano_Ronaldo_2018.jpg"},
    {"name": "نيمار", "aliases": ["neymar", "نيمار جونيور"], "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/65/20180610_FIFA_Friendly_Match_Austria_vs._Brazil_Neymar_850_1705.jpg/440px-20180610_FIFA_Friendly_Match_Austria_vs._Brazil_Neymar_850_1705.jpg"},
    {"name": "مبابي", "aliases": ["mbappe", "كيلان مبابي", "mbappé"], "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a8/Kylian_Mbapp%C3%A9_during_a_pre-season_friendly.jpg/440px-Kylian_Mbapp%C3%A9_during_a_pre-season_friendly.jpg"},
    {"name": "هالاند", "aliases": ["haaland", "إيرلينج", "ارلينج هالاند"], "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/07/Erling_Haaland_2023_%28cropped%29.jpg/440px-Erling_Haaland_2023_%28cropped%29.jpg"},
    {"name": "صلاح", "aliases": ["محمد صلاح", "salah", "mo salah"], "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/Mohamed_Salah_2018.jpg/440px-Mohamed_Salah_2018.jpg"},
    {"name": "محرز", "aliases": ["رياض محرز", "mahrez"], "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2c/Riyad_Mahrez_2018.jpg/440px-Riyad_Mahrez_2018.jpg"},
    {"name": "حكيمي", "aliases": ["اشرف حكيمي", "أشرف حكيمي", "hakimi"], "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Achraf_Hakimi_2022.jpg/440px-Achraf_Hakimi_2022.jpg"},
    {"name": "بنزيما", "aliases": ["كريم بنزيما", "benzema"], "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e2/Karim_Benzema_2018_%28cropped%29.jpg/440px-Karim_Benzema_2018_%28cropped%29.jpg"},
    {"name": "زيدان", "aliases": ["زين الدين زيدان", "zidane"], "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f3/Zinedine_Zidane_by_Augustas_Didzgalvis.jpg/440px-Zinedine_Zidane_by_Augustas_Didzgalvis.jpg"},
    {"name": "مودريتش", "aliases": ["لوكا مودريتش", "modric"], "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/2018-06-16_Luka_Modri%C4%87.jpg/440px-2018-06-16_Luka_Modri%C4%87.jpg"},
    {"name": "كروس", "aliases": ["توني كروس", "kroos"], "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/20180602_FIFA_Friendly_Match_Austria_vs._Germany_Toni_Kroos_850_0695.jpg/440px-20180602_FIFA_Friendly_Match_Austria_vs._Germany_Toni_Kroos_850_0695.jpg"},
    {"name": "فينيسيوس", "aliases": ["فينيسيوس جونيور", "vinicius", "vini"], "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f5/Vin%C3%ADcius_J%C3%BAnior_2021.jpg/440px-Vin%C3%ADcius_J%C3%BAnior_2021.jpg"},
    {"name": "يامال", "aliases": ["لامين يامال", "yamal"], "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Lamine_Yamal_2024.jpg/440px-Lamine_Yamal_2024.jpg"},
    {"name": "بيلينغهام", "aliases": ["jude bellingham", "بيلينجهام", "bellingham"], "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8e/Jude_Bellingham_2021.jpg/440px-Jude_Bellingham_2021.jpg"},
    {"name": "ليفاندوفسكي", "aliases": ["lewandowski", "روبرت ليفاندوفسكي"], "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/26/Robert_Lewandowski_2018.jpg/440px-Robert_Lewandowski_2018.jpg"},
    {"name": "دي بروين", "aliases": ["kevin de bruyne", "ديبروين"], "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7c/Kevin_De_Bruyne_2018.jpg/440px-Kevin_De_Bruyne_2018.jpg"},
    {"name": "بوفون", "aliases": ["buffon", "جانلويجي بوفون"], "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/Gianluigi_Buffon_2018.jpg/440px-Gianluigi_Buffon_2018.jpg"},
    {"name": "إينييستا", "aliases": ["iniesta", "اندريس انيستا"], "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/96/Andr%C3%A9s_Iniesta_2018.jpg/440px-Andr%C3%A9s_Iniesta_2018.jpg"},
    {"name": "رونالدينيو", "aliases": ["ronaldinho", "رونالدينيو"], "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/Ronaldinho_in_2019.jpg/440px-Ronaldinho_in_2019.jpg"},
]
PLAYERS = [p["name"] for p in PLAYER_POOL]

QUESTIONS = [
    # 400 سؤال كت — نقاش مفتوح (أي جواب يُحسب لأول مجيب)
    ("وش أكثر شيء يضحكك بسرعة؟", ["*"]),
    ("وش أول شيء تسويه لما تصحى؟", ["*"]),
    ("وش الأكلة اللي ما تمل منها؟", ["*"]),
    ("لو عندك يوم إجازة مفتوح، وش تسوي؟", ["*"]),
    ("أكثر كلمة تكررها في كلامك؟", ["*"]),
    ("وش لقبك المفضل؟", ["*"]),
    ("قهوة ولا شاي؟", ["*"]),
    ("بحر ولا بر؟", ["*"]),
    ("وش أغرب هواية عندك؟", ["*"]),
    ("وش آخر شيء ضحكت عليه من قلب؟", ["*"]),
    ("أكثر تطبيق تستخدمه؟", ["*"]),
    ("وش أجمل صفة في شخصيتك؟", ["*"]),
    ("وش العيب اللي تتمنى تتخلص منه؟", ["*"]),
    ("وش أول شيء تلاحظه في الشخص اللي تقابله؟", ["*"]),
    ("تحب الصباح ولا الليل؟", ["*"]),
    ("وش أكثر موسم تحبه؟", ["*"]),
    ("وش أكثر لون يمثلك؟", ["*"]),
    ("لو كنت حيوان، وش تكون؟", ["*"]),
    ("وش الأغنية اللي ما تمل منها؟", ["*"]),
    ("كم ساعة تنام عادةً؟", ["*"]),
    ("وش أكثر شيء يستفزك؟", ["*"]),
    ("وش أحسن نصيحة جاتك في حياتك؟", ["*"]),
    ("وش أول شيء تشتريه لو صار معك مليون؟", ["*"]),
    ("تفضل الجلسات الهادية ولا الصاخبة؟", ["*"]),
    ("وش أكثر مكان تحس فيه براحة؟", ["*"]),
    ("وش الشيء اللي تتقنه وما أحد يدري؟", ["*"]),
    ("وش أكثر جملة تنقال لك دايماً؟", ["*"]),
    ("وش عادتك الغريبة؟", ["*"]),
    ("تحب تتكلم ولا تسمع؟", ["*"]),
    ("وش وصف يومك المثالي بكلمة؟", ["*"]),
    ("وش أجمل ذكرى من طفولتك؟", ["*"]),
    ("وش أكثر موقف محرج صار لك؟", ["*"]),
    ("وش أول جوال استخدمته؟", ["*"]),
    ("وش أكثر لعبة كنت تلعبها وأنت صغير؟", ["*"]),
    ("من أول صديق لك في المدرسة؟", ["*"]),
    ("وش أحلى مناسبة حضرتها؟", ["*"]),
    ("أكثر هدية ما تنساها؟", ["*"]),
    ("وش أسوأ هدية جاتك؟", ["*"]),
    ("وش أطرف موقف صار لك في المدرسة؟", ["*"]),
    ("أول سفرة سافرتها لوحدك؟", ["*"]),
    ("وش أكثر شيء تشتاق له من الماضي؟", ["*"]),
    ("وش أحلى عيد مر عليك؟", ["*"]),
    ("من أكثر شخص أثر فيك؟", ["*"]),
    ("وش أول شيء اشتريته من مصروفك؟", ["*"]),
    ("وش الكرتون اللي كنت تتابعه؟", ["*"]),
    ("وش أكثر شيء ندمت عليه؟", ["*"]),
    ("وش أجمل رسالة وصلتك؟", ["*"]),
    ("موقف بكيت فيه من الضحك؟", ["*"]),
    ("وش أكثر عقاب تذكره من أهلك؟", ["*"]),
    ("وش أحلى رحلة مدرسية؟", ["*"]),
    ("وش الشيء اللي كنت تخاف منه وأنت صغير؟", ["*"]),
    ("أول مرة وقفت فيها على المسرح؟", ["*"]),
    ("وش أحلى سهرة مرت عليك؟", ["*"]),
    ("وش أكثر كذبة كذبتها وأنت صغير؟", ["*"]),
    ("وش اللعبة اللي كنت تحلم تملكها؟", ["*"]),
    ("وش أحسن يوم في حياتك لين الحين؟", ["*"]),
    ("وش الشيء اللي تتمنى ترجع له؟", ["*"]),
    ("وش أول شغلة عملتها بحياتك؟", ["*"]),
    ("من آخر شخص فاجأك بشيء حلو؟", ["*"]),
    ("وش أطرف اسم عرفته؟", ["*"]),
    ("وش رأيك بالأعراس الكبيرة ولا الصغيرة؟", ["*"]),
    ("وش أهم شيء يخلي الفرح ناجح؟", ["*"]),
    ("أحلى زفة شفتها؟", ["*"]),
    ("وش أكثر شيء يزعجك في المناسبات؟", ["*"]),
    ("تحب تكون ضيف ولا صاحب المناسبة؟", ["*"]),
    ("وش أجمل هدية تعطيها في الزواج؟", ["*"]),
    ("وش رأيك بالتصوير في المناسبات؟", ["*"]),
    ("أي وقت أحسن للمناسبات: نهار ولا ليل؟", ["*"]),
    ("وش أفضل أكلة تنقدم في الحفلات؟", ["*"]),
    ("وش أطرف موقف صار لك في عرس؟", ["*"]),
    ("هل تحب الرقص في المناسبات؟", ["*"]),
    ("وش لبسك المفضل في المناسبات؟", ["*"]),
    ("تفضل تحضر ولا تعتذر؟", ["*"]),
    ("وش أكثر شيء تستحي منه في المناسبات؟", ["*"]),
    ("وش رأيك بالمفاجآت في الأعياد؟", ["*"]),
    ("كيف تحتفل بعيد ميلادك؟", ["*"]),
    ("هدية عيد الميلاد المثالية بنظرك؟", ["*"]),
    ("وش أحلى حفلة تخرج حضرتها؟", ["*"]),
    ("وش أكثر كلمة تنقال في التهنئة وتعجبك؟", ["*"]),
    ("من أول شخص تتصل عليه لما تفرح؟", ["*"]),
    ("وش أول شيء تسويه لما تنجح؟", ["*"]),
    ("لو تنظم حفلة، وش الثيم؟", ["*"]),
    ("أحلى مكان لعقد المناسبات؟", ["*"]),
    ("وش رأيك بالعزائم الكبيرة؟", ["*"]),
    ("كم شخص تحب يحضر مناسبتك؟", ["*"]),
    ("وش أحسن سوالف سمعتها في مناسبة؟", ["*"]),
    ("وش تتمنى يتغير في المناسبات؟", ["*"]),
    ("تحب المناسبات العائلية ولا مع الأصدقاء؟", ["*"]),
    ("وش أجمل لحظة في المناسبات؟", ["*"]),
    ("وش الشيء اللي دايماً ينسونه في الحفلات؟", ["*"]),
    ("وش أول شيء تاكله على الفطور؟", ["*"]),
    ("أحلى مسلسل رمضاني شفته؟", ["*"]),
    ("كيف تقضي وقتك بعد التراويح؟", ["*"]),
    ("وش أحب أكلة رمضانية لك؟", ["*"]),
    ("تحب السحور ولا الفطور أكثر؟", ["*"]),
    ("وش أحلى عادة رمضانية عندكم؟", ["*"]),
    ("وش أكثر شيء تشتاق له في رمضان؟", ["*"]),
    ("وش أحلى ذكرى عيد؟", ["*"]),
    ("كم عيدية تحصل وأنت صغير؟", ["*"]),
    ("وش أكثر شيء تحب تسويه ليلة العيد؟", ["*"]),
    ("وش لبسك في العيد؟", ["*"]),
    ("من أول شخص تهنيه بالعيد؟", ["*"]),
    ("وش رأيك بالعيدية للكبار؟", ["*"]),
    ("حلوى العيد المفضلة؟", ["*"]),
    ("وين تقضي العيد غالباً؟", ["*"]),
    ("وش أكثر شيء يميز عيدكم؟", ["*"]),
    ("تفضل العيد بالبيت ولا السفر؟", ["*"]),
    ("أول شيء تسويه صباح العيد؟", ["*"]),
    ("أحلى تهنئة وصلتك؟", ["*"]),
    ("وش رأيك بالقرقيعان وعادات الأطفال؟", ["*"]),
    ("وش أطرف موقف صار في رمضان؟", ["*"]),
    ("أكثر شيء تتمنى تختمه في رمضان؟", ["*"]),
    ("تحب تصوم لوحدك ولا مع العائلة؟", ["*"]),
    ("مشروب رمضان المفضل؟", ["*"]),
    ("وش أجمل ليلة في رمضان عندك؟", ["*"]),
    ("لو خيروك بين السفر كل سنة أو بيت أحلامك؟", ["*"]),
    ("لو تقدر تعيش في أي بلد، وين؟", ["*"]),
    ("لو تقدر ترجع بالزمن، لأي سنة؟", ["*"]),
    ("لو تقابل شخصية تاريخية، من؟", ["*"]),
    ("لو عندك قدرة خارقة، وش تكون؟", ["*"]),
    ("لو تصير مشهور، بأي مجال؟", ["*"]),
    ("لو تأكل أكلة وحدة طول عمرك، وش تكون؟", ["*"]),
    ("لو تقدر تغير شيء بالعالم، وش هو؟", ["*"]),
    ("لو تصحى بكرة ثري، وش أول خطوة؟", ["*"]),
    ("لو خيروك بين المال والصحة؟", ["*"]),
    ("لو تعيش بجزيرة، وش تاخذ معك؟", ["*"]),
    ("لو تقدر تتكلم أي لغة، وش تختار؟", ["*"]),
    ("لو تغير اسمك، وش تسمي نفسك؟", ["*"]),
    ("لو تكون مدير ليوم واحد، وش تسوي؟", ["*"]),
    ("لو عندك آلة زمن، تروح للماضي ولا المستقبل؟", ["*"]),
    ("لو تقابل نفسك وأنت صغير، وش تقول له؟", ["*"]),
    ("لو تعيش بدون جوال أسبوع، تقدر؟", ["*"]),
    ("لو يسمحون لك بسؤال واحد لأي شخص، من ووش؟", ["*"]),
    ("لو تتحول لشخصية كرتونية، من؟", ["*"]),
    ("لو تقدر تتقن مهارة بدقيقة، وش تختار؟", ["*"]),
    ("لو تفتح مشروع، وش نوعه؟", ["*"]),
    ("لو تبني مطعم، وش يقدم؟", ["*"]),
    ("لو تسافر الحين، وين؟", ["*"]),
    ("لو تعيش بمدينة وحدة طول حياتك، وش تختار؟", ["*"]),
    ("لو تقدر تسمع أفكار أي شخص، تبي؟", ["*"]),
    ("لو تعطي نصيحة للناس كلهم، وش هي؟", ["*"]),
    ("لو تحصل على إجازة سنة، وش تسوي؟", ["*"]),
    ("لو تكتب كتاب، وش عنوانه؟", ["*"]),
    ("لو تقدر تحيي أحد من الماضي، من؟", ["*"]),
    ("لو يومك 30 ساعة، كيف تستغل الساعات الزيادة؟", ["*"]),
    ("وش صفة تحبها في الصديق؟", ["*"]),
    ("وش أكثر شيء يخليك تزعل من الصديق؟", ["*"]),
    ("من أكثر شخص يفهمك؟", ["*"]),
    ("وش أحلى موقف سواه لك صديق؟", ["*"]),
    ("كم عدد أصدقائك المقربين؟", ["*"]),
    ("وش رأيك: الصداقة تدوم ولا تتغير؟", ["*"]),
    ("تحب تسولف مكالمة ولا رسايل؟", ["*"]),
    ("وش أطرف لقب ناديت فيه صديقك؟", ["*"]),
    ("أكثر صديق يضحكك؟", ["*"]),
    ("وش أول شيء تسويه لما صديقك يزعل؟", ["*"]),
    ("وش الفرق بين الصديق والزميل بنظرك؟", ["*"]),
    ("هل تحفظ الأسرار؟", ["*"]),
    ("وش أحلى طلعة مع الشلة؟", ["*"]),
    ("تحب تسوي مفاجأة لأصحابك؟", ["*"]),
    ("وش أسوأ صفة في الصديق؟", ["*"]),
    ("تعتذر أول ولا تنتظر الاعتذار؟", ["*"]),
    ("من أكثر شخص تتصل عليه وقت الضيق؟", ["*"]),
    ("هل تفضل الصداقات القديمة ولا الجديدة؟", ["*"]),
    ("أحلى هدية أعطيتها لصديق؟", ["*"]),
    ("وش اللي يقوي العلاقة بين الناس؟", ["*"]),
    ("تعطي فرصة ثانية ولا لا؟", ["*"]),
    ("وش رأيك بالعتاب؟", ["*"]),
    ("أصعب شي في الصداقة؟", ["*"]),
    ("وش أجمل كلمة سمعتها من صديق؟", ["*"]),
    ("تحب تكون قائد الشلة ولا تتبع؟", ["*"]),
    ("غنِّ أي مقطع الحين!", ["*"]),
    ("قلّد صوت شخصية مشهورة.", ["*"]),
    ("وش أغرب أكلة جربتها؟", ["*"]),
    ("قول 3 أشياء تحبها بنفسك.", ["*"]),
    ("اذكر 5 أشياء بالغرفة بدون ما تلف.", ["*"]),
    ("وش أحرج رسالة أرسلتها بالغلط؟", ["*"]),
    ("حاول تضحك أحد بدون كلام.", ["*"]),
    ("اختر رقم من 1 إلى 10 وجاوب على سؤال بنفس الرقم.", ["*"]),
    ("وش اللي بمحفظتك الحين؟", ["*"]),
    ("وش آخر شيء بحثت عنه بجوجل؟", ["*"]),
    ("وش أكثر إيموجي تستخدمه؟", ["*"]),
    ("وش أطرف حلم شفته؟", ["*"]),
    ("كم مرة تغير رأيك بالأكل وقت الطلب؟", ["*"]),
    ("وش الشيء اللي تنسى مكانه دايماً؟", ["*"]),
    ("وش آخر شيء اشتريته وما احتجته؟", ["*"]),
    ("وش اللعبة اللي تتفوق فيها؟", ["*"]),
    ("وش أحلى مقلب سويته؟", ["*"]),
    ("وش أكثر مقلب انعمل فيك؟", ["*"]),
    ("كم عمرك تشوفه بالنفسية مو بالهوية؟", ["*"]),
    ("لو تكتب سيرتك بثلاث كلمات؟", ["*"]),
    ("وش أكثر شيء تتأخر بسببه؟", ["*"]),
    ("وش أول شيء تسويه لو انقطعت الكهرباء؟", ["*"]),
    ("وش أغرب شيء بقائمة أمنياتك؟", ["*"]),
    ("جاوب بكلمة وحدة: وش تحس الحين؟", ["*"]),
    ("وش أكثر جملة تقولها لما تتوتر؟", ["*"]),
    ("اذكر موقف خلاك تفتخر بنفسك.", ["*"]),
    ("وش أطرف رسالة صوتية وصلتك؟", ["*"]),
    ("ارسم أي شيء بخيالك واوصفه للجماعة.", ["*"]),
    ("وش أكثر شيء ممكن يخليك تضحك بالغلط في مكان جاد؟", ["*"]),
    ("وش أمنيتك لهالمناسبة ولكل الحاضرين؟ 🤍", ["*"]),
    ("من أكثر فرد بالعائلة يشبهك؟", ["*"]),
    ("وش أحلى عادة عائلية عندكم؟", ["*"]),
    ("وش أكثر أكلة تسويها أمك وتحبها؟", ["*"]),
    ("من أكثر شخص يضحكك بالعائلة؟", ["*"]),
    ("وش أحلى جمعة عائلية مرت عليك؟", ["*"]),
    ("وش النصيحة اللي ما تنساها من والدك؟", ["*"]),
    ("كم عدد إخوانك وأخواتك؟", ["*"]),
    ("من أكثر واحد منهم قريب منك؟", ["*"]),
    ("وش أطرف لقب ينادونك فيه بالبيت؟", ["*"]),
    ("وين تحب تسافر مع العائلة؟", ["*"]),
    ("وش أكثر شيء يميز بيت جدك وجدتك؟", ["*"]),
    ("وش أحلى قصة سمعتها من جدك أو جدتك؟", ["*"]),
    ("أكثر موقف فخرت فيه بأحد من عائلتك؟", ["*"]),
    ("وش الشيء اللي يزعجك في الاجتماعات العائلية؟", ["*"]),
    ("تحب تقعد بالبيت ولا تطلع مع العائلة؟", ["*"]),
    ("وش أكلة الجمعة المفضلة؟", ["*"]),
    ("من الشخص اللي تستشيره بقراراتك؟", ["*"]),
    ("وش أحلى هدية أعطيتها لأمك؟", ["*"]),
    ("وش أكثر شيء تعلمته من أهلك؟", ["*"]),
    ("وش أكثر جملة تقولها أمك دايماً؟", ["*"]),
    ("وش أكثر جملة يقولها أبوك دايماً؟", ["*"]),
    ("لو تعطي عائلتك لقب، وش يكون؟", ["*"]),
    ("وش أحلى رحلة برية مع العائلة؟", ["*"]),
    ("وش أكثر تقليد عائلي تتمنى يستمر؟", ["*"]),
    ("من أكثر واحد يتأخر بالعائلة؟", ["*"]),
    ("من أكثر واحد يحب المقالب؟", ["*"]),
    ("وش أحلى مفاجأة سووها لك أهلك؟", ["*"]),
    ("وش الشيء اللي تتمنى تسويه مع أهلك؟", ["*"]),
    ("كيف تحتفلون بعيد ميلاد أحد من العائلة؟", ["*"]),
    ("وش أغلى شيء عندك من ذكريات العائلة؟", ["*"]),
    ("وش المادة اللي كنت تحبها بالمدرسة؟", ["*"]),
    ("وش المادة اللي تكرهها؟", ["*"]),
    ("من أحسن معلم درسك؟", ["*"]),
    ("وش أطرف موقف مع معلم؟", ["*"]),
    ("وش حلمك وأنت صغير تصير؟", ["*"]),
    ("وش وظيفة أحلامك الحين؟", ["*"]),
    ("تفضل الدوام الصباحي ولا المسائي؟", ["*"]),
    ("وش أسوأ شغلة اشتغلتها؟", ["*"]),
    ("وش أحلى زميل شغل عرفته؟", ["*"]),
    ("تحب تشتغل لوحدك ولا ضمن فريق؟", ["*"]),
    ("وش أكثر شيء يخليك تتحمس بالشغل؟", ["*"]),
    ("وش أكثر شيء يطفشك بالدراسة أو الشغل؟", ["*"]),
    ("هل سهرت قبل اختبار؟ وش صار؟", ["*"]),
    ("وش أكثر عذر استخدمته للتأخر؟", ["*"]),
    ("وش أول راتب أخذته ووين صرفته؟", ["*"]),
    ("لو تكون مدير شركة، وش أول قرار؟", ["*"]),
    ("وش المهارة اللي تتمنى تتعلمها؟", ["*"]),
    ("وش أحسن كتاب قريته؟", ["*"]),
    ("تفضل القراءة ولا مشاهدة الفيديو؟", ["*"]),
    ("وش آخر شيء جديد تعلمته؟", ["*"]),
    ("وش أصعب قرار اتخذته بمسيرتك؟", ["*"]),
    ("وش أكثر إنجاز تفتخر فيه؟", ["*"]),
    ("تحب الإجازات ولا الشغل؟", ["*"]),
    ("كيف تنظم وقتك؟", ["*"]),
    ("وش أكثر شيء تؤجله دايماً؟", ["*"]),
    ("وش هدفك للسنة الجاية؟", ["*"]),
    ("لو تقدر ترجع تدرس تخصص ثاني، وش تختار؟", ["*"]),
    ("من أكثر شخص ألهمك بمسيرتك؟", ["*"]),
    ("وش رأيك بالعمل عن بعد؟", ["*"]),
    ("وش أطرف موقف صار لك بالاجتماع؟", ["*"]),
    ("وش اللعبة اللي قضيت فيها ساعات طويلة؟", ["*"]),
    ("جوال ولا كمبيوتر؟", ["*"]),
    ("وش أول لعبة لعبتها؟", ["*"]),
    ("وش أكثر تطبيق تقعد عليه بدون ما تحس؟", ["*"]),
    ("كم ساعة تقضي على الجوال؟", ["*"]),
    ("وش آخر مسلسل خلصته؟", ["*"]),
    ("وش أحسن فيلم شفته؟", ["*"]),
    ("تفضل السينما ولا البيت؟", ["*"]),
    ("وش أكثر بودكاست أو قناة تتابعها؟", ["*"]),
    ("لو تصمم لعبة، وش فكرتها؟", ["*"]),
    ("وش أكثر لعبة تتعصب منها؟", ["*"]),
    ("تلعب لوحدك ولا مع الشلة؟", ["*"]),
    ("وش أغرب اسم استخدمته بلعبة؟", ["*"]),
    ("وش أكثر شيء تكرهه في الألعاب أونلاين؟", ["*"]),
    ("وش رأيك بالذكاء الاصطناعي؟", ["*"]),
    ("لو تخترع تطبيق، وش يسوي؟", ["*"]),
    ("وش أطرف ستيكر أو ميم ترسله؟", ["*"]),
    ("وش أكثر شيء يضيع وقتك على الإنترنت؟", ["*"]),
    ("كم مرة تغير خلفية جوالك؟", ["*"]),
    ("وش أكثر برنامج تواصل تستخدمه؟", ["*"]),
    ("وش آخر شيء اشتريته أونلاين؟", ["*"]),
    ("تحب الألعاب الجماعية ولا الفردية؟", ["*"]),
    ("وش شخصيتك المفضلة بالألعاب؟", ["*"]),
    ("لو تعيش داخل لعبة، أي لعبة؟", ["*"]),
    ("وش أحلى ذكرى مع لعبة؟", ["*"]),
    ("وش أكثر شيء تتمنى يتوفر بالتقنية؟", ["*"]),
    ("هل تقدر تعيش بدون إنترنت يوم كامل؟", ["*"]),
    ("وش أول جوال حلمت تشتريه؟", ["*"]),
    ("وش رأيك بالألعاب القديمة؟", ["*"]),
    ("وش أطرف موقف صار لك أونلاين؟", ["*"]),
    ("وش أحلى بلد زرته؟", ["*"]),
    ("وش البلد اللي تحلم تزورها؟", ["*"]),
    ("تفضل السفر لوحدك ولا مع أحد؟", ["*"]),
    ("وش أول شيء تحطه بشنطة السفر؟", ["*"]),
    ("وش أغرب أكلة شفتها بالسفر؟", ["*"]),
    ("وش أسوأ موقف صار لك بمطار؟", ["*"]),
    ("فندق ولا شقة؟", ["*"]),
    ("وش أحلى مدينة مشيت فيها؟", ["*"]),
    ("صيف ولا شتاء للسفر؟", ["*"]),
    ("وش أكثر شيء تشتريه تذكار؟", ["*"]),
    ("وش أكلتك المفضلة بالعالم؟", ["*"]),
    ("مطعم ولا أكل البيت؟", ["*"]),
    ("وش أحلى كافيه تعرفه؟", ["*"]),
    ("حلو ولا مالح؟", ["*"]),
    ("وش أكثر أكلة تسويها بنفسك؟", ["*"]),
    ("تطبخ ولا تطلب؟", ["*"]),
    ("وش الأكلة اللي ما تقدر تقاومها؟", ["*"]),
    ("بيتزا ولا برجر؟", ["*"]),
    ("وش أكثر مشروب تشربه؟", ["*"]),
    ("وش أغرب خلطة أكل تحبها؟", ["*"]),
    ("وش أحلى وجبة فطور؟", ["*"]),
    ("وش الأكلة اللي ما تحبها أبداً؟", ["*"]),
    ("من أحسن طباخ تعرفه؟", ["*"]),
    ("وش أحلى عزيمة حضرتها؟", ["*"]),
    ("وش أحلى حلى جربته؟", ["*"]),
    ("وش رأيك بالمطاعم الفخمة؟", ["*"]),
    ("كباب ولا مشاوي؟", ["*"]),
    ("وش أول أكلة تعلمت تسويها؟", ["*"]),
    ("وش أكثر أكلة تفكرك بطفولتك؟", ["*"]),
    ("لو تفتح كافيه، وش تسميه؟", ["*"]),
    ("وش أكبر خوف عندك؟", ["*"]),
    ("وش أكثر شيء تتمنى تغيره بنفسك؟", ["*"]),
    ("وش معنى السعادة عندك؟", ["*"]),
    ("وش أهم قيمة بحياتك؟", ["*"]),
    ("وش أصعب فترة مرت عليك وكيف تجاوزتها؟", ["*"]),
    ("وش الشيء اللي تتمنى لو عرفته من بدري؟", ["*"]),
    ("هل تؤمن بالحظ؟", ["*"]),
    ("وش أكثر شيء تتمنى تحققه قبل ما تكبر؟", ["*"]),
    ("وش رأيك: النجاح مال ولا راحة بال؟", ["*"]),
    ("هل تسامح بسرعة؟", ["*"]),
    ("وش أكثر شيء يخليك تحس بالامتنان؟", ["*"]),
    ("وش أحسن قرار اتخذته؟", ["*"]),
    ("وش أسوأ قرار اتخذته وش تعلمت منه؟", ["*"]),
    ("وش الشيء اللي تتمنى الناس تفهمه عنك؟", ["*"]),
    ("هل تحب نفسك بالكامل؟", ["*"]),
    ("وش نصيحتك لنفسك بعد 10 سنين؟", ["*"]),
    ("وش أكثر شيء يخليك مرتاح نفسياً؟", ["*"]),
    ("هل تؤمن بالقدر؟", ["*"]),
    ("وش الشيء اللي تحس إنه رسالتك بالحياة؟", ["*"]),
    ("وش أحلى شعور جربته؟", ["*"]),
    ("وش أكثر شيء تخاف تخسره؟", ["*"]),
    ("كيف تتعامل مع الضغوط؟", ["*"]),
    ("وش أكثر شخص تحترمه ولماذا؟", ["*"]),
    ("الأفضل تعيش للحاضر ولا تخطط للمستقبل؟", ["*"]),
    ("وش أكثر شيء تعلمته من أخطائك؟", ["*"]),
    ("وش الصفة اللي تحترمها بالناس؟", ["*"]),
    ("وش الشيء الصغير اللي يسعدك؟", ["*"]),
    ("لو تعطي وصية لأولادك، وش تكون؟", ["*"]),
    ("وش تتمنى يقولون عنك بعد عمر طويل؟", ["*"]),
    ("وش أجمل شيء بحياتك الحين؟", ["*"]),
    ("هل تفضل تعرف المستقبل ولا تغير الماضي؟", ["*"]),
    ("هل تفضل تطير ولا تصير مخفي؟", ["*"]),
    ("هل تفضل تعيش بالبحر ولا بالجبل؟", ["*"]),
    ("هل تفضل تكون غني ومشغول ولا متوسط وفاضي؟", ["*"]),
    ("هل تفضل تسافر دايماً ولا تستقر؟", ["*"]),
    ("هل تفضل صديق صريح ولا مجامل؟", ["*"]),
    ("هل تفضل تنسى كل شيء ولا تتذكر كل شيء؟", ["*"]),
    ("هل تفضل تعيش بالماضي ولا بالمستقبل؟", ["*"]),
    ("هل تفضل ما تنام أبداً ولا تنام طول الوقت؟", ["*"]),
    ("هل تفضل تتكلم كل اللغات ولا تعزف كل الآلات؟", ["*"]),
    ("هل تفضل شهرة كبيرة ولا خصوصية كاملة؟", ["*"]),
    ("هل تفضل تأكل حلو بس ولا مالح بس؟", ["*"]),
    ("هل تفضل صيف دايم ولا شتاء دايم؟", ["*"]),
    ("هل تفضل بيت كبير بعيد ولا صغير بقلب المدينة؟", ["*"]),
    ("هل تفضل تقرأ أفكار الناس ولا تتحكم بالوقت؟", ["*"]),
    ("هل تفضل تخسر جوالك ولا محفظتك؟", ["*"]),
    ("هل تفضل شغل بشغفك براتب قليل ولا شغل ممل براتب عالي؟", ["*"]),
    ("هل تفضل تسولف مع صديق قديم ولا تتعرف على جديد؟", ["*"]),
    ("هل تفضل الصراحة المؤلمة ولا الكذبة الحلوة؟", ["*"]),
    ("هل تفضل الهدية ولا المفاجأة؟", ["*"]),
    ("هل تفضل حياة هادية ولا مليانة مغامرات؟", ["*"]),
    ("هل تفضل ما تستخدم الجوال شهر ولا ما تاكل برا شهر؟", ["*"]),
    ("هل تفضل تكون الأذكى ولا الأجمل؟", ["*"]),
    ("هل تفضل تتأخر دايماً ولا تجي بدري بزيادة؟", ["*"]),
    ("هل تفضل حفلة كبيرة ولا جلسة صغيرة؟", ["*"]),
    ("هل تفضل تسوي مقلب ولا تنعمل فيك؟", ["*"]),
    ("هل تفضل قهوة بدون سكر ولا شاي بدون نعناع؟", ["*"]),
    ("هل تفضل الصيد ولا التخييم؟", ["*"]),
    ("هل تفضل سيارة سريعة ولا مريحة؟", ["*"]),
    ("هل تفضل تعيش في عصر الأجداد ولا بعد 100 سنة؟", ["*"]),
    ("قل \"سيارة سريعة سارت سريعاً\" ثلاث مرات بسرعة بدون غلط.", ["*"]),
    ("مثّل مشهد بدون كلام والجماعة يخمنون.", ["*"]),
    ("احكِ نكتة تضحك الجميع.", ["*"]),
    ("اذكر 5 دول تبدأ بحرف الميم.", ["*"]),
    ("اذكر 5 أكلات خليجية في 15 ثانية.", ["*"]),
    ("قلّد طريقة كلام أحد من الحضور.", ["*"]),
    ("غمّض عينك ووصف شكل أقرب شخص لك.", ["*"]),
    ("اذكر 10 حيوانات في 20 ثانية.", ["*"]),
    ("غنِّ مقطع من أغنية قديمة.", ["*"]),
    ("قل مدح لكل شخص بالجلسة.", ["*"]),
    ("تكلم 30 ثانية عن أي شيء بدون توقف.", ["*"]),
    ("ارسم وجه أحد الحاضرين والباقي يخمنون.", ["*"]),
    ("قل 3 أشياء مشتركة بينك وبين الشخص اللي جنبك.", ["*"]),
    ("اذكر 5 أسماء تبدأ بحرف الراء.", ["*"]),
    ("اختر شخص وقل له كلمة حلوة.", ["*"]),
    ("تكلم بلهجة غير لهجتك لمدة دقيقة.", ["*"]),
    ("اذكر 5 مدن عربية بدون تفكير.", ["*"]),
    ("رتب 5 أشياء تحبها من الأهم للأقل.", ["*"]),
    ("قل أحلى ذكرى جمعتك بالحاضرين.", ["*"]),
    ("وش دعاؤك لكل الحاضرين؟ 🤍", ["*"]),
]

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
        return max(5, min(180, int(t)))
    except Exception:
        return default


async def _lobby_timeout(guild_id: int, key: str, default: int = 30) -> int:
    """وقت اللوبي قبل بداية اللعبة."""
    cfg = await _cfg(guild_id)
    lobby_map = cfg.get("lobby_timeouts") or {}
    t = lobby_map.get(key)
    if t is None:
        t = (cfg.get("timeouts") or {}).get("lobby", default)
    try:
        return max(5, min(180, int(t)))
    except Exception:
        return default


# (min_cap, max_cap, default_cap)
GAME_CAPACITY = {
    "silsila": (10, 40, 40),
    "replica": (2, 30, 30),
    "sabaq": (2, 40, 20),
    "xo": (2, 2, 2),
    "ghmida": (2, 30, 20),
    "roulette": (2, 100, 50),
    "mafia": (5, 40, 20),
}

# key, label, is_group, default_timeout, default_lobby
EDITABLE_GAMES = [
    ("kat", "كت", False, 30, 0),
    ("asra", "أسرع", False, 20, 0),
    ("player", "لاعب", False, 25, 0),
    ("tafkik", "تفكيك", False, 20, 0),
    ("tajmee", "تجميع", False, 20, 0),
    ("arqam", "أرقام", False, 15, 0),
    ("mufrad", "مفرد", False, 15, 0),
    ("jam", "جمع", False, 15, 0),
    ("harf", "حرف", False, 15, 0),
    ("aks", "عكس", False, 15, 0),
    ("silsila", "سلسلة", True, 40, 40),
    ("replica", "ريبلكا", True, 30, 30),
    ("sabaq", "سباق", True, 25, 30),
    ("xo", "XO", True, 30, 20),
    ("ghmida", "غميضة", True, 30, 30),
    ("roulette", "روليت", True, 20, 40),
    ("mafia", "مافيا", True, 30, 40),
]


async def _player_limits(
    guild_id: int, game_key: str, default_min: int = 2, default_max: int = 100
) -> tuple[int, int]:
    """أقلم/أقصى لاعبين من الإعدادات لكل لعبة."""
    cfg = await _cfg(guild_id)
    mn_map = cfg.get("min_players") or {}
    mx_map = cfg.get("max_players") or {}
    cap = GAME_CAPACITY.get(game_key)
    if cap:
        cmin, cmax, cdef = cap
        default_min = max(default_min, cmin)
        default_max = cdef
    try:
        mn = int(mn_map.get(game_key, default_min))
    except Exception:
        mn = default_min
    try:
        mx = int(mx_map.get(game_key, default_max))
    except Exception:
        mx = default_max
    mn = max(1, min(1000, mn))
    mx = max(mn, min(1000, mx))
    if cap:
        cmin, cmax, cdef = cap
        mn = max(cmin, min(cmax, mn))
        mx = max(cmin, min(cmax, mx))
        if mx < mn:
            mx = mn
    if game_key == "ghmida":
        mx = max(mn, min(30, mx))
    if game_key == "silsila":
        mn = max(10, min(40, mn))
        mx = max(10, min(40, mx))
        if mx < mn:
            mx = mn
    return mn, mx


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
    """أدمن أو رتب إيقاف العامة (فردي/جماعي) أو رتب البدء إن ما تحدد إيقاف."""
    if member.guild_permissions.administrator or member.guild_permissions.manage_guild:
        return True
    if member.guild.owner_id == member.id:
        return True
    cfg = await _cfg(member.guild.id)
    key = game_key or ""
    allowed = _role_ids_allowed(cfg, key, "stopper") if key else []
    if not allowed and key:
        # fallback: رتب البدء لنفس الفئة
        allowed = _role_ids_allowed(cfg, key, "starter")
    if not allowed:
        return member.guild_permissions.manage_messages
    return _member_has_role_threshold(member, allowed)

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
    """إمبد ألعاب بدون فوتر discord.gg/row."""
    return discord.Embed(
        title=title,
        description=desc,
        color=color or discord.Color.blurple(),
    )


def _pretty_letters(word: str, gap: str = "   ") -> str:
    """حروف متباعدة واضحة: ح   ل   و"""
    chars = [c for c in (word or "") if not c.isspace()]
    return gap.join(chars)


def _scramble_word(word: str) -> str:
    chars = [c for c in word if not c.isspace()]
    if len(chars) < 2:
        return "".join(chars)
    for _ in range(12):
        random.shuffle(chars)
        if "".join(chars) != word.replace(" ", ""):
            break
    return "".join(chars)


def _anti_copy_number(num: str) -> str:
    """أرقام بصيغة يصعب نسخها كرقم عادي (مسافات عرض صفر + عرض كامل بصري)."""
    # صفر-عرض بين كل رقم + تحويل لأشكال مشابهة للعرض
    trans = str.maketrans("0123456789", "𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗")  # mathematical bold digits
    styled = num.translate(trans)
    # zero-width space between digits so plain copy is awkward
    return "​".join(styled)


def _harf_mask(word: str) -> tuple[str, str]:
    """يرجع (المعروض بمسافات وشرطة، الكلمة الأصلية)."""
    word = word.replace(" ", "")
    if len(word) < 2:
        word = word + "ا"
    idx = random.randrange(len(word))
    chars = list(word)
    chars[idx] = "_"
    shown = "  ".join(chars)
    return shown, word


# ───────────── Views مشتركة ─────────────

class PlayAgainView(discord.ui.View):
    def __init__(self, cog: "GamesSystem", game_key: str, starter_id: int):
        super().__init__(timeout=120)
        self.cog = cog
        self.game_key = game_key
        self.starter_id = starter_id

    @discord.ui.button(label="العب مرة أخرى", style=discord.ButtonStyle.primary, emoji="🔄")
    async def again(self, interaction: discord.Interaction, button: discord.ui.Button):
        # أي أحد يقدر يبدأ جولة جديدة من الزر
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
    """دخول / خروج — عداد أو زر بدء."""

    def __init__(self, cog: "GamesSystem", channel_id: int, game_type: str, show_start: bool = False):
        super().__init__(timeout=600)
        self.cog = cog
        self.channel_id = channel_id
        self.game_type = game_type
        if show_start:
            btn = discord.ui.Button(label="بدء", style=discord.ButtonStyle.success, emoji="▶️", row=1)

            async def _start(interaction: discord.Interaction):
                st = _ACTIVE.get(self.channel_id)
                if not st or st.get("phase") != "lobby" or st.get("type") != self.game_type:
                    await interaction.response.send_message("ما في لوبي.", ephemeral=True)
                    return
                if interaction.user.id != st.get("host_id") and not (
                    isinstance(interaction.user, discord.Member)
                    and (interaction.user.guild_permissions.administrator
                         or interaction.user.guild_permissions.manage_guild)
                ):
                    await interaction.response.send_message("بس المضيف أو الإدارة.", ephemeral=True)
                    return
                n = len(st.get("players") or {})
                mn = int(st.get("min_players") or 2)
                if n < mn:
                    await interaction.response.send_message(f"لازم {mn} لاعبين على الأقل.", ephemeral=True)
                    return
                await interaction.response.defer()
                st["phase"] = "starting"
                try:
                    msg = await interaction.channel.fetch_message(st["msg_id"])
                    await msg.edit(view=None)
                except Exception:
                    pass
                await self.cog._lobby_start(st, interaction.channel)

            btn.callback = _start
            self.add_item(btn)

    @discord.ui.button(label="دخول", style=discord.ButtonStyle.secondary, emoji="👤")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        st = _ACTIVE.get(self.channel_id)
        if not st or st.get("phase") != "lobby" or st.get("type") != self.game_type:
            await interaction.response.send_message("ما في لوبي مفتوح.", ephemeral=True)
            return
        players = st.get("players") or {}
        if interaction.user.id in players:
            await interaction.response.send_message("أنت منضم بالفعل ✅", ephemeral=True)
            return
        max_p = int(st.get("max_players") or 300)
        if len(players) >= max_p:
            await interaction.response.send_message(f"اللعبة ممتلئة (حد {max_p}).", ephemeral=True)
            return
        st["players"][interaction.user.id] = interaction.user.display_name
        await interaction.response.send_message("تم دخولك ✅", ephemeral=True)
        await self.cog._lobby_refresh(st)

    @discord.ui.button(label="خروج", style=discord.ButtonStyle.secondary, emoji="🚪")
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        st = _ACTIVE.get(self.channel_id)
        if not st or st.get("phase") != "lobby":
            await interaction.response.send_message("ما في لوبي.", ephemeral=True)
            return
        st["players"].pop(interaction.user.id, None)
        if not st["players"]:
            await interaction.response.send_message("خرجت · اللوبي انلغى.", ephemeral=True)
            await self.cog._clear(self.channel_id)
            try:
                msg = await interaction.channel.fetch_message(st["msg_id"])
                await msg.edit(view=None)
            except Exception:
                pass
            return
        await interaction.response.send_message("خرجت.", ephemeral=True)
        await self.cog._lobby_refresh(st)



class RouletteJoinView(discord.ui.View):
    """دخول / خروج — عداد أو زر بدء."""

    def __init__(self, cog: "GamesSystem", channel_id: int, show_start: bool = False):
        super().__init__(timeout=900)
        self.cog = cog
        self.channel_id = channel_id
        if show_start:
            btn = discord.ui.Button(label="بدء", style=discord.ButtonStyle.success, emoji="▶️", row=1)

            async def _start(interaction: discord.Interaction):
                st = _ACTIVE.get(self.channel_id)
                if not st or st.get("type") != "roulette" or st.get("phase") != "join":
                    await interaction.response.send_message("ما في لوبي.", ephemeral=True)
                    return
                if interaction.user.id != st.get("host_id"):
                    await interaction.response.send_message(
                        "بس اللي فتح الروليت يقدر يضغط بدء.",
                        ephemeral=True,
                    )
                    return
                n = len(st.get("players") or {})
                mn = int(st.get("min_players") or 2)
                if n < mn:
                    await interaction.response.send_message(f"لازم {mn} لاعبين على الأقل.", ephemeral=True)
                    return
                await interaction.response.defer()
                st["phase"] = "starting"
                try:
                    msg = await interaction.channel.fetch_message(st["msg_id"])
                    await msg.edit(view=None)
                except Exception:
                    pass
                await interaction.channel.send(f"🎡 بدأت الروليت بـ **{n}** لاعب!")
                await self.cog._roulette_begin(st, interaction.channel)

            btn.callback = _start
            self.add_item(btn)

    @discord.ui.button(label="دخول", style=discord.ButtonStyle.secondary, emoji="👤")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        st = _ACTIVE.get(self.channel_id)
        if not st or st.get("type") != "roulette" or st.get("phase") != "join":
            await interaction.response.send_message("ما في روليت مفتوحة هنا.", ephemeral=True)
            return
        uid = interaction.user.id
        players = st.get("players") or {}
        if uid in players:
            await interaction.response.send_message("أنت منضم بالفعل ✅", ephemeral=True)
            return
        max_p = int(st.get("max_players") or 1000)
        if len(players) >= max_p:
            await interaction.response.send_message(f"ممتلئة (حد {max_p}).", ephemeral=True)
            return
        st["players"][uid] = interaction.user.display_name
        await interaction.response.send_message("تم دخولك للروليت ✅", ephemeral=True)
        await self.cog._roulette_refresh(st)

    @discord.ui.button(label="خروج", style=discord.ButtonStyle.secondary, emoji="🚪")
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        st = _ACTIVE.get(self.channel_id)
        if not st or st.get("type") != "roulette" or st.get("phase") != "join":
            await interaction.response.send_message("ما في روليت مفتوحة.", ephemeral=True)
            return
        uid = interaction.user.id
        st["players"].pop(uid, None)
        if not st["players"]:
            await interaction.response.send_message("خرجت · الروليت انلغت.", ephemeral=True)
            await self.cog._clear(self.channel_id)
            try:
                msg = await interaction.channel.fetch_message(st["msg_id"])
                await msg.edit(view=None)
            except Exception:
                pass
            return
        await interaction.response.send_message("خرجت من الروليت.", ephemeral=True)
        await self.cog._roulette_refresh(st)



class RoulettePickView(discord.ui.View):
    """أزرار لاعبين مرقّمة (زي أنظمة الروليت) + صفحات + طرد عشوائي."""

    PER_PAGE = 20  # 4 صفوف × 5 أزرار

    def __init__(self, cog: "GamesSystem", channel_id: int, chooser_id: int, page: int = 0):
        super().__init__(timeout=None)
        self.cog = cog
        self.channel_id = channel_id
        self.chooser_id = int(chooser_id)
        self.page = int(page or 0)
        self._build()

    def _players_items(self, st: dict) -> list[tuple[int, str]]:
        raw = st.get("players") or {}
        out: list[tuple[int, str]] = []
        if isinstance(raw, dict):
            for k, v in raw.items():
                try:
                    uid = int(k)
                except Exception:
                    continue
                out.append((uid, v if isinstance(v, str) else str(v)))
        elif isinstance(raw, (list, tuple, set)):
            for x in raw:
                try:
                    if isinstance(x, (list, tuple)) and len(x) >= 1:
                        out.append((int(x[0]), str(x[1]) if len(x) > 1 else str(x[0])))
                    else:
                        out.append((int(x), str(x)))
                except Exception:
                    continue
        return out

    def _ordered_targets(self, st: dict) -> list[tuple[int, int, str]]:
        numbers = st.get("join_numbers") if isinstance(st.get("join_numbers"), dict) else {}
        rows: list[tuple[int, int, str]] = []
        for i, (uid, name) in enumerate(self._players_items(st), 1):
            if uid == self.chooser_id:
                continue
            if str(uid) in numbers:
                try:
                    num = int(numbers[str(uid)])
                except Exception:
                    num = i
            elif uid in numbers:
                try:
                    num = int(numbers[uid])
                except Exception:
                    num = i
            else:
                num = i
            rows.append((num, uid, name or str(uid)))
        rows.sort(key=lambda x: x[0])
        return rows

    def _build(self):
        self.clear_items()
        st = _ACTIVE.get(self.channel_id)
        if not st:
            return
        targets = self._ordered_targets(st)
        pages = max(1, (len(targets) + self.PER_PAGE - 1) // self.PER_PAGE) if targets else 1
        self.page = max(0, min(self.page, pages - 1))
        start = self.page * self.PER_PAGE
        chunk = targets[start : start + self.PER_PAGE]

        # أزرار اللاعبين — 5 بكل صف
        for idx, item in enumerate(chunk):
            num, uid, name = item[0], item[1], item[2]
            label = f"{num} | {name}"
            if len(label) > 80:
                label = label[:77] + "..."
            row = idx // 5
            btn = discord.ui.Button(
                label=label,
                style=discord.ButtonStyle.secondary,
                row=row,
                custom_id=f"rl:kick:{self.channel_id}:{uid}:{self.chooser_id}:{self.page}",
            )

            async def _kick_btn(
                interaction: discord.Interaction,
                target_id=uid,
            ):
                if interaction.user.id != self.chooser_id:
                    await interaction.response.send_message("مو دورك.", ephemeral=True)
                    return
                await self.cog._roulette_kick(
                    interaction, self.channel_id, self.chooser_id, target_id
                )

            btn.callback = _kick_btn
            self.add_item(btn)

        # صف التحكم الأخير
        ctrl_row = min(4, (len(chunk) + 4) // 5 if chunk else 0)
        if pages > 1:
            prev = discord.ui.Button(
                label="◀",
                style=discord.ButtonStyle.primary,
                row=ctrl_row,
                disabled=self.page <= 0,
            )

            async def _prev(interaction: discord.Interaction):
                if interaction.user.id != self.chooser_id:
                    await interaction.response.send_message("مو دورك.", ephemeral=True)
                    return
                v = RoulettePickView(self.cog, self.channel_id, self.chooser_id, self.page - 1)
                await interaction.response.edit_message(view=v)

            prev.callback = _prev
            self.add_item(prev)

            page_lbl = discord.ui.Button(
                label=f"{self.page + 1}/{pages}",
                style=discord.ButtonStyle.secondary,
                row=ctrl_row,
                disabled=True,
            )
            self.add_item(page_lbl)

            nxt = discord.ui.Button(
                label="▶",
                style=discord.ButtonStyle.primary,
                row=ctrl_row,
                disabled=self.page >= pages - 1,
            )

            async def _nxt(interaction: discord.Interaction):
                if interaction.user.id != self.chooser_id:
                    await interaction.response.send_message("مو دورك.", ephemeral=True)
                    return
                v = RoulettePickView(self.cog, self.channel_id, self.chooser_id, self.page + 1)
                await interaction.response.edit_message(view=v)

            nxt.callback = _nxt
            self.add_item(nxt)

        rnd = discord.ui.Button(
            label="طرد عشوائي",
            style=discord.ButtonStyle.danger,
            emoji="🎲",
            row=ctrl_row,
        )

        async def _rnd(interaction: discord.Interaction):
            if interaction.user.id != self.chooser_id:
                await interaction.response.send_message("مو دورك.", ephemeral=True)
                return
            cur = _ACTIVE.get(self.channel_id)
            if not cur or cur.get("phase") != "play":
                await interaction.response.send_message("اللعبة خلصت.", ephemeral=True)
                return
            pool = [uid for uid, _ in self._players_items(cur) if uid != self.chooser_id]
            if not pool:
                await interaction.response.send_message("ما في أحد للطرد.", ephemeral=True)
                return
            await self.cog._roulette_kick(
                interaction, self.channel_id, self.chooser_id, random.choice(pool)
            )

        rnd.callback = _rnd
        self.add_item(rnd)

        withdraw = discord.ui.Button(
            label="انسحب",
            style=discord.ButtonStyle.secondary,
            row=ctrl_row,
        )

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



class GhmidaHideView(discord.ui.View):
    """زر يفتح قوائم المربعات الفاضية (1–50)."""

    def __init__(self, cog: "GamesSystem", channel_id: int):
        super().__init__(timeout=300)
        self.cog = cog
        self.channel_id = channel_id

    @discord.ui.button(label="اختبئ", style=discord.ButtonStyle.success, emoji="🙈")
    async def hide_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        st = _ACTIVE.get(self.channel_id)
        if not st or st.get("type") != "ghmida" or st.get("phase") != "hide":
            await interaction.response.send_message("ما في مرحلة اختباء.", ephemeral=True)
            return
        uid = interaction.user.id
        if uid not in (st.get("alive") or set()) and uid not in (st.get("players") or {}):
            await interaction.response.send_message("ما أنت من اللاعبين.", ephemeral=True)
            return
        if uid in (st.get("player_square") or {}):
            sq = st["player_square"][uid]
            await interaction.response.send_message(f"أنت أصلاً في المربع **{sq}**.", ephemeral=True)
            return
        empty = [i for i, u in st["squares"].items() if u is None]
        if not empty:
            await interaction.response.send_message("ما في مربع فاضي.", ephemeral=True)
            return
        empty.sort()
        view = GhmidaSquarePickView(self.cog, self.channel_id, uid, empty, mode="hide")
        await interaction.response.send_message(
            "اختر رقم المربع للاختباء:",
            view=view,
            ephemeral=True,
        )


class GhmidaSquarePickView(discord.ui.View):
    """قوائم أرقام مربعات (حتى 25 لكل قائمة)."""

    def __init__(
        self,
        cog: "GamesSystem",
        channel_id: int,
        user_id: int,
        squares: list[int],
        mode: str = "hide",
        page: int = 0,
    ):
        super().__init__(timeout=120)
        self.cog = cog
        self.channel_id = channel_id
        self.user_id = user_id
        self.squares = squares
        self.mode = mode
        self.page = page
        self._build()

    def _build(self):
        self.clear_items()
        per = 25
        pages = max(1, (len(self.squares) + per - 1) // per)
        self.page = max(0, min(self.page, pages - 1))
        chunk = self.squares[self.page * per : (self.page + 1) * per]
        if not chunk:
            return
        opts = [
            discord.SelectOption(label=f"مربع {n}", value=str(n), description=f"رقم {n}")
            for n in chunk
        ]
        sel = discord.ui.Select(
            placeholder=f"اختر مربع · صفحة {self.page + 1}/{pages}",
            options=opts,
            min_values=1,
            max_values=1,
        )

        async def _sel(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("مو لك.", ephemeral=True)
                return
            try:
                sq = int(sel.values[0])
            except Exception:
                await interaction.response.send_message("غير صالح.", ephemeral=True)
                return
            if self.mode == "hide":
                await self.cog._ghmida_claim_square(interaction, self.channel_id, self.user_id, sq)
            else:
                await self.cog._ghmida_search(interaction, self.channel_id, self.user_id, sq)

        sel.callback = _sel
        self.add_item(sel)
        if pages > 1:
            prev = discord.ui.Button(label="◀", disabled=self.page <= 0)

            async def _p(interaction: discord.Interaction):
                if interaction.user.id != self.user_id:
                    await interaction.response.send_message("مو لك.", ephemeral=True)
                    return
                v = GhmidaSquarePickView(
                    self.cog, self.channel_id, self.user_id, self.squares, self.mode, self.page - 1
                )
                await interaction.response.edit_message(view=v)

            prev.callback = _p
            self.add_item(prev)
            nxt = discord.ui.Button(label="▶", disabled=self.page >= pages - 1)

            async def _n(interaction: discord.Interaction):
                if interaction.user.id != self.user_id:
                    await interaction.response.send_message("مو لك.", ephemeral=True)
                    return
                v = GhmidaSquarePickView(
                    self.cog, self.channel_id, self.user_id, self.squares, self.mode, self.page + 1
                )
                await interaction.response.edit_message(view=v)

            nxt.callback = _n
            self.add_item(nxt)


class GhmidaHuntView(discord.ui.View):
    """الباحث يختار مربع مشغول أو بحث عشوائي."""

    def __init__(self, cog: "GamesSystem", channel_id: int, seeker_id: int):
        super().__init__(timeout=None)
        self.cog = cog
        self.channel_id = channel_id
        self.seeker_id = seeker_id
        self._build()

    def _build(self):
        self.clear_items()
        st = _ACTIVE.get(self.channel_id)
        if not st:
            return
        occupied = sorted(
            sq for uid, sq in (st.get("player_square") or {}).items()
            if sq and uid != self.seeker_id
        )
        # قوائم المربعات المشغولة (بدون الباحث)
        for m in range(0, min(4, (len(occupied) + 24) // 25 or 1)):
            part = occupied[m * 25 : (m + 1) * 25]
            if not part:
                break
            opts = [discord.SelectOption(label=f"مربع {n}", value=str(n)) for n in part]
            sel = discord.ui.Select(
                placeholder=f"مربعات مشغولة · قائمة {m + 1}",
                options=opts,
                min_values=1,
                max_values=1,
                row=m,
            )

            async def _sel(interaction: discord.Interaction, select=sel):
                if interaction.user.id != self.seeker_id:
                    await interaction.response.send_message("مو دورك.", ephemeral=True)
                    return
                try:
                    sq = int(select.values[0])
                except Exception:
                    return
                await self.cog._ghmida_search(interaction, self.channel_id, self.seeker_id, sq)

            sel.callback = _sel
            self.add_item(sel)

        rnd = discord.ui.Button(label="بحث عشوائي", style=discord.ButtonStyle.danger, emoji="🎲", row=4)

        async def _rnd(interaction: discord.Interaction):
            if interaction.user.id != self.seeker_id:
                await interaction.response.send_message("مو دورك.", ephemeral=True)
                return
            cur = _ACTIVE.get(self.channel_id)
            if not cur:
                return
            pool = [
                sq for uid, sq in (cur.get("player_square") or {}).items()
                if sq and uid != self.seeker_id
            ]
            if not pool:
                await interaction.response.send_message("ما في أحد.", ephemeral=True)
                return
            await self.cog._ghmida_search(
                interaction, self.channel_id, self.seeker_id, random.choice(pool)
            )

        rnd.callback = _rnd
        self.add_item(rnd)





# ───────────── /edit-games UI ─────────────

class EditGameModal(discord.ui.Modal):
    def __init__(self, cog: "GamesSystem", game_key: str, meta: tuple):
        key, label, is_group, def_to, def_lobby = meta
        super().__init__(title=f"تعديل · {label}"[:45])
        self.cog = cog
        self.game_key = game_key
        self.meta = meta
        self.is_group = is_group

        self.timeout_in = discord.ui.TextInput(
            label="وقت الجولة / اللعبة (ثواني)",
            placeholder=str(def_to),
            required=True,
            max_length=4,
            default=str(def_to),
        )
        self.add_item(self.timeout_in)

        if is_group:
            self.lobby_in = discord.ui.TextInput(
                label="وقت بداية اللوبي (ثواني)",
                placeholder=str(def_lobby or 30),
                required=True,
                max_length=4,
                default=str(def_lobby or 30),
            )
            self.add_item(self.lobby_in)
            cmin, cmax, cdef = GAME_CAPACITY.get(game_key, (2, 40, 20))
            self.max_in = discord.ui.TextInput(
                label=f"أقصى لاعبين ({cmin}–{cmax})",
                placeholder=str(cdef),
                required=True,
                max_length=4,
                default=str(cdef),
            )
            self.add_item(self.max_in)

    async def on_submit(self, interaction: discord.Interaction):
        gid = interaction.guild.id
        cfg = await _cfg(gid)
        timeouts = dict(cfg.get("timeouts") or {})
        lobbies = dict(cfg.get("lobby_timeouts") or {})
        max_map = dict(cfg.get("max_players") or {})

        try:
            to = int(str(self.timeout_in.value).strip())
        except Exception:
            await interaction.response.send_message("❌ وقت الجولة لازم رقم.", ephemeral=True)
            return
        to = max(5, min(180, to))
        timeouts[self.game_key] = to

        msg_bits = [f"⏱️ وقت الجولة: **{to}s**"]

        if self.is_group:
            try:
                lb = int(str(self.lobby_in.value).strip())
            except Exception:
                await interaction.response.send_message("❌ وقت اللوبي لازم رقم.", ephemeral=True)
                return
            lb = max(5, min(180, lb))
            lobbies[self.game_key] = lb
            msg_bits.append(f"🚪 لوبي: **{lb}s**")

            cmin, cmax, cdef = GAME_CAPACITY.get(self.game_key, (2, 100, 20))
            try:
                mx = int(str(self.max_in.value).strip())
            except Exception:
                await interaction.response.send_message("❌ عدد اللاعبين لازم رقم.", ephemeral=True)
                return
            mx = max(cmin, min(cmax, mx))
            max_map[self.game_key] = mx
            msg_bits.append(f"👥 السعة: **{mx}** (من {cmin} إلى {cmax})")

        await Storage.update_guild(gid, SECTION, {
            "timeouts": timeouts,
            "lobby_timeouts": lobbies,
            "max_players": max_map,
        })
        label = self.meta[1]
        await interaction.response.send_message(
            f"✅ تم حفظ **{label}**\n" + "\n".join(msg_bits),
            ephemeral=True,
        )


class EditGamesSelect(discord.ui.Select):
    def __init__(self, cog: "GamesSystem", guild_id: int, cfg: dict):
        self.cog = cog
        self.guild_id = guild_id
        options = []
        timeouts = cfg.get("timeouts") or {}
        lobbies = cfg.get("lobby_timeouts") or {}
        max_map = cfg.get("max_players") or {}
        for key, label, is_group, def_to, def_lobby in EDITABLE_GAMES:
            to = timeouts.get(key, def_to)
            if is_group:
                cmin, cmax, cdef = GAME_CAPACITY.get(key, (2, 40, 20))
                mx = max_map.get(key, cdef)
                lb = lobbies.get(key, def_lobby or 30)
                desc = f"وقت {to}s · لوبي {lb}s · سعة {mx}/{cmax}"
            else:
                desc = f"وقت {to}s"
            options.append(discord.SelectOption(
                label=label[:100],
                value=key,
                description=desc[:100],
            ))
        super().__init__(
            placeholder="اختر لعبة لتعديلها…",
            min_values=1,
            max_values=1,
            options=options[:25],
        )

    async def callback(self, interaction: discord.Interaction):
        key = self.values[0]
        meta = next((m for m in EDITABLE_GAMES if m[0] == key), None)
        if not meta:
            await interaction.response.send_message("لعبة غير معروفة.", ephemeral=True)
            return
        # عبّي القيم الحالية
        cfg = await _cfg(interaction.guild.id)
        timeouts = cfg.get("timeouts") or {}
        lobbies = cfg.get("lobby_timeouts") or {}
        max_map = cfg.get("max_players") or {}
        key, label, is_group, def_to, def_lobby = meta
        modal = EditGameModal(self.cog, key, meta)
        modal.timeout_in.default = str(timeouts.get(key, def_to))
        if is_group:
            modal.lobby_in.default = str(lobbies.get(key, def_lobby or 30))
            cmin, cmax, cdef = GAME_CAPACITY.get(key, (2, 40, 20))
            modal.max_in.default = str(max_map.get(key, cdef))
        await interaction.response.send_modal(modal)


class EditGamesView(discord.ui.View):
    def __init__(self, cog: "GamesSystem", guild_id: int, cfg: dict):
        super().__init__(timeout=300)
        self.add_item(EditGamesSelect(cog, guild_id, cfg))


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
            return False  # صامت — بدون رد
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


    async def _restart_solo(self, channel, user, game_type: str):
        """إعادة لعبة فردية من زر العب مرة أخرى."""
        if not channel or not user:
            return
        try:
            if not await _channel_allowed(channel.guild.id, channel.id):
                await channel.send("الألعاب مقفولة بهالروم.")
                return
        except Exception:
            pass
        if isinstance(user, discord.Member) and not await _can_start(user, game_type):
            return
        cur = _ACTIVE.get(channel.id)
        if cur:
            await self._clear(channel.id)
        st = {
            "type": game_type,
            "phase": "play",
            "players": {user.id: getattr(user, "display_name", str(user.id))},
            "host_id": user.id,
            "channel_id": channel.id,
            "min_players": 1,
            "max_players": 300,
        }
        _ACTIVE[channel.id] = st
        runners = {
            "kat": self._run_kat,
            "asra": self._run_asra,
            "player": self._run_player,
            "tafkik": self._run_tafkik,
            "tajmee": self._run_tajmee,
            "arqam": self._run_arqam,
            "harf": self._run_harf,
        }
        runner = runners.get(game_type)
        if runner:
            await runner(channel, st)

    async def start_kat(self, channel, user):
        await self._restart_solo(channel, user, "kat")

    async def start_asra(self, channel, user):
        await self._restart_solo(channel, user, "asra")

    async def start_player(self, channel, user):
        await self._restart_solo(channel, user, "player")

    async def start_tafkik(self, channel, user):
        await self._restart_solo(channel, user, "tafkik")

    async def start_tajmee(self, channel, user):
        await self._restart_solo(channel, user, "tajmee")


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
            return  # صامت
        def_max = GAME_CAPACITY.get(game_type, (2, 300, 300))[2]
        cfg_min, cfg_max = await _player_limits(channel.guild.id, game_type, min_players, def_max)
        cfg = await _cfg(channel.guild.id)
        lobby_map = cfg.get("lobby_timeouts") or {}
        _lobby_default = 40 if game_type == "silsila" else 30
        try:
            lobby_secs = int(lobby_map.get(game_type) or (cfg.get("timeouts") or {}).get("lobby") or _lobby_default)
        except Exception:
            lobby_secs = _lobby_default
        lobby_secs = max(15, min(600, int(lobby_secs)))
        modes = cfg.get("lobby_modes") or {}
        lobby_mode = str(modes.get(game_type) or cfg.get("lobby_mode") or "timer").lower()
        if lobby_mode not in ("timer", "button"):
            lobby_mode = "timer"
        emb = discord.Embed(
            title=title,
            description="للدخول على اللعبة قم بالضغط" + chr(10) + "على زر **دخول**",
            color=discord.Color.from_rgb(20, 24, 40),
        )
        if lobby_mode == "button":
            emb.set_author(name="اضغط «بدء» لما تجهزوا")
        else:
            emb.set_author(name=f"⏰ ستبدأ اللعبة خلال {lobby_secs} ثانية")
        emb.set_footer(text=f"(1/{cfg_max})")
        view = LobbyView(self, channel.id, game_type, show_start=(lobby_mode == "button"))
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
            "lobby_mode": lobby_mode,
            "title": title,
            "desc": desc,
        }
        if extra:
            st.update(extra)
            if "max_players" in extra:
                try:
                    st["max_players"] = min(int(st["max_players"]), int(extra["max_players"]))
                except Exception:
                    pass
        _ACTIVE[channel.id] = st
        await self._lobby_refresh(st)
        if lobby_mode == "timer":
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
            "silsila": "سلسلة", "replica": "ريبلكا", "sabaq": "سباق",
            "xo": "XO", "ghmida": "غميضة", "mafia": "مافيا", "roulette": "روليت",
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
        emb = discord.Embed(
            title=title,
            description="للدخول على اللعبة قم بالضغط" + chr(10) + "على زر **دخول**" + (extra or ""),
            color=discord.Color.from_rgb(20, 24, 40),
        )
        mode = st.get("lobby_mode") or "timer"
        if mode == "button":
            emb.set_author(name="اضغط «بدء» لما تجهزوا")
        else:
            emb.set_author(name=f"⏰ ستبدأ اللعبة خلال {left} ثانية")
        emb.set_footer(text=f"({n}/{mx})")
        try:
            await msg.edit(
                embed=emb,
                view=LobbyView(
                    self,
                    st["channel_id"],
                    st["type"],
                    show_start=(mode == "button"),
                ),
            )
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
        elif gtype == "mafia":
            await self._mafia_begin(st, channel)
        elif gtype == "roulette":
            await self._roulette_begin(st)



    # ===== كت =====
    @commands.command(name="كت")
    @commands.cooldown(1, 2.0, commands.BucketType.user)
    async def cmd_kat(self, ctx: commands.Context):
        if not await _channel_allowed(ctx.guild.id, ctx.channel.id):
            await ctx.reply("الألعاب مقفولة بهالروم. الأدمن يضبط الرومات بـ `/games`.")
            return
        if not await _can_start(ctx.author, "kat"):
            return
        cur = _ACTIVE.get(ctx.channel.id)
        if cur and cur.get("type") != "kat":
            await ctx.reply("في لعبة شغّالة هنا.")
            return
        if cur and cur.get("type") == "kat":
            await self._clear(ctx.channel.id)

        st = {
            "type": "kat",
            "phase": "play",
            "players": {ctx.author.id: ctx.author.display_name},
            "host_id": ctx.author.id,
            "channel_id": ctx.channel.id,
            "min_players": 1,
            "max_players": 300,
            "gen": 0,
        }
        _ACTIVE[ctx.channel.id] = st
        await self._run_kat(ctx.channel, st)

    @cmd_kat.error
    async def cmd_kat_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandOnCooldown):
            try:
                await ctx.message.add_reaction("⏳")
            except Exception:
                pass
            return
        raise error

    async def _run_kat(self, channel, st):
        q, answers = random.choice(QUESTIONS)
        timeout = await _timeout(channel.guild.id, "kat", 30)
        emb = _game_embed("❓ كت", f"**{q}**")
        await channel.send(embed=emb)
        st.update({
            "answer": answers if answers == ["*"] else [_norm(a) for a in answers],
            "start": time.monotonic(),
            "host": st["host_id"],
            "allowed": None,
            "type": "kat",
            "gen": int(st.get("gen") or 0) + 1,
        })
        gen = st["gen"]
        try:
            await asyncio.wait_for(self._wait_answer(channel.id), timeout=timeout)
        except asyncio.TimeoutError:
            cur = _ACTIVE.get(channel.id)
            if cur and cur.get("type") == "kat" and cur.get("gen") == gen:
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
            f"اكتب الكلمة التالية قبل انتهاء الوقت\n\n"
            f"# {word}\n\n"
            f"⏱️ الوقت **{timeout}s**",
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
        scrambled = _scramble_word(word)
        shown = _pretty_letters(scrambled, gap="   ")
        timeout = await _timeout(channel.guild.id, "tajmee", 20)
        desc = (
            "رتّب الحروف — اكتب الكلمة الصحيحة" + chr(10) + chr(10)
            + f"# {shown}" + chr(10) + chr(10)
            + f"⏱️ الوقت **{timeout}s**"
        )
        emb = _game_embed("🧩 تجميع", desc)
        await channel.send(embed=emb)
        st.update({
            "answer": _norm_spaces(word),
            "raw": word,
            "start": time.monotonic(),
            "host": st["host_id"],
            "space_insensitive": True,
            "allowed": None,
            "type": "tajmee",
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
        base_timeout = await _timeout(channel.guild.id, "silsila", 40)
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
            return
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
        await ctx.reply("لعبة **لغز** متوقفة حالياً.")

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
        display = _anti_copy_number(num)
        host = st["host_id"]
        desc = (
            "اكتب الأرقام التالية قبل انتهاء الوقت" + chr(10) + chr(10)
            + f"# {display}" + chr(10) + chr(10)
            + f"بواسطة <@{host}>" + chr(10)
            + f"⏱️ الوقت **{timeout}s**"
        )
        emb = _game_embed("🔢 لعبة أرقام", desc)
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
        word = random.choice([w for w in WORDS if " " not in w and 3 <= len(w) <= 8] or ["غربة", "كتاب", "مدرسة"])
        shown, word = _harf_mask(word)
        timeout = await _timeout(channel.guild.id, "harf", 15)
        host = st["host_id"]
        desc = (
            "اكتشف الحرف المفقود واكتب الكلمة كاملة قبل انتهاء الوقت" + chr(10)
            + f"بواسطة <@{host}>" + chr(10) + chr(10)
            + f"# {shown}" + chr(10) + chr(10)
            + f"⏱️ الوقت **{timeout}s**"
        )
        emb = _game_embed("🔤 لعبة حرف", desc)
        await channel.send(embed=emb)
        st.update({
            "answer": _norm(word),
            "raw": word,
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
            return
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
            return
        # حد أقصى 30 لاعب
        await self._open_lobby(
            ctx.channel,
            ctx.author,
            "ghmida",
            "غميضة",
            "50 مربع للاختباء · اختاروا مربعات ثم اطردوا بعض",
            2,
            extra={"max_players": 30},
        )

    async def _run_ghmida(self, channel, st):
        """غميضة: 50 مربع · اختيار مربعات · طرد بالمربع."""
        players = dict(st.get("players") or {})
        if len(players) > 30:
            # قص لـ 30 بالترتيب
            players = dict(list(players.items())[:30])
            st["players"] = players
        n = len(players)
        if n < 2:
            await channel.send("لازم لاعبين على الأقل.")
            await self._clear(channel.id)
            return
        timeout = await _timeout(channel.guild.id, "ghmida", 30)
        st.update({
            "type": "ghmida",
            "phase": "hide",
            "squares": {i: None for i in range(1, 51)},  # رقم المربع -> user_id أو None
            "player_square": {},  # user_id -> رقم المربع
            "timeout": timeout,
            "hide_deadline": time.monotonic() + max(45, timeout * 2),
            "alive": set(players.keys()),
        })
        emb = discord.Embed(
            title="غميضة — اختباء",
            description=(
                f"**{n}** لاعب · **50** مربع\n"
                "كل لاعب يضغط **اختبئ** ويختار مربع فاضي.\n"
                "بعد ما الكل يختبئ (أو ينتهي الوقت) تبدأ جولات الطرد."
            ),
            color=discord.Color.from_rgb(20, 24, 40),
        )
        emb.set_footer(text=f"مختبئون: 0/{n}")
        view = GhmidaHideView(self, channel.id)
        msg = await channel.send(embed=emb, view=view)
        st["msg_id"] = msg.id
        st["channel_id"] = channel.id
        asyncio.create_task(self._ghmida_hide_timer(channel.id))

    async def _ghmida_hide_timer(self, channel_id: int):
        while True:
            st = _ACTIVE.get(channel_id)
            if not st or st.get("type") != "ghmida" or st.get("phase") != "hide":
                return
            left = int(st.get("hide_deadline", 0) - time.monotonic())
            if left <= 0:
                break
            await asyncio.sleep(min(5, max(1, left)))
        st = _ACTIVE.get(channel_id)
        if not st or st.get("phase") != "hide":
            return
        ch = self.bot.get_channel(channel_id)
        if not ch:
            await self._clear(channel_id)
            return
        # من ما اختبأ: مربع عشوائي فاضي
        empty = [i for i, u in st["squares"].items() if u is None]
        random.shuffle(empty)
        for uid in list(st.get("alive") or []):
            if uid not in (st.get("player_square") or {}):
                if not empty:
                    break
                sq = empty.pop()
                st["squares"][sq] = uid
                st["player_square"][uid] = sq
        await self._ghmida_start_hunt(ch, st)

    async def _ghmida_refresh_hide(self, st: dict):
        ch = self.bot.get_channel(st["channel_id"])
        if not ch:
            return
        try:
            msg = await ch.fetch_message(st["msg_id"])
        except Exception:
            return
        n = len(st.get("alive") or {})
        hidden = len(st.get("player_square") or {})
        left = max(0, int(st.get("hide_deadline", 0) - time.monotonic()))
        emb = discord.Embed(
            title="غميضة — اختباء",
            description=(
                f"**{n}** لاعب · **50** مربع\n"
                "اضغط **اختبئ** واختر مربع فاضي.\n"
                f"⏱️ باقي **{left}**ث للاختباء"
            ),
            color=discord.Color.from_rgb(20, 24, 40),
        )
        emb.set_footer(text=f"مختبئون: {hidden}/{n}")
        try:
            await msg.edit(embed=emb, view=GhmidaHideView(self, st["channel_id"]))
        except Exception:
            pass
        if hidden >= n and n >= 2:
            await self._ghmida_start_hunt(ch, st)

    async def _ghmida_start_hunt(self, channel, st: dict):
        if st.get("phase") == "hunt":
            return
        st["phase"] = "hunt"
        # عطّل زر الاختباء
        try:
            msg = await channel.fetch_message(st["msg_id"])
            await msg.edit(view=None)
        except Exception:
            pass
        hidden = len(st.get("player_square") or {})
        if hidden < 2:
            await channel.send("ما اختبأ كفاية لاعبين.")
            await self._clear(channel.id)
            return
        await channel.send(
            embed=_game_embed(
                "غميضة — البحث",
                f"**{hidden}** مختبئ في 50 مربع.\n"
                "كل جولة يُختار باحث يختار **رقم مربع** لطرد من فيه.",
            )
        )
        await self._ghmida_hunt_turn(channel, st)

    async def _ghmida_hunt_turn(self, channel, st: dict):
        alive = [uid for uid, sq in (st.get("player_square") or {}).items() if sq]
        if len(alive) <= 1:
            if alive:
                uid = alive[0]
                pts = await _add_point(channel.guild.id, uid)
                await channel.send(f"🏆 فاز بالغميضة: <@{uid}> · نجوم: **{pts}**")
            else:
                await channel.send("انتهت الغميضة بدون فائز.")
            await self._clear(channel.id)
            return
        seeker = random.choice(alive)
        st["seeker"] = seeker
        timeout = int(st.get("timeout") or 30)
        occ = sorted(
            (sq, uid) for uid, sq in st["player_square"].items() if sq
        )
        emb = _game_embed(
            "غميضة — دور البحث",
            f"<@{seeker}> عندك **{timeout}**ث\n"
            f"اختر مربع من القوائم (المربعات المشغولة فقط) أو **بحث عشوائي**.\n"
            f"الباقي: **{len(alive)}** مختبئ",
        )
        view = GhmidaHuntView(self, channel.id, seeker)
        msg = await channel.send(embed=emb, view=view)
        st["pick_msg"] = msg.id
        st["deadline"] = time.monotonic() + timeout

        async def _timer():
            await asyncio.sleep(timeout)
            cur = _ACTIVE.get(channel.id)
            if not cur or cur.get("seeker") != seeker or cur.get("phase") != "hunt":
                return
            # الباحث ما اختار → ينطرد هو
            sq = cur.get("player_square", {}).pop(seeker, None)
            if sq:
                cur["squares"][sq] = None
            await channel.send(f"⏰ <@{seeker}> ما بحث — طلع من اللعبة.")
            await self._ghmida_hunt_turn(channel, cur)

        asyncio.create_task(_timer())


    async def _ghmida_claim_square(self, interaction: discord.Interaction, channel_id: int, uid: int, square: int):
        st = _ACTIVE.get(channel_id)
        if not st or st.get("type") != "ghmida" or st.get("phase") != "hide":
            await interaction.response.send_message("انتهت مرحلة الاختباء.", ephemeral=True)
            return
        if uid in (st.get("player_square") or {}):
            await interaction.response.send_message("أنت مختبئ أصلاً.", ephemeral=True)
            return
        if st["squares"].get(square) is not None:
            await interaction.response.send_message("المربع محجوز، اختار غيره.", ephemeral=True)
            return
        st["squares"][square] = uid
        st["player_square"][uid] = square
        await interaction.response.send_message(f"اختبأت في المربع **{square}** ✅", ephemeral=True)
        await self._ghmida_refresh_hide(st)

    async def _ghmida_search(self, interaction: discord.Interaction, channel_id: int, seeker_id: int, square: int):
        st = _ACTIVE.get(channel_id)
        if not st or st.get("type") != "ghmida" or st.get("phase") != "hunt":
            await interaction.response.send_message("اللعبة خلصت.", ephemeral=True)
            return
        if interaction.user.id != seeker_id or st.get("seeker") != seeker_id:
            await interaction.response.send_message("مو دورك.", ephemeral=True)
            return
        victim = st.get("squares", {}).get(square)
        ch = interaction.channel
        try:
            await interaction.response.defer()
        except Exception:
            pass
        try:
            msg = await ch.fetch_message(st.get("pick_msg"))
            await msg.edit(view=None)
        except Exception:
            pass
        if victim is None or victim not in st.get("player_square", {}):
            await ch.send(f"📭 المربع **{square}** فاضي!")
            # الباحث يضل، جولة جديدة
            await self._ghmida_hunt_turn(ch, st)
            return
        # طرد الضحية
        st["player_square"].pop(victim, None)
        st["squares"][square] = None
        await ch.send(f"🔦 المربع **{square}** — انطرد <@{victim}>!")
        await self._ghmida_hunt_turn(ch, st)

    # ===== خمن =====
    @commands.command(name="خمن")
    async def cmd_khammen(self, ctx):
        await ctx.reply("لعبة **خمن** متوقفة حالياً.")

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
        if not await self._guard(ctx, "roulette"):
            return
        cfg = await _cfg(ctx.guild.id)
        per = int(cfg.get("roulette_max_per_page") or 20)
        # وقت الطرد/الدور — مستقل تماماً عن اللوبي
        turn_timeout = await _timeout(ctx.guild.id, "roulette", 30)
        # وقت اللوبي — من lobby_timeouts.roulette أو العام
        lobby_map = cfg.get("lobby_timeouts") or {}
        try:
            lobby_secs = int(lobby_map.get("roulette") or (cfg.get("timeouts") or {}).get("lobby") or 30)
        except Exception:
            lobby_secs = 30
        lobby_secs = max(15, min(600, lobby_secs))
        modes = cfg.get("lobby_modes") or {}
        lobby_mode = str(modes.get("roulette") or cfg.get("lobby_mode") or "timer").lower()
        if lobby_mode not in ("timer", "button"):
            lobby_mode = "timer"
        _mn, _mx = await _player_limits(ctx.guild.id, "roulette", 2, 1000)
        emb = discord.Embed(
            title="🎡 روليت",
            description="للدخول على اللعبة اضغط **دخول**",
            color=discord.Color.from_rgb(20, 24, 40),
        )
        if lobby_mode == "button":
            emb.set_author(name="اضغط «بدء» لما تجهزوا")
        else:
            emb.set_author(name=f"⏰ اللوبي: {lobby_secs}ث")
        emb.set_footer(text=f"(1/{_mx}) · دور الطرد: {turn_timeout}ث")
        try:
            if ctx.guild and ctx.guild.icon:
                emb.set_thumbnail(url=ctx.guild.icon.url)
        except Exception:
            pass
        emb.set_image(url="attachment://roulette.jpg")
        view = RouletteJoinView(self, ctx.channel.id, show_start=(lobby_mode == "button"))
        file = _roulette_file()
        if file:
            msg = await ctx.send(embed=emb, view=view, file=file)
        else:
            msg = await ctx.send(embed=emb, view=view)
        st = {
            "type": "roulette",
            "phase": "join",
            "players": {ctx.author.id: ctx.author.display_name},
            "host_id": ctx.author.id,
            "msg_id": msg.id,
            "per_page": per,
            "timeout": turn_timeout,  # وقت الطرد فقط
            "channel_id": ctx.channel.id,
            "min_players": _mn,
            "max_players": _mx,
            "lobby_secs": lobby_secs,  # وقت اللوبي فقط
            "lobby_ends": time.monotonic() + lobby_secs,
            "lobby_mode": lobby_mode,
        }
        _ACTIVE[ctx.channel.id] = st
        await self._roulette_refresh(st)
        if lobby_mode == "timer":
            asyncio.create_task(self._roulette_countdown(ctx.channel.id))

    async def _roulette_refresh(self, st: dict):
        ch = self.bot.get_channel(st["channel_id"])
        if not ch:
            return
        try:
            msg = await ch.fetch_message(st["msg_id"])
        except Exception:
            return
        n = len(st.get("players") or {})
        mx = int(st.get("max_players") or 1000)
        mode = st.get("lobby_mode") or "timer"
        turn_t = int(st.get("timeout") or 30)
        emb = discord.Embed(
            title="🎡 روليت",
            description=f"اضغط **دخول** للانضمام" + chr(10) + f"اللاعبون: **{n}/{mx}**",
            color=discord.Color.from_rgb(20, 24, 40),
        )
        if mode == "button":
            emb.set_author(name="اضغط «بدء» لما تجهزوا")
        else:
            left = max(0, int(st.get("lobby_ends", 0) - time.monotonic())) if st.get("lobby_ends") else 0
            emb.set_author(name=f"⏰ اللوبي: {left}ث متبقية")
        emb.set_footer(text=f"({n}/{mx}) · دور الطرد: {turn_t}ث")
        emb.set_image(url="attachment://roulette.jpg")
        try:
            g = ch.guild
            if g and g.icon:
                emb.set_thumbnail(url=g.icon.url)
        except Exception:
            pass
        file = _roulette_file()
        try:
            if file:
                await msg.edit(
                    embed=emb,
                    attachments=[file],
                    view=RouletteJoinView(self, st["channel_id"], show_start=(mode == "button")),
                )
            else:
                await msg.edit(
                    embed=emb,
                    view=RouletteJoinView(self, st["channel_id"], show_start=(mode == "button")),
                )
        except Exception:
            try:
                await msg.edit(
                    embed=emb,
                    view=RouletteJoinView(self, st["channel_id"], show_start=(mode == "button")),
                )
            except Exception:
                pass

    async def _roulette_countdown(self, channel_id: int):
        while True:
            st = _ACTIVE.get(channel_id)
            if not st or st.get("type") != "roulette" or st.get("phase") != "join":
                return
            left = int(st.get("lobby_ends", 0) - time.monotonic())
            if left <= 0:
                break
            try:
                await self._roulette_refresh(st)
            except Exception:
                pass
            await asyncio.sleep(1 if left <= 15 else 5)
        st = _ACTIVE.get(channel_id)
        if not st or st.get("phase") != "join":
            return
        ch = self.bot.get_channel(channel_id)
        if not ch:
            await self._clear(channel_id)
            return
        n = len(st.get("players") or {})
        mn = int(st.get("min_players") or 2)
        if n < mn:
            try:
                msg = await ch.fetch_message(st["msg_id"])
                await msg.edit(view=None)
            except Exception:
                pass
            await ch.send(f"⏱️ انتهى اللوبي · ما اكتمل العدد ({n}/{mn}).")
            await self._clear(channel_id)
            return
        try:
            msg = await ch.fetch_message(st["msg_id"])
            await msg.edit(view=None)
        except Exception:
            pass
        await ch.send(f"🎡 بدأت الروليت بـ **{n}** لاعب!")
        try:
            await self._roulette_begin(st, ch)
        except Exception as e:
            logger.exception("roulette begin failed")
            try:
                await ch.send(f"❌ فشل بدء الروليت: `{type(e).__name__}: {e}`")
            except Exception:
                pass
            await self._clear(channel_id)

    async def _roulette_begin(self, st: dict, channel=None):
        st["phase"] = "play"
        # تثبيت أرقام الدخول حسب ترتيب الدخول (ثابت حتى نهاية اللعبة)
        if not st.get("join_numbers"):
            st["join_numbers"] = {
                str(uid): i for i, uid in enumerate(list((st.get("players") or {}).keys()), 1)
            }
        ch = channel
        if ch is None:
            ch = self.bot.get_channel(st["channel_id"])
        if ch is None:
            try:
                ch = await self.bot.fetch_channel(st["channel_id"])
            except Exception:
                ch = None
        if ch is None:
            await self._clear(st.get("channel_id"))
            return
        # تأكد إن الحالة لسا في _ACTIVE
        _ACTIVE[st["channel_id"]] = st
        await self._roulette_turn(ch, st)

    async def _roulette_turn(self, channel, st: dict):
        if channel is None:
            await self._clear(st.get("channel_id"))
            return
        players = list((st.get("players") or {}).keys())
        if len(players) <= 1:
            winner = players[0] if players else None
            if winner:
                try:
                    pts = await _add_point(channel.guild.id, winner)
                    await channel.send(f"🏆 الفائز بالروليت: <@{winner}> · نجوم: **{pts}**")
                except Exception:
                    await channel.send(f"🏆 الفائز بالروليت: <@{winner}>")
            else:
                await channel.send("انتهت الروليت بدون فائز.")
            await self._clear(channel.id)
            return

        chooser = random.choice(players)
        st["chooser"] = chooser
        st["phase"] = "play"
        timeout = max(10, min(300, int(st.get("timeout") or 30)))
        emb = discord.Embed(
            title="🎡 الروليت",
            description=(
                f"<@{chooser}> لديك **{timeout}** ثانية"
                + chr(10)
                + "**لاختيار لاعب لطرده:**"
                + chr(10)
                + chr(10)
                + f"اللاعبون المتبقون: **{len(players)}**"
            ),
            color=discord.Color.from_rgb(15, 18, 32),
        )
        try:
            g = channel.guild
            if g and g.icon:
                emb.set_thumbnail(url=g.icon.url)
        except Exception:
            pass
        emb.set_image(url="attachment://roulette.jpg")
        emb.set_footer(text=f"اضغط اسم اللاعب · أو طرد عشوائي")
        try:
            view = RoulettePickView(self, channel.id, chooser, 0)
        except Exception as e:
            logger.exception("RoulettePickView build failed")
            await channel.send(f"❌ فشل بناء قائمة الطرد: `{e}`")
            await self._clear(channel.id)
            return
        try:
            file = _roulette_file()
            kwargs = dict(
                content=f"⚡ | دور الطرد{chr(10)}<@{chooser}> لديك **{timeout}** ثانية لاختيار لاعب لطرده:",
                embed=emb,
                view=view,
            )
            if file:
                kwargs["file"] = file
            msg = await channel.send(**kwargs)
        except Exception as e:
            logger.exception("roulette turn send failed")
            await channel.send(f"❌ ما قدرت أرسل دور الطرد: `{e}`")
            await self._clear(channel.id)
            return

        st["pick_msg"] = msg.id
        st["deadline"] = time.monotonic() + timeout
        _ACTIVE[channel.id] = st

        async def _timer():
            await asyncio.sleep(timeout)
            cur = _ACTIVE.get(channel.id)
            if not cur or cur.get("chooser") != chooser or cur.get("phase") != "play":
                return
            cur["players"].pop(chooser, None)
            try:
                await channel.send(f"⏰ <@{chooser}> ما اختار — انطرد.")
            except Exception:
                pass
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
        if not await self._guard(ctx, "mafia"):
            return
        cfg = await _cfg(ctx.guild.id)
        mcfg = cfg.get("mafia") or {}
        min_p = int(mcfg.get("min_players") or 5)
        max_p = int(mcfg.get("max_players") or 300)
        max_p = max(min_p, min(300, max_p))
        timeout = await _timeout(ctx.guild.id, "mafia", 30)
        await self._open_lobby(
            ctx.channel,
            ctx.author,
            "mafia",
            "مافيا",
            "الأدوار تُرسل بالخاص بعد البداية.",
            min_players=min_p,
            extra={"timeout": timeout, "max_players": max_p, "mafia_cfg": mcfg},
        )

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
        winner = message.author
        if game == "asra":
            emb = _game_embed(
                "🏆 فاز!",
                f"**الفائز:** {winner.mention}\n"
                f"جاوب خلال **{elapsed:.2f}** ثانية\n"
                f"⭐ نقاطه: **{pts}** (+1)",
                color=discord.Color.green(),
            )
        else:
            emb = _game_embed(
                "✅ فوز!",
                f"**الفائز:** {winner.mention}\n"
                f"جاوب خلال **{elapsed:.2f}** ثانية\n"
                f"⭐ نقاطه: **{pts}** (+1)",
                color=discord.Color.green(),
            )
        view = PlayAgainView(self, game if game in ("kat", "asra", "player", "tafkik", "tajmee", "arqam", "harf") else "asra", message.author.id)
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
                # أرقام: اقبل النسخ حتى لو فيها رموز عرض
                raw = content.strip()
                raw = re.sub(r"[^0-9٠-٩0-9]", "", raw.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗", "01234567890123456789")))
                ok = raw == str(st.get("answer") or "")
                if not ok:
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
            return  # صامت
        await self._clear(ctx.channel.id)
        await ctx.reply(f"⏹️ تم إيقاف اللعبة ({gtype}).")
        await _log_game(ctx.guild, f"⏹️ أوقف {ctx.author.mention} لعبة **{gtype}** في {ctx.channel.mention}")

    @commands.command(name="العاب", aliases=["ألعاب"])
    async def list_games(self, ctx: commands.Context):
        emb = discord.Embed(
            title="🎮 قائمة الألعاب",
            description="اكتب الأمر بالشات عشان تبدأ · الجماعية تحتاج لوبي",
            color=discord.Color.from_rgb(88, 101, 242),
        )
        solo = (
            "`!كت` سؤال نقاش" + chr(10)
            + "`!اسرع` اكتب بأسرع وقت" + chr(10)
            + "`!لاعب` خمّن اللاعب" + chr(10)
            + "`!تفكيك` / `!تجميع`" + chr(10)
            + "`!ارقام` · `!مفرد` · `!جمع` · `!حرف` · `!عكس`" + chr(10)
            + "`!لاعب` صورة لاعب"
        )
        group = (
            "`!روليت` طرد بالدور" + chr(10)
            + "`!مافيا` أدوار سرية" + chr(10)
            + "`!سلسلة` كلمات مترابطة" + chr(10)
            + "`!ريبلكا` اسم حيوان جماد" + chr(10)
            + "`!سباق` أسئلة سريعة" + chr(10)
            + "`!غميضة` 50 مربع" + chr(10)
            + "`!xo` اكس او"
        )
        emb.add_field(name="🎯 فردية (فورية)", value=solo, inline=True)
        emb.add_field(name="👥 جماعية (لوبي)", value=group, inline=True)
        emb.add_field(
            name="📌 مساعدة",
            value="`!توب-العاب` · `/games` رومات · الداشبورد للأوقات",
            inline=False,
        )
        emb.set_footer(text="الرتب والأوقات من الداشبورد")
        await ctx.reply(embed=emb, mention_author=False)


    @app_commands.command(name="edit-games", description="لوحة تعديل أوقات وسعة الألعاب (سلسلة، روليت، …)")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def edit_games_cmd(self, interaction: discord.Interaction):
        cfg = await _cfg(interaction.guild.id)
        lines = []
        timeouts = cfg.get("timeouts") or {}
        lobbies = cfg.get("lobby_timeouts") or {}
        max_map = cfg.get("max_players") or {}
        for key, label, is_group, def_to, def_lobby in EDITABLE_GAMES:
            to = timeouts.get(key, def_to)
            if is_group:
                cmin, cmax, cdef = GAME_CAPACITY.get(key, (2, 40, 20))
                mx = max_map.get(key, cdef)
                lb = lobbies.get(key, def_lobby or 30)
                lines.append(f"**{label}** · جولة `{to}s` · لوبي `{lb}s` · سعة `{mx}` (حد {cmax})")
            else:
                lines.append(f"**{label}** · وقت `{to}s`")
        emb = discord.Embed(
            title="🎮 تعديل الألعاب",
            description=(
                "اختر لعبة من القائمة تحت عشان تعدّل:" + chr(10)
                + "• **وقت الجولة** (ثواني)" + chr(10)
                + "• **وقت اللوبي** (للجماعية)" + chr(10)
                + "• **السعة** — مثال سلسلة من **10** إلى **40**" + chr(10) + chr(10)
                + chr(10).join(lines[:14])
                + (chr(10) + "…" if len(lines) > 14 else "")
            ),
            color=discord.Color.from_rgb(88, 101, 242),
        )
        emb.set_footer(text="الإعدادات تنحفظ فوراً · سلسلة افتراضي 40 لاعب / 40ث")
        view = EditGamesView(self, interaction.guild.id, cfg)
        await interaction.response.send_message(embed=emb, view=view, ephemeral=True)

    @edit_games_cmd.error
    async def edit_games_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ للأدمن فقط.", ephemeral=True)
            return
        raise error


async def setup(bot: commands.Bot):
    await bot.add_cog(GamesSystem(bot))
