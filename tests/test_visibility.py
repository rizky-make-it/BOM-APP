import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.visibility import Box, face_visibility, visible_face_count


def B(name, x0, x1, y0, y1, z0, z1):
    return Box(name, (x0, y0, z0), (x1, y1, z1))


def unit(with_doors=False, with_back=True):
    """1000 wide, 400 deep, 700 high open unit, divider in the middle (thin along X). Front is -Y."""
    parts = [B("side L", 0, 20, 0, 400, 0, 700), B("side R", 980, 1000, 0, 400, 0, 700),
             B("bottom", 20, 980, 0, 400, 0, 20), B("top", 20, 980, 0, 400, 680, 700)]
    if with_back:
        parts.append(B("back", 20, 980, 400, 409, 20, 680))
    if with_doors:
        parts += [B("door L", 20, 490, -18, 0, 20, 680), B("door R", 510, 980, -18, 0, 20, 680)]
    return B("divider", 490, 510, 0, 400, 20, 680), parts


def test_open_unit_divider_is_visible_on_both_faces():
    d, parts = unit()
    assert visible_face_count(d, parts) == 2


def test_closed_doors_hide_the_divider():
    d, parts = unit(with_doors=True)
    assert visible_face_count(d, parts) == 0


def test_face_glued_to_another_panel_is_hidden():
    d, parts = unit()
    parts.append(B("laminated plate", 510, 530, 0, 400, 20, 680))      # glued on the +X side
    r = face_visibility(d, parts)
    assert r["share_plus"] == 0 and r["share_minus"] == 1
    assert visible_face_count(d, parts) == 1


def test_one_bay_closed_other_open():
    d, parts = unit()
    parts.append(B("door only left", 20, 490, -18, 0, 20, 680))
    # left bay: front closed by the door, but open? sides/top/bottom/back are closed -> hidden; right bay open
    assert visible_face_count(d, parts) == 1


def test_divider_not_counted_against_itself():
    d, parts = unit()
    assert visible_face_count(d, parts + [d]) == 2
