"""Telegram-бот: AI-помощник для архитекторов и прорабов + AI Qurilish Nazoratchisi (этап 1).
Запуск: python bot.py  (настройки — в переменных окружения / файле .env)"""
import asyncio
import base64
import datetime as dt
import logging
import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

from aiogram import Bot, Dispatcher, F  # noqa: E402
from aiogram.enums import ChatAction  # noqa: E402
from aiogram.filters import Command, CommandObject, CommandStart  # noqa: E402
from aiogram.fsm.context import FSMContext  # noqa: E402
from aiogram.fsm.state import State, StatesGroup  # noqa: E402
from aiogram.types import (CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup,  # noqa: E402
                           InputMediaPhoto, KeyboardButton, Message, ReplyKeyboardMarkup)

import ai  # noqa: E402
import db  # noqa: E402
import docgen  # noqa: E402
import estimate  # noqa: E402
import ledger  # noqa: E402
import roles  # noqa: E402
import site_ops  # noqa: E402
from i18n import LANGS, all_variants, role_name, t  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("bot")

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "100"))
DAILY_REPORT_TIME = os.getenv("DAILY_REPORT_TIME", "19:00")
PHOTO_REMINDER_TIME = os.getenv("PHOTO_REMINDER_TIME", "20:00")
BACKUP_TIME = os.getenv("BACKUP_TIME", "23:30")
MAX_FILE = 20 * 1024 * 1024
TZ = ZoneInfo("Asia/Tashkent")
docgen.COMPANY_NAME = os.getenv("COMPANY_NAME", "")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()
estimate.load_prices()
BOT_USERNAME = ""

LANG_KB = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
     InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang:uz")],
    [InlineKeyboardButton(text="🇺🇿 Ўзбекча (кирилл)", callback_data="lang:uzc"),
     InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")],
])

MODES = {"btn_calc": "calc", "btn_files": "files", "btn_estimate": "estimate", "btn_docs": "docs",
         "btn_objects": "objects"}
MODE_PREFIX = {
    "calc": "[Раздел: расчёты] ", "files": "[Раздел: анализ файлов] ",
    "estimate": "[Раздел: смета] ", "docs": "[Раздел: документы] ",
    "objects": "[Раздел: учёт по объектам] ", "chat": "",
}


class CheckIn(StatesGroup):
    location = State()
    selfie = State()


class CheckOut(StatesGroup):
    location = State()
    work = State()
    photos = State()


class PhotoRep(StatesGroup):
    photos = State()


class SetLoc(StatesGroup):
    location = State()


def B(key):
    """Фильтр: нажата кнопка key (на любом языке)."""
    return F.text.in_(all_variants(key))


def lang_of(uid):
    return db.get_lang(uid)


# ---------- клавиатуры ----------
def main_menu(uid, lang):
    btns = []
    if roles.is_staff(uid):
        btns += ["btn_calc", "btn_files", "btn_estimate", "btn_docs", "btn_objects"]
    rs = roles.all_roles(uid)
    if "worker" in rs:
        btns += ["btn_checkin", "btn_checkout", "btn_photo"]
    if "foreman" in rs or roles.is_admin(uid):
        btns += ["btn_photo", "btn_attendance", "btn_today", "btn_archive"]
    if "client" in rs:
        btns += ["btn_today", "btn_finance", "btn_archive"]
    if "supervisor" in rs:
        btns += ["btn_attendance", "btn_archive"]
    if rs & {"designer", "drafter"}:
        btns += ["btn_archive"]
    btns = list(dict.fromkeys(btns))
    rows = [[KeyboardButton(text=t(k, lang)) for k in btns[i:i + 2]] for i in range(0, len(btns), 2)]
    rows.append([KeyboardButton(text=t("btn_new", lang)), KeyboardButton(text=t("btn_lang", lang))])
    return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=rows)


def flow_kb(lang, location=False, done=False, skip=False):
    rows = []
    if location:
        rows.append([KeyboardButton(text=t("btn_location", lang), request_location=True)])
    extra = []
    if done:
        extra.append(KeyboardButton(text=t("btn_done", lang)))
    if skip:
        extra.append(KeyboardButton(text=t("btn_skip", lang)))
    if extra:
        rows.append(extra)
    rows.append([KeyboardButton(text=t("btn_cancel", lang))])
    return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=rows)


def pick_kb(purpose, object_ids):
    rows = [[InlineKeyboardButton(text=ledger.find_object(oid)["name"], callback_data=f"pick:{purpose}:{oid}")]
            for oid in object_ids]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ---------- отправка ----------
async def send_text(chat_id, text, markdown=False, **kw):
    for i in range(0, len(text), 4000):
        chunk = text[i:i + 4000]
        try:
            await bot.send_message(chat_id, chunk, parse_mode="Markdown" if markdown else None, **kw)
        except Exception:
            await bot.send_message(chat_id, chunk, **kw)


async def send_photos(chat_id, file_ids):
    file_ids = list(file_ids)
    for i in range(0, len(file_ids), 10):
        chunk = file_ids[i:i + 10]
        try:
            if len(chunk) == 1:
                await bot.send_photo(chat_id, chunk[0])
            else:
                await bot.send_media_group(chat_id, [InputMediaPhoto(media=f) for f in chunk])
        except Exception:
            log.exception("send photos failed")


async def notify(uids, key, exclude=None, **kw):
    for u in dict.fromkeys(uids):
        if u == exclude:
            continue
        try:
            await bot.send_message(u, t(key, lang_of(u), **kw))
        except Exception as e:  # пользователь не открыл бота или заблокировал
            log.warning("notify %s failed: %s", u, e)


def is_group(m: Message):
    return m.chat.type in ("group", "supergroup")


async def allowed(m: Message, silent=False) -> bool:
    db.upsert_user(m.from_user.id, m.from_user.full_name)
    if roles.is_known(m.from_user.id):
        return True
    if not silent and not is_group(m):
        await m.answer(t("no_access", lang_of(m.from_user.id), uid=m.from_user.id))
    return False


# ---------- AI ----------
async def process(m: Message, content, history_text: str, smart: bool, photo_file_id=None):
    uid = m.from_user.id
    lang = lang_of(uid)
    if not roles.is_admin(uid) and db.requests_today(uid) >= DAILY_LIMIT:
        await m.answer(t("limit", lang))
        return
    status = await m.answer(t("reading_file" if smart else "thinking", lang))
    await bot.send_chat_action(m.chat.id, ChatAction.TYPING)
    try:
        user = {"id": uid, "name": m.from_user.full_name, "photo_file_id": photo_file_id}
        answer, out, usage = await ai.ask(db.get_history(uid), content, lang, use_smart=smart, user=user)
    except Exception:
        log.exception("AI error")
        await status.edit_text(t("error", lang))
        return
    for model, i, o in usage:
        db.log_usage(uid, model, i, o)
    db.add_history(uid, "user", history_text)
    db.add_history(uid, "assistant", answer or "(файл)")
    await status.delete()
    for msg in out["messages"]:
        await send_text(m.chat.id, msg["text"])
        await send_photos(m.chat.id, msg["photos"])
    if answer:
        await send_text(m.chat.id, answer, markdown=True)
    for f in out["files"]:
        await m.answer_document(FSInputFile(f))
    for n in out["notify"]:
        to = n.pop("to")
        key = n.pop("key")
        await notify(to, key, exclude=uid, **n)


# ---------- старт, язык, приглашения ----------
@dp.message(CommandStart())
async def start(m: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    db.upsert_user(m.from_user.id, m.from_user.full_name)
    uid = m.from_user.id
    arg = (command.args or "").strip()
    if arg.startswith("j_"):
        res = roles.use_invite(arg[2:], uid)
        if not res:
            await m.answer(t("invite_bad", lang_of(uid)))
            return
        o = ledger.find_object(res["object_id"])
        db.audit(uid, m.from_user.full_name, o["id"], "join", res["role"])
        await m.answer(t("joined", lang_of(uid), obj=o["name"], role=role_name(res["role"], lang_of(uid))))
        if res["created_by"]:
            who = m.from_user.full_name + (f" ({res['label']})" if res["label"] else "")
            await notify([res["created_by"]], "joined_notify", exclude=uid, name=who, obj=o["name"],
                         role=role_name(res["role"], lang_of(res["created_by"])))
    elif not await allowed(m):
        return
    await m.answer(t("choose_lang", "ru"), reply_markup=LANG_KB)


def welcome_text(uid, lang):
    parts = []
    rs = roles.all_roles(uid)
    if roles.is_staff(uid):
        parts.append(t("welcome", lang))
    if "client" in rs:
        parts.append(t("welcome_client", lang, time=DAILY_REPORT_TIME))
    if "worker" in rs:
        parts.append(t("welcome_worker", lang))
    if not parts:
        parts.append(t("welcome_member", lang))
    return "\n\n".join(parts)


@dp.callback_query(F.data.startswith("lang:"))
async def set_lang(c: CallbackQuery):
    lang = c.data.split(":")[1]
    if lang not in LANGS:
        lang = "ru"
    db.upsert_user(c.from_user.id, c.from_user.full_name)
    db.set_lang(c.from_user.id, lang)
    await c.message.answer(welcome_text(c.from_user.id, lang), reply_markup=main_menu(c.from_user.id, lang))
    await c.answer()


@dp.message(Command("menu"))
async def menu_cmd(m: Message, state: FSMContext):
    await state.clear()
    if await allowed(m):
        await m.answer("👌", reply_markup=main_menu(m.from_user.id, lang_of(m.from_user.id)))


@dp.message(Command("new"))
async def new_chat(m: Message, state: FSMContext):
    await state.clear()
    db.clear_history(m.from_user.id)
    db.set_mode(m.from_user.id, "chat")
    await m.answer(t("new_chat", lang_of(m.from_user.id)))


@dp.message(Command("myid"))
async def myid(m: Message):
    await m.answer(f"Telegram ID: {m.from_user.id}")


# ---------- админ ----------
@dp.message(Command("stats"))
async def stats(m: Message):
    if not roles.is_admin(m.from_user.id):
        return
    s = db.stats()
    lines = [f"Пользователей всего: {s['users_total']}", f"Активных за 30 дней: {s['active_users']}"]
    for r in s["by_model"]:
        lines.append(f"{r['model']}: {r['requests']} вызовов, вход {r['input_tokens']:,} / выход {r['output_tokens']:,} токенов")
    await m.answer("\n".join(lines))


@dp.message(Command("reload_prices"))
async def reload_prices(m: Message):
    if not roles.is_admin(m.from_user.id):
        return
    p = estimate.load_prices()
    await m.answer(f"Прайс перезагружен, дата: {p['updated']}")


@dp.message(Command("backup"))
async def backup(m: Message):
    if not roles.is_admin(m.from_user.id):
        return
    await m.answer_document(FSInputFile(db.DB_PATH, filename="bot_backup.db"),
                            caption="Резервная копия базы. Храните в надёжном месте.")


@dp.message(Command("objects"))
async def objects_cmd(m: Message):
    if not await allowed(m):
        return
    uid = m.from_user.id
    fin = set(roles.objects_with(uid, "finance_view"))
    objs = ledger.list_objects(ids=roles.objects_with(uid))
    if not objs:
        await m.answer(t("no_objects", lang_of(uid)))
        return
    f = ledger._money
    lines = []
    for o in objs:
        my = ", ".join(role_name(r, lang_of(uid)) for r in sorted(roles.object_roles(uid, o["id"]))) or "admin"
        line = f"{o['id']}. {o['name']} — {o['client'] or '—'} [{my}]"
        if o["id"] in fin:
            line += (f"\n   {o['currency']}: получено {f(o['received'], o['currency'])} / потрачено "
                     f"{f(o['spent'], o['currency'])} / остаток {f(o['balance'], o['currency'])}")
        lines.append(line)
    await m.answer("\n".join(lines))


# ---------- группа объекта ----------
@dp.message(Command("link"))
async def link_group(m: Message, command: CommandObject):
    if not is_group(m):
        await m.answer(t("group_hint", lang_of(m.from_user.id)))
        return
    if not await allowed(m, silent=True):
        return
    uid, lang = m.from_user.id, lang_of(m.from_user.id)
    try:
        o = ledger.find_object((command.args or "").strip() or "?")
        roles.require(uid, o["id"], "manage")
    except (ValueError, PermissionError) as e:
        await m.answer(str(e))
        return
    ledger.update_object(o["id"], group_chat_id=m.chat.id)
    db.audit(uid, m.from_user.full_name, o["id"], "link_group", str(m.chat.id))
    await m.answer(t("group_linked", lang, obj=o["name"]))


@dp.message(F.new_chat_members)
async def bot_added(m: Message):
    if any(u.id == bot.id for u in m.new_chat_members):
        await m.answer(t("group_hint", "ru") + "\n" + t("group_hint", "uz"))


# ---------- отмена ----------
@dp.message(B("btn_cancel"))
async def cancel(m: Message, state: FSMContext):
    await state.clear()
    lang = lang_of(m.from_user.id)
    await m.answer(t("cancelled", lang), reply_markup=main_menu(m.from_user.id, lang))


# ---------- Keldim ----------
@dp.message(B("btn_checkin"), F.chat.type == "private")
async def checkin_start(m: Message, state: FSMContext):
    if not await allowed(m):
        return
    uid, lang = m.from_user.id, lang_of(m.from_user.id)
    if "worker" not in roles.all_roles(uid):
        await m.answer(t("not_worker", lang))
        return
    op = site_ops.open_checkin(uid)
    if op and op["date"] == site_ops.today():
        await m.answer(t("already_in", lang))
        return
    await state.set_state(CheckIn.location)
    await m.answer(t("ask_loc_in", lang), reply_markup=flow_kb(lang, location=True))


@dp.message(CheckIn.location, F.location)
async def checkin_location(m: Message, state: FSMContext):
    uid, lang = m.from_user.id, lang_of(m.from_user.id)
    lat, lon = m.location.latitude, m.location.longitude
    await state.update_data(lat=lat, lon=lon)
    o = site_ops.pick_object(uid, lat, lon)
    if not o:
        ids = [oid for oid, r, _l in roles.roles_of(uid) if r == "worker"]
        await m.answer(t("pick_obj", lang), reply_markup=pick_kb("ci", ids))
        return
    await state.update_data(oid=o["id"])
    await state.set_state(CheckIn.selfie)
    await m.answer(t("ask_selfie", lang), reply_markup=flow_kb(lang))


@dp.message(CheckIn.location)
async def checkin_need_location(m: Message):
    await m.answer(t("need_location", lang_of(m.from_user.id)))


@dp.message(CheckIn.selfie, F.photo)
async def checkin_selfie(m: Message, state: FSMContext):
    uid, lang = m.from_user.id, lang_of(m.from_user.id)
    d = await state.get_data()
    await state.clear()
    try:
        res = site_ops.check_in(d["oid"], uid, d["lat"], d["lon"], m.photo[-1].file_id)
    except ValueError as e:
        await m.answer(t("already_in", lang) if str(e) == "already_in" else str(e),
                       reply_markup=main_menu(uid, lang))
        return
    except PermissionError:
        await m.answer(t("not_worker", lang), reply_markup=main_menu(uid, lang))
        return
    text = t("checkin_ok", lang, obj=res["object"], time=dt.datetime.now(TZ).strftime("%H:%M"))
    if "far" in res["flags"]:
        text += "\n" + t("far_warn", lang, dist=round(res["dist"]))
        await notify(roles.users_with_role(res["object_id"], "foreman"), "far_alert", exclude=uid,
                     name=site_ops.person(res["object_id"], uid), obj=res["object"], dist=round(res["dist"]))
    await m.answer(text, reply_markup=main_menu(uid, lang))


@dp.message(CheckIn.selfie)
async def checkin_need_selfie(m: Message):
    await m.answer(t("need_photo", lang_of(m.from_user.id)))


# ---------- Ketdim ----------
@dp.message(B("btn_checkout"), F.chat.type == "private")
async def checkout_start(m: Message, state: FSMContext):
    if not await allowed(m):
        return
    uid, lang = m.from_user.id, lang_of(m.from_user.id)
    op = site_ops.open_checkin(uid)
    if not op:
        await m.answer(t("no_open", lang))
        return
    await state.set_state(CheckOut.location)
    await state.update_data(att=op["id"])
    await m.answer(t("ask_loc_out", lang), reply_markup=flow_kb(lang, location=True))


@dp.message(CheckOut.location, F.location)
async def checkout_location(m: Message, state: FSMContext):
    lang = lang_of(m.from_user.id)
    d = await state.get_data()
    res = site_ops.check_out(d["att"], m.location.latitude, m.location.longitude)
    await state.update_data(obj=res["object"], seconds=res["seconds"], photos=[])
    await state.set_state(CheckOut.work)
    await m.answer(t("ask_work", lang), reply_markup=flow_kb(lang, skip=True))


@dp.message(CheckOut.location)
async def checkout_need_location(m: Message):
    await m.answer(t("need_location", lang_of(m.from_user.id)))


@dp.message(CheckOut.work, F.text)
async def checkout_work(m: Message, state: FSMContext):
    lang = lang_of(m.from_user.id)
    text = "" if m.text in all_variants("btn_skip") else m.text
    await state.update_data(work=text)
    await state.set_state(CheckOut.photos)
    await m.answer(t("ask_work_photos", lang), reply_markup=flow_kb(lang, done=True, skip=True))


@dp.message(CheckOut.photos, F.photo)
async def checkout_photo(m: Message, state: FSMContext):
    d = await state.get_data()
    photos = d.get("photos", []) + [m.photo[-1].file_id]
    await state.update_data(photos=photos)
    if len(photos) == 1:
        await m.answer(t("photo_got", lang_of(m.from_user.id)))


@dp.message(CheckOut.photos, F.text)
async def checkout_finish(m: Message, state: FSMContext):
    uid, lang = m.from_user.id, lang_of(m.from_user.id)
    if m.text not in all_variants("btn_done") | all_variants("btn_skip"):
        await m.answer(t("ask_work_photos", lang))
        return
    d = await state.get_data()
    await state.clear()
    site_ops.set_work(d["att"], d.get("work", ""), d.get("photos", [])[:5])
    await m.answer(t("checkout_ok", lang, obj=d["obj"], hours=site_ops._dur(d["seconds"], lang)),
                   reply_markup=main_menu(uid, lang))


# ---------- фото-отчёт ----------
@dp.message(B("btn_photo"), F.chat.type == "private")
async def photo_start(m: Message, state: FSMContext):
    if not await allowed(m):
        return
    uid, lang = m.from_user.id, lang_of(m.from_user.id)
    ids = roles.objects_with(uid, "photo_add")
    if not ids:
        await m.answer(t("no_right", lang))
        return
    if len(ids) > 1:
        await m.answer(t("pick_obj", lang), reply_markup=pick_kb("ph", ids))
        return
    await _photo_begin(m.chat.id, uid, ids[0], state)


async def _photo_begin(chat_id, uid, oid, state: FSMContext):
    lang = lang_of(uid)
    await state.set_state(PhotoRep.photos)
    await state.update_data(oid=oid, photos=[])
    await bot.send_message(chat_id, t("photo_start", lang), reply_markup=flow_kb(lang, done=True))


@dp.message(PhotoRep.photos, F.photo)
async def photo_collect(m: Message, state: FSMContext):
    d = await state.get_data()
    photos = d.get("photos", []) + [[m.photo[-1].file_id, m.caption or ""]]
    await state.update_data(photos=photos)
    if len(photos) == 1:
        await m.answer(t("photo_got", lang_of(m.from_user.id)))


@dp.message(PhotoRep.photos, F.text)
async def photo_finish(m: Message, state: FSMContext):
    uid, lang = m.from_user.id, lang_of(m.from_user.id)
    if m.text not in all_variants("btn_done"):
        await state.update_data(caption=m.text)  # текст во время отчёта — подпись ко всем фото
        return
    d = await state.get_data()
    await state.clear()
    photos = d.get("photos", [])
    if not photos:
        await m.answer(t("photo_none", lang), reply_markup=main_menu(uid, lang))
        return
    common = d.get("caption", "")
    for fid, cap in photos:
        site_ops.add_photo(d["oid"], uid, fid, "daily", cap or common)
    o = ledger.find_object(d["oid"])
    db.audit(uid, m.from_user.full_name, o["id"], "photo_report", f"{len(photos)} photos")
    await m.answer(t("photo_saved", lang, n=len(photos), obj=o["name"]), reply_markup=main_menu(uid, lang))


# ---------- отчёты по кнопкам ----------
async def _choose(m: Message, cap, purpose):
    uid, lang = m.from_user.id, lang_of(m.from_user.id)
    ids = roles.objects_with(uid, cap)
    if not ids:
        await m.answer(t("no_right", lang))
        return None
    if len(ids) > 1:
        await m.answer(t("pick_obj", lang), reply_markup=pick_kb(purpose, ids))
        return None
    return ids[0]


async def show_today(chat_id, uid, oid):
    rep = site_ops.daily_report(oid, None, lang_of(uid), with_finance=roles.can(uid, oid, "finance_view"))
    await send_text(chat_id, rep["text"])
    await send_photos(chat_id, rep["photos"])


async def show_finance(chat_id, uid, oid):
    lang = lang_of(uid)
    s = ledger.summary(oid)
    c = s["currency"]
    mny = lambda x: site_ops.money(x, c, lang)  # noqa: E731
    lab = ledger.L.get(lang, ledger.L["ru"])
    lines = [f"💰 {s['object']}"]
    if s["budget"]:
        lines.append(f"{lab['budget']}: {mny(s['budget'])}")
    lines += [f"{lab['received']}: {mny(s['received'])}", f"{lab['spent']}: {mny(s['spent'])}"]
    if s["fee_percent"]:
        lines.append(f"{lab['fee']} ({s['fee_percent']:g}%): {mny(s['fee'])}")
    lines.append(f"{lab['balance'] if s['balance'] >= 0 else lab['overspend']}: {mny(abs(s['balance']))}")
    if s["budget_used_percent"] is not None:
        lines.append(f"{lab['budget_used']}: {s['budget_used_percent']}%")
    for k, v in s["by_category"].items():
        lines.append(f"• {lab['cats'][k]}: {mny(v)}")
    await send_text(chat_id, "\n".join(lines))


async def show_attendance(chat_id, uid, oid):
    await send_text(chat_id, site_ops.attendance_text(oid, site_ops.today(), lang_of(uid)))


async def show_archive_dates(chat_id, uid, oid):
    lang = lang_of(uid)
    dates = site_ops.photo_dates(oid, 12)
    if not dates:
        await bot.send_message(chat_id, t("archive_none", lang))
        return
    rows = [[InlineKeyboardButton(text=f"{dt.date.fromisoformat(d):%d.%m.%Y} · {n} 📷",
                                  callback_data=f"ad:{oid}:{d}")] for d, n in dates]
    await bot.send_message(chat_id, t("archive_pick_date", lang), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@dp.message(B("btn_today"))
async def today_btn(m: Message):
    if await allowed(m):
        oid = await _choose(m, "daily_report", "td")
        if oid:
            await show_today(m.chat.id, m.from_user.id, oid)


@dp.message(B("btn_finance"))
async def finance_btn(m: Message):
    if await allowed(m):
        oid = await _choose(m, "finance_view", "fi")
        if oid:
            await show_finance(m.chat.id, m.from_user.id, oid)


@dp.message(B("btn_attendance"))
async def attendance_btn(m: Message):
    if await allowed(m):
        oid = await _choose(m, "attendance_view", "at")
        if oid:
            await show_attendance(m.chat.id, m.from_user.id, oid)


@dp.message(B("btn_archive"))
async def archive_btn(m: Message):
    if await allowed(m):
        oid = await _choose(m, "photo_view", "ar")
        if oid:
            await show_archive_dates(m.chat.id, m.from_user.id, oid)


@dp.callback_query(F.data.startswith("ad:"))
async def archive_date(c: CallbackQuery):
    _, oid, date = c.data.split(":")
    oid = int(oid)
    await c.answer()
    if not roles.can(c.from_user.id, oid, "photo_view"):
        return
    ph = site_ops.photos_on(oid, date)
    caps = [p["caption"] for p in ph if p["caption"]]
    head = f"🖼 {ledger.find_object(oid)['name']} — {dt.date.fromisoformat(date):%d.%m.%Y}"
    await send_text(c.message.chat.id, head + ("\n" + "\n".join(f"• {x}" for x in dict.fromkeys(caps)) if caps else ""))
    await send_photos(c.message.chat.id, [p["file_id"] for p in ph][:40])


# ---------- локация объекта ----------
@dp.message(Command("setlocation"))
async def setloc_cmd(m: Message, state: FSMContext):
    if is_group(m):
        await m.answer(t("private_only", lang_of(m.from_user.id)))
        return
    if not await allowed(m):
        return
    oid = await _choose(m, "manage", "sl")
    if oid:
        await _setloc_begin(m.chat.id, m.from_user.id, oid, state)


async def _setloc_begin(chat_id, uid, oid, state: FSMContext):
    lang = lang_of(uid)
    await state.set_state(SetLoc.location)
    await state.update_data(oid=oid)
    await bot.send_message(chat_id, t("setloc_ask", lang, obj=ledger.find_object(oid)["name"]),
                           reply_markup=flow_kb(lang, location=True))


@dp.message(SetLoc.location, F.location)
async def setloc_save(m: Message, state: FSMContext):
    uid, lang = m.from_user.id, lang_of(m.from_user.id)
    d = await state.get_data()
    await state.clear()
    o = ledger.find_object(d["oid"])
    r = o["radius"] or site_ops.DEFAULT_RADIUS
    ledger.update_object(o["id"], lat=m.location.latitude, lon=m.location.longitude, radius=r)
    db.audit(uid, m.from_user.full_name, o["id"], "set_location", f"{m.location.latitude},{m.location.longitude}")
    await m.answer(t("setloc_ok", lang, obj=o["name"], r=round(r)), reply_markup=main_menu(uid, lang))


@dp.message(SetLoc.location)
async def setloc_need(m: Message):
    await m.answer(t("need_location", lang_of(m.from_user.id)))


# ---------- выбор объекта (inline) ----------
@dp.callback_query(F.data.startswith("pick:"))
async def picked(c: CallbackQuery, state: FSMContext):
    _, purpose, oid = c.data.split(":")
    oid, uid, chat = int(oid), c.from_user.id, c.message.chat.id
    lang = lang_of(uid)
    await c.answer()
    if purpose == "ci":
        if "worker" not in roles.object_roles(uid, oid):
            return
        await state.update_data(oid=oid)
        await state.set_state(CheckIn.selfie)
        await bot.send_message(chat, t("ask_selfie", lang), reply_markup=flow_kb(lang))
    elif purpose == "ph" and roles.can(uid, oid, "photo_add"):
        await _photo_begin(chat, uid, oid, state)
    elif purpose == "td" and roles.can(uid, oid, "daily_report"):
        await show_today(chat, uid, oid)
    elif purpose == "fi" and roles.can(uid, oid, "finance_view"):
        await show_finance(chat, uid, oid)
    elif purpose == "at" and roles.can(uid, oid, "attendance_view"):
        await show_attendance(chat, uid, oid)
    elif purpose == "ar" and roles.can(uid, oid, "photo_view"):
        await show_archive_dates(chat, uid, oid)
    elif purpose == "sl" and roles.can(uid, oid, "manage"):
        await _setloc_begin(chat, uid, oid, state)


# ---------- файлы → AI ----------
async def _download(file_id) -> bytes:
    f = await bot.get_file(file_id)
    data = await bot.download_file(f.file_path)
    return data.read()


def _addressed(m: Message, text: str) -> bool:
    """В группе бот отвечает только на упоминание или ответ на своё сообщение."""
    if not is_group(m):
        return True
    if BOT_USERNAME and f"@{BOT_USERNAME.lower()}" in (text or "").lower():
        return True
    r = m.reply_to_message
    return bool(r and r.from_user and r.from_user.id == bot.id)


def _clean(text):
    return (text or "").replace(f"@{BOT_USERNAME}", "").strip() if BOT_USERNAME else (text or "")


def _group_prefix(m: Message):
    if not is_group(m):
        return ""
    r = db._con.execute("SELECT name FROM objects WHERE group_chat_id=?", (m.chat.id,)).fetchone()
    return f"[Сообщение из Telegram-группы объекта «{r[0]}»] " if r else "[Сообщение из Telegram-группы] "


def _file_caption(m: Message, default: str) -> str:
    mode = db.get_mode(m.from_user.id)
    if mode == "objects":
        default = "Это чек или накладная. Распознай позиции, количество, цены и итог."
    return _group_prefix(m) + MODE_PREFIX.get(mode, "") + (_clean(m.caption) or default)


@dp.message(F.photo)
async def on_photo(m: Message):
    if not _addressed(m, m.caption) or not await allowed(m, silent=is_group(m)):
        return
    photo = m.photo[-1]
    raw = await _download(photo.file_id)
    caption = _file_caption(m, "Проанализируй изображение: что на нём, найди ошибки и замечания.")
    content = [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                     "data": base64.b64encode(raw).decode()}},
        {"type": "text", "text": caption},
    ]
    await process(m, content, f"[фото] {caption}", smart=True, photo_file_id=photo.file_id)


@dp.message(F.document)
async def on_document(m: Message):
    if not _addressed(m, m.caption) or not await allowed(m, silent=is_group(m)):
        return
    lang = lang_of(m.from_user.id)
    doc = m.document
    if doc.file_size and doc.file_size > MAX_FILE:
        await m.answer(t("too_big", lang))
        return
    mime = (doc.mime_type or "").lower()
    name = (doc.file_name or "").lower()
    caption = _file_caption(m, "Проанализируй документ: суть, ошибки, несоответствия, замечания.")
    raw = await _download(doc.file_id)
    b64 = base64.b64encode(raw).decode()
    if mime == "application/pdf" or name.endswith(".pdf"):
        block = {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": b64}}
    elif mime in ("image/jpeg", "image/png", "image/webp") or name.endswith((".jpg", ".jpeg", ".png", ".webp")):
        mt = mime if mime.startswith("image/") else ("image/png" if name.endswith(".png") else "image/jpeg")
        block = {"type": "image", "source": {"type": "base64", "media_type": mt, "data": b64}}
    else:
        await m.answer(t("bad_type", lang))
        return
    await process(m, [block, {"type": "text", "text": caption}], f"[файл {doc.file_name}] {caption}", smart=True)


# ---------- текст ----------
@dp.message(F.text)
async def on_text(m: Message, state: FSMContext):
    if not _addressed(m, m.text) or not await allowed(m, silent=is_group(m)):
        return
    uid = m.from_user.id
    lang = lang_of(uid)
    if not is_group(m):
        if m.text in all_variants("btn_lang"):
            await m.answer(t("choose_lang", lang), reply_markup=LANG_KB)
            return
        if m.text in all_variants("btn_new"):
            await state.clear()
            db.clear_history(uid)
            db.set_mode(uid, "chat")
            await m.answer(t("new_chat", lang), reply_markup=main_menu(uid, lang))
            return
        for key, mode in MODES.items():
            if m.text in all_variants(key):
                if not roles.is_staff(uid):
                    await m.answer(t("no_right", lang))
                    return
                db.set_mode(uid, mode)
                await m.answer(t("hint_" + mode, lang))
                return
    mode = db.get_mode(uid) if not is_group(m) else "chat"
    text = _group_prefix(m) + MODE_PREFIX.get(mode, "") + _clean(m.text)
    await process(m, text, text, smart=(mode in ("docs", "objects")))


# ---------- расписание (ТЗ, раздел 6) ----------
async def job_daily_reports():
    for o in ledger.list_objects(with_finance=False):
        clients = roles.users_with_role(o["id"], "client")
        if not clients:
            continue
        for u in clients:
            lang = lang_of(u)
            rep = site_ops.daily_report(o["id"], None, lang)
            try:
                if rep["has_activity"]:
                    await send_text(u, rep["text"])
                    await send_photos(u, rep["photos"])
                else:
                    await bot.send_message(u, t("report_none", lang, obj=o["name"]))
            except Exception as e:
                log.warning("daily report to %s failed: %s", u, e)


async def job_photo_reminders():
    day = site_ops.today()
    for o in ledger.list_objects(with_finance=False):
        foremen = roles.users_with_role(o["id"], "foreman")
        if foremen and not site_ops.daily_photo_done(o["id"], day):
            await notify(foremen, "photo_reminder", obj=o["name"])


async def job_backup():
    for a in roles.ADMINS:
        try:
            await bot.send_document(a, FSInputFile(db.DB_PATH, filename=f"backup_{site_ops.today()}.db"),
                                    caption="Ежедневная резервная копия базы")
        except Exception as e:
            log.warning("backup to %s failed: %s", a, e)


JOBS = [("daily_report", DAILY_REPORT_TIME, job_daily_reports),
        ("photo_reminder", PHOTO_REMINDER_TIME, job_photo_reminders),
        ("backup", BACKUP_TIME, job_backup)]


async def scheduler():
    while True:
        now = dt.datetime.now(TZ)
        hm, day = now.strftime("%H:%M"), now.date().isoformat()
        for name, at, fn in JOBS:
            if hm >= at and db.get_setting(f"job:{name}") != day:
                db.set_setting(f"job:{name}", day)  # сначала отмечаем, чтобы не отправить дважды
                try:
                    await fn()
                except Exception:
                    log.exception("job %s failed", name)
        await asyncio.sleep(30)


async def main():
    global BOT_USERNAME
    me = await bot.get_me()
    BOT_USERNAME = me.username or ""
    ai.BOT_USERNAME = BOT_USERNAME
    for name, at, _fn in JOBS:  # при первом запуске не слать «вчерашние» задачи
        if db.get_setting(f"job:{name}") is None and dt.datetime.now(TZ).strftime("%H:%M") >= at:
            db.set_setting(f"job:{name}", site_ops.today())
    log.info("Bot started as @%s", BOT_USERNAME)
    asyncio.create_task(scheduler())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
