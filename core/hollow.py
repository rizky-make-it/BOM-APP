"""METAL = black hollow steel section (rule 19 Oct 2026).

A METAL solid part is priced from the supplier list (RATES block "STEEL HOLLOW SECTION"):
    cost = length (m) x qty x price per metre of  HOLLOW-<a>x<b>x<wall>      (a <= b, the part's w and t)
The wall thickness is NOT on the drawings -> one setting, RATES!HOLLOW_WALL (default 1.2 mm, CONFIRM).
If the cross-section is not in the list, the price is 0 and the row turns orange.
"""

def code(w: float, t: float, wall: float) -> str:
    a, b = sorted((float(w), float(t)))
    return f"HOLLOW-{a:g}x{b:g}x{float(wall):g}"


def price_per_m(rates: dict, w: float, t: float) -> float:
    wall = rates.get("HOLLOW_WALL", 1.2)
    return float(rates.get(code(w, t, wall), 0.0) or 0.0)


def equiv_rate_m3(rates: dict, w: float, t: float) -> float:
    """IDR per m3 that gives the same cost as price per metre (so the item sheet's volume x rate still works)."""
    area_m2 = (float(w) * float(t)) / 1e6
    return price_per_m(rates, w, t) / area_m2 if area_m2 else 0.0
