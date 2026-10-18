"""لوحة حماية كاملة لداشبورد الموقع."""
from __future__ import annotations

import html as _html


def _esc(v) -> str:
    return _html.escape(str(v if v is not None else ""))


# مفاتيح الأقسام + هل تحتاج jail + هل لها إعدادات رقمية
SECURITY_SECTIONS = [
    {
        "key": "bot_add",
        "title": "🤖 إضافة بوتات",
        "desc": "طرد أي بوت يضاف من غير المسموح",
        "has_jail": True,
        "roles_key": "allowed_role_ids",
        "has_enabled": True,
    },
    {
        "key": "prune",
        "title": "🧹 البرون / المسح الجماعي",
        "desc": "حماية من prune members",
        "has_jail": True,
        "roles_key": "allowed_role_ids",
    },
    {
        "key": "webhook",
        "title": "🔗 الويبهوك",
        "desc": "حماية إنشاء webhooks",
        "has_jail": True,
        "roles_key": "allowed_role_ids",
    },
    {
        "key": "channels",
        "title": "📁 الرومات",
        "desc": "إنشاء/حذف/تعديل رومات",
        "has_jail": True,
        "roles_key": "allowed_role_ids",
    },
    {
        "key": "roles",
        "title": "🎭 الرتب",
        "desc": "إنشاء/تعديل/حذف رتب",
        "has_jail": True,
        "roles_key": "allowed_role_ids",
    },
    {
        "key": "permission_escalation",
        "title": "⚠️ تصعيد الصلاحيات",
        "desc": "Administrator / Manage Server / Manage Roles",
        "has_jail": False,
        "roles_key": "allowed_role_ids",
    },
    {
        "key": "guild_update",
        "title": "🏠 تعديل السيرفر",
        "desc": "اسم، أيقونة، إعدادات السيرفر",
        "has_jail": False,
        "roles_key": "allowed_role_ids",
    },
    {
        "key": "rate_limit",
        "title": "🚦 الحد السريع (Rate Limit)",
        "desc": "كم إجراء خطير خلال ثواني",
        "has_jail": True,
        "roles_key": "allowed_role_ids",
        "extra_numbers": [
            ("threshold_count", "عدد الإجراءات", 5),
            ("threshold_seconds", "خلال كم ثانية", 15),
        ],
    },
    {
        "key": "anti_spam",
        "title": "🚫 مكافحة السبام",
        "desc": "رسائل متكررة",
        "has_jail": False,
        "roles_key": "exempt_role_ids",
        "has_enabled": True,
        "extra_numbers": [
            ("max_repeats", "أقصى تكرار لنفس النص", 3),
            ("max_messages", "أقصى رسائل سريعة", 6),
            ("window_seconds", "نافذة السرعة (ثواني)", 8),
            ("timeout_seconds", "مدة التايم (ثواني)", 600),
        ],
    },
    {
        "key": "anti_link",
        "title": "🔗 مكافحة الروابط",
        "desc": "دعوات · كل الروابط · اختصارات",
        "has_jail": False,
        "roles_key": "exempt_role_ids",
        "has_enabled": True,
        "extra_numbers": [
            ("timeout_seconds", "مدة التايم (ثواني)", 300),
        ],
        "extra_flags": [
            ("block_invites", "منع دعوات ديسكورد"),
            ("block_all_links", "منع كل الروابط"),
        ],
    },
]


def build_security_html(guild, guild_id: str, conf: dict, role_picker, channel_picker, role_name_fn) -> str:
    sec_root = conf.get("security") or {}
    cards = []

    for meta in SECURITY_SECTIONS:
        sub = dict(sec_root.get(meta["key"]) or {})
        roles_key = meta["roles_key"]
        role_ids = list(sub.get(roles_key) or [])
        current_roles = " ".join(
            f'<span class="chip role-chip">{_esc(role_name_fn(guild, rid))}</span>' for rid in role_ids
        ) or '<span class="muted">لا رتب</span>'

        log_id = sub.get("log_channel_id")
        notify_id = sub.get("notify_role_id")
        jail_id = sub.get("jail_role_id")

        extra_nums = ""
        for field, label, default in meta.get("extra_numbers") or []:
            val = sub.get(field, default)
            extra_nums += (
                f'<div class="field"><label>{_esc(label)}</label>'
                f'<input type="text" name="{field}" value="{_esc(val)}" autocomplete="off"/></div>'
            )

        enabled_html = ""
        if meta.get("has_enabled"):
            # bot_add و anti_* مفعّلة افتراضياً إلا إذا False صراحة
            default_on = meta["key"] in ("bot_add", "anti_spam", "anti_link")
            is_on = sub.get("enabled") if "enabled" in sub else default_on
            checked = "checked" if is_on else ""
            enabled_html = (
                f'<div class="toggle-row">'
                f'<label><input type="checkbox" name="enabled" value="1" {checked}/> تفعيل</label>'
                f'</div>'
            )
        flags_html = ""
        for field, label in meta.get("extra_flags") or []:
            default_flag = field == "block_invites"
            is_on = sub.get(field) if field in sub else default_flag
            chk = "checked" if is_on else ""
            flags_html += (
                f'<div class="toggle-row">'
                f'<label><input type="checkbox" name="{field}" value="1" {chk}/> {_esc(label)}</label>'
                f'</div>'
            )

        jail_html = ""
        if meta.get("has_jail"):
            jail_html = (
                f'<div class="field"><label>رتبة السجن (العقاب)</label>'
                f'{role_picker(guild, "jail_role_id", multi=False, selected_ids=[jail_id] if jail_id else [])}'
                f'</div>'
            )

        cards.append(
            f'<div class="card manage-card" id="sec-{meta["key"]}">'
            f'<div class="manage-head"><h3>{meta["title"]}</h3>'
            f'<p class="muted">{_esc(meta["desc"])}</p></div>'
            f'<div class="kv"><span>الرتب الحالية</span><b>{current_roles}</b></div>'
            f'<form method="post" action="/guild/{guild_id}/security-update" class="form manage-form">'
            f'<input type="hidden" name="subsection" value="{meta["key"]}"/>'
            f'{enabled_html}{flags_html}'
            f'<div class="field"><label>رتب مسموحة / مستثناة (اختيار متعدد)</label>'
            f'{role_picker(guild, "role_ids", multi=True, selected_ids=role_ids)}'
            f'<p class="muted small">حدّد الرتب ثم احفظ — القائمة تستبدل القديمة</p></div>'
            f'<div class="field"><label>قناة اللوق</label>'
            f'{channel_picker(guild, "log_channel_id", selected_id=log_id)}</div>'
            f'<div class="field"><label>رتبة الإشعار</label>'
            f'{role_picker(guild, "notify_role_id", multi=False, selected_ids=[notify_id] if notify_id else [])}</div>'
            f'{jail_html}'
            f'{extra_nums}'
            f'<button type="submit" class="btn primary">حفظ {meta["title"]}</button>'
            f'</form></div>'
        )

    lockdown = "مفعّل" if sec_root.get("lockdown_active") else "متوقف"
    head = (
        f'<section class="card-head-row"><h2>الحماية / السكوريتي</h2>'
        f'<p class="muted">كل إعدادات الحماية · اللوكداون حالياً: <b>{lockdown}</b></p></section>'
        f'<section class="grid-2">{"".join(cards)}</section>'
    )
    return head
