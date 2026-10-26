"""Работа с Claude API: системный промпт, инструменты (калькуляторы, смета, документы), цикл tool use."""
import json
import logging
import os

from anthropic import AsyncAnthropic

import datetime as dt
from zoneinfo import ZoneInfo

import calculators
import docgen
import estimate
import db
import ledger
import roles
import site_ops

log = logging.getLogger(__name__)
client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODEL_FAST = os.getenv("MODEL_FAST", "claude-haiku-5-5")     # обычные вопросы и расчёты
MODEL_SMART = os.getenv("MODEL_SMART", "claude-sonnet-5-5")  # анализ файлов и документы
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4000"))

LANG_NAME = {"ru": "русском", "uz": "узбекском (латиница)", "uzc": "узбекском (кириллица)", "en": "английском"}
BOT_USERNAME = ""  # задаётся ботом при запуске

SYSTEM = """Ты — AI-помощник архитектурно-строительной компании в Узбекистане. Пользователи: архитекторы, ГИПы, прорабы, инженеры.

Правила:
1. Отвечай на {lang_name} языке, если пользователь сам не пишет на другом — тогда отвечай на языке его сообщения.
2. Кратко и по делу, как опытный коллега. Для Telegram: без таблиц Markdown, используй короткие списки, *жирный* для итогов.
3. ЛЮБЫЕ числа (объёмы, массы, площади, нагрузки, количество) получай ТОЛЬКО через инструменты calc_*. Не считай в уме. Если данных не хватает — спроси недостающие размеры, не выдумывай.
4. Сметы — только через get_price_catalog и make_estimate. Если у позиции нет цены (items_without_price) — прямо скажи, что цена не заполнена в прайсе, не придумывай цену.
5. Нормы: в Узбекистане действуют ШНК (шаҳарсозлик нормалари ва қоидалари) и КМК, частично СНиП/ГОСТ. Ссылайся на норму, только если уверен в номере документа; если не уверен — так и скажи и посоветуй проверить актуальную редакцию.
6. Анализ чертежей/фото: перечисли найденные замечания по пунктам (что, где, почему важно, что сделать), отдельно — что не видно на изображении и нужно уточнить. Не утверждай того, чего не видно.
7. Документы (ТЗ, акт, письмо, договор подряда, пояснительная записка, смета): сначала уточни ключевые данные (стороны, объект, суммы, сроки), если их нет; затем вызови create_document. Документ составляй на языке, который просит пользователь (по умолчанию — язык диалога). Пустые поля оставляй как «__________».
8. Конструктивные расчёты (несущая способность, сечения, сейсмика) ты не заменяешь: давай ориентир и указывай, что окончательный расчёт — за инженером-конструктором. Объекты в Узбекистане часто находятся в сейсмичных районах (7–9 баллов) — помни об этом.
9. Учёт по объектам (фирма строит за счёт клиента): создавай объекты (create_object), записывай поступления от клиента (type=income: advance/payment) и расходы (type=expense: materials, works, equipment, transport, design, permits, other) через add_transactions.
   - Суммы бери ТОЛЬКО из слов пользователя или с фото чека/накладной. Ничего не додумывай. Не ясна сумма, объект или это приход/расход — спроси.
   - Если указаны количество и цена — передавай qty, unit, price (сумму посчитает код). Иначе amount.
   - «млн» = 1 000 000, «тыс»/«к» = 1 000. Валюты только UZS и USD; объект ведётся в одной из них (currency при создании, по умолчанию UZS).
   - Операция в другой валюте, чем объект (например, аванс в долларах при объекте в сумах): передай currency и rate — курс в сумах за 1 USD. Курс берёшь ТОЛЬКО от пользователя, сам не подставляй и не ищи. Курс не назван — спроси: «По какому курсу пересчитать?»
   - Чек на фото: перечисли распознанные позиции и итог; если пользователь назвал объект — сразу запиши, иначе спроси объект.
   - После записи всегда коротко подтверди: номера операций, суммы, остаток средств клиента. Ошибочную операцию удаляй delete_transaction по номеру.
   - Объект не назван, а объектов несколько — спроси, к какому отнести. Если объект один — используй его.
   - Отчёт клиенту — client_report (Word и Excel). Язык отчёта — какой попросят (клиент может быть иностранцем), по умолчанию язык диалога. Период — если назван.
   - Остаток и цифры по объекту бери только из object_summary/client_report, не считай сам.
10. Роли и доступ (ТЗ AI Qurilish Nazoratchisi). Роли на объекте: client (mijoz), foreman (prorab), designer, drafter (chertyojchi), supervisor (texnadzor), worker (usta); admin — студия, видит всё.
   - Финансы видят только client, foreman и admin; записывает операции foreman/admin. Ustalar финансы не видят.
   - Davomat видят client, foreman, supervisor. Фото-отчёты видят все роли, кроме ustalar.
   - Инструменты сами проверяют права. Если вернулось «Нет доступа» — вежливо объясни, что для роли это недоступно. Не пытайся обойти.
   - Добавить человека на объект: create_invite (роль + для ustalar можно label — бригада/специальность) и отдай ссылку; человек открывает её в Telegram.
   - Ты советуешь, напоминаешь и контролируешь, но НЕ принимаешь решений о платежах, договорах, остановке работ — их принимают люди.
   - Отклонения фиксируй как факт («цена на 15% выше рынка», «usta отметился в 420 м от объекта»), никого не обвиняй.
   - Конструктив (несущие стены, армирование, газ, электробезопасность) — не давай заключений, направляй к технадзору.
   - Не знаешь ответа по объекту — скажи «не знаю, уточню у специалиста» и подскажи, кого спросить.
Текущий пользователь: {user_ctx}
Сегодня: {today} (Ташкент).
"""

TOOLS = [
    {"name": "calc_area", "description": "Площади помещений и общая площадь.",
     "input_schema": {"type": "object", "properties": {
         "rooms": {"type": "array", "items": {"type": "object", "properties": {
             "name": {"type": "string"}, "length": {"type": "number"}, "width": {"type": "number"}},
             "required": ["length", "width"]}}}, "required": ["rooms"]}},
    {"name": "calc_concrete",
     "description": "Объём бетона. element: slab(length,width,thickness) | strip_foundation(perimeter,width,height) | "
                    "columns(count,section_a,section_b,height) | beam(count,length,section_b,section_h) | custom_volume(volume). Все размеры в метрах.",
     "input_schema": {"type": "object", "properties": {
         "element": {"type": "string", "enum": ["slab", "strip_foundation", "columns", "beam", "custom_volume"]},
         "length": {"type": "number"}, "width": {"type": "number"}, "thickness": {"type": "number"},
         "perimeter": {"type": "number"}, "height": {"type": "number"}, "count": {"type": "integer"},
         "section_a": {"type": "number"}, "section_b": {"type": "number"}, "section_h": {"type": "number"},
         "volume": {"type": "number"}, "reserve_percent": {"type": "number"}}, "required": ["element"]}},
    {"name": "calc_rebar_slab", "description": "Арматурная сетка плиты: длина, масса, число прутков 11,7 м. Размеры в м, шаг и диаметр в мм.",
     "input_schema": {"type": "object", "properties": {
         "length": {"type": "number"}, "width": {"type": "number"}, "spacing_mm": {"type": "number"},
         "diameter_mm": {"type": "number"}, "layers": {"type": "integer"}, "overlap_percent": {"type": "number"}},
         "required": ["length", "width"]}},
    {"name": "calc_rebar_mass", "description": "Масса арматуры по диаметру (мм) и общей длине (м).",
     "input_schema": {"type": "object", "properties": {
         "diameter_mm": {"type": "number"}, "total_length_m": {"type": "number"}},
         "required": ["diameter_mm", "total_length_m"]}},
    {"name": "calc_bricks", "description": "Кирпич и раствор для стены. thickness_bricks: 0.5/1/1.5/2/2.5; brick_type: single|one_and_half|double. openings_area — площадь проёмов, м².",
     "input_schema": {"type": "object", "properties": {
         "wall_length": {"type": "number"}, "wall_height": {"type": "number"},
         "thickness_bricks": {"type": "number"}, "brick_type": {"type": "string", "enum": ["single", "one_and_half", "double"]},
         "openings_area": {"type": "number"}, "reserve_percent": {"type": "number"}},
         "required": ["wall_length", "wall_height"]}},
    {"name": "calc_roof", "description": "Площадь кровли. roof_type: shed|gable|hip. pitch_deg — уклон в градусах, overhang — свес, м.",
     "input_schema": {"type": "object", "properties": {
         "building_length": {"type": "number"}, "building_width": {"type": "number"}, "pitch_deg": {"type": "number"},
         "roof_type": {"type": "string", "enum": ["shed", "gable", "hip"]}, "overhang": {"type": "number"},
         "reserve_percent": {"type": "number"}}, "required": ["building_length", "building_width", "pitch_deg"]}},
    {"name": "calc_insulation", "description": "Толщина утеплителя по требуемому R (м²·°C/Вт) и λ материала (Вт/м·°C), объём на площадь.",
     "input_schema": {"type": "object", "properties": {
         "area_m2": {"type": "number"}, "required_R": {"type": "number"}, "lambda_w_mk": {"type": "number"}},
         "required": ["area_m2", "required_R", "lambda_w_mk"]}},
    {"name": "calc_slab_load", "description": "Упрощённый сбор нагрузок на 1 м² перекрытия. Толщина плиты в м, нагрузки в кПа.",
     "input_schema": {"type": "object", "properties": {
         "slab_thickness": {"type": "number"}, "live_load_kpa": {"type": "number"}, "finishes_kpa": {"type": "number"},
         "partitions_kpa": {"type": "number"}}, "required": ["slab_thickness"]}},
    {"name": "get_price_catalog", "description": "Список позиций прайса (ключи, единицы, есть ли цена) и регионов. Вызывай перед make_estimate.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "make_estimate",
     "description": "Смета. items: [{key, qty}] из прайса или [{name, unit, qty, price}] для своих позиций (price — только если пользователь сам назвал цену). "
                    "region — ключ региона. as_document=true — сформировать Word-файл сметы.",
     "input_schema": {"type": "object", "properties": {
         "items": {"type": "array", "items": {"type": "object"}}, "region": {"type": "string"},
         "contingency_percent": {"type": "number"}, "as_document": {"type": "boolean"},
         "title": {"type": "string"}}, "required": ["items"]}},
    {"name": "create_document",
     "description": "Создать Word-документ (.docx) и отправить пользователю. doc_type: tz|act|letter|contract|explanatory_note|other. "
                    "sections: [{heading, text}] — полный текст документа; пункты списка начинай с '- '. "
                    "table: {columns, rows} — необязательно. signatures: например ['Заказчик','Подрядчик'].",
     "input_schema": {"type": "object", "properties": {
         "title": {"type": "string"}, "doc_type": {"type": "string"},
         "sections": {"type": "array", "items": {"type": "object", "properties": {
             "heading": {"type": "string"}, "text": {"type": "string"}}}},
         "table": {"type": "object"}, "signatures": {"type": "array", "items": {"type": "string"}},
         "city": {"type": "string"}}, "required": ["title", "sections"]}},
    {"name": "create_object", "description": "Создать объект для учёта средств клиента. budget — сумма договора/бюджет (сум), fee_percent — вознаграждение фирмы в % от расходов (0, если нет).",
     "input_schema": {"type": "object", "properties": {
         "name": {"type": "string"}, "client": {"type": "string"}, "address": {"type": "string"},
         "budget": {"type": "number"}, "fee_percent": {"type": "number"},
         "currency": {"type": "string", "enum": ["UZS", "USD"], "description": "валюта учёта объекта"},
         "obj_type": {"type": "string", "description": "kvartira / hovli / ofis / tijorat"},
         "area": {"type": "number", "description": "м²"}, "floors": {"type": "integer"},
         "start_date": {"type": "string"}, "end_date": {"type": "string", "description": "плановое окончание"}},
         "required": ["name"]}},
    {"name": "update_object", "description": "Изменить данные объекта (клиент, адрес, бюджет, процент, статус active/closed, название).",
     "input_schema": {"type": "object", "properties": {
         "object": {"type": "string"}, "name": {"type": "string"}, "client": {"type": "string"}, "address": {"type": "string"},
         "budget": {"type": "number"}, "fee_percent": {"type": "number"}, "status": {"type": "string", "enum": ["active", "closed"]},
         "currency": {"type": "string", "enum": ["UZS", "USD"]}, "obj_type": {"type": "string"},
         "area": {"type": "number"}, "floors": {"type": "integer"}, "start_date": {"type": "string"},
         "end_date": {"type": "string"}, "radius": {"type": "number", "description": "радиус отметки Keldim, м"}},
         "required": ["object"]}},
    {"name": "list_objects", "description": "Список объектов с поступлениями, расходами и остатком.",
     "input_schema": {"type": "object", "properties": {"include_closed": {"type": "boolean"}}}},
    {"name": "add_transactions",
     "description": "Записать операции по объекту. items: [{type: income|expense, category, description, date (ДД.ММ.ГГГГ, по умолчанию сегодня), amount ИЛИ qty+unit+price}]. "
                    "Категории расходов: materials, works, equipment, transport, design, permits, other. Поступлений: advance, payment, other_income.",
     "input_schema": {"type": "object", "properties": {
         "object": {"type": "string", "description": "название или номер объекта"},
         "items": {"type": "array", "items": {"type": "object", "properties": {
             "type": {"type": "string", "enum": ["income", "expense"]}, "category": {"type": "string"},
             "description": {"type": "string"}, "date": {"type": "string"}, "amount": {"type": "number"},
             "qty": {"type": "number"}, "unit": {"type": "string"}, "price": {"type": "number"},
             "currency": {"type": "string", "enum": ["UZS", "USD"], "description": "валюта операции, если отличается от валюты объекта"},
             "rate": {"type": "number", "description": "курс: сумов за 1 USD, только со слов пользователя"},
             "paid_by": {"type": "string", "enum": ["client", "foreman", "company", "other"],
                         "description": "кто заплатил (kim to'ladi), если сказано"}},
             "required": ["type", "description"]}}}, "required": ["object", "items"]}},
    {"name": "delete_transaction", "description": "Удалить ошибочную операцию по её номеру.",
     "input_schema": {"type": "object", "properties": {"transaction_id": {"type": "integer"}}, "required": ["transaction_id"]}},
    {"name": "list_transactions", "description": "Последние операции по объекту (с номерами). Даты ДД.ММ.ГГГГ.",
     "input_schema": {"type": "object", "properties": {
         "object": {"type": "string"}, "last": {"type": "integer"}, "date_from": {"type": "string"}, "date_to": {"type": "string"}},
         "required": ["object"]}},
    {"name": "object_summary", "description": "Сводка по объекту: бюджет, получено, израсходовано, вознаграждение, остаток, расходы по статьям.",
     "input_schema": {"type": "object", "properties": {
         "object": {"type": "string"}, "date_from": {"type": "string"}, "date_to": {"type": "string"}}, "required": ["object"]}},
    {"name": "client_report", "description": "Сформировать отчёт клиенту об использовании средств (Word и/или Excel) и отправить пользователю. language: ru|uz|uzc|en.",
     "input_schema": {"type": "object", "properties": {
         "object": {"type": "string"}, "date_from": {"type": "string"}, "date_to": {"type": "string"},
         "language": {"type": "string", "enum": ["ru", "uz", "uzc", "en"]},
         "formats": {"type": "array", "items": {"type": "string", "enum": ["docx", "xlsx"]}}}, "required": ["object"]}},
    {"name": "create_invite", "description": "Ссылка-приглашение на объект для роли: client, foreman, designer, drafter, supervisor, worker. label — бригада/специальность (для ustalar).",
     "input_schema": {"type": "object", "properties": {
         "object": {"type": "string"}, "role": {"type": "string", "enum": list(roles.ROLES)}, "label": {"type": "string"}},
         "required": ["object", "role"]}},
    {"name": "list_participants", "description": "Участники объекта и их роли.",
     "input_schema": {"type": "object", "properties": {"object": {"type": "string"}}, "required": ["object"]}},
    {"name": "remove_participant", "description": "Убрать участника с объекта (по имени или ID), можно только одну роль.",
     "input_schema": {"type": "object", "properties": {
         "object": {"type": "string"}, "person": {"type": "string"}, "role": {"type": "string"}}, "required": ["object", "person"]}},
    {"name": "attendance_report", "description": "Davomat за день: кто пришёл, во сколько, сколько часов, кто не пришёл, отметки вне объекта. date ДД.ММ.ГГГГ, по умолчанию сегодня.",
     "input_schema": {"type": "object", "properties": {"object": {"type": "string"}, "date": {"type": "string"}}, "required": ["object"]}},
    {"name": "daily_report", "description": "Отправить пользователю ежедневный отчёт по объекту (davomat, работы, расходы, фото) за дату.",
     "input_schema": {"type": "object", "properties": {"object": {"type": "string"}, "date": {"type": "string"}}, "required": ["object"]}},
    {"name": "photo_archive", "description": "Отправить пользователю фото-отчёты объекта за дату (или список дат с фото, если дата не указана).",
     "input_schema": {"type": "object", "properties": {"object": {"type": "string"}, "date": {"type": "string"}}, "required": ["object"]}},
    {"name": "get_receipts", "description": "Отправить пользователю фото чеков по номерам операций или за период.",
     "input_schema": {"type": "object", "properties": {
         "object": {"type": "string"}, "transaction_ids": {"type": "array", "items": {"type": "integer"}},
         "date_from": {"type": "string"}, "date_to": {"type": "string"}}, "required": ["object"]}},
]

WRITE_TOOLS = {"create_object", "update_object", "add_transactions", "delete_transaction", "create_invite",
               "remove_participant"}


def user_context(uid, name, lang="ru"):
    status = "админ студии (видит всё)" if roles.is_admin(uid) else ("сотрудник студии" if roles.is_staff(uid) else "внешний участник")
    rs = []
    for oid, role, label in roles.roles_of(uid):
        try:
            rs.append(f"{ledger.find_object(oid)['name']} — {role}" + (f" ({label})" if label else ""))
        except ValueError:
            pass
    return f"{name} (ID {uid}), {status}; роли на объектах: " + ("; ".join(rs) if rs else "нет")


def _date(d):
    return ledger._parse_date(d) if d else site_ops.today()


def _run_tool(name, args, out, user=None):
    """out — «исходящие»: files (документы), messages (текст+фото), notify (уведомления другим)."""
    user = user or {}
    uid, uname = user.get("id"), user.get("name", "")
    files_out = out["files"]
    try:
        res = _object_tool(name, args, out, uid, uname, user)
        if res is not None:
            if name in WRITE_TOOLS and "error" not in res:
                oid = res.get("object_id") or res.get("id")
                db.audit(uid, uname, oid if isinstance(oid, int) else None, name,
                         json.dumps(args, ensure_ascii=False, default=str))
            return res
        if name in calculators.CALCULATORS:
            return calculators.CALCULATORS[name](**args)
        if name == "get_price_catalog":
            return estimate.price_catalog()
        if name == "make_estimate":
            est = estimate.make_estimate(args["items"], args.get("region", "tashkent"),
                                         args.get("contingency_percent", 5))
            if args.get("as_document"):
                files_out.append(docgen.estimate_to_document(est, args.get("title", "Смета")))
                est["document"] = "создан и будет отправлен пользователю"
            return est
        if name == "create_document":
            path = docgen.create_document(args["title"], args["sections"], args.get("doc_type", "other"),
                                          args.get("table"), args.get("signatures"), args.get("city", "Ташкент"))
            files_out.append(path)
            return {"status": "ok", "file": os.path.basename(path), "note": "файл будет отправлен пользователю"}
        return {"error": f"unknown tool {name}"}
    except PermissionError as e:
        return {"error": str(e)}
    except Exception as e:  # отдаём ошибку модели, чтобы она переспросила данные
        log.exception("tool %s failed", name)
        return {"error": str(e)}


def _obj(ref, uid, cap):
    o = ledger.find_object(ref)
    roles.require(uid, o["id"], cap)
    return o


def _object_tool(name, args, out, uid, uname, user):
    """Инструменты объектов с проверкой прав. None — инструмент не из этой группы."""
    if name == "create_object":
        if not roles.is_staff(uid):
            raise PermissionError("Нет доступа: объекты создают сотрудники студии.")
        o = ledger.create_object(**args)
        if not roles.is_admin(uid):
            roles.add_participant(o["id"], uid, "foreman", "", uid)
        return {**o, "object_id": o["id"], "note": "создатель добавлен прорабом объекта" if not roles.is_admin(uid) else ""}
    if name == "update_object":
        o = _obj(args.pop("object"), uid, "manage")
        r = ledger.update_object(o["id"], **args)
        return {**r, "object_id": o["id"]}
    if name == "list_objects":
        ids = roles.objects_with(uid)
        fin = set(roles.objects_with(uid, "finance_view"))
        res = []
        for o in ledger.list_objects(args.get("include_closed", False), ids=ids):
            if o["id"] not in fin:
                o = {k: o[k] for k in ("id", "name", "client", "status")}
            o["my_roles"] = sorted(roles.object_roles(uid, o["id"])) or (["admin"] if roles.is_admin(uid) else [])
            res.append(o)
        return {"objects": res}
    if name == "add_transactions":
        o = _obj(args["object"], uid, "finance_edit")
        r = ledger.add_transactions(o["id"], args["items"], uid, uname, receipt_file_id=user.get("photo_file_id"))
        if r.get("budget_exceeded"):
            out["notify"].append({"to": roles.users_with_role(o["id"], "client") + list(roles.ADMINS),
                                  "key": "budget_alert", "obj": o["name"],
                                  "used": f"{ledger._money(r['budget_exceeded']['used'], o['currency'])} {o['currency']}",
                                  "budget": f"{ledger._money(r['budget_exceeded']['budget'], o['currency'])} {o['currency']}"})
        if r.get("client_funds_negative") is not None:
            out["notify"].append({"to": roles.users_with_role(o["id"], "client", "foreman") + list(roles.ADMINS),
                                  "key": "funds_alert", "obj": o["name"],
                                  "sum": f"{ledger._money(-r['client_funds_negative'], o['currency'])} {o['currency']}"})
        return r
    if name == "delete_transaction":
        oid = ledger.tx_object_id(args["transaction_id"])
        roles.require(uid, oid, "finance_edit")
        return {**ledger.delete_transaction(args["transaction_id"]), "object_id": oid}
    if name == "list_transactions":
        o = _obj(args.pop("object"), uid, "finance_view")
        return ledger.list_transactions(o["id"], **args)
    if name == "object_summary":
        o = _obj(args.pop("object"), uid, "finance_view")
        return ledger.summary(o["id"], **args)
    if name == "client_report":
        o = _obj(args["object"], uid, "finance_view")
        rep = ledger.client_report(o["id"], args.get("date_from"), args.get("date_to"),
                                   args.get("language", "ru"), args.get("formats") or ["docx", "xlsx"],
                                   company=docgen.COMPANY_NAME)
        out["files"].extend(rep["files"])
        return {"summary": rep["summary"], "files": "отчёт сформирован и будет отправлен пользователю"}
    if name == "create_invite":
        o = _obj(args["object"], uid, "manage")
        code = roles.create_invite(o["id"], args["role"], args.get("label", ""), uid)
        link = f"https://t.me/{BOT_USERNAME}?start=j_{code}" if BOT_USERNAME else f"/start j_{code}"
        return {"object_id": o["id"], "object": o["name"], "role": args["role"], "link": link,
                "note": "ссылка многоразовая: по ней может присоединиться несколько человек с этой ролью"}
    if name == "list_participants":
        o = ledger.find_object(args["object"])
        if not (roles.is_admin(uid) or roles.object_roles(uid, o["id"]) & {"client", "foreman", "supervisor", "designer"}):
            raise PermissionError("Нет доступа: список участников недоступен для вашей роли.")
        return {"object": o["name"], "participants": roles.list_participants(o["id"])}
    if name == "remove_participant":
        o = _obj(args["object"], uid, "manage")
        p = roles.find_participant(o["id"], args["person"])
        n = roles.remove_participant(o["id"], p["user_id"], args.get("role"))
        return {"object_id": o["id"], "removed": p["name"], "roles_removed": n}
    if name == "attendance_report":
        o = ledger.find_object(args["object"])
        date = _date(args.get("date"))
        if roles.can(uid, o["id"], "attendance_view"):
            return {"object": o["name"], "date": date, **site_ops.attendance_day(o["id"], date)}
        if "worker" in roles.object_roles(uid, o["id"]):  # usta видит только себя
            a = site_ops.attendance_day(o["id"], date)
            return {"object": o["name"], "date": date, "me": [c for c in a["came"] if c["user_id"] == uid]}
        raise PermissionError("Нет доступа: davomat недоступен для вашей роли.")
    if name == "daily_report":
        o = _obj(args["object"], uid, "daily_report")
        rep = site_ops.daily_report(o["id"], _date(args.get("date")), user.get("lang", "ru"))
        out["messages"].append({"text": rep["text"], "photos": rep["photos"]})
        return {"status": "отчёт будет отправлен пользователю отдельным сообщением — не пересказывай его целиком"}
    if name == "photo_archive":
        o = _obj(args["object"], uid, "photo_view")
        if not args.get("date"):
            return {"object": o["name"], "dates_with_photos": [{"date": d, "photos": n} for d, n in site_ops.photo_dates(o["id"], 14)]}
        date = _date(args["date"])
        ph = site_ops.photos_on(o["id"], date)
        out["messages"].append({"text": f"🖼 {o['name']} — {dt.date.fromisoformat(date):%d.%m.%Y}",
                                "photos": [p["file_id"] for p in ph][:30]})
        return {"object": o["name"], "date": date, "photos_sent": min(len(ph), 30)}
    if name == "get_receipts":
        o = _obj(args["object"], uid, "finance_view")
        rows = ledger.receipts(o["id"], args.get("transaction_ids"), args.get("date_from"), args.get("date_to"))
        out["messages"].append({"text": "📎 " + ", ".join(f"№{r['id']} {r['description']}" for r in rows[:30]),
                                "photos": [r["receipt_file_id"] for r in rows][:30]})
        return {"receipts_sent": min(len(rows), 30)}
    return None


def new_outbox():
    return {"files": [], "messages": [], "notify": []}


async def ask(history, user_content, lang="ru", use_smart=False, user=None):
    """history — прошлые сообщения (только текст), user_content — текущее сообщение (str или блоки).
    Возвращает (текст_ответа, outbox, usage_list); outbox = {files, messages, notify}."""
    model = MODEL_SMART if use_smart else MODEL_FAST
    messages = list(history) + [{"role": "user", "content": user_content}]
    files, usage = new_outbox(), []
    user = dict(user or {}, lang=lang)
    ctx = user_context(user["id"], user.get("name", ""), lang) if user.get("id") is not None else "неизвестен"
    system = SYSTEM.format(lang_name=LANG_NAME.get(lang, "русском"), user_ctx=ctx,
                           today=dt.datetime.now(ZoneInfo("Asia/Tashkent")).strftime("%d.%m.%Y"))

    for _ in range(8):  # максимум 8 шагов инструментов
        resp = await client.messages.create(model=model, max_tokens=MAX_TOKENS, system=system,
                                            tools=TOOLS, messages=messages)
        usage.append((model, resp.usage.input_tokens, resp.usage.output_tokens))
        if resp.stop_reason != "tool_use":
            text = "".join(b.text for b in resp.content if b.type == "text").strip()
            return text, files, usage
        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for b in resp.content:
            if b.type == "tool_use":
                out = _run_tool(b.name, b.input, files, user)
                results.append({"type": "tool_result", "tool_use_id": b.id,
                                "content": json.dumps(out, ensure_ascii=False, default=str)})
        messages.append({"role": "user", "content": results})
    return "…", files, usage
