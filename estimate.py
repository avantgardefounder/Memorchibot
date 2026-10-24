"""Сметы по прайсу из prices.json."""
import json
from pathlib import Path

PRICES_PATH = Path(__file__).with_name("prices.json")
_prices = {}


def load_prices():
    global _prices
    _prices = json.loads(PRICES_PATH.read_text(encoding="utf-8"))
    return _prices


def price_catalog():
    """Короткий список позиций для AI (ключ, название, единица, есть ли цена)."""
    p = _prices or load_prices()
    rows = []
    for group in ("materials", "works"):
        for key, it in p[group].items():
            rows.append({"key": key, "group": group, "name": it["name"],
                         "unit": it["unit"], "has_price": it["price"] > 0})
    return {"currency": p["currency"], "updated": p["updated"],
            "regions": list(p["regions"].keys()), "items": rows}


def make_estimate(items, region="tashkent", contingency_percent=5):
    """items: [{key, qty}] или [{name, unit, qty, price}] для своих позиций."""
    p = _prices or load_prices()
    k = p["regions"].get(region, 1.0)
    lines, total, missing = [], 0.0, []
    for it in items:
        qty = float(it["qty"])
        key = it.get("key")
        if key:
            src = p["materials"].get(key) or p["works"].get(key)
            if not src:
                missing.append(key)
                continue
            name, unit, price = src["name"], src["unit"], src["price"] * k
        else:
            name, unit, price = it["name"], it.get("unit", ""), float(it.get("price", 0))
        if price <= 0:
            missing.append(name)
        s = qty * price
        total += s
        lines.append({"name": name, "unit": unit, "qty": round(qty, 3),
                      "price": round(price), "sum": round(s)})
    cont = total * contingency_percent / 100
    return {
        "region": region, "region_coef": k, "currency": p["currency"],
        "price_list_date": p["updated"], "lines": lines,
        "subtotal": round(total), "contingency_percent": contingency_percent,
        "contingency": round(cont), "total": round(total + cont),
        "items_without_price": missing,
    }
