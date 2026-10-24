"""Telegram-бот: AI-помощник для архитекторов и прорабов.
Запуск: python bot.py  (настройки — в файле .env)"""
import asyncio
import base64
import logging
import os

from dotenv import load_dotenv

load_dotenv()

from aiogram import Bot, Dispatcher, F  # noqa: E402
from aiogram.filters import Command, CommandStart  # noqa: E402
from aiogram.types import (CallbackQuery, FSInputFile, InlineKeyboardButton,  # noqa: E402
                           InlineKeyboardMarkup, KeyboardButton, Message, ReplyKeyboardMarkup)
from aiogram.enums import ChatAction  # noqa: E402

import ai  # noqa: E402
import db  # noqa: E402
import docgen  # noqa: E402
import estimate  # noqa: E402
from i18n import t  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("bot")

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ALLOWED = {int(x) for x in os.getenv("ALLOWED_USERS", "").replace(" ", "").split(",") if x}
ADMINS = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x}
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "100"))
MAX_FILE = 20 * 1024 * 1024
docgen.COMPANY_NAME = os.getenv("COMPANY_NAME", "")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()
estimate.load_prices()

LANG_KB = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
    InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang:uz"),
    InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
]])

MODES = {"btn_calc": "calc", "btn_files": "files", "btn_estimate": "estimate", "btn_docs": "docs"}
MODE_PREFIX = {  # подсказка модели, в каком разделе пользователь
    "calc": "[Раздел: расчёты] ", "files": "[Раздел: анализ файлов] ",
    "estimate": "[Раздел: смета] ", "docs": "[Раздел: документы] ", "chat": "",
}


def menu(lang):
    return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text=t("btn_calc", lang)), KeyboardButton(text=t("btn_files", lang))],
        [KeyboardButton(text=t("btn_estimate", lang)), KeyboardButton(text=t("btn_docs", lang))],
        [KeyboardButton(text=t("btn_new", lang)), KeyboardButton(text=t("btn_lang", lang))],
    ])


def button_key(text):
    """Определяет, какая кнопка нажата (на любом языке)."""
    from i18n import T
    for key in list(MODES) + ["btn_new", "btn_lang"]:
        if text in T[key].values():
            return key
    return None


async def allowed(m: Message) -> bool:
    db.upsert_user(m.from_user.id, m.from_user.full_name)
    if ALLOWED and m.from_user.id not in ALLOWED and m.from_user.id not in ADMINS:
        await m.answer(t("no_access", db.get_lang(m.from_user.id), uid=m.from_user.id))
        return False
    return True


async def send_long(m: Message, text: str):
    for i in range(0, len(text), 4000):
        chunk = text[i:i + 4000]
        try:
            await m.answer(chunk, parse_mode="Markdown")
        except Exception:
            await m.answer(chunk)  # если Markdown сломался — отправляем как есть


async def process(m: Message, content, history_text: str, smart: bool):
    uid = m.from_user.id
    lang = db.get_lang(uid)
    if uid not in ADMINS and db.requests_today(uid) >= DAILY_LIMIT:
        await m.answer(t("limit", lang))
        return
    status = await m.answer(t("reading_file" if smart else "thinking", lang))
    await bot.send_chat_action(m.chat.id, ChatAction.TYPING)
    try:
        answer, files, usage = await ai.ask(db.get_history(uid), content, lang, use_smart=smart)
    except Exception:
        log.exception("AI error")
        await status.edit_text(t("error", lang))
        return
    for model, i, o in usage:
        db.log_usage(uid, model, i, o)
    db.add_history(uid, "user", history_text)
    db.add_history(uid, "assistant", answer or "(файл)")
    await status.delete()
    if answer:
        await send_long(m, answer)
    for f in files:
        await m.answer_document(FSInputFile(f))


# ---------- команды ----------
@dp.message(CommandStart())
async def start(m: Message):
    if not await allowed(m):
        return
    await m.answer(t("choose_lang", "ru"), reply_markup=LANG_KB)


@dp.callback_query(F.data.startswith("lang:"))
async def set_lang(c: CallbackQuery):
    lang = c.data.split(":")[1]
    db.upsert_user(c.from_user.id, c.from_user.full_name)
    db.set_lang(c.from_user.id, lang)
    await c.message.answer(t("welcome", lang), reply_markup=menu(lang))
    await c.answer()


@dp.message(Command("new"))
async def new_chat(m: Message):
    db.clear_history(m.from_user.id)
    db.set_mode(m.from_user.id, "chat")
    await m.answer(t("new_chat", db.get_lang(m.from_user.id)))


@dp.message(Command("stats"))
async def stats(m: Message):
    if m.from_user.id not in ADMINS:
        return
    s = db.stats()
    lines = [f"Пользователей всего: {s['users_total']}", f"Активных за 30 дней: {s['active_users']}"]
    for r in s["by_model"]:
        lines.append(f"{r['model']}: {r['requests']} вызовов, вход {r['input_tokens']:,} / выход {r['output_tokens']:,} токенов")
    await m.answer("\n".join(lines))


@dp.message(Command("reload_prices"))
async def reload_prices(m: Message):
    if m.from_user.id not in ADMINS:
        return
    p = estimate.load_prices()
    await m.answer(f"Прайс перезагружен, дата: {p['updated']}")


@dp.message(Command("myid"))
async def myid(m: Message):
    await m.answer(f"Ваш Telegram ID: {m.from_user.id}")


# ---------- файлы ----------
async def _download(file_id) -> bytes:
    f = await bot.get_file(file_id)
    data = await bot.download_file(f.file_path)
    return data.read()


@dp.message(F.photo)
async def on_photo(m: Message):
    if not await allowed(m):
        return
    photo = m.photo[-1]  # наибольшее разрешение
    raw = await _download(photo.file_id)
    caption = m.caption or "Проанализируй изображение: что на нём, найди ошибки и замечания."
    content = [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                     "data": base64.b64encode(raw).decode()}},
        {"type": "text", "text": caption},
    ]
    await process(m, content, f"[фото] {caption}", smart=True)


@dp.message(F.document)
async def on_document(m: Message):
    if not await allowed(m):
        return
    lang = db.get_lang(m.from_user.id)
    doc = m.document
    if doc.file_size and doc.file_size > MAX_FILE:
        await m.answer(t("too_big", lang))
        return
    mime = (doc.mime_type or "").lower()
    name = (doc.file_name or "").lower()
    caption = m.caption or "Проанализируй документ: суть, ошибки, несоответствия, замечания."
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
async def on_text(m: Message):
    if not await allowed(m):
        return
    uid = m.from_user.id
    lang = db.get_lang(uid)
    key = button_key(m.text)
    if key == "btn_lang":
        await m.answer(t("choose_lang", lang), reply_markup=LANG_KB)
        return
    if key == "btn_new":
        db.clear_history(uid)
        db.set_mode(uid, "chat")
        await m.answer(t("new_chat", lang))
        return
    if key in MODES:
        mode = MODES[key]
        db.set_mode(uid, mode)
        await m.answer(t("hint_" + mode, lang))
        return
    mode = db.get_mode(uid)
    text = MODE_PREFIX.get(mode, "") + m.text
    await process(m, text, text, smart=(mode == "docs"))


async def main():
    log.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
