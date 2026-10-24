"""Тексты интерфейса на трёх языках. Ответы AI идут на языке пользователя автоматически."""

T = {
    "choose_lang": {
        "ru": "Выберите язык / Tilni tanlang / Choose language",
        "uz": "Выберите язык / Tilni tanlang / Choose language",
        "en": "Выберите язык / Tilni tanlang / Choose language",
    },
    "welcome": {
        "ru": ("👷 Я AI-помощник для архитекторов и прорабов.\n\n"
               "Что умею:\n"
               "📐 Расчёты — бетон, арматура, кирпич, кровля, утепление, нагрузки, площади\n"
               "📄 Анализ файлов — пришлите фото объекта, чертёж или PDF проекта\n"
               "💰 Сметы — ориентировочная стоимость материалов и работ\n"
               "📝 Документы — ТЗ, акты, письма, договоры подряда, пояснительные записки (Word)\n\n"
               "Выберите раздел или просто напишите вопрос текстом, пришлите фото или PDF."),
        "uz": ("👷 Men arxitektorlar va prorablar uchun AI-yordamchiman.\n\n"
               "Imkoniyatlarim:\n"
               "📐 Hisob-kitoblar — beton, armatura, g'isht, tom, issiqlik izolyatsiyasi, yuklamalar, maydonlar\n"
               "📄 Fayllarni tahlil qilish — obyekt rasmi, chizma yoki loyiha PDF faylini yuboring\n"
               "💰 Smeta — materiallar va ishlarning taxminiy narxi\n"
               "📝 Hujjatlar — TT, dalolatnomalar, xatlar, pudrat shartnomalari, tushuntirish xatlari (Word)\n\n"
               "Bo'limni tanlang yoki savolingizni yozing."),
        "en": ("👷 I'm an AI assistant for architects and site managers.\n\n"
               "What I can do:\n"
               "📐 Calculations — concrete, rebar, bricks, roofing, insulation, loads, areas\n"
               "📄 File review — send a site photo, drawing or project PDF\n"
               "💰 Estimates — approximate cost of materials and works\n"
               "📝 Documents — specs, acts, letters, construction contracts, explanatory notes (Word)\n\n"
               "Pick a section or just type your question."),
    },
    "btn_calc": {"ru": "📐 Расчёты", "uz": "📐 Hisob-kitob", "en": "📐 Calculations"},
    "btn_files": {"ru": "📄 Анализ файла", "uz": "📄 Fayl tahlili", "en": "📄 File review"},
    "btn_estimate": {"ru": "💰 Смета", "uz": "💰 Smeta", "en": "💰 Estimate"},
    "btn_docs": {"ru": "📝 Документ", "uz": "📝 Hujjat", "en": "📝 Document"},
    "btn_new": {"ru": "🔄 Новый диалог", "uz": "🔄 Yangi suhbat", "en": "🔄 New chat"},
    "btn_lang": {"ru": "🌐 Язык", "uz": "🌐 Til", "en": "🌐 Language"},
    "hint_calc": {
        "ru": "Опишите, что посчитать. Например: «Плита 10×12 м, толщина 200 мм — сколько бетона и арматуры Ø12 шаг 200 в 2 слоя?»",
        "uz": "Nimani hisoblash kerakligini yozing. Masalan: «Plita 10×12 m, qalinligi 200 mm — qancha beton va Ø12 armatura, qadam 200, 2 qatlam?»",
        "en": "Describe what to calculate. E.g.: “Slab 10×12 m, 200 mm thick — how much concrete and Ø12 rebar at 200 mm, 2 layers?”",
    },
    "hint_files": {
        "ru": "Пришлите фото, скриншот чертежа или PDF (до 20 МБ). В подписи можно указать, на что обратить внимание. DWG сохраните в PDF.",
        "uz": "Rasm, chizma skrinshoti yoki PDF yuboring (20 MB gacha). Izohda nimaga e'tibor berish kerakligini yozing. DWG ni PDF ga saqlang.",
        "en": "Send a photo, drawing screenshot or PDF (up to 20 MB). Add a caption on what to check. Export DWG to PDF first.",
    },
    "hint_estimate": {
        "ru": "Опишите объект или список работ и регион. Например: «Дом 10×12, 2 этажа, кирпич, Самарканд — примерная смета на коробку».",
        "uz": "Obyekt yoki ishlar ro'yxatini va hududni yozing. Masalan: «Uy 10×12, 2 qavat, g'isht, Samarqand — karkas uchun taxminiy smeta».",
        "en": "Describe the project or list of works and the region. E.g.: “House 10×12, 2 floors, brick, Samarkand — rough estimate for the shell”.",
    },
    "hint_docs": {
        "ru": "Какой документ нужен? Например: «Договор подряда на строительство дома, заказчик — ..., подрядчик — ..., сумма ..., срок ...». Чем больше данных — тем точнее.",
        "uz": "Qanday hujjat kerak? Masalan: «Uy qurilishi uchun pudrat shartnomasi, buyurtmachi — ..., pudratchi — ..., summa ..., muddat ...».",
        "en": "Which document do you need? E.g.: “Construction contract for a house, client — ..., contractor — ..., amount ..., term ...”.",
    },
    "thinking": {"ru": "⏳ Думаю...", "uz": "⏳ O'ylayapman...", "en": "⏳ Thinking..."},
    "reading_file": {"ru": "⏳ Изучаю файл...", "uz": "⏳ Faylni o'rganyapman...", "en": "⏳ Reviewing the file..."},
    "new_chat": {"ru": "Начали новый диалог.", "uz": "Yangi suhbat boshlandi.", "en": "Started a new chat."},
    "no_access": {
        "ru": "Бот работает только для сотрудников. Ваш ID: {uid} — отправьте его администратору.",
        "uz": "Bot faqat xodimlar uchun. ID raqamingiz: {uid} — uni administratorga yuboring.",
        "en": "This bot is for staff only. Your ID: {uid} — send it to the administrator.",
    },
    "too_big": {"ru": "Файл больше 20 МБ — сожмите или разделите.", "uz": "Fayl 20 MB dan katta.", "en": "File is over 20 MB."},
    "bad_type": {
        "ru": "Этот формат не поддерживается. Пришлите JPG/PNG или PDF (DWG экспортируйте в PDF).",
        "uz": "Bu format qo'llab-quvvatlanmaydi. JPG/PNG yoki PDF yuboring.",
        "en": "Unsupported format. Send JPG/PNG or PDF (export DWG to PDF).",
    },
    "limit": {
        "ru": "Дневной лимит запросов исчерпан. Попробуйте завтра.",
        "uz": "Kunlik so'rovlar limiti tugadi. Ertaga urinib ko'ring.",
        "en": "Daily request limit reached. Try again tomorrow.",
    },
    "error": {
        "ru": "Произошла ошибка, попробуйте ещё раз.",
        "uz": "Xatolik yuz berdi, qaytadan urinib ko'ring.",
        "en": "Something went wrong, please try again.",
    },
}


def t(key, lang, **kw):
    s = T[key].get(lang) or T[key]["ru"]
    return s.format(**kw) if kw else s
