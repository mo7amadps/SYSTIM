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

from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

# يُملأ من main بعد تشغيل البوت
bot_ref = None
storage_ref = None

APP_DIR = Path(__file__).parent
DASHBOARD_SECRET = os.getenv("DASHBOARD_SECRET", "").strip()
SESSION_SECRET = os.getenv("DASHBOARD_SESSION_SECRET") or secrets.token_hex(32)

app = FastAPI(title="ROW Dashboard", docs_url=None, redoc_url=None)
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
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": ["سجن"],
        "cmd_name": "سجن",
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
    "unban": {
        "title": "✅ فك الباند",
        "desc": "إلغاء الحظر",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": ["فك-الباند"],
        "cmd_name": "فك-الباند",
    },
    "role": {
        "title": "🎭 الرتب",
        "desc": "إدارة رتب الأعضاء",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": ["رتب"],
        "cmd_name": "رتب",
    },
    "nickname": {
        "title": "✏️ النك",
        "desc": "تغيير الاسم المستعار",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": ["نك"],
        "cmd_name": "نك",
    },
    "lock": {
        "title": "🔐 قفل القناة (ق)",
        "desc": "قفل الشات",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": ["ق"],
        "cmd_name": "ق",
    },
    "unlock": {
        "title": "🔓 فتح القناة (ف)",
        "desc": "فتح الشات",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": ["ف"],
        "cmd_name": "ف",
    },
    "clear": {
        "title": "🧹 مسح الرسائل",
        "desc": "حذف رسائل",
        "roles_key": "allowed_role_ids",
        "extra_role_key": None,
        "extra_label": None,
        "default_aliases": ["مسح"],
        "cmd_name": "مسح",
    },
}


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


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    redir = _require_auth(request)
    if redir:
        return redir
    info = _bot_info()
    guilds = _guilds_data()
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
        <div class="stat"><b>{_esc(info["latency"])}</b><span>بنق</span></div>
      </div>
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
        sec = conf.get(section, {}) or {}
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
              <select name="extra_role_id">
                <option value="">— بدون تغيير —</option>
                <option value="0">إزالة</option>
                {role_options}
              </select>
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
                  <select name="add_role_id">
                    <option value="">— اختر رتبة —</option>
                    {role_options}
                  </select>
                </div>
                <div class="field">
                  <label>➖ إزالة رتبة (ID)</label>
                  <input type="text" name="remove_role_id" placeholder="الصق ID الرتبة لإزالتها" list="roles-{section}"/>
                  <datalist id="roles-{section}">
                    {''.join(f'<option value="{i}">{_esc(_role_name(guild, i))}</option>' for i in role_ids)}
                  </datalist>
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

    def row(label, value):
        return f"<div class='kv'><span>{label}</span><b>{value}</b></div>"

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
    </section>

    <section class="grid-2">
      <div class="card">
        <h2>🎫 التذاكر</h2>
        {row('أنواع معدّة', len(tickets))}
        {row('مفتوحة الآن', len(open_t))}
      </div>
      <div class="card">
        <h2>🔊 الفويس</h2>
        {row('روم الزرار', av.get('trigger_channel_id') or '—')}
        {row('رومات نشطة', len(av.get('rooms') or {}))}
      </div>
      <div class="card">
        <h2>⭐ XP</h2>
        {row('الحالة', 'مفعّل' if xp.get('enabled', True) else 'متوقف')}
      </div>
      <div class="card">
        <h2>🛡️ الفلتر</h2>
        {row('كلمات ممنوعة', len(wf.get('words') or []))}
        {row('منع دعوات', 'نعم' if wf.get('block_invites', True) else 'لا')}
      </div>
    </section>

    <section class="card-head-row" style="margin-top:28px">
      <h2>⚙️ إدارة الأوامر — رتب وكلمات</h2>
      <p class="muted">زيد أو قلّل الرتب اللي تقدر تستخدم كل أمر، وعدّل الكلمات (مثل تايم / اص / اسكت)</p>
    </section>
    <section class="grid-2">
      {''.join(manage_cards)}
    </section>

    <p class="muted center" style="margin-top:24px"><a href="/guilds">← رجوع للسيرفرات</a></p>
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
    sec = dict(conf.get(section, {}) or {})
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
        await storage_ref.update_guild(gid, section, updates)

    title = meta["title"]
    return RedirectResponse(
        f"/guild/{guild_id}?ok=تم حفظ إعدادات {title}",
        status_code=303,
    )


@app.get("/commands", response_class=HTMLResponse)
async def commands_page(request: Request):
    redir = _require_auth(request)
    if redir:
        return redir
    groups = [
        ("⚔️ إشراف", ["باند", "فك-الباند", "تايم", "ان", "تحذير", "شيل", "سجن", "انسجن", "ق", "ف", "مسح", "نك"]),
        ("🎭 رتب", ["رتب", "رول", "ترقية", "تخفيض", "صغرى", "عليا", "اونر", "مفصول", "/autorole", "/role-all"]),
        ("⭐ تفاعل", ["رانك", "توب", "$top", "اعطي-اكسبي", "اقتراح", "/suggest"]),
        ("🎫 تذاكر", ["/ticket-setup", "/ticket-panel", "/close", "/forceclose", "!close", "!forceclose", "!rename"]),
        ("🔊 فويس", ["/set-up-auto-voice", "/room-voice"]),
        ("🎉 فعاليات", ["/giveaway", "/gend", "/mo7_win", "/wheel-panel", "/points", "!bc", "!obc"]),
        ("🧰 أدوات", ["/backup", "/back", "/filter", "/dashboard", "/dashboard-mo7", "/help", "/mo7-log", "/time-add-role"]),
    ]
    blocks = []
    for title, cmds in groups:
        chips = "".join(f'<span class="cmd">{_esc(c)}</span>' for c in cmds)
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
        ("📦", "باكاب", "تصدير واستعادة إعدادات", "/backup"),
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
