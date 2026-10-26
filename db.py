"""SQLite: пользователи, язык, история диалога, статистика."""
import json
import os
import sqlite3
import time
from pathlib import Path

# На Railway подключите Volume (путь /data): база попадёт туда автоматически и не будет сбрасываться при обновлениях
DATA_DIR = Path(os.getenv("DATA_DIR") or os.getenv("RAILWAY_VOLUME_MOUNT_PATH") or Path(__file__).parent)
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "bot.db"
_con = sqlite3.connect(DB_PATH, check_same_thread=False)
_con.executescript("""
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY, name TEXT, lang TEXT DEFAULT 'ru', mode TEXT DEFAULT 'chat',
  created REAL, last_seen REAL);
CREATE TABLE IF NOT EXISTS history(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, role TEXT, content TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS usage(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, model TEXT,
  input_tokens INTEGER, output_tokens INTEGER, ts REAL);
CREATE TABLE IF NOT EXISTS objects(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, client TEXT, address TEXT,
  budget REAL DEFAULT 0, fee_percent REAL DEFAULT 0, currency TEXT DEFAULT 'UZS',
  status TEXT DEFAULT 'active', created REAL);
CREATE TABLE IF NOT EXISTS transactions(
  id INTEGER PRIMARY KEY AUTOINCREMENT, object_id INTEGER, date TEXT, type TEXT,
  category TEXT, description TEXT, qty REAL, unit TEXT, price REAL, amount REAL,
  author_id INTEGER, author_name TEXT, created REAL, deleted INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS participants(
  id INTEGER PRIMARY KEY AUTOINCREMENT, object_id INTEGER, user_id INTEGER, role TEXT,
  label TEXT, added_by INTEGER, created REAL, active INTEGER DEFAULT 1,
  UNIQUE(object_id, user_id, role));
CREATE TABLE IF NOT EXISTS invites(
  code TEXT PRIMARY KEY, object_id INTEGER, role TEXT, label TEXT, created_by INTEGER,
  created REAL, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS attendance(
  id INTEGER PRIMARY KEY AUTOINCREMENT, object_id INTEGER, user_id INTEGER, date TEXT,
  in_ts REAL, in_lat REAL, in_lon REAL, in_dist REAL, in_selfie TEXT,
  out_ts REAL, out_lat REAL, out_lon REAL, out_dist REAL, work_text TEXT, flags TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS photos(
  id INTEGER PRIMARY KEY AUTOINCREMENT, object_id INTEGER, user_id INTEGER, date TEXT, ts REAL,
  file_id TEXT, kind TEXT, caption TEXT, ref_id INTEGER);
CREATE TABLE IF NOT EXISTS audit(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, user_id INTEGER, user_name TEXT,
  object_id INTEGER, action TEXT, details TEXT);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
""")
_MIGRATIONS = {  # новые колонки для баз, созданных старыми версиями
    "transactions": ("orig_currency TEXT", "orig_amount REAL", "rate REAL", "paid_by TEXT", "receipt_file_id TEXT"),
    "objects": ("obj_type TEXT", "area REAL", "floors INTEGER", "lat REAL", "lon REAL", "radius REAL",
                "start_date TEXT", "end_date TEXT", "group_chat_id INTEGER"),
}
for _table, _cols in _MIGRATIONS.items():
    for _col in _cols:
        try:
            _con.execute(f"ALTER TABLE {_table} ADD COLUMN {_col}")
        except sqlite3.OperationalError:
            pass
_con.commit()


def get_setting(key, default=None):
    r = _con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return r[0] if r else default


def set_setting(key, value):
    _con.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                 (key, str(value)))
    _con.commit()


def audit(user_id, user_name, object_id, action, details=""):
    """Журнал изменений: кто, когда, что сделал (ТЗ, раздел 7)."""
    _con.execute("INSERT INTO audit(ts,user_id,user_name,object_id,action,details) VALUES(?,?,?,?,?,?)",
                 (time.time(), user_id, user_name, object_id, action, details[:2000]))
    _con.commit()

HISTORY_LIMIT = 12  # последних сообщений в контексте (экономит токены)


def upsert_user(uid, name):
    now = time.time()
    _con.execute("INSERT INTO users(id,name,created,last_seen) VALUES(?,?,?,?) "
                 "ON CONFLICT(id) DO UPDATE SET name=excluded.name,last_seen=excluded.last_seen",
                 (uid, name, now, now))
    _con.commit()


def get_lang(uid):
    r = _con.execute("SELECT lang FROM users WHERE id=?", (uid,)).fetchone()
    return r[0] if r else "ru"


def set_lang(uid, lang):
    _con.execute("UPDATE users SET lang=? WHERE id=?", (lang, uid))
    _con.commit()


def get_mode(uid):
    r = _con.execute("SELECT mode FROM users WHERE id=?", (uid,)).fetchone()
    return r[0] if r else "chat"


def set_mode(uid, mode):
    _con.execute("UPDATE users SET mode=? WHERE id=?", (mode, uid))
    _con.commit()


def add_history(uid, role, text):
    _con.execute("INSERT INTO history(user_id,role,content,ts) VALUES(?,?,?,?)",
                 (uid, role, json.dumps(text, ensure_ascii=False), time.time()))
    _con.commit()


def get_history(uid):
    rows = _con.execute("SELECT role,content FROM history WHERE user_id=? ORDER BY id DESC LIMIT ?",
                        (uid, HISTORY_LIMIT)).fetchall()
    msgs = [{"role": r, "content": json.loads(c)} for r, c in reversed(rows)]
    while msgs and msgs[0]["role"] != "user":  # история должна начинаться с user
        msgs.pop(0)
    return msgs


def clear_history(uid):
    _con.execute("DELETE FROM history WHERE user_id=?", (uid,))
    _con.commit()


def log_usage(uid, model, inp, out):
    _con.execute("INSERT INTO usage(user_id,model,input_tokens,output_tokens,ts) VALUES(?,?,?,?,?)",
                 (uid, model, inp, out, time.time()))
    _con.commit()


def requests_today(uid):
    since = time.time() - 86400
    return _con.execute("SELECT COUNT(*) FROM history WHERE user_id=? AND role='user' AND ts>?",
                        (uid, since)).fetchone()[0]


def stats(days=30):
    since = time.time() - days * 86400
    users = _con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    active = _con.execute("SELECT COUNT(DISTINCT user_id) FROM usage WHERE ts>?", (since,)).fetchone()[0]
    rows = _con.execute("SELECT model, COUNT(*), SUM(input_tokens), SUM(output_tokens) FROM usage "
                        "WHERE ts>? GROUP BY model", (since,)).fetchall()
    return {"users_total": users, "active_users": active,
            "by_model": [{"model": m, "requests": n, "input_tokens": i or 0, "output_tokens": o or 0}
                         for m, n, i, o in rows]}
