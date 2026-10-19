"""Panel material rules (locked 19 Oct 2026).

Drawing code  <Group>-<T>-<n>X   (e.g. B-18-1X, C-12-0X)
  Group B = PLYWOOD  -> rate code LND-PLY-E0-<T> | LND-PLY-E0-<T>-MSF | -MDF(!) (Mindi Double Face)
  Group C = MDF board -> rate code LND-MDF-E0-<T> (veneered: LND-MDF-E0-<T>-MSF)
  n = veneered faces: 0X RAW, 1X single face (S F), 2X double face (D F)
  Species letter M = mindi, T = teak.
Board grade is E0 everywhere (RATES!PANEL_GRADE = E0). Rule set by the meeting of 19 Oct 2026; it replaced the earlier E2 lock.

WARNING (naming clash): in rate codes 'PLY-18-MDF' means PLYWOOD with Mindi Double
Face veneer. It is NOT MDF board. MDF board codes always start with 'MDF-' or 'LND-MDF-'.
"""
import re

PANEL_GRADE = "E0"  # LOCKED: plywood and MDF are always E0
BANNED_GRADES = ("E2", "CARB")
_RATE = re.compile(r"^(?:PLY|LND-PLY-E2|LND-MDF-E2|MDF)-(\d+)(?:-(?:RAW|[MT][SD]F))?(?:-V\d\d)?$")
_LABEL = re.compile(r"\b([BC])-?(\d+)-?([012])X\b", re.I)


_LEGACY_PLY = re.compile(r"^PLY-(\d+)-(RAW|[MT][SD]F)(-V\d\d)?$")
_LEGACY_MDF = re.compile(r"^MDF-(\d+)-(RAW|MSF|MDF)(-V\d\d)?$")


def to_e0(panel_type: str) -> str:
    """Normalise ANY panel code (legacy PLY-/MDF-, or old E2 codes) to its explicit E0 landed code.
    PLY-18-RAW -> LND-PLY-E0-18 ; LND-PLY-E2-18-MSF -> LND-PLY-E0-18-MSF ; MDF-9-RAW -> LND-MDF-E0-9."""
    pt = re.sub(r"^(LND-(?:PLY|MDF))-E2-", r"\g<1>-E0-", panel_type or "")
    return _to_explicit(pt)


def _to_explicit(panel_type: str) -> str:
    """Legacy code -> explicit landed code (grade E0).
    PLY-18-RAW -> LND-PLY-E0-18 ; PLY-18-MSF -> LND-PLY-E0-18-MSF ; MDF-9-RAW -> LND-MDF-E0-9."""
    m = _LEGACY_PLY.match(panel_type or "")
    if m:
        t, s, v = m.groups()
        return f"LND-PLY-E0-{t}" if s == "RAW" else f"LND-PLY-E0-{t}-{s}{v or ''}"
    m = _LEGACY_MDF.match(panel_type or "")
    if m:
        t, s, v = m.groups()
        return f"LND-MDF-E0-{t}" if s == "RAW" else f"LND-MDF-E0-{t}-{s}{v or ''}"
    return panel_type


def rate_code_from_label(label: str, species: str = "M") -> str | None:  # legacy-style code; compare via to_e2
    m = _LABEL.search(label or "")
    if not m:
        return None
    grp, t, faces = m.group(1).upper(), m.group(2), m.group(3)
    pre = "PLY" if grp == "B" else "MDF"
    if faces == "0":
        return to_e0(f"{pre}-{t}-RAW")
    if grp == "C":  # veneered MDF is priced as landed board + veneer
        return f"LND-MDF-E0-{t}-{species}{'S' if faces == '1' else 'D'}F"
    return to_e0(f"PLY-{t}-{species}{'S' if faces == '1' else 'D'}F")


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
    if pt and pt != to_e0(pt):
        out.append(f"{pt} is not an explicit E0 code, use {to_e0(pt)}")
    exp = rate_code_from_label(label)
    meeting = MEETING_MARK in (g("note") or "")  # meeting rule (19 Oct 2026) overrides the drawing label
    if exp and not meeting and to_e0(exp) != to_e0(pt):
        out.append(f"label {label.strip()} implies {exp}, spec uses {pt}")
    return out


# ---------------------------------------------------------------------------------------------
# MEETING RULE (19 Oct 2026): which board family and how many veneer faces per panel role.
#   Plywood E0 (furniture grade): drawer box parts (side, front/back, bottom, support), back panel (keeps its faces),
#   divider/partition = PLAIN (no veneer, Rizky 19 Oct 2026).
#   MDF veneer E0:               side panel = 1 face (MSF), door = 2 faces (MDF), drawer face = 1 face (MSF).
#   Everything else (top, shelves, headboard ...) keeps the family it already has.
# Thickness is never changed here (thickness follows RULES, see README G). Idempotent.
# ---------------------------------------------------------------------------------------------
MEETING_MARK = "[MEETING]"
_THICK = (3, 6, 9, 12, 15, 18)
_ROLE_PLY = re.compile(
    r"drawer (box|base|bottom|support|side|inner)|drawer (front/back|side) box|side drawer|\bback panel\b",
    re.I)
_ROLE_DRAWER_ANY = re.compile(r"drawer", re.I)
_ROLE_DIVIDER = re.compile(r"\bdividers?\b|partition", re.I)
_ROLE_SIDE = re.compile(r"\bside panel\b", re.I)
_ROLE_DOOR = re.compile(r"\bdoor\b", re.I)
_ROLE_FACE = re.compile(r"drawer (face|front)\b", re.I)


def _code(family: str, t: float, faces: int) -> str | None:
    ti = int(round(float(t)))
    if ti not in _THICK or abs(ti - float(t)) > 0.5:
        return None
    base = f"LND-{family}-E0-{ti}"
    return base if faces == 0 else f"{base}-{'MSF' if faces == 1 else 'MDF'}"


def role_of(component: str) -> str | None:
    c = component or ""
    if _ROLE_DIVIDER.search(c) and not _ROLE_DRAWER_ANY.search(c):
        return "divider"
    if _ROLE_PLY.search(c):
        return "ply"
    if _ROLE_DOOR.search(c):
        return "door"
    if _ROLE_FACE.search(c):
        return "face"
    if _ROLE_SIDE.search(c):
        return "side"
    return None


def apply_meeting_rule(part):
    """Mutates a PanelPart: board family and veneer faces per role. Returns the part."""
    role = role_of(part.component)
    if role is None or MEETING_MARK in (part.note or ""):
        return part
    if role == "ply":
        faces = int(part.exposed_faces or 0)           # back panel keeps its face count; drawer parts stay raw
        fam = "PLY"
    elif role == "divider":
        fam, faces = "PLY", 0                          # divider / partition: plywood E0, plain (no veneer)
    elif role == "door":
        fam, faces = "MDF", 2
    else:                                              # drawer face and side panel: MDF, 1 face
        fam, faces = "MDF", 1
    new = _code(fam, part.t, faces)
    if new is None:                                    # thickness not in the board table: leave it and flag
        part.note = f"{MEETING_MARK} tebal {part.t:g} tidak ada di tabel papan, tipe tidak diubah. " + (part.note or "")
        return part
    if new != part.panel_type:
        part.note = f"{MEETING_MARK} {part.panel_type} -> {new}. " + (part.note or "")
    else:
        part.note = f"{MEETING_MARK} sudah sesuai. " + (part.note or "")
    part.panel_type, part.exposed_faces = new, faces
    return part

