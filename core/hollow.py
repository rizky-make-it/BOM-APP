"""METAL = black hollow steel section (rule 19 Oct 2026; per-metre METAL section 20 Oct 2026).

A METAL solid part is priced per METRE from the supplier list (RATES block "STEEL HOLLOW SECTION"):
    cost = length (m) x qty x IDR/m of  HOLLOW-<a>x<b>x<wall>      (a <= b)
Which section / wall:
  1. part.material is itself a hollow code ("HOLLOW-20x20x0.8" or "20x20x1.2"): used as written.
  2. part.material == "METAL": section = part.w x part.t, wall = RATES!HOLLOW_WALL (default 0.8 mm);
     if the list has no such wall for that section the next thicker listed wall is used.
If the section is not in the list at all the price is 0 and the row turns orange.
In the workbook METAL parts live in their own section (rows 34-42) whose RATE column is IDR/m.
"""
import re

_CODE = re.compile(r"^(?:HOLLOW-)?(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)$", re.I)


def is_metal(material) -> bool:
    m = str(material or "").strip().upper()
    return m == "METAL" or m.startswith("HOLLOW-") or bool(_CODE.match(m))


def code(w: float, t: float, wall: float) -> str:
    a, b = sorted((float(w), float(t)))
    return f"HOLLOW-{a:g}x{b:g}x{float(wall):g}"


def parse_code(material):
    """'HOLLOW-20x20x0.8' / '20x20x0.8' -> (a, b, wall) or None."""
    m = _CODE.match(str(material or "").strip())
    if not m:
        return None
    a, b, wall = (float(x) for x in m.groups())
    return a, b, wall


def resolve_code(rates: dict, material, w: float, t: float) -> str:
    """The HOLLOW-... code actually priced for this part ('' when none is listed)."""
    p = parse_code(material)
    if p:
        c = code(p[0], p[1], p[2])
        return c if c in rates else ""
    wall = float(rates.get("HOLLOW_WALL", 0.8))
    a, b = sorted((float(w), float(t)))
    prefix = f"HOLLOW-{a:g}x{b:g}x"
    walls = sorted(float(k[len(prefix):]) for k in rates if k.startswith(prefix))
    for x in walls:
        if x >= wall - 1e-9:
            return code(a, b, x)
    return ""


def price_per_m(rates: dict, w: float, t: float, material="METAL") -> float:
    c = resolve_code(rates, material, w, t)
    return float(rates[c] or 0.0) if c else 0.0


def equiv_rate_m3(rates: dict, w: float, t: float, material="METAL") -> float:
    """IDR per m3 giving the same cost as IDR/m (for callers that still think in volume)."""
    area_m2 = (float(w) * float(t)) / 1e6
    return price_per_m(rates, w, t, material) / area_m2 if area_m2 else 0.0
