"""Работа с Claude API: системный промпт, инструменты (калькуляторы, смета, документы), цикл tool use."""
import json
import logging
import os

from anthropic import AsyncAnthropic

import calculators
import docgen
import estimate

log = logging.getLogger(__name__)
client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODEL_FAST = os.getenv("MODEL_FAST", "claude-haiku-5-5")     # обычные вопросы и расчёты
MODEL_SMART = os.getenv("MODEL_SMART", "claude-sonnet-5-5")  # анализ файлов и документы
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4000"))

LANG_NAME = {"ru": "русском", "uz": "узбекском (латиница)", "en": "английском"}

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
]


def _run_tool(name, args, files_out):
    try:
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
    except Exception as e:  # отдаём ошибку модели, чтобы она переспросила данные
        log.exception("tool %s failed", name)
        return {"error": str(e)}


async def ask(history, user_content, lang="ru", use_smart=False):
    """history — прошлые сообщения (только текст), user_content — текущее сообщение (str или блоки).
    Возвращает (текст_ответа, [пути_к_файлам], usage_list)."""
    model = MODEL_SMART if use_smart else MODEL_FAST
    messages = list(history) + [{"role": "user", "content": user_content}]
    files, usage = [], []
    system = SYSTEM.format(lang_name=LANG_NAME.get(lang, "русском"))

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
                out = _run_tool(b.name, b.input, files)
                results.append({"type": "tool_result", "tool_use_id": b.id,
                                "content": json.dumps(out, ensure_ascii=False)})
        messages.append({"role": "user", "content": results})
    return "…", files, usage
