"""Детерминированные строительные калькуляторы.

AI не считает «в уме»: он вызывает эти функции, поэтому цифры воспроизводимы.
Все размеры — в метрах, если не указано иное.
"""
import math

STEEL_DENSITY_FACTOR = 0.00617  # масса 1 м арматуры, кг = 0.00617 * d(мм)^2

# Кирпич на 1 м² стены (с учётом швов), по толщине стены
BRICKS_PER_M2 = {
    "single": {0.5: 51, 1: 102, 1.5: 153, 2: 204, 2.5: 255},   # одинарный 250x120x65
    "one_and_half": {0.5: 39, 1: 78, 1.5: 117, 2: 156, 2.5: 195},  # полуторный 250x120x88
    "double": {0.5: 26, 1: 52, 1.5: 78, 2: 104, 2.5: 130},     # двойной 250x120x138
}
WALL_THICKNESS_M = {0.5: 0.12, 1: 0.25, 1.5: 0.38, 2: 0.51, 2.5: 0.64}


def _r(x, n=2):
    return round(x, n)


def calc_area(rooms):
    """rooms: [{name, length, width}] -> площадь каждой комнаты и общая."""
    out, total = [], 0.0
    for r in rooms:
        a = float(r["length"]) * float(r["width"])
        total += a
        out.append({"name": r.get("name", ""), "area_m2": _r(a)})
    return {"rooms": out, "total_area_m2": _r(total)}


def calc_concrete(element, reserve_percent=5, **p):
    """element: slab | strip_foundation | columns | beam | custom_volume."""
    if element == "slab":
        v = p["length"] * p["width"] * p["thickness"]
    elif element == "strip_foundation":
        v = p["perimeter"] * p["width"] * p["height"]
    elif element == "columns":
        v = p["count"] * p["section_a"] * p["section_b"] * p["height"]
    elif element == "beam":
        v = p.get("count", 1) * p["length"] * p["section_b"] * p["section_h"]
    elif element == "custom_volume":
        v = p["volume"]
    else:
        raise ValueError("unknown element")
    total = v * (1 + reserve_percent / 100)
    # Ориентировочный расход на 1 м³ бетона класса B20 (М250)
    return {
        "net_volume_m3": _r(v),
        "with_reserve_m3": _r(total),
        "reserve_percent": reserve_percent,
        "approx_materials_B20_per_total": {
            "cement_kg": _r(total * 330, 0),
            "sand_m3": _r(total * 0.45),
            "gravel_m3": _r(total * 0.85),
            "water_l": _r(total * 185, 0),
        },
        "note": "Состав бетона ориентировочный, точный подбор — по лабораторному составу/паспорту БСУ.",
    }


def calc_rebar_slab(length, width, spacing_mm=200, diameter_mm=12, layers=2,
                    overlap_percent=5):
    """Сетка арматуры плиты: стержни в двух направлениях в каждом слое."""
    s = spacing_mm / 1000
    bars_along_length = math.floor(width / s) + 1   # стержни длиной length
    bars_along_width = math.floor(length / s) + 1   # стержни длиной width
    per_layer = bars_along_length * length + bars_along_width * width
    total_len = per_layer * layers * (1 + overlap_percent / 100)
    kg_per_m = STEEL_DENSITY_FACTOR * diameter_mm ** 2
    mass = total_len * kg_per_m
    return {
        "bars_per_layer": {"long_direction": bars_along_length, "short_direction": bars_along_width},
        "total_length_m": _r(total_len, 1),
        "kg_per_m": _r(kg_per_m, 3),
        "total_mass_kg": _r(mass, 1),
        "total_mass_t": _r(mass / 1000, 3),
        "pieces_11_7m": math.ceil(total_len / 11.7),
    }


def calc_rebar_mass(diameter_mm, total_length_m):
    kg = STEEL_DENSITY_FACTOR * diameter_mm ** 2 * total_length_m
    return {"kg_per_m": _r(STEEL_DENSITY_FACTOR * diameter_mm ** 2, 3), "total_mass_kg": _r(kg, 1)}


def calc_bricks(wall_length, wall_height, thickness_bricks=1, brick_type="single",
                openings_area=0.0, reserve_percent=5):
    if thickness_bricks not in WALL_THICKNESS_M:
        raise ValueError("thickness_bricks: 0.5, 1, 1.5, 2, 2.5")
    area = wall_length * wall_height - openings_area
    pcs = area * BRICKS_PER_M2[brick_type][thickness_bricks] * (1 + reserve_percent / 100)
    masonry_vol = area * WALL_THICKNESS_M[thickness_bricks]
    return {
        "net_wall_area_m2": _r(area),
        "bricks_pcs": math.ceil(pcs),
        "masonry_volume_m3": _r(masonry_vol),
        "mortar_m3": _r(masonry_vol * 0.23),
        "pallets_approx": _r(pcs / 300, 1),
        "wall_thickness_m": WALL_THICKNESS_M[thickness_bricks],
    }


def calc_roof(building_length, building_width, pitch_deg, roof_type="gable",
              overhang=0.5, reserve_percent=10):
    a = math.radians(pitch_deg)
    L = building_length + 2 * overhang
    if roof_type == "shed":
        slope = (building_width + 2 * overhang) / math.cos(a)
        area = slope * L
    elif roof_type == "gable":
        slope = (building_width / 2 + overhang) / math.cos(a)
        area = 2 * slope * L
    elif roof_type == "hip":
        # приближение: площадь плана с выносами / cos(угла)
        area = (building_length + 2 * overhang) * (building_width + 2 * overhang) / math.cos(a)
        slope = None
    else:
        raise ValueError("roof_type: shed | gable | hip")
    ridge_h = (building_width / 2) * math.tan(a) if roof_type != "shed" else building_width * math.tan(a)
    return {
        "roof_area_m2": _r(area),
        "with_reserve_m2": _r(area * (1 + reserve_percent / 100)),
        "slope_length_m": _r(slope) if slope else None,
        "ridge_height_m": _r(ridge_h),
    }


def calc_insulation(area_m2, required_R, lambda_w_mk, layer_options_mm=(50, 100, 150, 200)):
    """Толщина утеплителя δ = R·λ. R (м²·°C/Вт) — из теплотехнического расчёта/норм региона."""
    t = required_R * lambda_w_mk
    t_mm = t * 1000
    choose = next((x for x in sorted(layer_options_mm) if x >= t_mm), None)
    if choose is None:
        choose = math.ceil(t_mm / 50) * 50
    return {
        "required_thickness_mm": _r(t_mm, 0),
        "recommended_thickness_mm": choose,
        "volume_m3": _r(area_m2 * choose / 1000),
    }


def calc_slab_load(slab_thickness, live_load_kpa=1.5, finishes_kpa=1.2,
                   partitions_kpa=0.5, concrete_density_kn=25.0,
                   gamma_dead=1.1, gamma_live=1.3):
    """Сбор нагрузок на 1 м² перекрытия (упрощённо)."""
    own = slab_thickness * concrete_density_kn
    dead_n = own + finishes_kpa + partitions_kpa
    dead_d = own * gamma_dead + (finishes_kpa + partitions_kpa) * 1.2
    live_d = live_load_kpa * gamma_live
    return {
        "own_weight_kpa": _r(own),
        "normative_total_kpa": _r(dead_n + live_load_kpa),
        "design_total_kpa": _r(dead_d + live_d),
        "design_total_kg_m2": _r((dead_d + live_d) * 101.97, 0),
        "note": "Упрощённый сбор нагрузок. Конструктивный расчёт выполняет инженер-конструктор.",
    }


CALCULATORS = {
    "calc_area": calc_area,
    "calc_concrete": calc_concrete,
    "calc_rebar_slab": calc_rebar_slab,
    "calc_rebar_mass": calc_rebar_mass,
    "calc_bricks": calc_bricks,
    "calc_roof": calc_roof,
    "calc_insulation": calc_insulation,
    "calc_slab_load": calc_slab_load,
}
