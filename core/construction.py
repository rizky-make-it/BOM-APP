"""Furniture construction logic that fills what the 2D drawing does not state, WITHOUT contradicting RULES.

Every function returns (value, formula_text). formula_text is written into the spec note so the derivation is auditable.
Rules used (all existing in BOM-APP):
  - core.rules_v2.derive_drawer_box: factory drawer box v2.2 (inner front W-64 / H-30, side D, base W-54 x D-7)
  - panel thickness per part (Part Master v3 default codes / meeting 19 Oct): side C18 1X, back B9 1X, top C18 1X,
    shelf B18 1X, divider B18, drawer front C18 1X, drawer box B12 0X, drawer base B6 0X, door C18 2X
  - a panel that spans a frame opening = opening span; a panel sitting between two members = span - 2 x member section
"""
from typing import Optional, Tuple

RULE_T = {301: 18, 302: 9, 306: 18, 307: 18, 308: 18, 310: 18, 401: 18, 402: 12, 403: 12, 404: 12, 405: 6, 501: 18, 601: 18, 801: 18, 804: 18}
RULE_FAMILY = {301: "C", 302: "B", 306: "B", 307: "B", 308: "B", 310: "B", 401: "C", 402: "B", 403: "B", 404: "B", 405: "B", 501: "C", 601: "C", 801: "B", 804: "B"}
RULE_FACES = {301: 1, 302: 1, 306: 0, 307: 1, 308: 1, 310: 0, 401: 1, 402: 0, 403: 0, 404: 0, 405: 0, 501: 2, 601: 1, 801: 1, 804: 1}


def thickness(part_no: int, drawn_t: Optional[float]) -> Tuple[float, str]:
    """RULES thickness wins over the drawing; returns (t, formula)."""
    t = RULE_T.get(part_no)
    if t is None:
        return (drawn_t or 0.0), "tebal dari gambar (tidak ada RULES untuk part ini)"
    if drawn_t and abs(drawn_t - t) > 0.5:
        return float(t), f"RULES {t} mm (gambar {drawn_t:g} mm, RULES menang)"
    return float(t), f"RULES {t} mm"


def panel_code(part_no: int, fam_from_label: str, faces_from_label: Optional[int], t: float) -> Tuple[str, str]:
    """rate-card panel_type; family (B ply / C MDF) and faces follow RULES per part, label only fills gaps."""
    fam = RULE_FAMILY.get(part_no, fam_from_label or "B")
    faces = RULE_FACES.get(part_no, faces_from_label if faces_from_label is not None else 0)
    base = "LND-PLY-E0" if fam == "B" else "LND-MDF-E0"
    suf = {0: "", 1: "-MSF", 2: "-MDF"}[faces]
    tt = int(t) if t in (3, 6, 9, 12, 15, 18) else 18
    return f"{base}-{tt}{suf}", f"{'plywood' if fam == 'B' else 'MDF'} E0 {tt} mm, {faces} muka veneer"


def width_from_span(span_outer: float, member: float, inside: bool = True) -> Tuple[float, str]:
    """panel between two frame members: outer span - 2 x member section; spanning panel: outer span."""
    if inside:
        return span_outer - 2 * member, f"bentang {span_outer:g} - 2 x {member:g} (di antara rangka)"
    return span_outer, f"= bentang rangka {span_outer:g}"


def drawer_parts(w_front: float, h_front: float, case_depth: float, qty: int = 1):
    """factory drawer box from the opening; returns list of (part_no, name, l, w, t, qty, formula)."""
    from core.rules_v2 import derive_drawer_box
    box = derive_drawer_box(w_front=w_front, h_front=h_front, case_depth=case_depth, qty=qty)
    out = []
    for key, no in (("side", 402), ("box_front_back", 404), ("bottom", 405)):
        p = box[key]
        out.append((no, p.component, p.l, p.w, p.t, p.qty, f"derive_drawer_box({w_front:g} x {h_front:g}, D {case_depth:g}): {p.note}"))
    return out


def glide_length(case_depth: float) -> Tuple[int, str]:
    from core.rules_v2 import get_standard_glide_length
    try:
        L = get_standard_glide_length(case_depth)
    except Exception:
        L = int(max(250, min(550, (case_depth // 50) * 50 - 50)))
    return int(L), f"rel laci standar untuk kedalaman {case_depth:g}"
