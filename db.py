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
""")
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
