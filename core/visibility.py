"""Visible faces of a divider / partition (Rizky, 20 Oct 2026: "yang terlihat veneer, yang tidak terlihat polos").

Input is the 3D position of every part as an axis-aligned box (from the DWG/STEP reader). Output = how many of the
divider's two large faces are VISIBLE; that number goes into PanelPart.exposed_faces (0 plain, 1 MSF, 2 MDF).

Logic, per face (sampled on a 5 x 5 grid; a face counts as visible when >= 50 % of the samples are visible):
  1. Cast a ray from the sample point straight out of the face.
       - hits nothing                      -> VISIBLE (open to the room)
       - hits a part at <= 1.5 mm          -> HIDDEN  (glued against another part)
  2. Otherwise the point looks into a bay (gap) of depth d. The bay is VISIBLE only if it is open somewhere: a ray from
     the middle of the bay, sent sideways (4 directions), escapes without hitting a part. A bay closed on all sides
     (by side panels, back, top, bottom, a closed door or a drawer front) is HIDDEN.
Closed doors and drawer fronts are just parts in the way, so they hide what is behind them. This is an ASSUMPTION
(a bay behind a closed door counts as hidden); change DOOR_HIDES_BAY handling by removing door boxes from `others`.
"""
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

    def size(self) -> Tuple[float, float, float]:
        return tuple(h - l for l, h in zip(self.lo, self.hi))


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


def face_visibility(divider: Box, others: Sequence[Box]) -> Dict[str, object]:
    """Share (0..1) of each large face that is visible. `others` must not contain the divider itself."""
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
    return int(r["share_plus"] >= VISIBLE_SHARE) + int(r["share_minus"] >= VISIBLE_SHARE)
