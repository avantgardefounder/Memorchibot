"""Объект на стройке: davomat (Keldim/Ketdim), фото-отчёты, ежедневный отчёт клиенту (ТЗ 3.4, 3.9, 4, 6)."""
import datetime as dt
import math
import os
import time
from zoneinfo import ZoneInfo

import db
import ledger
import roles
from translit import to_cyr

TZ = ZoneInfo("Asia/Tashkent")
DEFAULT_RADIUS = float(os.getenv("GEO_RADIUS_M", "200"))  # радиус объекта, м

R = {
    "ru": {
        "title": "📊 Ежедневный отчёт — {obj}, {date}",
        "att": "👷 Davomat: отметились {n} из {total}", "att_none": "👷 Davomat: сегодня никто не отметился",
        "no_out": "уход не отмечен", "missing": "⚠️ Не пришли: {names}", "far": "⚠️ Отметка вне объекта: {items}",
        "nogeo": "ℹ️ Локация объекта не задана — радиус не проверяется",
        "done": "🛠 Сделано:", "foreman_photo": "Фото-отчёт", "nothing_done": "🛠 Описаний работ нет",
        "exp": "💰 Расходы за день: {sum}", "exp_none": "💰 Расходов за день нет",
        "inc": "💵 Поступило от клиента: {sum}", "balance": "Остаток средств клиента: {sum}",
        "overspend": "⚠️ Перерасход: {sum}", "photos": "📸 Фото: {n}", "photos_none": "📸 Фото-отчёта сегодня нет",
        "h": "{h} ч {m} мин", "receipt": "чек 📎", "more": "…и ещё {n}",
        "att_title": "👷 Davomat — {obj}, {date}",
    },
    "uz": {
        "title": "📊 Kunlik hisobot — {obj}, {date}",
        "att": "👷 Davomat: {total} tadan {n} kishi belgilandi", "att_none": "👷 Davomat: bugun hech kim belgilanmadi",
        "no_out": "ketish belgilanmagan", "missing": "⚠️ Kelmadi: {names}", "far": "⚠️ Obyektdan tashqarida belgilangan: {items}",
        "nogeo": "ℹ️ Obyekt lokatsiyasi kiritilmagan — radius tekshirilmaydi",
        "done": "🛠 Bajarilgan ishlar:", "foreman_photo": "Foto-hisobot", "nothing_done": "🛠 Ish tavsifi yo'q",
        "exp": "💰 Bugungi xarajatlar: {sum}", "exp_none": "💰 Bugun xarajat yo'q",
        "inc": "💵 Mijozdan tushum: {sum}", "balance": "Mijoz mablag'lari qoldig'i: {sum}",
        "overspend": "⚠️ Ortiqcha sarf: {sum}", "photos": "📸 Rasmlar: {n}", "photos_none": "📸 Bugun foto-hisobot yo'q",
        "h": "{h} soat {m} daq", "receipt": "chek 📎", "more": "…yana {n} ta",
        "att_title": "👷 Davomat — {obj}, {date}",
    },
    "en": {
        "title": "📊 Daily report — {obj}, {date}",
        "att": "👷 Attendance: {n} of {total} checked in", "att_none": "👷 Attendance: nobody checked in today",
        "no_out": "check-out missing", "missing": "⚠️ Absent: {names}", "far": "⚠️ Checked in outside the site: {items}",
        "nogeo": "ℹ️ Site location not set — radius not checked",
        "done": "🛠 Work done:", "foreman_photo": "Photo report", "nothing_done": "🛠 No work descriptions",
        "exp": "💰 Expenses today: {sum}", "exp_none": "💰 No expenses today",
        "inc": "💵 Received from client: {sum}", "balance": "Client funds balance: {sum}",
        "overspend": "⚠️ Overspend: {sum}", "photos": "📸 Photos: {n}", "photos_none": "📸 No photo report today",
        "h": "{h} h {m} min", "receipt": "receipt 📎", "more": "…and {n} more",
        "att_title": "👷 Attendance — {obj}, {date}",
    },
}
R["uzc"] = to_cyr(R["uz"])
CUR = {"UZS": {"ru": "сум", "uz": "so'm", "uzc": "сўм", "en": "UZS"}, "USD": {"ru": "$", "uz": "$", "uzc": "$", "en": "USD"}}


def today():
    return dt.datetime.now(TZ).date().isoformat()


def _hm(ts):
    return dt.datetime.fromtimestamp(ts, TZ).strftime("%H:%M")


def _dur(sec, lang):
    m = int(sec // 60)
    return R[lang]["h"].format(h=m // 60, m=m % 60)


def money(x, cur, lang):
    return f"{ledger._money(x, cur)} {CUR[cur][lang]}"


def distance_m(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _name(uid):
    r = db._con.execute("SELECT name FROM users WHERE id=?", (uid,)).fetchone()
    return (r[0] if r else "") or str(uid)


def _label(object_id, uid):
    r = db._con.execute("SELECT label FROM participants WHERE object_id=? AND user_id=? AND role='worker' AND active=1",
                        (object_id, uid)).fetchone()
    return (r[0] if r else "") or ""


def person(object_id, uid):
    lab = _label(object_id, uid)
    return f"{_name(uid)} ({lab})" if lab else _name(uid)


# ---------- выбор объекта по локации ----------
def pick_object(uid, lat, lon):
    """Объект для отметки: единственный, иначе ближайший с заданной локацией. None — спросить."""
    objs = [ledger.find_object(oid) for oid, r, _l in roles.roles_of(uid) if r == "worker"]
    if len(objs) == 1:
        return objs[0]
    located = [(distance_m(lat, lon, o["lat"], o["lon"]), o) for o in objs if o["lat"] is not None]
    if located:
        d, o = min(located, key=lambda x: x[0])
        if d <= (o["radius"] or DEFAULT_RADIUS) * 3:
            return o
    return None


# ---------- davomat ----------
def open_checkin(uid):
    r = db._con.execute("SELECT id, object_id, date, in_ts FROM attendance WHERE user_id=? AND out_ts IS NULL "
                        "ORDER BY id DESC LIMIT 1", (uid,)).fetchone()
    return {"id": r[0], "object_id": r[1], "date": r[2], "in_ts": r[3]} if r else None


def _geo_check(o, lat, lon):
    if o["lat"] is None or o["lon"] is None:
        return None, ["nogeo"]
    d = distance_m(lat, lon, o["lat"], o["lon"])
    return d, (["far"] if d > (o["radius"] or DEFAULT_RADIUS) else [])


def check_in(object_id, uid, lat, lon, selfie_file_id=None):
    roles.require(uid, object_id, "attendance_mark")
    op = open_checkin(uid)
    if op and op["date"] == today():
        raise ValueError("already_in")
    if op:  # вчера забыл «Ketdim» — закрываем без времени ухода
        db._con.execute("UPDATE attendance SET flags=flags||',no_out', out_ts=0 WHERE id=?", (op["id"],))
    o = ledger.find_object(object_id)
    d, flags = _geo_check(o, lat, lon)
    cur = db._con.execute(
        "INSERT INTO attendance(object_id,user_id,date,in_ts,in_lat,in_lon,in_dist,in_selfie,flags) VALUES(?,?,?,?,?,?,?,?,?)",
        (object_id, uid, today(), time.time(), lat, lon, d, selfie_file_id, ",".join(flags)))
    db._con.commit()
    if selfie_file_id:
        add_photo(object_id, uid, selfie_file_id, "selfie", "", cur.lastrowid)
    db.audit(uid, _name(uid), object_id, "check_in", f"dist={d} flags={flags}")
    return {"id": cur.lastrowid, "object": o["name"], "object_id": object_id, "dist": d, "flags": flags}


def set_selfie(att_id, file_id):
    r = db._con.execute("SELECT object_id, user_id FROM attendance WHERE id=?", (att_id,)).fetchone()
    db._con.execute("UPDATE attendance SET in_selfie=? WHERE id=?", (file_id, att_id))
    db._con.commit()
    add_photo(r[0], r[1], file_id, "selfie", "", att_id)


def check_out(att_id, lat, lon):
    r = db._con.execute("SELECT object_id, user_id, in_ts, flags FROM attendance WHERE id=?", (att_id,)).fetchone()
    object_id, uid, in_ts, flags = r
    o = ledger.find_object(object_id)
    d, f2 = _geo_check(o, lat, lon)
    flags = ",".join(x for x in (flags or "").split(",") + [("far_out" if "far" in f2 else "")] if x)
    now = time.time()
    db._con.execute("UPDATE attendance SET out_ts=?, out_lat=?, out_lon=?, out_dist=?, flags=? WHERE id=?",
                    (now, lat, lon, d, flags, att_id))
    db._con.commit()
    db.audit(uid, _name(uid), object_id, "check_out", f"dist={d}")
    return {"object": o["name"], "object_id": object_id, "seconds": now - in_ts, "dist": d, "far": "far" in f2}


def set_work(att_id, text, photo_ids=()):
    r = db._con.execute("SELECT object_id, user_id FROM attendance WHERE id=?", (att_id,)).fetchone()
    db._con.execute("UPDATE attendance SET work_text=? WHERE id=?", (text or "", att_id))
    db._con.commit()
    for fid in photo_ids:
        add_photo(r[0], r[1], fid, "work", text or "", att_id)


# ---------- фото ----------
def add_photo(object_id, uid, file_id, kind="daily", caption="", ref_id=None):
    db._con.execute("INSERT INTO photos(object_id,user_id,date,ts,file_id,kind,caption,ref_id) VALUES(?,?,?,?,?,?,?,?)",
                    (object_id, uid, today(), time.time(), file_id, kind, caption or "", ref_id))
    db._con.commit()


def photos_on(object_id, date, kinds=("daily", "work")):
    marks = ",".join("?" * len(kinds))
    return [{"file_id": f, "kind": k, "caption": c, "user_id": u} for f, k, c, u in db._con.execute(
        f"SELECT file_id, kind, caption, user_id FROM photos WHERE object_id=? AND date=? AND kind IN ({marks}) ORDER BY id",
        (object_id, date, *kinds))]


def photo_dates(object_id, limit=10):
    return db._con.execute("SELECT date, COUNT(*) FROM photos WHERE object_id=? AND kind IN ('daily','work') "
                           "GROUP BY date ORDER BY date DESC LIMIT ?", (object_id, limit)).fetchall()


def daily_photo_done(object_id, date):
    return bool(db._con.execute("SELECT 1 FROM photos WHERE object_id=? AND date=? AND kind='daily' LIMIT 1",
                                (object_id, date)).fetchone())


# ---------- отчёты ----------
def attendance_day(object_id, date):
    rows = db._con.execute("SELECT user_id, in_ts, out_ts, in_dist, flags, work_text FROM attendance "
                           "WHERE object_id=? AND date=? ORDER BY in_ts", (object_id, date)).fetchall()
    came = []
    for uid, in_ts, out_ts, dist, flags, work in rows:
        came.append({"user_id": uid, "name": person(object_id, uid), "in": _hm(in_ts),
                     "out": _hm(out_ts) if out_ts else None, "seconds": (out_ts - in_ts) if out_ts else None,
                     "dist": round(dist) if dist is not None else None, "flags": [f for f in (flags or "").split(",") if f],
                     "work": work or ""})
    workers = roles.users_with_role(object_id, "worker")
    came_ids = {c["user_id"] for c in came}
    missing = [person(object_id, u) for u in workers if u not in came_ids]
    return {"came": came, "missing": missing, "total": len(set(workers) | came_ids)}


def attendance_text(object_id, date, lang):
    t = R.get(lang, R["ru"])
    o = ledger.find_object(object_id)
    a = attendance_day(object_id, date)
    lines = [t["att_title"].format(obj=o["name"], date=_d(date))]
    lines += _att_lines(a, t, lang, o)
    return "\n".join(lines)


def _d(date):
    return dt.date.fromisoformat(date).strftime("%d.%m.%Y")


def _att_lines(a, t, lang, o):
    lines = []
    if a["came"]:
        lines.append(t["att"].format(n=len(a["came"]), total=a["total"]))
        for c in a["came"]:
            span = f"{c['in']}–{c['out']}, {_dur(c['seconds'], lang)}" if c["out"] else f"{c['in']}–… ({t['no_out']})"
            lines.append(f"• {c['name']} — {span}")
    else:
        lines.append(t["att_none"])
    if a["missing"]:
        lines.append(t["missing"].format(names=", ".join(a["missing"])))
    far = [f"{c['name']} ({c['dist']} m)" for c in a["came"] if "far" in c["flags"] or "far_out" in c["flags"]]
    if far:
        lines.append(t["far"].format(items=", ".join(far)))
    if a["came"] and o["lat"] is None:
        lines.append(t["nogeo"])
    return lines


def daily_report(object_id, date=None, lang="ru", with_finance=True, max_photos=10):
    """Текст ежедневного отчёта + file_id фото (не больше max_photos)."""
    date = date or today()
    t = R.get(lang, R["ru"])
    o = ledger.find_object(object_id)
    a = attendance_day(object_id, date)
    lines = [t["title"].format(obj=o["name"], date=_d(date)), ""]
    lines += _att_lines(a, t, lang, o)

    lines.append("")
    work = [f"• {c['name']}: {c['work']}" for c in a["came"] if c["work"]]
    daily = photos_on(object_id, date, ("daily",))
    for cap in dict.fromkeys(p["caption"] for p in daily if p["caption"]):
        work.append(f"• {t['foreman_photo']}: {cap}")
    if work:
        lines.append(t["done"])
        lines += work
    else:
        lines.append(t["nothing_done"])

    receipt_ids = []
    if with_finance:
        lines.append("")
        cur = o["currency"]
        tx = ledger._tx(object_id, date, date)
        exp = [x for x in tx if x["type"] == "expense"]
        inc = [x for x in tx if x["type"] == "income"]
        if exp:
            lines.append(t["exp"].format(sum=money(sum(x["amount"] for x in exp), cur, lang)))
            for x in exp[:12]:
                mark = f" ({t['receipt']})" if x.get("receipt_file_id") else ""
                lines.append(f"• {x['description']} — {ledger._money(x['amount'], cur)}{mark}")
            if len(exp) > 12:
                lines.append(t["more"].format(n=len(exp) - 12))
            receipt_ids = [x["receipt_file_id"] for x in exp if x.get("receipt_file_id")]
        else:
            lines.append(t["exp_none"])
        if inc:
            lines.append(t["inc"].format(sum=money(sum(x["amount"] for x in inc), cur, lang)))
        s = ledger.summary(object_id)
        if s["balance"] >= 0:
            lines.append(t["balance"].format(sum=money(s["balance"], cur, lang)))
        else:
            lines.append(t["overspend"].format(sum=money(-s["balance"], cur, lang)))

    photos = [p["file_id"] for p in daily] + [p["file_id"] for p in photos_on(object_id, date, ("work",))]
    photos = list(dict.fromkeys(photos + receipt_ids))[:max_photos]
    lines.append("")
    lines.append(t["photos"].format(n=len(photos)) if photos else t["photos_none"])
    has_activity = bool(a["came"] or work or photos or (with_finance and ledger._tx(object_id, date, date)))
    return {"text": "\n".join(lines), "photos": photos, "has_activity": has_activity}
