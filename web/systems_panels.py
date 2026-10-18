"""لوحات الأنظمة — يمكن طلب قسم واحد عبر only=."""
from __future__ import annotations

import html as _html


def _esc(v) -> str:
    return _html.escape(str(v if v is not None else ""))


def _cat_options(guild, selected_id=None) -> str:
    opts = ['<option value="0">— بدون —</option>']
    if not guild:
        return "".join(opts)
    for cat in sorted(guild.categories, key=lambda c: c.position):
        sel = " selected" if selected_id and int(selected_id) == cat.id else ""
        opts.append(f'<option value="{cat.id}"{sel}>📁 {_esc(cat.name)}</option>')
    return "".join(opts)


def _text_channel_options(guild, selected_id=None) -> str:
    opts = ['<option value="0">— بدون —</option>']
    if not guild:
        return "".join(opts)
    for c in sorted(guild.text_channels, key=lambda x: ((x.category.position if x.category else -1), x.position)):
        sel = " selected" if selected_id and int(selected_id) == c.id else ""
        cat = c.category.name if c.category else ""
        opts.append(f'<option value="{c.id}"{sel}>#{_esc(c.name)} {_esc(cat)}</option>')
    return "".join(opts)


def _role_options(guild, selected_id=None) -> str:
    opts = ['<option value="0">— بدون —</option>']
    if not guild:
        return "".join(opts)
    for r in sorted(guild.roles, key=lambda x: x.position, reverse=True):
        if r.is_default():
            continue
        sel = " selected" if selected_id and int(selected_id) == r.id else ""
        opts.append(f'<option value="{r.id}"{sel}>{_esc(r.name)}</option>')
    return "".join(opts)


def build_systems_html(guild, guild_id: str, conf: dict, role_picker, channel_picker, role_name_fn, only: str | None = None) -> str:
    wf = conf.get("word_filter") or {}
    words = list(wf.get("words") or [])
    words_bits = []
    for w in words[:100]:
        words_bits.append(
            f'<span class="chip word-chip">{_esc(w)}'
            f'<form method="post" action="/guild/{guild_id}/filter-remove" style="display:inline">'
            f'<input type="hidden" name="word" value="{_esc(w)}"/>'
            f'<button type="submit" title="حذف">x</button></form></span>'
        )
    words_html = "".join(words_bits) or '<span class="muted">لا كلمات بعد</span>'

    av = conf.get("auto_voice") or {}
    xp = conf.get("xp") or {}
    rewards = xp.get("role_rewards") or {}
    rewards_bits = []
    for lv, rid in sorted(rewards.items(), key=lambda x: int(x[0]) if str(x[0]).isdigit() else 0):
        rewards_bits.append(
            f'<div class="kv"><span>مستوى {_esc(lv)}</span><b>{_esc(role_name_fn(guild, rid))} '
            f'<form method="post" action="/guild/{guild_id}/xp-reward-remove" style="display:inline">'
            f'<input type="hidden" name="level" value="{_esc(lv)}"/>'
            f'<button type="submit" class="btn-mini">حذف</button></form></b></div>'
        )
    rewards_html = "".join(rewards_bits) or '<p class="muted">لا مكافآت رتب</p>'

    open_tickets = (conf.get("tickets") or {}).get("open") or {}
    types = (conf.get("tickets") or {}).get("types") or {}
    ticket_rows = []
    for ch_id, tk in list(open_tickets.items())[:50]:
        tnum = tk.get("ticket_num")
        tname = (types.get(str(tnum)) or {}).get("name") or f"نوع {tnum}"
        uid = tk.get("user_id")
        claimed = tk.get("claimed_by")
        ch_obj = guild.get_channel(int(ch_id)) if guild else None
        ch_label = f"#{ch_obj.name}" if ch_obj else f"ID:{ch_id}"
        ticket_rows.append(
            f'<div class="ticket-row"><div><b>{_esc(ch_label)}</b> · {_esc(str(tname))}<br/>'
            f'<span class="muted small">عضو: {_esc(uid)} · استلام: {_esc(claimed or "—")}</span></div>'
            f'<form method="post" action="/guild/{guild_id}/ticket-close">'
            f'<input type="hidden" name="channel_id" value="{_esc(ch_id)}"/>'
            f'<button type="submit" class="btn primary" style="background:linear-gradient(135deg,#c45c6a,#a84858)">إغلاق</button></form></div>'
        )
    tickets_html = "".join(ticket_rows) or '<p class="muted">لا تذاكر مفتوحة</p>'

    type_cards = []
    for num in range(1, 16):
        cfg = dict(types.get(str(num)) or {})
        name = cfg.get("name") or ""
        type_cards.append(
            f'<div class="card manage-card"><h3>نوع تذكرة #{num} {_esc(name) if name else "(فاضي)"}</h3>'
            f'<form method="post" action="/guild/{guild_id}/ticket-type" class="form manage-form">'
            f'<input type="hidden" name="ticket_num" value="{num}"/>'
            f'<div class="field"><label>الاسم</label><input type="text" name="name" value="{_esc(name)}" autocomplete="off"/></div>'
            f'<div class="field"><label>الكاتيغوري</label><select name="category_id">{_cat_options(guild, cfg.get("category_id"))}</select></div>'
            f'<div class="field"><label>رول التذكرة</label><select name="role_id">{_role_options(guild, cfg.get("role_id"))}</select></div>'
            f'<div class="field"><label>رول الأدمن</label><select name="admin_id">{_role_options(guild, cfg.get("admin_id"))}</select></div>'
            f'<div class="field"><label>لوق التذاكر</label><select name="log_channel_id">{_text_channel_options(guild, cfg.get("log_channel_id"))}</select></div>'
            f'<div class="field"><label>روم التقييم</label><select name="tqeem_room_id">{_text_channel_options(guild, cfg.get("tqeem_room_id"))}</select></div>'
            f'<div class="field"><label>رسالة الترحيب</label><input type="text" name="welcome_msg" value="{_esc(cfg.get("welcome_msg") or "")}" autocomplete="off"/></div>'
            f'<button type="submit" class="btn primary">حفظ النوع #{num}</button></form></div>'
        )
    shown = []
    empty_shown = 0
    for i, card in enumerate(type_cards, 1):
        cfg = types.get(str(i)) or {}
        if cfg.get("name") or cfg.get("category_id") or cfg.get("role_id"):
            shown.append(card)
        elif empty_shown < 3:
            shown.append(card)
            empty_shown += 1
    types_html = "".join(shown) or "".join(type_cards[:3])

    ar = conf.get("auto_role") or {}
    ar_roles = list(ar.get("role_ids") or [])
    ar_roles_html = "".join(
        f'<span class="chip role-chip">{_esc(role_name_fn(guild, rid))} '
        f'<form method="post" action="/guild/{guild_id}/autorole-remove" style="display:inline">'
        f'<input type="hidden" name="role_id" value="{rid}"/>'
        f'<button type="submit" class="btn-mini">x</button></form></span>'
        for rid in ar_roles
    ) or '<span class="muted">لا رتب</span>'

    wheel = conf.get("wheel") or {}
    points = wheel.get("points") or {}
    sorted_pts = sorted(points.items(), key=lambda x: int(x[1] or 0), reverse=True)[:30]
    pts_rows = []
    for uid, pts in sorted_pts:
        name = str(uid)
        if guild and str(uid).isdigit():
            m = guild.get_member(int(uid))
            if m:
                name = str(m)
        pts_rows.append(
            f'<div class="ticket-row"><div><b>{_esc(name)}</b><br/>'
            f'<span class="muted small">ID: {_esc(uid)} · نقاط: <b>{_esc(pts)}</b></span></div>'
            f'<form method="post" action="/guild/{guild_id}/wheel-points" style="display:flex;gap:8px;align-items:center">'
            f'<input type="hidden" name="user_id" value="{_esc(uid)}"/>'
            f'<input type="text" name="points" value="{_esc(pts)}" style="width:80px;padding:8px;border-radius:10px;'
            f'border:1px solid var(--stroke);background:#121826;color:var(--text)" autocomplete="off"/>'
            f'<button type="submit" class="btn primary">حفظ</button></form></div>'
        )
    pts_html = "".join(pts_rows) or '<p class="muted">لا نقاط مسجّلة بعد</p>'

    voice_opts = ['<option value="0">— بدون —</option>']
    cat_opts = ['<option value="0">— بدون —</option>']
    if guild:
        for vc in sorted(guild.voice_channels, key=lambda c: c.position):
            sel = " selected" if av.get("trigger_channel_id") == vc.id else ""
            voice_opts.append(f'<option value="{vc.id}"{sel}>🔊 {_esc(vc.name)}</option>')
        for cat in sorted(guild.categories, key=lambda c: c.position):
            sel = " selected" if av.get("category_id") == cat.id else ""
            cat_opts.append(f'<option value="{cat.id}"{sel}>📁 {_esc(cat.name)}</option>')

    xp_enabled = xp.get("enabled", True)
    template = av.get("name_template") or "🔊 روم {user}"
    limit = av.get("user_limit") if av.get("user_limit") is not None else 0

    sections = {}

    sections["filter"] = (
        f'<section class="card-head-row"><h2>فلتر الكلمات</h2></section>'
        f'<section class="grid-2"><div class="card manage-card">'
        f'<h3>فلتر الكلمات</h3>'
        f'<p class="muted">الحالة: <b>{"مفعّل" if wf.get("enabled", True) else "متوقف"}</b>'
        f' · منع دعوات: <b>{"نعم" if wf.get("block_invites", True) else "لا"}</b>'
        f' · كلمات: <b>{len(words)}</b></p>'
        f'<div class="cmd-wrap" style="margin:12px 0;pointer-events:auto">{words_html}</div>'
        f'<form method="post" action="/guild/{guild_id}/filter-add" class="form manage-form">'
        f'<div class="field"><label>إضافة كلمة</label>'
        f'<input type="text" name="word" placeholder="اكتب هنا فقط..." required autocomplete="off"/></div>'
        f'<button type="submit" class="btn primary">إضافة</button></form>'
        f'<form method="post" action="/guild/{guild_id}/filter-toggle" class="form manage-form" style="margin-top:10px">'
        f'<div class="toggle-row">'
        f'<label><input type="checkbox" name="enabled" value="1" {"checked" if wf.get("enabled", True) else ""}/> تفعيل الفلتر</label>'
        f'<label><input type="checkbox" name="block_invites" value="1" {"checked" if wf.get("block_invites", True) else ""}/> منع دعوات ديسكورد</label>'
        f'</div><button type="submit" class="btn primary">حفظ إعدادات الفلتر</button></form>'
        f'</div></section>'
    )

    sections["voice"] = (
        f'<section class="card-head-row"><h2>Auto Voice</h2></section>'
        f'<section class="grid-2"><div class="card manage-card">'
        f'<h3>Auto Voice</h3><p class="muted">رومات نشطة: <b>{len(av.get("rooms") or {})}</b></p>'
        f'<form method="post" action="/guild/{guild_id}/auto-voice" class="form manage-form">'
        f'<div class="field"><label>روم الزرار</label><select name="trigger_channel_id">{"".join(voice_opts)}</select></div>'
        f'<div class="field"><label>الكاتيغوري</label><select name="category_id">{"".join(cat_opts)}</select></div>'
        f'<div class="field"><label>قالب الاسم</label>'
        f'<input type="text" name="name_template" value="{_esc(template)}" placeholder="روم {{user}}" autocomplete="off"/></div>'
        f'<div class="field"><label>حد الأعضاء (0 = بدون)</label>'
        f'<input type="text" name="user_limit" value="{_esc(limit)}" autocomplete="off"/></div>'
        f'<button type="submit" class="btn primary">حفظ الفويس</button></form>'
        f'</div></section>'
    )

    sections["xp"] = (
        f'<section class="card-head-row"><h2>نظام XP</h2></section>'
        f'<section class="grid-2"><div class="card manage-card"><h3>نظام XP</h3>'
        f'<form method="post" action="/guild/{guild_id}/xp-settings" class="form manage-form">'
        f'<div class="toggle-row"><label><input type="checkbox" name="enabled" value="1" {"checked" if xp_enabled else ""}/> تفعيل XP</label></div>'
        f'<div class="field"><label>أقل XP</label><input type="text" name="xp_min" value="{_esc(xp.get("xp_min", 5))}" autocomplete="off"/></div>'
        f'<div class="field"><label>أعلى XP</label><input type="text" name="xp_max" value="{_esc(xp.get("xp_max", 15))}" autocomplete="off"/></div>'
        f'<div class="field"><label>كولداون</label><input type="text" name="cooldown_seconds" value="{_esc(xp.get("cooldown_seconds", 30))}" autocomplete="off"/></div>'
        f'<div class="field"><label>روم اللفل أب</label>{channel_picker(guild, "levelup_channel_id", selected_id=xp.get("levelup_channel_id"))}</div>'
        f'<button type="submit" class="btn primary">حفظ XP</button></form>'
        f'<hr style="border-color:var(--stroke);margin:16px 0"/><h4>مكافآت الرتب</h4>{rewards_html}'
        f'<form method="post" action="/guild/{guild_id}/xp-reward-add" class="form manage-form" style="margin-top:10px">'
        f'<div class="field"><label>المستوى</label><input type="text" name="level" required autocomplete="off"/></div>'
        f'<div class="field"><label>الرتبة</label>{role_picker(guild, "role_id", multi=False)}</div>'
        f'<button type="submit" class="btn primary">إضافة مكافأة</button></form></div></section>'
    )

    sections["autorole"] = (
        f'<section class="card-head-row"><h2>Auto Role</h2></section>'
        f'<section class="grid-2"><div class="card manage-card"><h3>Auto Role</h3>'
        f'<p class="muted">رتب عند دخول عضو</p>'
        f'<div class="cmd-wrap" style="margin:10px 0;pointer-events:auto">{ar_roles_html}</div>'
        f'<form method="post" action="/guild/{guild_id}/autorole-save" class="form manage-form">'
        f'<div class="toggle-row"><label><input type="checkbox" name="enabled" value="1" {"checked" if ar.get("enabled") else ""}/> تفعيل</label></div>'
        f'<div class="field"><label>إضافة رتبة</label>{role_picker(guild, "add_role_id", multi=False)}</div>'
        f'<button type="submit" class="btn primary">حفظ</button></form></div></section>'
    )

    sections["tickets"] = (
        f'<section class="card-head-row"><h2>التذاكر المفتوحة</h2></section>'
        f'<section class="card manage-card"><h3>مفتوحة <span class="badge">{len(open_tickets)}</span></h3>'
        f'<p class="muted">إغلاق = force close</p>{tickets_html}</section>'
    )

    sections["types"] = (
        f'<section class="card-head-row"><h2>أنواع التذاكر</h2></section>'
        f'<section class="grid-2">{types_html}</section>'
    )

    sections["wheel"] = (
        f'<section class="card-head-row"><h2>نقاط العجلة</h2></section>'
        f'<section class="card manage-card">{pts_html}'
        f'<hr style="border-color:var(--stroke);margin:16px 0"/>'
        f'<form method="post" action="/guild/{guild_id}/wheel-points" class="form manage-form">'
        f'<div class="field"><label>User ID</label><input type="text" name="user_id" required autocomplete="off"/></div>'
        f'<div class="field"><label>النقاط</label><input type="text" name="points" value="0" required autocomplete="off"/></div>'
        f'<button type="submit" class="btn primary">تعيين</button></form>'
        f'<form method="post" action="/guild/{guild_id}/wheel-reset-all" class="form manage-form" style="margin-top:12px" '
        f'onsubmit="return confirm(\'تصفير الكل؟\');">'
        f'<button type="submit" class="btn primary" style="background:linear-gradient(135deg,#c45c6a,#a84858)">تصفير الكل</button></form></section>'
    )

    if only and only in sections:
        return sections[only]
    return "".join(sections[k] for k in ("filter", "voice", "xp", "autorole", "tickets", "types", "wheel"))
