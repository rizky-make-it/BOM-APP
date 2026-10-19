"""METAL = black hollow steel section (rule 19 Oct 2026).

A METAL solid part is priced from the supplier list (RATES block "STEEL HOLLOW SECTION"):
    cost = length (m) x qty x price per metre of  HOLLOW-<a>x<b>x<wall>      (a <= b, the part's w and t)
The wall thickness is NOT on the drawings -> one setting, RATES!HOLLOW_WALL (0.8 mm for now, change it by hand in RATES).
If the supplier list has no such wall for that section (e.g. 50x50 and 40x60 start at 1.0 mm), the next thicker wall that IS listed is used.
If the cross-section is not in the list at all, the price is 0 and the row turns orange.
"""

def code(w: float, t: float, wall: float) -> str:
    a, b = sorted((float(w), float(t)))
    return f"HOLLOW-{a:g}x{b:g}x{float(wall):g}"


def price_per_m(rates: dict, w: float, t: float) -> float:
    wall = float(rates.get("HOLLOW_WALL", 0.8))
    a, b = sorted((float(w), float(t)))
    prefix = f"HOLLOW-{a:g}x{b:g}x"
    walls = sorted(float(k[len(prefix):]) for k in rates if k.startswith(prefix))
    for x in walls:
        if x >= wall - 1e-9:
            return float(rates[code(w, t, x)] or 0.0)
    return 0.0


def equiv_rate_m3(rates: dict, w: float, t: float) -> float:
    """IDR per m3 that gives the same cost as price per metre (so the item sheet's volume x rate still works)."""
    area_m2 = (float(w) * float(t)) / 1e6
    return price_per_m(rates, w, t) / area_m2 if area_m2 else 0.0
