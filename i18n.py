"""Тексты интерфейса: ru, uz (латиница), uzc (кириллица — автоматически из uz), en."""
from translit import to_cyr

LANGS = ("ru", "uz", "uzc", "en")

T = {
    "choose_lang": {
        "ru": "Выберите язык / Tilni tanlang / Тилни танланг / Choose language",
        "uz": "Выберите язык / Tilni tanlang / Тилни танланг / Choose language",
        "en": "Выберите язык / Tilni tanlang / Тилни танланг / Choose language",
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
    "btn_objects": {"ru": "🏗 Объекты", "uz": "🏗 Obyektlar", "en": "🏗 Projects"},
    "hint_objects": {
        "ru": ("Учёт денег клиента по объектам. Примеры:\n"
               "• «Новый объект Юнусабад, клиент Каримов А., бюджет 1,2 млрд, наше вознаграждение 10%»\n"
               "• «Юнусабад: получили аванс 20 000 $ по курсу 12 850»\n"
               "• «Юнусабад: бетон B25 25 м³ по 850 000, доставка 1,5 млн»\n"
               "• Фото чека или накладной с подписью «Юнусабад»\n"
               "• «Сколько осталось по Юнусабаду?»\n"
               "• «Отчёт клиенту по Юнусабаду за октябрь на английском»\n"
               "• «Удали операцию 15»\n\n"
               "Участники и стройка:\n"
               "• «Ссылка-приглашение клиенту на Юнусабад»\n"
               "• «Ссылка для ustalar на Юнусабад, бригада Алишера»\n"
               "• «Кто работал сегодня на Юнусабаде?»\n"
               "• /setlocation — задать точку объекта для проверки Keldim\n"
               "• /link Юнусабад — в группе объекта, чтобы привязать её"),
        "uz": ("Obyektlar bo'yicha mijoz mablag'lari hisobi. Misollar:\n"
               "• «Yangi obyekt Yunusobod, mijoz Karimov A., byudjet 1,2 mlrd, mukofotimiz 10%»\n"
               "• «Yunusobod: 20 000 $ avans oldik, kurs 12 850»\n"
               "• «Yunusobod: beton B25 25 m³ 850 000 dan, yetkazish 1,5 mln»\n"
               "• Chek yoki yuk xati rasmi, izohida «Yunusobod»\n"
               "• «Yunusobod bo'yicha qancha qoldi?»\n"
               "• «Yunusobod bo'yicha oktyabr uchun mijozga hisobot»\n"
               "• «15-operatsiyani o'chir»\n\n"
               "Ishtirokchilar va qurilish:\n"
               "• «Yunusobod uchun mijozga taklif havolasi»\n"
               "• «Yunusobod ustalari uchun havola, Alisher brigadasi»\n"
               "• «Bugun Yunusobodda kim ishladi?»\n"
               "• /setlocation — Keldim tekshiruvi uchun obyekt nuqtasi\n"
               "• /link Yunusobod — obyekt guruhida, guruhni bog'lash uchun"),
        "en": ("Client funds tracking per project. Examples:\n"
               "• “New project Yunusabad, client Karimov A., budget 1.2 bn, our fee 10%”\n"
               "• “Yunusabad: received 20,000 USD advance at rate 12,850”\n"
               "• “Yunusabad: concrete B25 25 m³ at 850,000, delivery 1.5 mln”\n"
               "• Photo of a receipt or delivery note captioned “Yunusabad”\n"
               "• “What's left on Yunusabad?”\n"
               "• “Client report for Yunusabad for October in English”\n"
               "• “Delete operation 15”\n\n"
               "People and site:\n"
               "• “Invite link for the client on Yunusabad”\n"
               "• “Invite link for workers on Yunusabad, Alisher's crew”\n"
               "• “Who worked on Yunusabad today?”\n"
               "• /setlocation — set the site point for check-in validation\n"
               "• /link Yunusabad — in the project group, to link it"),
    },
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

T.update({
    "btn_checkin": {"ru": "✅ Пришёл", "uz": "✅ Keldim", "en": "✅ Check in"},
    "btn_checkout": {"ru": "🏁 Ушёл", "uz": "🏁 Ketdim", "en": "🏁 Check out"},
    "btn_photo": {"ru": "📸 Фото-отчёт", "uz": "📸 Foto-hisobot", "en": "📸 Photo report"},
    "btn_attendance": {"ru": "👷 Davomat", "uz": "👷 Davomat", "en": "👷 Attendance"},
    "btn_today": {"ru": "📊 Отчёт за сегодня", "uz": "📊 Bugungi hisobot", "en": "📊 Today's report"},
    "btn_archive": {"ru": "🖼 Фото-архив", "uz": "🖼 Foto-arxiv", "en": "🖼 Photo archive"},
    "btn_finance": {"ru": "💰 Финансы", "uz": "💰 Moliya", "en": "💰 Finance"},
    "btn_done": {"ru": "✅ Готово", "uz": "✅ Tayyor", "en": "✅ Done"},
    "btn_skip": {"ru": "⏭ Пропустить", "uz": "⏭ O'tkazib yuborish", "en": "⏭ Skip"},
    "btn_cancel": {"ru": "❌ Отмена", "uz": "❌ Bekor qilish", "en": "❌ Cancel"},
    "btn_location": {"ru": "📍 Отправить локацию", "uz": "📍 Lokatsiyani yuborish", "en": "📍 Send location"},

    "role_client": {"ru": "клиент", "uz": "mijoz", "en": "client"},
    "role_foreman": {"ru": "прораб", "uz": "prorab", "en": "site manager"},
    "role_designer": {"ru": "дизайнер", "uz": "dizayner", "en": "designer"},
    "role_drafter": {"ru": "чертёжник", "uz": "chertyojchi", "en": "draftsman"},
    "role_supervisor": {"ru": "технадзор", "uz": "texnadzor", "en": "technical supervisor"},
    "role_worker": {"ru": "уста", "uz": "usta", "en": "worker"},

    "welcome_worker": {
        "ru": ("👷 Здравствуйте! Здесь вы отмечаете приход и уход и отправляете фото работы.\n\n"
               "✅ Пришёл — в начале дня: локация + селфи\n"
               "🏁 Ушёл — в конце дня: локация + что сделано + фото\n"
               "📸 Фото-отчёт — фото работы в любое время"),
        "uz": ("👷 Assalomu alaykum! Bu yerda kelish-ketishni belgilaysiz va ish rasmlarini yuborasiz.\n\n"
               "✅ Keldim — kun boshida: lokatsiya + selfi\n"
               "🏁 Ketdim — kun oxirida: lokatsiya + nima qilindi + rasm\n"
               "📸 Foto-hisobot — istalgan vaqtda ish rasmlari"),
        "en": ("👷 Hello! Here you check in and out and send photos of your work.\n\n"
               "✅ Check in — at the start of the day: location + selfie\n"
               "🏁 Check out — at the end of the day: location + what was done + photos\n"
               "📸 Photo report — work photos any time"),
    },
    "welcome_client": {
        "ru": ("🏠 Здравствуйте! Здесь видно, что происходит на вашем объекте.\n\n"
               "📊 Отчёт за сегодня — кто работал, что сделано, расходы, фото\n"
               "💰 Финансы — получено, потрачено, остаток\n"
               "🖼 Фото-архив — фото по датам\n\n"
               "Каждый день в {time} отчёт приходит автоматически. Вопросы пишите сюда текстом."),
        "uz": ("🏠 Assalomu alaykum! Bu yerda obyektingizda nima bo'layotganini ko'rasiz.\n\n"
               "📊 Bugungi hisobot — kim ishladi, nima qilindi, xarajatlar, rasmlar\n"
               "💰 Moliya — olingan, sarflangan, qoldiq\n"
               "🖼 Foto-arxiv — sanalar bo'yicha rasmlar\n\n"
               "Har kuni {time} da hisobot avtomatik keladi. Savollarni shu yerga yozing."),
        "en": ("🏠 Hello! Here you can see what is happening on your project.\n\n"
               "📊 Today's report — who worked, what was done, expenses, photos\n"
               "💰 Finance — received, spent, balance\n"
               "🖼 Photo archive — photos by date\n\n"
               "Every day at {time} the report arrives automatically. Ask questions here in text."),
    },
    "welcome_member": {
        "ru": "👋 Здравствуйте! Вы участник объекта. Используйте кнопки меню или пишите вопросы текстом.",
        "uz": "👋 Assalomu alaykum! Siz obyekt ishtirokchisisiz. Menyu tugmalaridan foydalaning yoki savolingizni yozing.",
        "en": "👋 Hello! You are a project participant. Use the menu buttons or type your questions.",
    },

    "ask_loc_in": {"ru": "Отправьте текущую локацию кнопкой «📍 Отправить локацию» ниже.",
                   "uz": "Pastdagi «📍 Lokatsiyani yuborish» tugmasi orqali joriy lokatsiyani yuboring.",
                   "en": "Send your current location with the “📍 Send location” button below."},
    "ask_loc_out": {"ru": "Чтобы отметить уход, отправьте локацию кнопкой «📍 Отправить локацию».",
                    "uz": "Ketishni belgilash uchun «📍 Lokatsiyani yuborish» tugmasini bosing.",
                    "en": "To check out, send your location with the “📍 Send location” button."},
    "need_location": {"ru": "Нужна локация — нажмите «📍 Отправить локацию» или «❌ Отмена».",
                      "uz": "Lokatsiya kerak — «📍 Lokatsiyani yuborish» yoki «❌ Bekor qilish» tugmasini bosing.",
                      "en": "Location needed — press “📍 Send location” or “❌ Cancel”."},
    "ask_selfie": {"ru": "Теперь сделайте селфи на объекте и отправьте фото 🤳",
                   "uz": "Endi obyektda selfi tushib, rasmni yuboring 🤳",
                   "en": "Now take a selfie on site and send the photo 🤳"},
    "need_photo": {"ru": "Нужно фото. Отправьте селфи или нажмите «❌ Отмена».",
                   "uz": "Rasm kerak. Selfi yuboring yoki «❌ Bekor qilish» tugmasini bosing.",
                   "en": "A photo is needed. Send a selfie or press “❌ Cancel”."},
    "checkin_ok": {"ru": "✅ Приход отмечен: {obj}, {time}. Хорошего дня!",
                   "uz": "✅ Kelish belgilandi: {obj}, {time}. Ishingizga omad!",
                   "en": "✅ Checked in: {obj}, {time}. Have a good day!"},
    "far_warn": {"ru": "⚠️ Вы в {dist} м от точки объекта — отметка помечена, прораб увидит это в отчёте.",
                 "uz": "⚠️ Siz obyekt nuqtasidan {dist} m uzoqdasiz — belgi qo'yildi, prorab hisobotda ko'radi.",
                 "en": "⚠️ You are {dist} m from the site point — the check-in is flagged and the site manager will see it."},
    "already_in": {"ru": "Вы уже отметили приход сегодня. Когда закончите — нажмите «🏁 Ушёл».",
                   "uz": "Bugun kelishni allaqachon belgilagansiz. Ish tugagach «🏁 Ketdim» tugmasini bosing.",
                   "en": "You have already checked in today. When you finish, press “🏁 Check out”."},
    "no_open": {"ru": "Нет отметки прихода. Сначала нажмите «✅ Пришёл».",
                "uz": "Kelish belgilanmagan. Avval «✅ Keldim» tugmasini bosing.",
                "en": "No check-in found. Press “✅ Check in” first."},
    "ask_work": {"ru": "Коротко напишите, что сделали сегодня.",
                 "uz": "Bugun nima qilganingizni qisqacha yozing.",
                 "en": "Briefly write what you did today."},
    "ask_work_photos": {"ru": "Пришлите 1–3 фото выполненной работы и нажмите «✅ Готово» (или «⏭ Пропустить»).",
                        "uz": "Bajarilgan ishning 1–3 ta rasmini yuboring va «✅ Tayyor» tugmasini bosing (yoki «⏭ O'tkazib yuborish»).",
                        "en": "Send 1–3 photos of the work and press “✅ Done” (or “⏭ Skip”)."},
    "checkout_ok": {"ru": "🏁 Уход отмечен: {obj}. Сегодня отработано: {hours}. Спасибо!",
                    "uz": "🏁 Ketish belgilandi: {obj}. Bugun ishlangan vaqt: {hours}. Rahmat!",
                    "en": "🏁 Checked out: {obj}. Worked today: {hours}. Thank you!"},
    "not_worker": {"ru": "Отмечать приход могут только ustalar, добавленные на объект. Попросите прораба прислать ссылку-приглашение.",
                   "uz": "Kelishni faqat obyektga qo'shilgan ustalar belgilaydi. Prorabdan taklif havolasini so'rang.",
                   "en": "Only workers added to a project can check in. Ask the site manager for an invite link."},
    "pick_obj": {"ru": "Выберите объект:", "uz": "Obyektni tanlang:", "en": "Choose the project:"},
    "photo_start": {"ru": "Пришлите фото: общий вид и выполненная работа. Можно добавить подпись к фото. Затем нажмите «✅ Готово».",
                    "uz": "Rasmlarni yuboring: umumiy ko'rinish va bajarilgan ish. Rasmga izoh qo'shish mumkin. So'ng «✅ Tayyor» tugmasini bosing.",
                    "en": "Send photos: general view and work done. You can add a caption. Then press “✅ Done”."},
    "photo_got": {"ru": "📥 Фото принимаются… Когда закончите — «✅ Готово».",
                  "uz": "📥 Rasmlar qabul qilinmoqda… Tugatgach — «✅ Tayyor».",
                  "en": "📥 Receiving photos… When finished — “✅ Done”."},
    "photo_saved": {"ru": "✅ Фото-отчёт сохранён: {n} фото ({obj}).",
                    "uz": "✅ Foto-hisobot saqlandi: {n} ta rasm ({obj}).",
                    "en": "✅ Photo report saved: {n} photos ({obj})."},
    "photo_none": {"ru": "Фото не получено, отчёт не сохранён.", "uz": "Rasm olinmadi, hisobot saqlanmadi.",
                   "en": "No photos received, report not saved."},
    "cancelled": {"ru": "Отменено.", "uz": "Bekor qilindi.", "en": "Cancelled."},
    "no_objects": {"ru": "У вас пока нет объектов.", "uz": "Sizda hali obyekt yo'q.", "en": "You have no projects yet."},
    "no_right": {"ru": "Для вашей роли это недоступно.", "uz": "Bu sizning rolingiz uchun mavjud emas.",
                 "en": "This is not available for your role."},
    "joined": {"ru": "✅ Вы добавлены на объект «{obj}» как {role}.", "uz": "✅ Siz «{obj}» obyektiga {role} sifatida qo'shildingiz.",
               "en": "✅ You have been added to “{obj}” as {role}."},
    "joined_notify": {"ru": "👤 {name} присоединился к объекту «{obj}» как {role}.",
                      "uz": "👤 {name} «{obj}» obyektiga {role} sifatida qo'shildi.",
                      "en": "👤 {name} joined “{obj}” as {role}."},
    "invite_bad": {"ru": "Ссылка-приглашение недействительна. Попросите новую.", "uz": "Taklif havolasi yaroqsiz. Yangisini so'rang.",
                   "en": "The invite link is invalid. Ask for a new one."},
    "archive_pick_date": {"ru": "Выберите дату:", "uz": "Sanani tanlang:", "en": "Choose a date:"},
    "archive_none": {"ru": "Фото пока нет.", "uz": "Hozircha rasm yo'q.", "en": "No photos yet."},
    "report_none": {"ru": "Сегодня по объекту «{obj}» активности не было.", "uz": "Bugun «{obj}» obyektida faollik bo'lmadi.",
                    "en": "No activity on “{obj}” today."},
    "photo_reminder": {"ru": "📸 Напоминание: сегодня нет фото-отчёта по объекту «{obj}». Пришлите фото общего вида и выполненной работы (кнопка «📸 Фото-отчёт»).",
                       "uz": "📸 Eslatma: bugun «{obj}» obyekti bo'yicha foto-hisobot yo'q. Umumiy ko'rinish va bajarilgan ish rasmlarini yuboring («📸 Foto-hisobot» tugmasi).",
                       "en": "📸 Reminder: no photo report for “{obj}” today. Send photos of the general view and work done (“📸 Photo report” button)."},
    "budget_alert": {"ru": "⚠️ Превышен бюджет объекта «{obj}»: использовано {used} при бюджете {budget}.",
                     "uz": "⚠️ «{obj}» obyekti byudjetdan oshdi: byudjet {budget}, sarflangan {used}.",
                     "en": "⚠️ Budget exceeded on “{obj}”: {used} used against a budget of {budget}."},
    "funds_alert": {"ru": "⚠️ По объекту «{obj}» закончились средства клиента: перерасход {sum}. Нужен следующий платёж.",
                    "uz": "⚠️ «{obj}» obyektida mijoz mablag'i tugadi: ortiqcha sarf {sum}. Keyingi to'lov kerak.",
                    "en": "⚠️ Client funds on “{obj}” are used up: overspend {sum}. The next payment is needed."},
    "far_alert": {"ru": "⚠️ {name} отметил приход вне объекта «{obj}»: {dist} м от точки.",
                  "uz": "⚠️ {name} «{obj}» obyektidan tashqarida keldim belgiladi: nuqtadan {dist} m.",
                  "en": "⚠️ {name} checked in outside “{obj}”: {dist} m from the site point."},
    "setloc_ask": {"ru": "Отправьте точку объекта «{obj}»: 📎 → Локация (можно выбрать точку на карте) или кнопкой ниже, если вы на объекте.",
                   "uz": "«{obj}» obyekti nuqtasini yuboring: 📎 → Lokatsiya (xaritadan tanlash mumkin) yoki obyektda bo'lsangiz pastdagi tugma.",
                   "en": "Send the point of “{obj}”: 📎 → Location (you can pick a point on the map) or the button below if you are on site."},
    "setloc_ok": {"ru": "📍 Локация объекта «{obj}» сохранена. Радиус отметки: {r} м.",
                  "uz": "📍 «{obj}» obyekti lokatsiyasi saqlandi. Belgilash radiusi: {r} m.",
                  "en": "📍 Location of “{obj}” saved. Check-in radius: {r} m."},
    "group_linked": {"ru": "✅ Эта группа привязана к объекту «{obj}». Обращайтесь ко мне через @ или ответом на моё сообщение.",
                     "uz": "✅ Bu guruh «{obj}» obyektiga bog'landi. Menga @ orqali yoki xabarimga javob bilan murojaat qiling.",
                     "en": "✅ This group is linked to “{obj}”. Mention me with @ or reply to my message."},
    "group_hint": {"ru": "Привяжите группу к объекту: /link <название объекта> (прораб или админ).",
                   "uz": "Guruhni obyektga bog'lang: /link <obyekt nomi> (prorab yoki admin).",
                   "en": "Link this group to a project: /link <project name> (site manager or admin)."},
    "private_only": {"ru": "Это делается в личном чате с ботом.", "uz": "Bu bot bilan shaxsiy chatda qilinadi.",
                     "en": "Please do this in a private chat with the bot."},
})


def t(key, lang, **kw):
    if lang == "uzc":
        s = to_cyr(T[key].get("uz") or T[key]["ru"])
    else:
        s = T[key].get(lang) or T[key]["ru"]
    return s.format(**kw) if kw else s


def role_name(role, lang):
    return t("role_" + role, lang)


def all_variants(key):
    """Текст кнопки на всех языках — чтобы понять, какая кнопка нажата."""
    return {t(key, lang) for lang in LANGS}
