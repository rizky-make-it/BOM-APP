"""Curve rule, locked 19 Oct 2026 (revised same day).

TWO DIFFERENT THINGS:
  * ROUTER PROFILE / rounded corner (drawing callout R30, R38, R40 on a straight part): made by the router on a normal
    straight board. NO tier change, NO blank change, NO extra cost. Only noted on the row.
  * TRUE CURVED WOOD (curved="Y" set on the part: bent/shaped member such as a curved headboard rail): rules below.

For every SOLID part with curved == "Y" (and radius > 0):
  1. tier      -> A-CURVED  (rate MINDI_AC / TEAK_AC, yield 4.6 in the rate card)
  2. blank     -> finished size + ARC + TOLERANCE
        arc       = corners x (pi/2 x R)            added to the LENGTH
        tolerance = RATES!CURVE_ALLOW (mm)          added to LENGTH and WIDTH
  3. the sheet row shows the BLANK size (so m3 and cost follow), the note keeps the finished size.
RATES!CURVE_ALLOW is EMPTY until the factory gives the figure: tolerance counts as 0 and the cell shows orange.
Idempotent: a part already carrying the [CURVE] marker is not changed twice.
"""
import math

MARK = "[CURVE]"


def arc_length(radius: float, corners: int = 1) -> float:
    return corners * (math.pi / 2.0) * radius


def apply_curve_rule(part, allow: float = 0.0):
    """Mutates and returns a SolidPart. METAL parts only get the marker (metal has no tier rates)."""
    r = float(getattr(part, "radius", 0) or 0)
    if r <= 0 or MARK in (part.note or ""):
        return part
    if getattr(part, "curved", "N") != "Y":  # router profile only: note, no cost impact
        if "[PROFIL]" not in (part.note or ""):
            part.note = f"[PROFIL] R{r:g} hasil router, tidak mengubah tier/ukuran. " + (part.note or "")
        return part
    arc = arc_length(r, int(getattr(part, "corners", 1) or 1))
    fin_l, fin_w = part.l, part.w
    part.l = round(fin_l + arc + allow, 1)
    part.w = round(fin_w + allow, 1)
    part.curved = "Y"
    if part.material != "METAL":
        part.tier_override = "A-CURVED"
    part.note = f"{MARK} R{r:g} x{part.corners}: jadi {fin_l:g}x{fin_w:g}, blank +busur {arc:.0f} +toleransi {allow:g}. " + (part.note or "")
    return part


def apply_to_spec(spec, allow: float = 0.0):
    for p in spec.solid_parts:
        apply_curve_rule(p, allow)
    return spec
