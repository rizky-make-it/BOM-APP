"""Panel material rules (locked 19 Oct 2026).

Drawing code  <Group>-<T>-<n>X   (e.g. B-18-1X, C-12-0X)
  Group B = PLYWOOD  -> rate code LND-PLY-E2-<T> | LND-PLY-E2-<T>-MSF | -MDF(!) (Mindi Double Face)
  Group C = MDF board -> rate code LND-MDF-E2-<T> (veneered: LND-MDF-E2-<T>-MSF)
  n = veneered faces: 0X RAW, 1X single face (S F), 2X double face (D F)
  Species letter M = mindi, T = teak.
Board grade is E2 everywhere (RATES!PANEL_GRADE = E2, landed Linyi quote).

WARNING (naming clash): in rate codes 'PLY-18-MDF' means PLYWOOD with Mindi Double
Face veneer. It is NOT MDF board. MDF board codes always start with 'MDF-' or 'LND-MDF-'.
"""
import re

PANEL_GRADE = "E2"  # LOCKED: plywood and MDF are always E2
BANNED_GRADES = ("E0", "CARB")
_RATE = re.compile(r"^(?:PLY|LND-PLY-E2|LND-MDF-E2|MDF)-(\d+)(?:-(?:RAW|[MT][SD]F))?$")
_LABEL = re.compile(r"\b([BC])-?(\d+)-?([012])X\b", re.I)


_LEGACY_PLY = re.compile(r"^PLY-(\d+)-(RAW|[MT][SD]F)$")
_LEGACY_MDF = re.compile(r"^MDF-(\d+)-(RAW|MSF|MDF)$")


def to_e2(panel_type: str) -> str:
    """Normalise any legacy panel code to its explicit E2 landed code.
    PLY-18-RAW -> LND-PLY-E2-18 ; PLY-18-MSF -> LND-PLY-E2-18-MSF ; MDF-9-RAW -> LND-MDF-E2-9."""
    m = _LEGACY_PLY.match(panel_type or "")
    if m:
        t, s = m.groups()
        return f"LND-PLY-E2-{t}" if s == "RAW" else f"LND-PLY-E2-{t}-{s}"
    m = _LEGACY_MDF.match(panel_type or "")
    if m:
        t, s = m.groups()
        return f"LND-MDF-E2-{t}" if s == "RAW" else f"LND-MDF-E2-{t}-{s}"
    return panel_type


def rate_code_from_label(label: str, species: str = "M") -> str | None:  # legacy-style code; compare via to_e2
    m = _LABEL.search(label or "")
    if not m:
        return None
    grp, t, faces = m.group(1).upper(), m.group(2), m.group(3)
    pre = "PLY" if grp == "B" else "MDF"
    if faces == "0":
        return to_e2(f"{pre}-{t}-RAW")
    if grp == "C":  # veneered MDF is priced as landed board + veneer
        return f"LND-MDF-E2-{t}-{species}{'S' if faces == '1' else 'D'}F"
    return to_e2(f"PLY-{t}-{species}{'S' if faces == '1' else 'D'}F")


def check_panel(part) -> list[str]:
    """Return problems for one PanelPart/dict (thickness vs rate code, label vs rate code)."""
    g = (lambda k: getattr(part, k, None) if not isinstance(part, dict) else part.get(k))
    pt, t, label = g("panel_type"), g("t"), g("label") or ""
    out = []
    if any(f"-{g}-" in (pt or "") for g in BANNED_GRADES):
        out.append(f"grade not allowed in {pt}: only {PANEL_GRADE}")
    m = _RATE.match(pt or "")
    if m and t is not None and abs(int(m.group(1)) - float(t)) > 0.5:
        out.append(f"thickness {t} mm but rate code {pt}")
    if pt and pt != to_e2(pt):
        out.append(f"{pt} is not an explicit E2 code, use {to_e2(pt)}")
    exp = rate_code_from_label(label)
    if exp and to_e2(exp) != to_e2(pt):
        out.append(f"label {label.strip()} implies {exp}, spec uses {pt}")
    return out
