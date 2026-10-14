"""لوحات إدارة التذاكر / الفلتر / الفويس / XP / أوتو رول / العجلة."""
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


def build_systems_html(guild, guild_id: str, conf: dict, role_picker, channel_picker, role_name_fn) -> str:
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
        user_label = f"UID:{uid}" if uid else "—"
        claim_label = f"UID:{claimed}" if claimed else "غير مستلم"
        ticket_rows.append(
            f'<div class="ticket-row"><div><b>{_esc(ch_label)}</b> · {_esc(str(tname))}<br/>'
            f'<span class="muted small">عضو: {_esc(user_label)} · استلام: {_esc(claim_label)}</span></div>'
            f'<form method="post" action="/guild/{guild_id}/ticket-close">'
            f'<input type="hidden" name="channel_id" value="{_esc(ch_id)}"/>'
            f'<button type="submit" class="btn primary" style="background:linear-gradient(135deg,#c45c6a,#a84858)">'
            f'إغلاق</button></form></div>'
        )
    tickets_html = "".join(ticket_rows) or '<p class="muted">لا تذاكر مفتوحة</p>'

    # Ticket types edit cards
    type_cards = []
    for num in range(1, 16):
        cfg = dict(types.get(str(num)) or {})
        name = cfg.get("name") or ""
        type_cards.append(
            f'''<div class="card manage-card">
              <h3>🎫 نوع تذكرة #{num} {_esc(name) if name else "(فاضي)"}</h3>
              <form method="post" action="/guild/{guild_id}/ticket-type" class="form manage-form">
                <input type="hidden" name="ticket_num" value="{num}"/>
                <div class="field"><label>الاسم</label>
                  <input type="text" name="name" value="{_esc(name)}" placeholder="مثلاً دعم فني"/></div>
                <div class="field"><label>الكاتيغوري</label>
                  <select name="category_id">{_cat_options(guild, cfg.get("category_id"))}</select></div>
                <div class="field"><label>رول التذكرة</label>
                  <select name="role_id">{_role_options(guild, cfg.get("role_id"))}</select></div>
                <div class="field"><label>رول الأدمن</label>
                  <select name="admin_id">{_role_options(guild, cfg.get("admin_id"))}</select></div>
                <div class="field"><label>لوق التذاكر</label>
                  <select name="log_channel_id">{_text_channel_options(guild, cfg.get("log_channel_id"))}</select></div>
                <div class="field"><label>روم التقييم</label>
                  <select name="tqeem_room_id">{_text_channel_options(guild, cfg.get("tqeem_room_id"))}</select></div>
                <div class="field"><label>رسالة الترحيب</label>
                  <input type="text" name="welcome_msg" value="{_esc(cfg.get("welcome_msg") or "")}"/></div>
                <button type="submit" class="btn primary">حفظ النوع #{num}</button>
              </form>
            </div>'''
        )
    # only show configured + first empty slot to avoid huge page - show all that have name or first 5 empty
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

    # Auto role
    ar = conf.get("auto_role") or {}
    ar_roles = list(ar.get("role_ids") or [])
    ar_roles_html = "".join(
        f'<span class="chip role-chip">{_esc(role_name_fn(guild, rid))} '
        f'<form method="post" action="/guild/{guild_id}/autorole-remove" style="display:inline">'
        f'<input type="hidden" name="role_id" value="{rid}"/>'
        f'<button type="submit" class="btn-mini">x</button></form></span>'
        for rid in ar_roles
    ) or '<span class="muted">لا رتب</span>'

    # Wheel points top
    wheel = conf.get("wheel") or {}
    points = wheel.get("points") or {}
    sorted_pts = sorted(points.items(), key=lambda x: int(x[1] or 0), reverse=True)[:30]
    pts_rows = []
    for uid, pts in sorted_pts:
        name = str(uid)
        if guild:
            m = guild.get_member(int(uid)) if str(uid).isdigit() else None
            if m:
                name = str(m)
        pts_rows.append(
            f'<div class="ticket-row"><div><b>{_esc(name)}</b><br/>'
            f'<span class="muted small">ID: {_esc(uid)} · نقاط: <b>{_esc(pts)}</b></span></div>'
            f'<form method="post" action="/guild/{guild_id}/wheel-points" class="form" style="display:flex;gap:8px;align-items:center">'
            f'<input type="hidden" name="user_id" value="{_esc(uid)}"/>'
            f'<input type="text" name="points" value="{_esc(pts)}" style="width:80px;padding:8px;border-radius:10px;'
            f'border:1px solid var(--stroke);background:#121826;color:var(--text)"/>'
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

    return f'''
    <section class="card-head-row" style="margin-top:28px">
      <h2>🧩 الأنظمة</h2>
      <p class="muted">تذاكر · فلتر · فويس · XP · أوتو رول · عجلة</p>
    </section>
    <section class="grid-2">
      <div class="card manage-card">
        <h3>🛡️ فلتر الكلمات</h3>
        <p class="muted">الحالة: <b>{"مفعّل" if wf.get("enabled", True) else "متوقف"}</b>
           · منع دعوات: <b>{"نعم" if wf.get("block_invites", True) else "لا"}</b>
           · كلمات: <b>{len(words)}</b></p>
        <div class="cmd-wrap" style="margin:12px 0;pointer-events:auto">{words_html}</div>
        <form method="post" action="/guild/{guild_id}/filter-add" class="form manage-form">
          <div class="field"><label>إضافة كلمة</label>
            <input type="text" name="word" placeholder="اكتب الكلمة..." required/></div>
          <button type="submit" class="btn primary">إضافة</button>
        </form>
        <form method="post" action="/guild/{guild_id}/filter-toggle" class="form manage-form" style="margin-top:10px">
          <div class="toggle-row">
            <label><input type="checkbox" name="enabled" value="1" {"checked" if wf.get("enabled", True) else ""}/> تفعيل الفلتر</label>
            <label><input type="checkbox" name="block_invites" value="1" {"checked" if wf.get("block_invites", True) else ""}/> منع دعوات ديسكورد</label>
          </div>
          <button type="submit" class="btn primary">حفظ إعدادات الفلتر</button>
        </form>
      </div>

      <div class="card manage-card">
        <h3>🔊 Auto Voice</h3>
        <p class="muted">رومات نشطة: <b>{len(av.get("rooms") or {})}</b></p>
        <form method="post" action="/guild/{guild_id}/auto-voice" class="form manage-form">
          <div class="field"><label>روم الزرار</label>
            <select name="trigger_channel_id">{''.join(voice_opts)}</select></div>
          <div class="field"><label>الكاتيغوري</label>
            <select name="category_id">{''.join(cat_opts)}</select></div>
          <div class="field"><label>قالب الاسم (استخدم {{user}})</label>
            <input type="text" name="name_template" value="{_esc(template)}"/></div>
          <div class="field"><label>حد الأعضاء (0 = بدون)</label>
            <input type="text" name="user_limit" value="{_esc(limit)}"/></div>
          <button type="submit" class="btn primary">حفظ الفويس</button>
        </form>
      </div>

      <div class="card manage-card">
        <h3>⭐ نظام XP</h3>
        <form method="post" action="/guild/{guild_id}/xp-settings" class="form manage-form">
          <div class="toggle-row">
            <label><input type="checkbox" name="enabled" value="1" {"checked" if xp_enabled else ""}/> تفعيل XP</label>
          </div>
          <div class="field"><label>أقل XP / رسالة</label>
            <input type="text" name="xp_min" value="{_esc(xp.get("xp_min", 5))}"/></div>
          <div class="field"><label>أعلى XP / رسالة</label>
            <input type="text" name="xp_max" value="{_esc(xp.get("xp_max", 15))}"/></div>
          <div class="field"><label>كولداون (ثواني)</label>
            <input type="text" name="cooldown_seconds" value="{_esc(xp.get("cooldown_seconds", 30))}"/></div>
          <div class="field"><label>روم إعلان اللفل أب</label>
            {channel_picker(guild, "levelup_channel_id", selected_id=xp.get("levelup_channel_id"))}</div>
          <button type="submit" class="btn primary">حفظ XP</button>
        </form>
        <hr style="border-color:var(--stroke);margin:16px 0"/>
        <h4>مكافآت الرتب حسب المستوى</h4>
        {rewards_html}
        <form method="post" action="/guild/{guild_id}/xp-reward-add" class="form manage-form" style="margin-top:10px">
          <div class="field"><label>المستوى</label>
            <input type="text" name="level" placeholder="مثلاً 5" required/></div>
          <div class="field"><label>الرتبة</label>
            {role_picker(guild, "role_id", multi=False)}</div>
          <button type="submit" class="btn primary">إضافة مكافأة</button>
        </form>
      </div>

      <div class="card manage-card">
        <h3>🤖 Auto Role</h3>
        <p class="muted">رتب تُعطى تلقائياً عند دخول عضو</p>
        <div class="cmd-wrap" style="margin:10px 0;pointer-events:auto">{ar_roles_html}</div>
        <form method="post" action="/guild/{guild_id}/autorole-save" class="form manage-form">
          <div class="toggle-row">
            <label><input type="checkbox" name="enabled" value="1" {"checked" if ar.get("enabled") else ""}/> تفعيل Auto Role</label>
          </div>
          <div class="field"><label>إضافة رتبة</label>
            {role_picker(guild, "add_role_id", multi=False)}</div>
          <button type="submit" class="btn primary">حفظ أوتو رول</button>
        </form>
      </div>

      <div class="card manage-card" style="grid-column:1/-1">
        <h3>🎫 التذاكر المفتوحة <span class="badge">{len(open_tickets)}</span></h3>
        <p class="muted">إغلاق من هنا = حذف الروم وإزالته من القائمة (force close)</p>
        {tickets_html}
      </div>
    </section>

    <section class="card-head-row" style="margin-top:28px">
      <h2>🎫 أنواع التذاكر</h2>
      <p class="muted">تعديل الاسم · الكاتيغوري · الرول · اللوق · التقييم</p>
    </section>
    <section class="grid-2">
      {types_html}
    </section>

    <section class="card-head-row" style="margin-top:28px">
      <h2>🎡 نقاط العجلة</h2>
      <p class="muted">أعلى 30 · عدّل الرقم واضغط حفظ · أو أضف يوزر بالـ ID</p>
    </section>
    <section class="card manage-card">
      {pts_html}
      <hr style="border-color:var(--stroke);margin:16px 0"/>
      <form method="post" action="/guild/{guild_id}/wheel-points" class="form manage-form">
        <div class="field"><label>User ID</label>
          <input type="text" name="user_id" placeholder="Discord user id" required/></div>
        <div class="field"><label>النقاط</label>
          <input type="text" name="points" value="0" required/></div>
        <button type="submit" class="btn primary">تعيين نقاط</button>
      </form>
      <form method="post" action="/guild/{guild_id}/wheel-reset-all" class="form manage-form" style="margin-top:12px"
            onsubmit="return confirm('تصفير كل النقاط؟');">
        <button type="submit" class="btn primary" style="background:linear-gradient(135deg,#c45c6a,#a84858)">تصفير كل النقاط</button>
      </form>
    </section>
    '''
