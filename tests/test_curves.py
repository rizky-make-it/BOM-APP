import os, sys, math
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from models.item import SolidPart
from core.curves import apply_curve_rule, arc_length


def _p(**k):
    d = dict(label="1 / A", component="Leg", l=500, w=60, t=60, qty=4, material="MINDI", tier_override="B", radius=30, corners=1, curved="Y")
    d.update(k)
    return SolidPart(**d)


def test_arc_length():
    assert abs(arc_length(40, 2) - 2 * math.pi / 2 * 40) < 1e-9


def test_curve_sets_tier_and_blank():
    p = apply_curve_rule(_p(), allow=10)
    assert p.tier_override == "A-CURVED" and p.curved == "Y"
    assert p.l == round(500 + math.pi / 2 * 30 + 10, 1) and p.w == 70


def test_idempotent():
    p = apply_curve_rule(_p())
    l = p.l
    apply_curve_rule(p)
    assert p.l == l


def test_no_radius_untouched():
    p = apply_curve_rule(_p(radius=0))
    assert (p.l, p.w, p.tier_override) == (500, 60, "B")


def test_metal_keeps_tier():
    p = apply_curve_rule(_p(material="METAL"))
    assert p.tier_override == "B" and p.l > 500


def test_engine_maps_curved_rate():
    from core.costing_engine import calculate_bom_costing
    from models.item import ItemHeader, BOMSpecification
    from config import DEFAULT_RATES
    h = ItemHeader("X", "X", "T", 100, 100, 100)
    for tier, key in (("A-CURVED", "MINDI_AC"), ("B", "MINDI_B")):
        c = calculate_bom_costing(BOMSpecification(h, [_p(radius=0, tier_override=tier)], [], []), dict(DEFAULT_RATES))
        assert c["solid_rows"][0]["rate"] == DEFAULT_RATES[key]


def test_router_profile_has_no_cost_impact():
    p = apply_curve_rule(_p(curved="N"), allow=10)
    assert (p.l, p.w, p.tier_override) == (500, 60, "B")
    assert "[PROFIL]" in p.note
