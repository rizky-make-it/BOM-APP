"""Panel material rules (locked 19 Oct 2026).

Drawing code  <Group>-<T>-<n>X   (e.g. B-18-1X, C-12-0X)
  Group B = PLYWOOD  -> rate code PLY-<T>-RAW | PLY-<T>-MSF | PLY-<T>-MDF(!) | TSF | TDF
  Group C = MDF board -> rate code MDF-<T>-RAW (veneered: LND-MDF-E2-<T>-MSF)
  n = veneered faces: 0X RAW, 1X single face (S F), 2X double face (D F)
  Species letter M = mindi, T = teak.
Board grade is E2 everywhere (RATES!PANEL_GRADE = E2, landed Linyi quote).

WARNING (naming clash): in rate codes 'PLY-18-MDF' means PLYWOOD with Mindi Double
Face veneer. It is NOT MDF board. MDF board codes always start with 'MDF-' or 'LND-MDF-'.
"""
import re

PANEL_GRADE = "E2"
_RATE = re.compile(r"^PLY-(\d+)-(RAW|[MT][SD]F)$")
_LABEL = re.compile(r"\b([BC])-?(\d+)-?([012])X\b", re.I)


def rate_code_from_label(label: str, species: str = "M") -> str | None:
    m = _LABEL.search(label or "")
    if not m:
        return None
    grp, t, faces = m.group(1).upper(), m.group(2), m.group(3)
    pre = "PLY" if grp == "B" else "MDF"
    if faces == "0":
        return f"{pre}-{t}-RAW"
    if grp == "C":  # veneered MDF is priced as landed board + veneer
        return f"LND-MDF-{PANEL_GRADE}-{t}-{species}{'S' if faces == '1' else 'D'}F"
    return f"PLY-{t}-{species}{'S' if faces == '1' else 'D'}F"


def check_panel(part) -> list[str]:
    """Return problems for one PanelPart/dict (thickness vs rate code, label vs rate code)."""
    g = (lambda k: getattr(part, k, None) if not isinstance(part, dict) else part.get(k))
    pt, t, label = g("panel_type"), g("t"), g("label") or ""
    out = []
    m = _RATE.match(pt or "")
    if m and t is not None and abs(int(m.group(1)) - float(t)) > 0.5:
        out.append(f"thickness {t} mm but rate code {pt}")
    exp = rate_code_from_label(label)
    if exp and exp != pt and not (exp.startswith("LND-MDF") and (pt or "").startswith("LND-MDF")):
        out.append(f"label {label.strip()} implies {exp}, spec uses {pt}")
    return out
