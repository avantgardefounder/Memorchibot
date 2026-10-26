"""Роли, участники объектов, приглашения и права доступа (ТЗ, разделы 2 и 5).

Роли на объекте: client (mijoz), foreman (prorab), designer (dizayner), drafter (chertyojchi),
supervisor (texnadzor), worker (usta). Admin — студия (ADMIN_IDS), видит всё.
Сотрудники (ALLOWED_USERS) пользуются общими инструментами и создают объекты;
доступ к данным конкретного объекта — только по роли на нём.
"""
import os
import secrets
import time

import db

ROLES = ("client", "foreman", "designer", "drafter", "supervisor", "worker")


def _ids(var):
    return {int(x) for x in os.getenv(var, "").replace(" ", "").split(",") if x.strip().lstrip("-").isdigit()}


ADMINS = _ids("ADMIN_IDS")
STAFF = _ids("ALLOWED_USERS")

# Что может каждая роль (этап 1 ТЗ). Admin может всё.
CAPS = {
    "finance_view": {"client", "foreman"},      # расходы, поступления, остаток, отчёт клиенту
    "finance_edit": {"foreman"},                # записывать и удалять операции
    "attendance_view": {"client", "foreman", "supervisor"},
    "attendance_mark": {"worker"},              # Keldim / Ketdim
    "photo_view": {"client", "foreman", "designer", "drafter", "supervisor"},
    "photo_add": {"foreman", "worker"},
    "daily_report": {"client", "foreman"},
    "manage": {"foreman"},                      # приглашения, карточка объекта, локация, группа
}
CAP_TEXT = {
    "finance_view": "просмотр финансов объекта", "finance_edit": "запись и удаление операций",
    "attendance_view": "просмотр davomat", "attendance_mark": "отметка Keldim/Ketdim",
    "photo_view": "просмотр фото-отчётов", "photo_add": "фото-отчёт", "daily_report": "ежедневный отчёт",
    "manage": "управление объектом и участниками",
}


def is_admin(uid):
    return uid in ADMINS


def is_staff(uid):
    return uid in STAFF or uid in ADMINS


def roles_of(uid):
    """[(object_id, role, label)] активных объектов."""
    return db._con.execute(
        "SELECT p.object_id, p.role, p.label FROM participants p JOIN objects o ON o.id=p.object_id "
        "WHERE p.user_id=? AND p.active=1 AND o.status='active' ORDER BY p.object_id", (uid,)).fetchall()


def object_roles(uid, object_id):
    return {r for (oid, r, _l) in roles_of(uid) if oid == object_id}


def can(uid, object_id, cap):
    if is_admin(uid):
        return True
    return bool(object_roles(uid, object_id) & CAPS[cap])


def require(uid, object_id, cap):
    if not can(uid, object_id, cap):
        raise PermissionError(f"Нет доступа: {CAP_TEXT.get(cap, cap)} по этому объекту недоступно для вашей роли.")


def objects_with(uid, cap=None):
    """id активных объектов, где у пользователя есть право cap (или любая роль, если cap=None)."""
    if is_admin(uid):
        return [r[0] for r in db._con.execute("SELECT id FROM objects WHERE status='active' ORDER BY id")]
    out = []
    for oid, role, _l in roles_of(uid):
        if (cap is None or role in CAPS[cap]) and oid not in out:
            out.append(oid)
    return out


def is_known(uid):
    return is_staff(uid) or bool(roles_of(uid))


def all_roles(uid):
    return {r for (_o, r, _l) in roles_of(uid)}


# ---------- участники ----------
def add_participant(object_id, uid, role, label="", added_by=None):
    if role not in ROLES:
        raise ValueError(f"Неизвестная роль {role}. Роли: {', '.join(ROLES)}")
    db._con.execute(
        "INSERT INTO participants(object_id,user_id,role,label,added_by,created,active) VALUES(?,?,?,?,?,?,1) "
        "ON CONFLICT(object_id,user_id,role) DO UPDATE SET active=1, label=excluded.label",
        (object_id, uid, role, label or "", added_by, time.time()))
    db._con.commit()


def remove_participant(object_id, uid, role=None):
    q = "UPDATE participants SET active=0 WHERE object_id=? AND user_id=?"
    args = [object_id, uid]
    if role:
        q += " AND role=?"
        args.append(role)
    n = db._con.execute(q, args).rowcount
    db._con.commit()
    return n


def list_participants(object_id):
    rows = db._con.execute(
        "SELECT p.user_id, COALESCE(u.name,''), p.role, p.label FROM participants p "
        "LEFT JOIN users u ON u.id=p.user_id WHERE p.object_id=? AND p.active=1 ORDER BY p.role, u.name",
        (object_id,)).fetchall()
    return [{"user_id": u, "name": n, "role": r, "label": l or ""} for u, n, r, l in rows]


def users_with_role(object_id, *roles):
    marks = ",".join("?" * len(roles))
    return [r[0] for r in db._con.execute(
        f"SELECT DISTINCT user_id FROM participants WHERE object_id=? AND active=1 AND role IN ({marks})",
        (object_id, *roles))]


def find_participant(object_id, ref):
    """Участник по ID или части имени."""
    people = list_participants(object_id)
    if str(ref).lstrip("-").isdigit():
        hit = [p for p in people if p["user_id"] == int(ref)]
    else:
        ref_l = str(ref).lower()
        hit = [p for p in people if ref_l in p["name"].lower() or ref_l in p["label"].lower()]
    ids = {p["user_id"] for p in hit}
    if len(ids) == 1:
        return hit[0]
    if not ids:
        raise ValueError(f"Участник «{ref}» не найден на объекте")
    raise ValueError("Подходит несколько участников: " + ", ".join(p["name"] for p in hit))


# ---------- приглашения ----------
def create_invite(object_id, role, label="", created_by=None):
    if role not in ROLES:
        raise ValueError(f"Неизвестная роль {role}. Роли: {', '.join(ROLES)}")
    code = secrets.token_urlsafe(6).replace("-", "x").replace("_", "y")
    db._con.execute("INSERT INTO invites(code,object_id,role,label,created_by,created) VALUES(?,?,?,?,?,?)",
                    (code, object_id, role, label or "", created_by, time.time()))
    db._con.commit()
    return code


def use_invite(code, uid):
    r = db._con.execute("SELECT object_id, role, label, created_by FROM invites WHERE code=? AND active=1",
                        (code,)).fetchone()
    if not r:
        return None
    object_id, role, label, created_by = r
    add_participant(object_id, uid, role, label, created_by)
    return {"object_id": object_id, "role": role, "label": label, "created_by": created_by}


def revoke_invites(object_id, role=None):
    q, args = "UPDATE invites SET active=0 WHERE object_id=?", [object_id]
    if role:
        q += " AND role=?"
        args.append(role)
    n = db._con.execute(q, args).rowcount
    db._con.commit()
    return n
