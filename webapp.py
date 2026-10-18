"""
داشبورد ويب لبوت ROW — يعمل جنب البوت على نفس العملية.
الدخول عبر DASHBOARD_SECRET من Environment.
يدعم إدارة رتب الأوامر والكلمات (Aliases) لكل سيرفر.
"""

from __future__ import annotations

import html
import os
import secrets
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

try:
    from web.systems_panels import build_systems_html
except Exception:
    try:
        from systems_panels import build_systems_html  # fallback
    except Exception:
        def build_systems_html(*args, **kwargs):
            return '<section class="card"><p class="muted">لوحة الأنظمة غير متاحة حالياً.</p></section>'

try:
    from web.security_panels import build_security_html
except Exception:
    def build_security_html(*args, **kwargs):
        return '<section class="card"><p class="muted">لوحة الحماية غير متاحة.</p></section>'


# يُملأ من main بعد تشغيل البوت
bot_ref = None
storage_ref = None

APP_DIR = Path(__file__).parent
DASHBOARD_SECRET = os.getenv("DASHBOARD_SECRET", "").strip()
SESSION_SECRET = os.getenv("DASHBOARD_SESSION_SECRET") or secrets.token_hex(32)

app = FastAPI(title="ROW Dashboard", docs_url=None, redoc_url=None)

@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception):
    import traceback
    traceback.print_exc()
    msg = html.escape(str(exc)[:500])
    body = f"""
    <section class="card warn">
      <h1>حدث خطأ</h1>
      <p class="muted">الداشبورد واجه مشكلة. التفاصيل للمطور:</p>
      <pre style="white-space:pre-wrap;direction:ltr;text-align:left;background:#0a0f1a;padding:12px;border-radius:12px">{msg}</pre>
      <p><a href="/">الرئيسية</a> · <a href="/login">دخول</a></p>
    </section>
    """
    try:
        return HTMLResponse(layout("خطأ", body, request), status_code=500)
    except Exception:
        return HTMLResponse(f"<h1>Error</h1><pre>{msg}</pre>", status_code=500)


app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, max_age=60 * 60 * 12)

static_dir = APP_DIR / "web" / "static"
static_dir.mkdir(parents=True, exist_ok=True)
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ── أنظمة قابلة للإدارة من الويب ──
# section_key → (عنوان, وصف, مفتاح الرتب, مفتاح الرتبة الإضافية, كلمات افتراضية)
MANAGEABLE = {
    "time": {
        "title": "⏱️ التايم",
        "desc": "إعطاء تايم أوت",
        "roles_key": "giver_role_ids",
        "extra_role_key": "admin_role_id",
        "extra_label": "رتبة الأدمن (غير محدود)",
        "default_aliases": ["تايم", "اص", "اسكت"],
        "cmd_name": "تايم",
    },
    "ban": {
        "title": "🔨 الباند",
        "desc": "حظر الأعضاء",
        "roles_key": "allowed_role_ids",
        "extra_role_key": "unlimited_role_id",
        "extra_label": "رتبة غير محدود",
        "default_aliases": ["باند", "بانكاي", "لف", "تفو", "زحلق"],
        "cmd_name": "باند",
    },
    "unban": {
        "title": "✅ فك الباند",
        "desc": "إلغاء الحظر",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": ["فك-الباند"],
        "cmd_name": "فك-الباند",
    },
    "warn": {
        "title": "⚠️ التحذير",
        "desc": "تحذير الأعضاء",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": ["تحذير", "ت"],
        "cmd_name": "تحذير",
    },
    "unwarn": {
        "title": "🧹 شيل التحذير",
        "desc": "إزالة تحذير",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": ["شيل"],
        "cmd_name": "شيل",
    },
    "prison": {
        "title": "🔒 السجن",
        "desc": "سجن الأعضاء",
        "roles_key": "imprison_role_ids",
        "extra_role_key": "jail_role_id",
        "extra_label": "رتبة السجن (تُعطى للمسجون)",
        "default_aliases": ["سجن"],
        "cmd_name": "سجن",
    },
    "prison_release": {
        "title": "🔓 انسجن",
        "desc": "فك السجن",
        "roles_key": "release_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": ["انسجن"],
        "cmd_name": "انسجن",
        "storage_section": "prison",
    },
    "unmute": {
        "title": "🔊 فك الميوت (ان)",
        "desc": "إزالة التايم أوت",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": ["ان"],
        "cmd_name": "ان",
    },
    "role": {
        "title": "🎭 رتب",
        "desc": "تعديل رتب الأعضاء",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": ["رتب"],
        "cmd_name": "رتب",
    },
    "role_assign": {
        "title": "🏷️ رول",
        "desc": "إعطاء/سحب رول",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": ["رول"],
        "cmd_name": "رول",
    },
    "add_role": {
        "title": "⬆️ ترقية",
        "desc": "ترقية عضو",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": ["ترقية"],
        "cmd_name": "ترقية",
    },
    "remove_role": {
        "title": "⬇️ تخفيض",
        "desc": "تخفيض عضو",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": ["تخفيض"],
        "cmd_name": "تخفيض",
    },
    "staff": {
        "title": "👔 صغرى",
        "desc": "ستاف صغرى (سلسلة رتب)",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": ["صغرى"],
        "cmd_name": "صغرى",
    },
    "highstaff": {
        "title": "👔 عليا",
        "desc": "ستاف عليا",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": ["عليا"],
        "cmd_name": "عليا",
    },
    "owner": {
        "title": "👑 اونر",
        "desc": "أوامر الأونر / سلسلة اونر",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": ["اونر"],
        "cmd_name": "اونر",
    },
    "dismiss": {
        "title": "🚫 مفصول",
        "desc": "فصل/شيل رتب مع حماية",
        "roles_key": "allowed_role_ids",
        "extra_role_key": "protect_role_id",
        "extra_label": "رتبة الحماية (ما تنشال)",
        "default_aliases": ["مفصول"],
        "cmd_name": "مفصول",
    },
    "nickname": {
        "title": "✏️ نك",
        "desc": "تغيير النك نيم",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": ["نك"],
        "cmd_name": "نك",
    },
    "lock": {
        "title": "🔐 ق",
        "desc": "قفل الروم",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": ["ق"],
        "cmd_name": "ق",
    },
    "unlock": {
        "title": "🔓 ف",
        "desc": "فتح الروم",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": ["ف"],
        "cmd_name": "ف",
    },
    "clear": {
        "title": "🧹 مسح",
        "desc": "مسح رسائل",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": ["مسح"],
        "cmd_name": "مسح",
    },
    "clear_v2": {
        "title": "🧹 مسح @شخص",
        "desc": "مسح رسائل شخص محدد",
        "roles_key": "allowed_role_ids",
        "extra_role_key": "protected_role_id",
        "extra_label": "رتبة محمية (ما تنمسح رسائلها)",
        "default_aliases": ["مسح"],
        "cmd_name": None,
    },
    "rar": {
        "title": "🧹 rar",
        "desc": "شيل كل رتب شخص",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": ["rar"],
        "cmd_name": "rar",
    },

    "security_bot_add": {
        "title": "🤖 حماية إضافة بوتات",
        "desc": "مين يقدر يضيف بوت بدون عقاب",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": [],
        "cmd_name": None,
        "storage_section": "security",
        "subsection": "bot_add",
    },
    "security_prune": {
        "title": "🧹 حماية البرون / المسح الجماعي",
        "desc": "حماية من prune",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": [],
        "cmd_name": None,
        "storage_section": "security",
        "subsection": "prune",
    },
    "security_webhook": {
        "title": "🔗 حماية الويبهوك",
        "desc": "حماية إنشاء webhooks",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": [],
        "cmd_name": None,
        "storage_section": "security",
        "subsection": "webhook",
    },
    "security_channels": {
        "title": "📁 حماية الرومات",
        "desc": "حماية إنشاء/حذف رومات",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": [],
        "cmd_name": None,
        "storage_section": "security",
        "subsection": "channels",
    },
    "security_roles": {
        "title": "🎭 حماية الرتب",
        "desc": "حماية إنشاء/تعديل رتب",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": [],
        "cmd_name": None,
        "storage_section": "security",
        "subsection": "roles",
    },
    "security_permission": {
        "title": "⚠️ حماية تصعيد الصلاحيات",
        "desc": "permission escalation",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": [],
        "cmd_name": None,
        "storage_section": "security",
        "subsection": "permission_escalation",
    },
    "security_guild_update": {
        "title": "🏠 حماية تعديل السيرفر",
        "desc": "تغيير اسم/أيقونة السيرفر",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": [],
        "cmd_name": None,
        "storage_section": "security",
        "subsection": "guild_update",
    },
    "security_rate_limit": {
        "title": "🚦 حماية السبام السريع",
        "desc": "rate limit / إساءة أوامر",
        "roles_key": "allowed_role_ids",
        "extra_role_key": "jail_role_id",
        "extra_label": "رتبة العقاب (jail)",
        "default_aliases": [],
        "cmd_name": None,
        "storage_section": "security",
        "subsection": "rate_limit",
    },
    "security_anti_spam": {
        "title": "🚫 مكافحة السبام",
        "desc": "anti-spam",
        "roles_key": "exempt_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": [],
        "cmd_name": None,
        "storage_section": "security",
        "subsection": "anti_spam",
    },
    "security_anti_link": {
        "title": "🔗 مكافحة الروابط",
        "desc": "anti-link · الرتب المستثناة",
        "roles_key": "exempt_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": [],
        "cmd_name": None,
        "storage_section": "security",
        "subsection": "anti_link",
    },
    "word_filter": {
        "title": "🛡️ فلتر الكلمات",
        "desc": "رتب مستثناة من الفلتر (إن وُجدت)",
        "roles_key": "exempt_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": [],
        "cmd_name": None,
    },

}




# قنوات اللوق القابلة للضبط من الويب (مثل /mo7-log + المزيد)
LOG_TARGETS = [
    {"key": "ban_log", "label": "🔨 لوق الباند", "section": "ban", "field": "log_channel_id"},
    {"key": "warn_log", "label": "⚠️ لوق التحذير", "section": "warn", "field": "log_channel_id"},
    {"key": "unwarn_log", "label": "🧹 لوق شيل التحذير", "section": "unwarn", "field": "log_channel_id"},
    {"key": "time_log", "label": "⏱️ لوق التايم", "section": "time", "field": "log_channel_id"},
    {"key": "unmute_log", "label": "🔊 لوق فك الميوت", "section": "unmute", "field": "log_channel_id"},
    {"key": "unban_log", "label": "🔓 لوق فك الباند", "section": "unban", "field": "log_channel_id"},
    {"key": "prison_log", "label": "🔒 لوق السجن", "section": "prison", "field": "log_channel_id"},
    {"key": "clear_log", "label": "🧹 لوق المسح", "section": "clear", "field": "log_channel_id", "also": [("clear_v2", "log_channel_id")]},
    {"key": "rar_log", "label": "🧹 لوق rar", "section": "rar", "field": "log_channel_id"},
    {"key": "role_log", "label": "🎭 لوق الرتب", "section": "role", "field": "log_channel_id"},
    {"key": "nickname_log", "label": "✏️ لوق النك", "section": "nickname", "field": "log_channel_id"},
    {"key": "lock_log", "label": "🔐 لوق القفل", "section": "lock", "field": "log_channel_id"},
    {"key": "unlock_log", "label": "🔓 لوق الفتح", "section": "unlock", "field": "log_channel_id"},
    {"key": "staff_log", "label": "👔 لوق صغرى", "section": "staff", "field": "log_channel_id"},
    {"key": "highstaff_log", "label": "👔 لوق عليا", "section": "highstaff", "field": "log_channel_id"},
    {"key": "owner_log", "label": "👑 لوق اونر", "section": "owner", "field": "log_channel_id"},
    {"key": "dismiss_log", "label": "🚫 لوق مفصول", "section": "dismiss", "field": "log_channel_id"},
    {"key": "message_log", "label": "💬 لوق الرسائل", "section": "message_log", "field": "channel_id"},
    {"key": "join_log", "label": "📥 لوق الدخول", "section": "join_log", "field": "channel_id"},
    {"key": "leave_log", "label": "📤 لوق الخروج", "section": "leave_log", "field": "channel_id"},
    {"key": "command_log", "label": "🤖 لوق كل الأوامر", "section": "command_log", "field": "channel_id"},
    {"key": "filter_log", "label": "🛡️ لوق الفلتر", "section": "word_filter", "field": "log_channel_id"},
    {"key": "xp_log", "label": "⭐ لوق XP", "section": "xp", "field": "log_channel_id"},
    {"key": "security_log", "label": "🛡️ لوق الحماية العام", "section": "security", "field": "log_channel_id", "security_shared": True},
    {"key": "webhook_log", "label": "🔗 لوق الويبهوك", "section": "security", "field": "log_channel_id", "security_sub": "webhook"},
]



def _logged_in(request: Request) -> bool:
    return bool(request.session.get("auth"))


def _require_auth(request: Request) -> Optional[RedirectResponse]:
    if not _logged_in(request):
        return RedirectResponse("/login", status_code=303)
    return None


def _esc(v: Any) -> str:
    return html.escape(str(v if v is not None else ""))


def _bot_info() -> dict:
    bot = bot_ref
    if not bot or not bot.user:
        return {
            "online": False,
            "name": "—",
            "id": "—",
            "guilds": 0,
            "users": 0,
            "latency": "—",
            "avatar": "",
        }
    users = sum(g.member_count or 0 for g in bot.guilds)
    return {
        "online": True,
        "name": str(bot.user),
        "id": str(bot.user.id),
        "guilds": len(bot.guilds),
        "users": users,
        "latency": f"{round(bot.latency * 1000)}ms",
        "avatar": bot.user.display_avatar.url if bot.user else "",
    }


def _guilds_data() -> list[dict]:
    bot = bot_ref
    if not bot:
        return []
    rows = []
    for g in sorted(bot.guilds, key=lambda x: (x.member_count or 0), reverse=True):
        rows.append(
            {
                "id": str(g.id),
                "name": g.name,
                "members": g.member_count or 0,
                "icon": g.icon.url if g.icon else "",
                "owner_id": str(g.owner_id) if g.owner_id else "",
            }
        )
    return rows


async def _guild_settings(guild_id: int) -> dict:
    if not storage_ref:
        return {}
    try:
        return await storage_ref.get_guild(guild_id)
    except Exception:
        return {}


def _role_name(guild, role_id) -> str:
    if not role_id or not guild:
        return str(role_id or "—")
    try:
        r = guild.get_role(int(role_id))
        return r.name if r else f"ID:{role_id}"
    except Exception:
        return f"ID:{role_id}"


def _roles_list_html(guild, ids) -> str:
    if not ids:
        return '<span class="muted">لا يوجد</span>'
    parts = []
    for i in ids:
        name = _role_name(guild, i)
        parts.append(f'<span class="chip role-chip">{_esc(name)}</span>')
    return " ".join(parts)





# سكربت واحد للبحث في قوائم الرتب/الرومات (يُدرج مرة بالصفحة)
ROLE_FILTER_SCRIPT = """
<script>
window.filterRoles = function(input){
  const q = (input.value || '').toLowerCase();
  const box = input.nextElementSibling;
  if(!box) return;
  box.querySelectorAll('.role-opt').forEach(el => {
    const n = el.getAttribute('data-name') || '';
    el.style.display = (!q || n.includes(q)) ? '' : 'none';
  });
};
</script>
"""

def _role_picker_html(guild, name: str, multi: bool = False, selected_ids=None, colorize: bool = True, compact: bool = False) -> str:
    """قائمة رتب — بدون سكربت مكرر؛ البحث يفلتر فقط القائمة المجاورة."""
    selected_ids = set(int(x) for x in (selected_ids or []) if x)
    if not guild:
        return f'<input type="text" name="{name}" placeholder="ID الرتبة"/>'
    rows = []
    roles = sorted(guild.roles, key=lambda x: x.position, reverse=True)
    selected_names = []
    for r in roles:
        if r.is_default():
            continue
        color = f"#{r.color.value:06x}" if getattr(r, "color", None) and r.color.value else "#6c8cff"
        checked = "checked" if r.id in selected_ids else ""
        if checked:
            selected_names.append(r.name)
        itype = "checkbox" if multi else "radio"
        rows.append(
            f'<label class="role-opt" data-name="{_esc(r.name.lower())}">'
            f'<input type="{itype}" name="{name}" value="{r.id}" {checked}/>'
            f'<span class="dot" style="background:{color}"></span>'
            f'<span>{_esc(r.name)}</span>'
            f'</label>'
        )
    body = "".join(rows) if rows else '<div class="muted">لا رتب</div>'
    summary = "، ".join(selected_names[:6]) if selected_names else "لا شيء محدد (الكل / الافتراضي)"
    if len(selected_names) > 6:
        summary += f" +{len(selected_names)-6}"
    # details حتى ما تتكرر القوائم مفتوحة كلها
    return (
        f'<details class="role-details">'
        f'<summary class="role-summary">الرتب: {_esc(summary)}</summary>'
        f'<input type="search" class="role-search" placeholder="ابحث عن رتبة..." '
        f'oninput="filterRoles(this)"/>'
        f'<div class="role-picker">{body}</div>'
        f'</details>'
    )





def _channel_picker_html(guild, name: str, selected_id=None) -> str:
    """قائمة قنوات نصية داكنة لاختيار اللوق."""
    if not guild:
        return f'<input type="text" name="{name}" placeholder="ID القناة"/>'
    selected = int(selected_id) if selected_id else None
    rows = []
    channels = sorted(
        [c for c in guild.text_channels],
        key=lambda c: ((c.category.position if c.category else -1), c.position),
    )
    # خيار مسح
    rows.append(
        f'<label class="role-opt" data-name="none">'
        f'<input type="radio" name="{name}" value="0"/>'
        f'<span class="dot" style="background:#666"></span>'
        f'<span>—— بدون / إزالة ——</span></label>'
    )
    for c in channels:
        checked = "checked" if selected and c.id == selected else ""
        cat = c.category.name if c.category else "بدون كاتيغوري"
        label = f"#{c.name} · {cat}"
        rows.append(
            f'<label class="role-opt" data-name="{_esc(label.lower())}">'
            f'<input type="radio" name="{name}" value="{c.id}" {checked}/>'
            f'<span class="dot" style="background:#3ddc97"></span>'
            f'<span>{_esc(label)}</span></label>'
        )
    search = (
        f'<input type="search" class="role-search" placeholder="ابحث عن روم..." '
        f'oninput="filterRoles(this)"/>'
    )
    body = "".join(rows) if rows else '<div class="muted">لا قنوات</div>'
    return search + f'<div class="role-picker">{body}</div>'


def _channel_name(guild, channel_id) -> str:
    if not channel_id or not guild:
        return "—"
    try:
        ch = guild.get_channel(int(channel_id))
        return f"#{ch.name}" if ch else f"ID:{channel_id}"
    except Exception:
        return f"ID:{channel_id}"



def _apply_live_aliases(section: str, cmd_name: str, aliases: list[str]) -> None:
    """يحاول تحديث aliases الأمر الحي على البوت إن وُجد."""
    bot = bot_ref
    if not bot or not cmd_name:
        return
    try:
        cmd = bot.get_command(cmd_name)
        if not cmd:
            return
        # أزل الاسم الأساسي من aliases
        clean = [a for a in aliases if a and a != cmd_name]
        # حدّث خريطة الأوامر
        old_aliases = list(getattr(cmd, "aliases", []) or [])
        for a in old_aliases:
            if a in bot.all_commands and bot.all_commands.get(a) is cmd:
                bot.all_commands.pop(a, None)
        cmd.aliases = clean
        for a in clean:
            bot.all_commands[a] = cmd
    except Exception as e:
        print(f"⚠️ فشل تحديث aliases لـ {cmd_name}: {e}")


def layout(title: str, body: str, request: Request) -> str:
    user = "Admin" if _logged_in(request) else ""
    nav = ""
    if _logged_in(request):
        nav = """
        <nav class="nav">
          <a href="/">الرئيسية</a>
          <a href="/guilds">السيرفرات</a>
          <a href="/commands">الأوامر</a>
          <a href="/systems">الأنظمة</a>
          <a href="/logout" class="danger">خروج</a>
        </nav>
        """
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{_esc(title)} · ROW Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/static/style.css"/>
</head>
<body>
<div class="bg-glow"></div>
<header class="top">
  <div class="brand">
    <span class="logo">◆</span>
    <div>
      <strong>ROW</strong>
      <small>Control Dashboard</small>
    </div>
  </div>
  {nav}
</header>
<main class="container">
{body}
</main>
<footer class="foot">ROW System · Web Dashboard</footer>

{ROLE_FILTER_SCRIPT}
</body>
</html>"""


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if _logged_in(request):
        return RedirectResponse("/", status_code=303)
    if not DASHBOARD_SECRET:
        body = """
        <section class="card warn">
          <h1>⚠️ لم يُضبط سر الدخول</h1>
          <p>أضف متغير البيئة <code>DASHBOARD_SECRET</code> في Railway ثم أعد التشغيل.</p>
        </section>
        """
        return HTMLResponse(layout("Login", body, request))
    body = """
    <section class="login-wrap">
      <div class="card login-card">
        <div class="login-head">
          <span class="logo big">◆</span>
          <h1>تسجيل الدخول</h1>
          <p>لوحة تحكم بوت ROW</p>
        </div>
        <form method="post" action="/login" class="form">
          <label>كلمة السر</label>
          <input type="password" name="password" placeholder="DASHBOARD_SECRET" required autofocus/>
          <button type="submit" class="btn primary full">دخول</button>
        </form>
      </div>
    </section>
    """
    return HTMLResponse(layout("Login", body, request))


@app.post("/login")
async def login_post(request: Request, password: str = Form(...)):
    if DASHBOARD_SECRET and secrets.compare_digest(password, DASHBOARD_SECRET):
        request.session["auth"] = True
        return RedirectResponse("/", status_code=303)
    body = """
    <section class="login-wrap">
      <div class="card login-card">
        <h1>❌ كلمة السر خطأ</h1>
        <p><a href="/login">حاول مرة ثانية</a></p>
      </div>
    </section>
    """
    return HTMLResponse(layout("Login", body, request), status_code=401)


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


async def _global_stats() -> dict:
    """إحصائيات مجمّعة لكل السيرفرات."""
    tickets_open = 0
    voice_rooms = 0
    filter_words = 0
    giveaways = 0
    if not storage_ref or not bot_ref:
        return {
            "tickets_open": 0,
            "voice_rooms": 0,
            "filter_words": 0,
            "giveaways": 0,
            "guilds": 0,
        }
    for g in bot_ref.guilds:
        try:
            conf = await storage_ref.get_guild(g.id)
        except Exception:
            continue
        tickets_open += len((conf.get("tickets") or {}).get("open") or {})
        voice_rooms += len((conf.get("auto_voice") or {}).get("rooms") or {})
        filter_words += len((conf.get("word_filter") or {}).get("words") or {})
        giveaways += len((conf.get("giveaways") or {}).get("active") or {})
    return {
        "tickets_open": tickets_open,
        "voice_rooms": voice_rooms,
        "filter_words": filter_words,
        "giveaways": giveaways,
        "guilds": len(bot_ref.guilds),
    }


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    redir = _require_auth(request)
    if redir:
        return redir
    info = _bot_info()
    guilds = _guilds_data()
    try:
        stats = await _global_stats()
    except Exception as e:
        print(f"stats error: {e}")
        stats = {"tickets_open": 0, "voice_rooms": 0, "filter_words": 0, "giveaways": 0, "guilds": 0}
    status_chip = '<span class="chip on">Online</span>' if info["online"] else '<span class="chip off">Offline</span>'
    avatar = f'<img class="avatar" src="{info["avatar"]}" alt=""/>' if info["avatar"] else '<div class="avatar ph">◆</div>'
    body = f"""
    <section class="hero card">
      <div class="hero-left">
        {avatar}
        <div>
          <h1>{_esc(info["name"])} {status_chip}</h1>
          <p class="muted">ID: <code>{_esc(info["id"])}</code></p>
        </div>
      </div>
      <div class="hero-stats">
        <div class="stat"><b>{info["guilds"]}</b><span>سيرفر</span></div>
        <div class="stat"><b>{info["users"]}</b><span>عضو</span></div>
        <div class="stat"><b>{info["latency"]}</b><span>بنق</span></div>
      </div>
    </section>

    <section class="grid-3" style="margin-top:16px">
      <div class="card"><div class="stat"><b>{stats["tickets_open"]}</b><span>تذاكر مفتوحة</span></div></div>
      <div class="card"><div class="stat"><b>{stats["voice_rooms"]}</b><span>رومات فويس</span></div></div>
      <div class="card"><div class="stat"><b>{stats["filter_words"]}</b><span>كلمات فلتر</span></div></div>
    </section>
    <section class="grid-3">
      <div class="card"><div class="stat"><b>{stats["giveaways"]}</b><span>قيف أواي نشط</span></div></div>
      <div class="card"><div class="stat"><b>{info["guilds"]}</b><span>سيرفرات متصلة</span></div></div>
      <div class="card"><div class="stat"><b>{info["latency"]}</b><span>بنق مباشر</span></div></div>
    </section>

    <section class="grid-3">
      <a class="card link-card" href="/guilds"><span>🏠</span><h3>السيرفرات</h3><p>إدارة كل سيرفر · رتب · كلمات الأوامر</p></a>
      <a class="card link-card" href="/commands"><span>⚡</span><h3>الأوامر</h3><p>قائمة أوامر السلاش والنصية</p></a>
      <a class="card link-card" href="/systems"><span>🧩</span><h3>الأنظمة</h3><p>تذاكر · فويس · XP · فلتر · باكاب</p></a>
    </section>

    <section class="card">
      <div class="card-head"><h2>أحدث السيرفرات</h2></div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>السيرفر</th><th>الأعضاء</th><th>ID</th><th></th></tr></thead>
          <tbody>
            {''.join(
                f'<tr><td>{_esc(g["name"])}</td><td>{g["members"]}</td><td><code>{g["id"]}</code></td>'
                f'<td><a class="btn-mini" href="/guild/{g["id"]}">إدارة</a></td></tr>'
                for g in guilds[:8]
            ) or '<tr><td colspan="4">لا يوجد</td></tr>'}
          </tbody>
        </table>
      </div>
    </section>
    """
    return HTMLResponse(layout("الرئيسية", body, request))


@app.get("/guilds", response_class=HTMLResponse)
async def guilds_page(request: Request):
    redir = _require_auth(request)
    if redir:
        return redir
    guilds = _guilds_data()
    cards = []
    for g in guilds:
        icon = f'<img src="{g["icon"]}"/>' if g["icon"] else '<div class="g-ph">🏠</div>'
        cards.append(
            f"""
            <a class="card guild-card" href="/guild/{g["id"]}">
              {icon}
              <div>
                <strong>{_esc(g["name"])}</strong>
                <div class="muted">{g["members"]} عضو</div>
              </div>
            </a>
            """
        )
    body = f"""
    <section class="card-head-row">
      <h1>السيرفرات <span class="badge">{len(guilds)}</span></h1>
      <p class="muted">اضغط على سيرفر لإدارة رتب الأوامر والكلمات</p>
    </section>
    <section class="guild-grid">{''.join(cards) or '<div class="card">لا يوجد سيرفرات</div>'}</section>
    """
    return HTMLResponse(layout("السيرفرات", body, request))


@app.get("/guild/{guild_id}", response_class=HTMLResponse)
async def guild_detail(request: Request, guild_id: str):
    redir = _require_auth(request)
    if redir:
        return redir
    try:
        gid = int(guild_id)
    except ValueError:
        return HTMLResponse("Invalid id", status_code=400)

    bot = bot_ref
    guild = bot.get_guild(gid) if bot else None
    conf = await _guild_settings(gid)
    tab = (request.query_params.get("tab") or "overview").strip().lower()

    name = guild.name if guild else f"Guild {guild_id}"
    members = guild.member_count if guild else "—"
    icon = guild.icon.url if guild and guild.icon else ""

    tickets = conf.get("tickets", {}).get("types", {}) or {}
    open_t = conf.get("tickets", {}).get("open", {}) or {}
    av = conf.get("auto_voice", {})
    wf = conf.get("word_filter", {})
    xp = conf.get("xp", {})

    # قائمة رتب السيرفر للـ select
    role_options = ""
    if guild:
        for r in sorted(guild.roles, key=lambda x: x.position, reverse=True):
            if r.is_default() or r.managed:
                continue
            role_options += f'<option value="{r.id}">{_esc(r.name)}</option>'

    # بطاقات إدارة كل نظام
    manage_cards = []
    flash = request.query_params.get("ok")
    flash_html = f'<div class="flash ok">✅ {html.escape(flash)}</div>' if flash else ""

    for section, meta in MANAGEABLE.items():
        if section.startswith("security_") or section == "word_filter":
            continue  # الحماية والفلتر لهم صفحات خاصة
        storage_key = meta.get("storage_section") or section
        sec = conf.get(storage_key, {}) or {}
        if meta.get("subsection"):
            sec = (sec.get(meta["subsection"]) or {}) if isinstance(sec, dict) else {}
        role_ids = list(sec.get(meta["roles_key"]) or [])
        extra_id = sec.get(meta["extra_role_key"]) if meta.get("extra_role_key") else None
        aliases = list(sec.get("aliases") or meta["default_aliases"])
        aliases_str = "، ".join(aliases)

        current_roles = _roles_list_html(guild, role_ids)
        extra_html = ""
        if meta.get("extra_role_key"):
            extra_html = f"""
            <div class="field">
              <label>{_esc(meta.get('extra_label') or 'رتبة إضافية')}</label>
              <div class="muted small">الحالية: {_esc(_role_name(guild, extra_id))}</div>
              {_role_picker_html(guild, "extra_role_id", multi=False, selected_ids=[extra_id] if extra_id else [])}
              <p class="muted small">اتركها بدون اختيار = بدون تغيير · أو اختر رتبة جديدة</p>
            </div>
            """

        manage_cards.append(
            f"""
            <div class="card manage-card" id="sec-{section}">
              <div class="manage-head">
                <h3>{meta['title']}</h3>
                <p class="muted">{_esc(meta['desc'])}</p>
              </div>
              <div class="kv"><span>الرتب الحالية</span><b>{current_roles}</b></div>
              <form method="post" action="/guild/{guild_id}/update/{section}" class="form manage-form">
                <div class="field">
                  <label>➕ إضافة رتبة</label>
                  {_role_picker_html(guild, "add_role_id", multi=False)}
                  <p class="muted small">اختَر رتبة من القائمة (ابحث بالاسم)</p>
                </div>
                <div class="field">
                  <label>➖ إزالة رتبة</label>
                  {_role_picker_html(guild, "remove_role_id", multi=False, selected_ids=[])}
                  <p class="muted small">اختَر الرتبة اللي بدك تشيلها من المسموح</p>
                </div>
                {extra_html}
                <div class="field">
                  <label>📝 كلمات الأمر (مفصولة بفاصلة)</label>
                  <input type="text" name="aliases" value="{_esc(aliases_str)}" placeholder="تايم، اص، اسكت"/>
                  <p class="muted small">أول كلمة = الاسم الأساسي · الباقي aliases</p>
                </div>
                <button type="submit" class="btn primary">💾 حفظ</button>
              </form>
            </div>
            """
        )


    # بطاقات اللوقات
    log_cards = []
    for lt in LOG_TARGETS:
        cur = None
        if lt.get("security_shared"):
            # خذ أول subsection مشترك
            sec_root = conf.get("security") or {}
            for sub in ("bot_add", "channels", "roles", "prune", "guild_update", "permission_escalation", "rate_limit"):
                cur = (sec_root.get(sub) or {}).get("log_channel_id")
                if cur:
                    break
        elif lt.get("security_sub"):
            cur = ((conf.get("security") or {}).get(lt["security_sub"]) or {}).get(lt["field"])
        else:
            cur = (conf.get(lt["section"]) or {}).get(lt["field"])
        current_name = _channel_name(guild, cur)
        log_cards.append(
            f"""
            <div class="card manage-card" id="log-{lt['key']}">
              <div class="manage-head">
                <h3>{lt['label']}</h3>
                <p class="muted">الحالي: <b>{_esc(current_name)}</b></p>
              </div>
              <form method="post" action="/guild/{guild_id}/update-log" class="form manage-form">
                <input type="hidden" name="log_key" value="{lt['key']}"/>
                <div class="field">
                  <label>اختيار روم اللوق</label>
                  {_channel_picker_html(guild, "channel_id", selected_id=cur)}
                </div>
                <button type="submit" class="btn primary">💾 حفظ اللوق</button>
              </form>
            </div>
            """
        )



    system_tabs = {"filter", "voice", "xp", "autorole", "tickets", "types", "wheel"}
    systems_html = ""
    if tab in system_tabs:
        try:
            systems_html = build_systems_html(
                guild, guild_id, conf,
                role_picker=_role_picker_html,
                channel_picker=_channel_picker_html,
                role_name_fn=_role_name,
                only=tab,
            )
        except Exception as e:
            print(f"systems_html error: {e}")
            systems_html = f'<section class="card warn"><p>تعذر تحميل اللوحة: {html.escape(str(e)[:200])}</p></section>'

    def row(label, value):
        return f"<div class='kv'><span>{label}</span><b>{value}</b></div>"

    # قائمة جانبية
    tabs = [
        ("overview", "نظرة عامة"),
        ("logs", "لوقات"),
        ("security", "حماية"),
        ("filter", "فلتر"),
        ("voice", "فويس"),
        ("xp", "XP"),
        ("autorole", "أوتو رول"),
        ("tickets", "تذاكر مفتوحة"),
        ("types", "أنواع تذاكر"),
        ("wheel", "عجلة"),
        ("commands", "أوامر"),
        ("games", "ألعاب"),
    ]
    side = []
    for key, label in tabs:
        cls = "active" if tab == key else ""
        side.append(f'<a class="{cls}" href="/guild/{guild_id}?tab={key}">{label}</a>')
    side_nav = '<aside class="side-nav">' + "".join(side) + "</aside>"

    if tab == "logs":
        main_content = (
            '<section class="card-head-row"><h2>اللوقات</h2>'
            '<p class="muted">حدّد روم اللوق لكل نظام</p></section>'
            f'<section class="grid-2">{"".join(log_cards)}</section>'
        )
    elif tab == "security":
        try:
            main_content = build_security_html(
                guild, guild_id, conf,
                role_picker=_role_picker_html,
                channel_picker=_channel_picker_html,
                role_name_fn=_role_name,
            )
        except Exception as e:
            print(f"security_html error: {e}")
            main_content = f'<section class="card warn"><p>تعذر تحميل الحماية: {html.escape(str(e)[:200])}</p></section>'
    elif tab == "commands":
        main_content = (
            '<section class="card-head-row"><h2>إدارة الأوامر</h2>'
            '<p class="muted">رتب + كلمات لكل أمر</p></section>'
            f'<section class="grid-2">{"".join(manage_cards)}</section>'
        )
    elif tab == "games":
        gcfg = conf.get("games") or {}
        to = gcfg.get("timeouts") or {}
        mn = gcfg.get("min_players") or {}
        mx = gcfg.get("max_players") or {}
        mf = gcfg.get("mafia") or {}
        el = gcfg.get("eliminate") or {}
        sr = gcfg.get("starter_roles") or {}
        spr = gcfg.get("stopper_roles") or {}
        chans = gcfg.get("allowed_channels") or []
        race_target = gcfg.get("race_target", 10)
        log_ch = gcfg.get("log_channel_id")
        guild = bot_ref.get_guild(gid) if bot_ref else None
        # key, عنوان، أمر فعلي، وقت افتراضي
        solo_meta = [
            ("kat", "كت", "!كت", 30),
            ("asra", "أسرع", "!اسرع", 20),
            ("player", "لاعب", "!لاعب", 25),
            ("tafkik", "تفكيك", "!تفكيك", 20),
            ("tajmee", "تجميع", "!تجميع", 20),
            ("lughz", "لغز", "!لغز", 30),
            ("arqam", "أرقام", "!ارقام", 15),
            ("mufrad", "مفرد", "!مفرد", 15),
            ("jam", "جمع", "!جمع", 15),
            ("harf", "حرف مفقود", "!حرف", 15),
            ("aks", "عكس", "!عكس", 15),
            ("khammen", "خمن", "!خمن", 40),
        ]
        group_meta = [
            ("silsila", "سلسلة", "!سلسلة", 30, 2),
            ("replica", "ريبلكا", "!ريبلكا", 30, 2),
            ("sabaq", "سباق", "!سباق", 20, 1),
            ("xo", "XO", "!xo", 60, 2),
            ("ghmida", "غميضة", "!غميضة", 30, 2),
            ("roulette", "روليت", "!روليت", 30, 2),
            ("mafia", "مافيا", "!مافيا", 30, 5),
        ]
        solo_blocks = []
        for key, label, cmd, def_t in solo_meta:
            solo_blocks.append(f"""
            <details class="game-block">
              <summary><b>{_esc(label)}</b> <code>{_esc(cmd)}</code> · { _esc(to.get(key, def_t)) }ث</summary>
              <div class="game-body">
                <div class="field"><label>الوقت (ثواني)</label>
                  <input type="text" name="t_{key}" value="{_esc(to.get(key, def_t))}"/></div>
                <div class="field"><label>مين يبدأ</label>
                  {_role_picker_html(guild, f"start_{key}", multi=True, selected_ids=sr.get(key) or [])}</div>
                <div class="field"><label>مين يوقف</label>
                  {_role_picker_html(guild, f"stop_{key}", multi=True, selected_ids=spr.get(key) or [])}</div>
              </div>
            </details>""")
        group_blocks = []
        for key, label, cmd, def_t, def_min in group_meta:
            hard = 1000 if key == "roulette" else 300
            group_blocks.append(f"""
            <details class="game-block">
              <summary><b>{_esc(label)}</b> <code>{_esc(cmd)}</code> · { _esc(to.get(key, def_t)) }ث</summary>
              <div class="game-body">
                <div class="grid-2">
                  <div class="field"><label>الوقت</label>
                    <input type="text" name="t_{key}" value="{_esc(to.get(key, def_t))}"/></div>
                  <div class="field"><label>أقل لاعبين</label>
                    <input type="text" name="min_{key}" value="{_esc(mn.get(key, def_min))}"/></div>
                  <div class="field"><label>أقصى لاعبين</label>
                    <input type="text" name="max_{key}" value="{_esc(mx.get(key, hard))}"/></div>
                </div>
                <div class="field"><label>مين يبدأ</label>
                  {_role_picker_html(guild, f"start_{key}", multi=True, selected_ids=sr.get(key) or [])}</div>
                <div class="field"><label>مين يوقف</label>
                  {_role_picker_html(guild, f"stop_{key}", multi=True, selected_ids=spr.get(key) or [])}</div>
              </div>
            </details>""")
        ch_txt = ", ".join(str(c) for c in chans)
        main_content = f"""
        <section class="card-head-row"><h2>نظام الألعاب</h2>
          <p class="muted">اضغط على اسم اللعبة للتعديل · الأمر المعروض هو الأمر الحقيقي · الرتب الأعلى من المختارة تشتغل أيضاً</p></section>
        <section class="card manage-card">
          <form method="post" action="/guild/{guild_id}/games-settings" class="form manage-form">
            <h3>روم سجل الألعاب (فوز / إيقاف)</h3>
            {_channel_picker_html(guild, "log_channel_id", selected_id=log_ch)}
            <h3 style="margin-top:16px">رومات الألعاب (IDs — فارغ = الكل) أو استخدم /games</h3>
            <div class="field"><input type="text" name="allowed_channels" value="{_esc(ch_txt)}" placeholder="123,456"/></div>
            <h3 style="margin-top:18px">ألعاب فردية (بدون لوبي)</h3>
            {''.join(solo_blocks)}
            <h3 style="margin-top:18px">ألعاب جماعية (لوبي)</h3>
            {''.join(group_blocks)}
            <h3 style="margin-top:18px">سباق · إقصاء · مافيا</h3>
            <div class="field"><label>هدف نقاط السباق</label>
              <input type="text" name="race_target" value="{_esc(race_target)}"/></div>
            <div class="grid-2">
              <div class="field"><label>إقصاء سلسلة (0=تلقائي)</label><input type="text" name="elim_silsila" value="{_esc(el.get('silsila',0))}"/></div>
              <div class="field"><label>إقصاء ريبلكا</label><input type="text" name="elim_replica" value="{_esc(el.get('replica',0))}"/></div>
              <div class="field"><label>إقصاء غميضة</label><input type="text" name="elim_ghmida" value="{_esc(el.get('ghmida',0))}"/></div>
              <div class="field"><label>مافيا أقل</label><input type="text" name="mafia_min" value="{_esc(mf.get('min_players',5))}"/></div>
              <div class="field"><label>مافيا أقصى</label><input type="text" name="mafia_max" value="{_esc(mf.get('max_players',300))}"/></div>
              <div class="field"><label>عدد مافيا (0=تلقائي)</label><input type="text" name="mafia_count" value="{_esc(mf.get('mafia_count',0))}"/></div>
              <div class="field"><label>عدد طبيب</label><input type="text" name="doctor_count" value="{_esc(mf.get('doctor_count',0))}"/></div>
            </div>
            <p class="muted small">أوامر مساعدة: <code>!توب</code> · <code>!وقف</code> · <code>!العاب</code> · <code>/games</code></p>
            <button type="submit" class="btn primary">حفظ</button>
          </form>
        </section>
        """ + ROLE_FILTER_SCRIPT


    else:
        main_content = f"""
        <section class="grid-2">
          <div class="card">
            <h2>التذاكر</h2>
            {row("أنواع معدّة", len(tickets))}
            {row("مفتوحة الآن", len(open_t))}
          </div>
          <div class="card">
            <h2>الفويس</h2>
            {row("روم الزرار", av.get("trigger_channel_id") or "—")}
            {row("رومات نشطة", len(av.get("rooms") or {}))}
          </div>
          <div class="card">
            <h2>XP</h2>
            {row("الحالة", "مفعّل" if xp.get("enabled", True) else "متوقف")}
          </div>
          <div class="card">
            <h2>الفلتر</h2>
            {row("كلمات", len(wf.get("words") or []))}
            {row("مفعّل", "نعم" if wf.get("enabled", True) else "لا")}
          </div>
          <div class="card">
            <h2>الحماية</h2>
            {row("اللوكداون", "مفعّل" if (conf.get("security") or {}).get("lockdown_active") else "متوقف")}
            {row("الأقسام", "10")}
          </div>
        </section>
        <p class="muted" style="margin-top:16px">اختَر قسم من القائمة: لوقات · فلتر · فويس · أوامر…</p>
        """

    body = f"""
    {flash_html}
    <section class="hero card">
      <div class="hero-left">
        {'<img class="avatar" src="'+icon+'"/>' if icon else '<div class="avatar ph">🏠</div>'}
        <div>
          <h1>{_esc(name)}</h1>
          <p class="muted">{members} عضو · <code>{_esc(guild_id)}</code></p>
        </div>
      </div>
      <div class="hero-stats">
        <div class="stat"><b>{len(open_t)}</b><span>تذاكر</span></div>
        <div class="stat"><b>{len(av.get("rooms") or {})}</b><span>فويس</span></div>
        <div class="stat"><b>{len(wf.get("words") or [])}</b><span>فلتر</span></div>
      </div>
    </section>

    <div class="guild-layout">
      {side_nav}
      <div class="guild-main">
        {main_content}
        <p class="muted center" style="margin-top:24px"><a href="/guilds">← رجوع للسيرفرات</a></p>
      </div>
    </div>
    """

    return HTMLResponse(layout(name, body, request))


@app.post("/guild/{guild_id}/update/{section}")
async def guild_update_section(
    request: Request,
    guild_id: str,
    section: str,
    add_role_id: str = Form(""),
    remove_role_id: str = Form(""),
    aliases: str = Form(""),
    extra_role_id: str = Form(""),
):
    redir = _require_auth(request)
    if redir:
        return redir
    if section not in MANAGEABLE:
        return HTMLResponse("Unknown section", status_code=400)
    try:
        gid = int(guild_id)
    except ValueError:
        return HTMLResponse("Invalid id", status_code=400)

    meta = MANAGEABLE[section]
    conf = await _guild_settings(gid)
    storage_key = meta.get("storage_section") or section
    sec = dict(conf.get(storage_key, {}) or {})
    roles_key = meta["roles_key"]
    role_ids = list(sec.get(roles_key) or [])

    # إضافة رتبة
    if add_role_id and add_role_id.strip().isdigit():
        rid = int(add_role_id.strip())
        if rid not in role_ids:
            role_ids.append(rid)

    # إزالة رتبة
    if remove_role_id and remove_role_id.strip().isdigit():
        rid = int(remove_role_id.strip())
        role_ids = [x for x in role_ids if x != rid]

    updates: dict = {roles_key: role_ids}

    # رتبة إضافية (أدمن / غير محدود)
    if meta.get("extra_role_key") and extra_role_id != "":
        if extra_role_id == "0":
            updates[meta["extra_role_key"]] = None
        elif extra_role_id.strip().isdigit():
            updates[meta["extra_role_key"]] = int(extra_role_id.strip())

    # aliases
    if aliases is not None:
        parts = [p.strip() for p in aliases.replace("،", ",").replace("|", ",").split(",") if p.strip()]
        # إزالة تكرار مع الحفاظ على الترتيب
        seen = set()
        clean = []
        for p in parts:
            if p not in seen:
                seen.add(p)
                clean.append(p)
        if clean:
            updates["aliases"] = clean
            _apply_live_aliases(section, meta.get("cmd_name") or clean[0], clean)

    if storage_ref:
        if meta.get("subsection") and hasattr(storage_ref, "update_security"):
            await storage_ref.update_security(gid, meta["subsection"], updates)
        else:
            await storage_ref.update_guild(gid, storage_key, updates)

    title = meta["title"]
    return RedirectResponse(
        f"/guild/{guild_id}?ok=تم حفظ إعدادات {title}",
        status_code=303,
    )




@app.post("/guild/{guild_id}/update-log")
async def guild_update_log(
    request: Request,
    guild_id: str,
    log_key: str = Form(""),
    channel_id: str = Form(""),
):
    redir = _require_auth(request)
    if redir:
        return redir
    try:
        gid = int(guild_id)
    except ValueError:
        return HTMLResponse("Invalid id", status_code=400)

    target = next((x for x in LOG_TARGETS if x["key"] == log_key), None)
    if not target:
        return HTMLResponse("Unknown log", status_code=400)

    ch_id = None
    if channel_id and channel_id.strip().isdigit():
        val = int(channel_id.strip())
        ch_id = None if val == 0 else val

    if not storage_ref:
        return RedirectResponse(f"/guild/{guild_id}?ok=لا تخزين", status_code=303)

    field = target["field"]
    updates = {field: ch_id}

    if target.get("security_shared"):
        for sub in ("bot_add", "channels", "roles", "prune", "guild_update", "permission_escalation", "rate_limit", "anti_spam", "anti_link"):
            try:
                await storage_ref.update_security(gid, sub, updates)
            except Exception:
                pass
    elif target.get("security_sub"):
        await storage_ref.update_security(gid, target["security_sub"], updates)
    else:
        await storage_ref.update_guild(gid, target["section"], updates)
        for also_sec, also_field in target.get("also") or []:
            await storage_ref.update_guild(gid, also_sec, {also_field: ch_id})

    return RedirectResponse(
        f"/guild/{guild_id}?ok=تم حفظ {target['label']}",
        status_code=303,
    )




# ───────── أنظمة: فلتر / فويس / XP / تذاكر ─────────

@app.post("/guild/{guild_id}/filter-add")
async def filter_add(request: Request, guild_id: str, word: str = Form("")):
    redir = _require_auth(request)
    if redir:
        return redir
    gid = int(guild_id)
    w = (word or "").strip().lower()
    if not w or not storage_ref:
        return RedirectResponse(f"/guild/{guild_id}", status_code=303)
    conf = await _guild_settings(gid)
    words = list((conf.get("word_filter") or {}).get("words") or [])
    if w not in words:
        words.append(w)
        await storage_ref.update_guild(gid, "word_filter", {"words": words, "enabled": True})
    return RedirectResponse(f"/guild/{guild_id}?ok=تمت إضافة الكلمة", status_code=303)


@app.post("/guild/{guild_id}/filter-remove")
async def filter_remove(request: Request, guild_id: str, word: str = Form("")):
    redir = _require_auth(request)
    if redir:
        return redir
    gid = int(guild_id)
    w = (word or "").strip().lower()
    conf = await _guild_settings(gid)
    words = [x for x in ((conf.get("word_filter") or {}).get("words") or []) if x != w]
    if storage_ref:
        await storage_ref.update_guild(gid, "word_filter", {"words": words})
    return RedirectResponse(f"/guild/{guild_id}?ok=تم حذف الكلمة", status_code=303)


@app.post("/guild/{guild_id}/filter-toggle")
async def filter_toggle(
    request: Request,
    guild_id: str,
    enabled: str = Form(""),
    block_invites: str = Form(""),
):
    redir = _require_auth(request)
    if redir:
        return redir
    gid = int(guild_id)
    if storage_ref:
        await storage_ref.update_guild(
            gid,
            "word_filter",
            {
                "enabled": enabled == "1",
                "block_invites": block_invites == "1",
            },
        )
    return RedirectResponse(f"/guild/{guild_id}?ok=تم حفظ إعدادات الفلتر", status_code=303)


@app.post("/guild/{guild_id}/auto-voice")
async def auto_voice_update(
    request: Request,
    guild_id: str,
    trigger_channel_id: str = Form("0"),
    category_id: str = Form("0"),
    name_template: str = Form(""),
    user_limit: str = Form("0"),
):
    redir = _require_auth(request)
    if redir:
        return redir
    gid = int(guild_id)
    def _id(v):
        try:
            n = int(str(v).strip())
            return None if n == 0 else n
        except Exception:
            return None
    try:
        limit = int(str(user_limit).strip() or "0")
    except Exception:
        limit = 0
    tpl = (name_template or "").strip() or "🔊 روم {user}"
    if storage_ref:
        await storage_ref.update_guild(
            gid,
            "auto_voice",
            {
                "trigger_channel_id": _id(trigger_channel_id),
                "category_id": _id(category_id),
                "name_template": tpl,
                "user_limit": max(0, limit),
            },
        )
    return RedirectResponse(f"/guild/{guild_id}?ok=تم حفظ Auto Voice", status_code=303)


@app.post("/guild/{guild_id}/xp-settings")
async def xp_settings(
    request: Request,
    guild_id: str,
    enabled: str = Form(""),
    xp_min: str = Form("5"),
    xp_max: str = Form("15"),
    cooldown_seconds: str = Form("30"),
    levelup_channel_id: str = Form(""),
):
    redir = _require_auth(request)
    if redir:
        return redir
    gid = int(guild_id)
    def _int(v, default):
        try:
            return int(str(v).strip())
        except Exception:
            return default
    ch = None
    if levelup_channel_id and str(levelup_channel_id).strip().isdigit():
        n = int(levelup_channel_id.strip())
        ch = None if n == 0 else n
    updates = {
        "enabled": enabled == "1",
        "xp_min": max(1, _int(xp_min, 5)),
        "xp_max": max(1, _int(xp_max, 15)),
        "cooldown_seconds": max(0, _int(cooldown_seconds, 30)),
        "levelup_channel_id": ch,
    }
    if updates["xp_min"] > updates["xp_max"]:
        updates["xp_min"], updates["xp_max"] = updates["xp_max"], updates["xp_min"]
    if storage_ref:
        await storage_ref.update_guild(gid, "xp", updates)
    return RedirectResponse(f"/guild/{guild_id}?ok=تم حفظ XP", status_code=303)


@app.post("/guild/{guild_id}/xp-reward-add")
async def xp_reward_add(
    request: Request,
    guild_id: str,
    level: str = Form(""),
    role_id: str = Form(""),
):
    redir = _require_auth(request)
    if redir:
        return redir
    gid = int(guild_id)
    if not str(level).strip().isdigit() or not str(role_id).strip().isdigit():
        return RedirectResponse(f"/guild/{guild_id}?ok=بيانات غير صالحة", status_code=303)
    conf = await _guild_settings(gid)
    rewards = dict((conf.get("xp") or {}).get("role_rewards") or {})
    rewards[str(int(level))] = int(role_id)
    if storage_ref:
        await storage_ref.update_guild(gid, "xp", {"role_rewards": rewards})
    return RedirectResponse(f"/guild/{guild_id}?ok=تمت إضافة المكافأة", status_code=303)


@app.post("/guild/{guild_id}/xp-reward-remove")
async def xp_reward_remove(request: Request, guild_id: str, level: str = Form("")):
    redir = _require_auth(request)
    if redir:
        return redir
    gid = int(guild_id)
    conf = await _guild_settings(gid)
    rewards = dict((conf.get("xp") or {}).get("role_rewards") or {})
    rewards.pop(str(level).strip(), None)
    if storage_ref:
        await storage_ref.update_guild(gid, "xp", {"role_rewards": rewards})
    return RedirectResponse(f"/guild/{guild_id}?ok=تم حذف المكافأة", status_code=303)


@app.post("/guild/{guild_id}/ticket-close")
async def ticket_close_web(request: Request, guild_id: str, channel_id: str = Form("")):
    redir = _require_auth(request)
    if redir:
        return redir
    try:
        gid = int(guild_id)
        cid = int(str(channel_id).strip())
    except Exception:
        return RedirectResponse(f"/guild/{guild_id}", status_code=303)

    conf = await _guild_settings(gid)
    tickets = dict(conf.get("tickets") or {})
    open_map = dict(tickets.get("open") or {})
    open_map.pop(str(cid), None)
    tickets["open"] = open_map
    if storage_ref:
        await storage_ref.update_guild(gid, "tickets", {"open": open_map})

    # حذف الروم إن أمكن
    bot = bot_ref
    if bot:
        guild = bot.get_guild(gid)
        ch = guild.get_channel(cid) if guild else None
        if ch:
            try:
                await ch.delete(reason="Closed from ROW web dashboard")
            except Exception as e:
                print(f"ticket close delete failed: {e}")

    return RedirectResponse(f"/guild/{guild_id}?ok=تم إغلاق التذكرة", status_code=303)




@app.post("/guild/{guild_id}/ticket-type")
async def ticket_type_update(
    request: Request,
    guild_id: str,
    ticket_num: str = Form(""),
    name: str = Form(""),
    category_id: str = Form("0"),
    role_id: str = Form("0"),
    admin_id: str = Form("0"),
    log_channel_id: str = Form("0"),
    tqeem_room_id: str = Form("0"),
    welcome_msg: str = Form(""),
):
    redir = _require_auth(request)
    if redir:
        return redir
    try:
        gid = int(guild_id)
        num = int(str(ticket_num).strip())
        if num < 1 or num > 15:
            raise ValueError("num")
    except Exception:
        return RedirectResponse(f"/guild/{guild_id}", status_code=303)

    def _id(v):
        try:
            n = int(str(v).strip())
            return None if n == 0 else n
        except Exception:
            return None

    conf = await _guild_settings(gid)
    tickets = dict(conf.get("tickets") or {})
    types = dict(tickets.get("types") or {})
    current = dict(types.get(str(num)) or {})
    if name.strip():
        current["name"] = name.strip()
    current["category_id"] = _id(category_id)
    current["role_id"] = _id(role_id)
    current["admin_id"] = _id(admin_id)
    current["log_channel_id"] = _id(log_channel_id)
    current["tqeem_room_id"] = _id(tqeem_room_id)
    if welcome_msg is not None:
        current["welcome_msg"] = welcome_msg.strip()
    types[str(num)] = current
    if storage_ref:
        await storage_ref.update_guild(gid, "tickets", {"types": types})
    return RedirectResponse(f"/guild/{guild_id}?ok=تم حفظ نوع التذكرة {num}", status_code=303)


@app.post("/guild/{guild_id}/autorole-save")
async def autorole_save(
    request: Request,
    guild_id: str,
    enabled: str = Form(""),
    add_role_id: str = Form(""),
):
    redir = _require_auth(request)
    if redir:
        return redir
    gid = int(guild_id)
    conf = await _guild_settings(gid)
    ar = dict(conf.get("auto_role") or {})
    roles = list(ar.get("role_ids") or [])
    if add_role_id and str(add_role_id).strip().isdigit():
        rid = int(add_role_id)
        if rid and rid not in roles:
            roles.append(rid)
    if storage_ref:
        await storage_ref.update_guild(
            gid,
            "auto_role",
            {"enabled": enabled == "1", "role_ids": roles},
        )
    return RedirectResponse(f"/guild/{guild_id}?ok=تم حفظ Auto Role", status_code=303)


@app.post("/guild/{guild_id}/autorole-remove")
async def autorole_remove(request: Request, guild_id: str, role_id: str = Form("")):
    redir = _require_auth(request)
    if redir:
        return redir
    gid = int(guild_id)
    conf = await _guild_settings(gid)
    roles = [r for r in ((conf.get("auto_role") or {}).get("role_ids") or []) if int(r) != int(role_id or 0)]
    if storage_ref:
        await storage_ref.update_guild(gid, "auto_role", {"role_ids": roles})
    return RedirectResponse(f"/guild/{guild_id}?ok=تم حذف الرتبة", status_code=303)


@app.post("/guild/{guild_id}/wheel-points")
async def wheel_points_set(
    request: Request,
    guild_id: str,
    user_id: str = Form(""),
    points: str = Form("0"),
):
    redir = _require_auth(request)
    if redir:
        return redir
    try:
        gid = int(guild_id)
        uid = int(str(user_id).strip())
        pts = max(0, int(str(points).strip() or "0"))
    except Exception:
        return RedirectResponse(f"/guild/{guild_id}?ok=بيانات غير صالحة", status_code=303)
    conf = await _guild_settings(gid)
    wheel = dict(conf.get("wheel") or {})
    points_map = dict(wheel.get("points") or {})
    points_map[str(uid)] = pts
    if storage_ref:
        await storage_ref.update_guild(gid, "wheel", {"points": points_map})
    return RedirectResponse(f"/guild/{guild_id}?ok=تم تحديث النقاط", status_code=303)


@app.post("/guild/{guild_id}/wheel-reset-all")
async def wheel_reset_all(request: Request, guild_id: str):
    redir = _require_auth(request)
    if redir:
        return redir
    gid = int(guild_id)
    if storage_ref:
        await storage_ref.update_guild(gid, "wheel", {"points": {}})
    return RedirectResponse(f"/guild/{guild_id}?ok=تم تصفير كل النقاط", status_code=303)







@app.post("/guild/{guild_id}/security-update")
async def security_update(request: Request, guild_id: str):
    redir = _require_auth(request)
    if redir:
        return redir
    try:
        gid = int(guild_id)
    except ValueError:
        return HTMLResponse("Invalid id", status_code=400)

    form = await request.form()
    subsection = str(form.get("subsection") or "").strip()
    allowed_keys = {
        "bot_add", "prune", "webhook", "channels", "roles",
        "permission_escalation", "guild_update", "rate_limit",
        "anti_spam", "anti_link",
    }
    if subsection not in allowed_keys:
        return RedirectResponse(f"/guild/{guild_id}?tab=security", status_code=303)

    def _id(v):
        try:
            n = int(str(v).strip())
            return None if n == 0 else n
        except Exception:
            return None

    # multi checkbox role_ids
    raw_roles = form.getlist("role_ids") if hasattr(form, "getlist") else form.get("role_ids")
    role_ids = []
    if isinstance(raw_roles, list):
        for x in raw_roles:
            i = _id(x)
            if i:
                role_ids.append(i)
    elif raw_roles:
        i = _id(raw_roles)
        if i:
            role_ids.append(i)

    updates = {
        "log_channel_id": _id(form.get("log_channel_id")),
        "notify_role_id": _id(form.get("notify_role_id")),
    }

    # roles key depends on subsection
    if subsection in ("anti_spam", "anti_link"):
        updates["exempt_role_ids"] = role_ids
        updates["enabled"] = str(form.get("enabled") or "") == "1"
    else:
        updates["allowed_role_ids"] = role_ids
        if subsection == "bot_add":
            updates["enabled"] = str(form.get("enabled") or "") == "1"

    if subsection in ("bot_add", "prune", "webhook", "channels", "roles", "rate_limit"):
        updates["jail_role_id"] = _id(form.get("jail_role_id"))

    # flags
    for field in ("block_invites", "block_all_links"):
        if field in form:
            updates[field] = str(form.get(field) or "") == "1"
        elif subsection == "anti_link":
            # checkbox missing = off
            updates[field] = False

    # numbers
    for field in ("threshold_count", "threshold_seconds", "max_repeats", "timeout_seconds", "max_messages", "window_seconds"):
        if field in form and str(form.get(field) or "").strip() != "":
            try:
                updates[field] = max(0, int(str(form.get(field)).strip()))
            except Exception:
                pass

    if storage_ref and hasattr(storage_ref, "update_security"):
        await storage_ref.update_security(gid, subsection, updates)

    return RedirectResponse(f"/guild/{guild_id}?tab=security&ok=تم+حفظ+الحماية", status_code=303)



@app.post("/guild/{guild_id}/games-settings")
async def games_settings(request: Request, guild_id: str):
    redir = _require_auth(request)
    if redir:
        return redir
    try:
        gid = int(guild_id)
    except ValueError:
        return HTMLResponse("bad id", status_code=400)
    form = await request.form()

    def _int(name, default, lo=0, hi=1000):
        try:
            return max(lo, min(hi, int(str(form.get(name) or default).strip())))
        except Exception:
            return default

    def _multi_ids(prefix_key):
        # checkbox multi: form.getlist(name)
        try:
            vals = form.getlist(prefix_key)
        except Exception:
            vals = [form.get(prefix_key)] if form.get(prefix_key) else []
        out = []
        for v in vals:
            try:
                i = int(str(v).strip())
                if i and i not in out:
                    out.append(i)
            except Exception:
                pass
        return out[:20]

    solo = ["kat","asra","player","tafkik","tajmee","lughz","arqam","mufrad","jam","harf","aks","khammen"]
    group = ["silsila","replica","sabaq","xo","ghmida","roulette","mafia"]
    keys = solo + group
    timeouts = {}
    min_players = {}
    max_players = {}
    starter_roles = {}
    stopper_roles = {}
    for k in keys:
        hard = 1000 if k == "roulette" else 300
        timeouts[k] = _int(f"t_{k}", 30, 5, 100)
        starter_roles[k] = _multi_ids(f"start_{k}")
        stopper_roles[k] = _multi_ids(f"stop_{k}")
        if k in group:
            min_players[k] = _int(f"min_{k}", 1, 1, hard)
            max_players[k] = _int(f"max_{k}", hard, 1, hard)
            if max_players[k] < min_players[k]:
                max_players[k] = min_players[k]
        else:
            min_players[k] = 1
            max_players[k] = hard
    eliminate = {
        "silsila": _int("elim_silsila", 0, 0, 100),
        "replica": _int("elim_replica", 0, 0, 100),
        "ghmida": _int("elim_ghmida", 0, 0, 100),
        "roulette": 0,
    }
    mafia_min = _int("mafia_min", 5, 3, 300)
    mafia_max = _int("mafia_max", 300, 5, 300)
    min_players["mafia"] = mafia_min
    max_players["mafia"] = mafia_max
    mafia = {
        "min_players": mafia_min,
        "max_players": mafia_max,
        "mafia_count": _int("mafia_count", 0, 0, 40),
        "doctor_count": _int("doctor_count", 0, 0, 15),
    }
    race_target = _int("race_target", 10, 3, 50)
    log_channel_id = _int("log_channel_id", 0, 0, 10**18) or None
    ch_raw = str(form.get("allowed_channels") or "").strip()
    allowed_channels = []
    for part in ch_raw.replace(" ", ",").split(","):
        if part.strip().isdigit():
            allowed_channels.append(int(part.strip()))
    if storage_ref:
        await storage_ref.update_guild(gid, "games", {
            "timeouts": timeouts,
            "min_players": min_players,
            "max_players": max_players,
            "eliminate": eliminate,
            "mafia": mafia,
            "race_target": race_target,
            "starter_roles": starter_roles,
            "stopper_roles": stopper_roles,
            "allowed_channels": allowed_channels,
            "log_channel_id": log_channel_id,
        })
    return RedirectResponse(f"/guild/{guild_id}?tab=games&ok=تم+الحفظ", status_code=303)

@app.get("/commands", response_class=HTMLResponse)
async def commands_page(request: Request):
    redir = _require_auth(request)
    if redir:
        return redir
    groups = [
        ("⚔️ إشراف", [
            "باند", "فك-الباند", "تايم", "ان", "تحذير", "شيل", "سجن", "انسجن",
            "ق", "ف", "مسح", "نك", "rar",
        ]),
        ("🎭 رتب", [
            "رتب", "رول", "ترقية", "تخفيض", "صغرى", "عليا", "اونر", "مفصول",
            "/autorole", "/role-all",
        ]),
        ("⚙️ إعداد إشراف", [
            "/set-up-time", "/set-up-ban", "/set-up-unban", "/set-up-warn", "/set-up-unwarn",
            "/set-up-prison", "/set-up-unmute", "/set-up-nickname", "/set-up-lock", "/set-up-unlock",
            "/set-up-clear", "/set-up-clear-v2", "/set-up-rar",
        ]),
        ("⚙️ إعداد رتب", [
            "/set-up-role", "/set-up-roles", "/set-up-add-role", "/set-up-remove-role",
            "/set-up-staff", "/set-up-highstaff", "/set-up-owner", "/set-up-مفصول",
        ]),
        ("⭐ تفاعل", [
            "رانك", "توب", "$top", "اعطي-اكسبي", "اقتراح", "/suggest",
            "/set-up-xp", "/set-up-quest-staff", "/set-up-quest-highstaff", "/set-up-quest-owner",
            "/set-up-suggestions",
        ]),
        ("🎫 تذاكر", [
            "/ticket-setup", "/ticket-panel", "/close", "/forceclose",
            "!close", "!forceclose", "!rename",
        ]),
        ("🔊 فويس", ["/set-up-auto-voice", "/room-voice"]),
        ("🎉 فعاليات", [
            "/giveaway", "/gend", "/mo7_win", "/wheel-panel", "/points",
            "/add-points", "/reset-points", "!bc", "!obc", "/send-broadcast-panel",
            "/broadcast-bots",
        ]),
        ("🛡️ حماية", ["/set-up-security", "/filter", "/filter add", "/filter list", "/filter toggle"]),
        ("🧰 أدوات إدارة", [
            "/backup", "/back", "/dashboard", "/dashboard-mo7", "/help", "/mo7-log",
            "/set-up-reply", "/set-up-embed", "/time-add-role",
        ]),
    ]
    blocks = []
    for title, cmds in groups:
        chips = "".join(f'<span class="cmd" title="عرض فقط">{_esc(c)}</span>' for c in cmds)
        blocks.append(f'<div class="card"><h2>{title}</h2><div class="cmd-wrap">{chips}</div></div>')
    body = f"""
    <section class="card-head-row">
      <h1>الأوامر</h1>
      <p class="muted">لإدارة الرتب والكلمات ادخل على <a href="/guilds">السيرفرات</a> ثم اختر سيرفرك</p>
    </section>
    <section class="grid-2">{''.join(blocks)}</section>
    """
    return HTMLResponse(layout("الأوامر", body, request))


@app.get("/systems", response_class=HTMLResponse)
async def systems_page(request: Request):
    redir = _require_auth(request)
    if redir:
        return redir
    systems = [
        ("🎫", "التذاكر", "فتح · استلام · تقييم · ترنسكريبت", "/ticket-setup"),
        ("🔊", "Auto Voice", "رومات مؤقتة + بانل تحكم", "/set-up-auto-voice"),
        ("🛡️", "الفلتر", "كلمات ممنوعة + منع دعوات", "/filter"),
        ("⭐", "XP والمهام", "مستويات وتوب ومهام ستاف", "/set-up-xp"),
        ("🎁", "قيف أواي", "سحوبات وجوائز", "/giveaway"),
        ("🎡", "العجلة", "نقاط ودعوات", "/wheel-panel"),
        ("📢", "برودكاست", "إرسال جماعي عبر توكنات", "/send-broadcast-panel"),
        ("📦", "باكاب", "من ديسكورد: /backup و /back", "/help"),
        ("🔐", "الحماية", "سكوريتي ومراقبة", "/set-up-security"),
        ("🤖", "Auto Role", "رتب تلقائية عند الدخول", "/autorole"),
        ("⚙️", "إدارة الأوامر", "رتب + كلمات من الداشبورد", "/guilds"),
    ]
    cards = "".join(
        f"""
        <div class="card sys-card">
          <div class="sys-ico">{ico}</div>
          <h3>{name}</h3>
          <p class="muted">{desc}</p>
          <code>{cmd}</code>
        </div>
        """
        for ico, name, desc, cmd in systems
    )
    body = f"""
    <section class="card-head-row"><h1>الأنظمة</h1></section>
    <section class="grid-3">{cards}</section>
    """
    return HTMLResponse(layout("الأنظمة", body, request))


@app.get("/health")
async def health():
    info = _bot_info()
    return {"ok": True, "bot_online": info["online"], "guilds": info["guilds"]}
