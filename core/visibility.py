"""Exposed faces of a divider / partition (Rizky, 20 Oct 2026).

RULE: a face is EXPOSED if a person's hand can touch it while the furniture is in use. Doors and drawers are
opened/pulled in use, so they never hide what is behind them (they are `movable` and ignored as obstacles).
Not exposed: a face glued against another fixed part, or a cavity closed on every side by fixed parts.

Input is every part as an axis-aligned box (from the DWG/STEP reader). Output = how many of the divider's two large
faces are exposed (0 plain, 1 MSF, 2 MDF) -> PanelPart.exposed_faces.

Per face (5 x 5 sample grid; the face counts as exposed when >= 50 % of the samples are reachable):
  1. Ray straight out of the face: hits nothing                  -> reachable
  2. hits a fixed part at <= 1.5 mm (glued)                      -> not reachable
  3. otherwise the point looks into a gap: reachable only if the gap is open somewhere (a sideways ray from the
     middle of the gap escapes through fixed parts) = a hand can get in.
"""
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

AXES = (0, 1, 2)
CONTACT_TOL = 1.5      # mm: closer than this = glued, face hidden
GRID = 5               # samples per direction
VISIBLE_SHARE = 0.5    # share of the face that must be visible


@dataclass(frozen=True)
class Box:
    name: str
    lo: Tuple[float, float, float]
    hi: Tuple[float, float, float]
    movable: bool = False     # door / drawer: opened in use, so it never hides anything


    def size(self) -> Tuple[float, float, float]:
        return (self.hi[0] - self.lo[0], self.hi[1] - self.lo[1], self.hi[2] - self.lo[2])


def _hit(origin: Sequence[float], axis: int, sign: int, boxes: Iterable[Box], eps: float = 0.01):
    """Distance to the nearest box on the ray (origin, axis*sign); None if the ray escapes."""
    best = None
    for b in boxes:
        if any(not (b.lo[k] + eps < origin[k] < b.hi[k] - eps) for k in AXES if k != axis):
            continue
        if sign > 0:
            if b.hi[axis] <= origin[axis] + eps:
                continue
            d = max(0.0, b.lo[axis] - origin[axis])
        else:
            if b.lo[axis] >= origin[axis] - eps:
                continue
            d = max(0.0, origin[axis] - b.hi[axis])
        if best is None or d < best:
            best = d
    return best


MOVABLE_NAME = re.compile(r"\b(door|drawer)\b", re.I)


def is_movable(name: str) -> bool:
    """Door and drawer parts (front, box, sides) are opened in use."""
    return bool(MOVABLE_NAME.search(name or ""))


def face_visibility(divider: Box, others: Sequence[Box]) -> Dict[str, object]:
    """Share (0..1) of each large face a hand can reach. Movable parts (doors, drawers) are ignored as obstacles."""
    others = [b for b in others if not (b.movable or is_movable(b.name))]
    sz = divider.size()
    n = min(AXES, key=lambda k: sz[k])                 # thin axis = face normal
    u, v = [k for k in AXES if k != n]
    share = {}
    for sign in (+1, -1):
        plane = divider.hi[n] if sign > 0 else divider.lo[n]
        vis = 0
        for i in range(GRID):
            for j in range(GRID):
                p = [0.0, 0.0, 0.0]
                p[u] = divider.lo[u] + (divider.hi[u] - divider.lo[u]) * (i + 0.5) / GRID
                p[v] = divider.lo[v] + (divider.hi[v] - divider.lo[v]) * (j + 0.5) / GRID
                p[n] = plane
                d = _hit(p, n, sign, others)
                if d is None:
                    vis += 1
                    continue
                if d <= CONTACT_TOL:
                    continue
                mid = list(p)
                mid[n] = plane + sign * d / 2
                if any(_hit(mid, ax, s, others) is None for ax in (u, v) for s in (+1, -1)):
                    vis += 1
        share[sign] = vis / (GRID * GRID)
    return {"normal_axis": "XYZ"[n], "share_plus": share[+1], "share_minus": share[-1]}


def visible_face_count(divider: Box, others: Sequence[Box]) -> int:
    """0, 1 or 2: number of large faces that are visible. Goes into PanelPart.exposed_faces."""
    r = face_visibility(divider, [b for b in others if b is not divider and b.name != divider.name])
    return int(float(r["share_plus"]) >= VISIBLE_SHARE) + int(float(r["share_minus"]) >= VISIBLE_SHARE)
