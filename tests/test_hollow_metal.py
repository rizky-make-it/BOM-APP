import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from models.item import ItemHeader, SolidPart, BOMSpecification
from core.costing_engine import calculate_bom_costing
from core.hollow import code, price_per_m
from config import DEFAULT_RATES as R


def _spec(l, w, t, q=1, mat="METAL"):
    return BOMSpecification(ItemHeader("X", "X", "T", 100, 100, 100),
                            [SolidPart("1 / M", "rail", l, w, t, q, material=mat)], [], [])


def test_code_orders_sides():
    assert code(60, 30, 0.8) == "HOLLOW-30x60x0.8"
    assert code(20, 20, 1) == "HOLLOW-20x20x1"


def test_price_per_m_is_bar_over_6():
    assert abs(price_per_m(R, 20, 20) - 42700 / 6) < 0.01   # 20x20x0.8 default wall


def test_metal_cost_is_length_times_price_per_m():
    c = calculate_bom_costing(_spec(860, 20, 20, q=4), dict(R))
    assert abs(c["metal_cost"] - 0.86 * 4 * 42700 / 6) < 0.5
    assert c["timber_cost"] == 0                       # metal is its own section, not timber
    assert c["fasteners_cost"] == 0                    # fasteners follow solid-wood m3 only
    assert c["metal_rows"][0]["code"] == "HOLLOW-20x20x0.8"
    assert abs(c["metal_rows"][0]["rate"] - 42700 / 6) < 0.01   # IDR per metre


def test_explicit_hollow_code_in_material():
    from core.hollow import is_metal
    assert is_metal("HOLLOW-30x60x1.2") and is_metal("20x20x1.5") and is_metal("METAL") and not is_metal("MINDI")
    c = calculate_bom_costing(_spec(1000, 20, 20, mat="HOLLOW-20x20x1.5"), dict(R))
    assert abs(c["metal_cost"] - 68000 / 6) < 0.5      # code wins over W x T + HOLLOW_WALL
    c2 = calculate_bom_costing(_spec(1000, 20, 20, mat="HOLLOW-99x99x1"), dict(R))
    assert c2["metal_cost"] == 0 and c2["metal_rows"][0]["check"] == "hollow code?"


def test_wall_setting_changes_price():
    r = dict(R); r["HOLLOW_WALL"] = 1.5
    c = calculate_bom_costing(_spec(1000, 20, 20), r)
    assert abs(c["metal_cost"] - 68000 / 6) < 0.5


def test_unknown_section_costs_zero():
    c = calculate_bom_costing(_spec(1000, 22, 22), dict(R))
    assert c["metal_cost"] == 0


def test_wood_unaffected():
    c = calculate_bom_costing(_spec(1000, 50, 50, mat="MINDI"), dict(R))
    assert c["timber_cost"] > 0


def test_default_wall_is_08():
    assert R["HOLLOW_WALL"] == 0.8


def test_missing_wall_falls_back_to_next_listed():
    # 50x50 starts at 1.0 mm in the supplier list: 0.8 must use the 1.0 mm price, not 0
    assert abs(price_per_m(R, 50, 50) - 132100 / 6) < 0.01
    assert abs(price_per_m(R, 40, 60) - 132100 / 6) < 0.01


def test_wall_above_list_costs_zero():
    r = dict(R); r["HOLLOW_WALL"] = 9.0
    assert price_per_m(r, 20, 20) == 0.0
