"""
Test Suite for Part Master v3 & Rules v3 (October 2026 Mandates)
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.part_catalog_v3 import (
    PART_CATALOG_V3,
    FAMILIES_V3,
    format_part_label,
    map_legacy_to_v3,
    get_part,
    find_part_by_name,
    find_parts_by_family,
)
from core.rules_v3 import (
    derive_drawer_box,
    derive_door,
    derive_bed_anatomy,
    derive_buffet_casegoods,
)


def test_catalog_completeness():
    assert len(PART_CATALOG_V3) == 126, f"Expected 126 parts, got {len(PART_CATALOG_V3)}"
    assert len(FAMILIES_V3) == 9, f"Expected 9 families, got {len(FAMILIES_V3)}"

    # Check each family has parts
    for fam_id in range(1, 10):
        parts = find_parts_by_family(fam_id)
        assert len(parts) > 0, f"Family {fam_id} has no parts"


def test_format_part_label():
    assert format_part_label(401, "A-20-0X") == "401 A-20-0X"
    assert format_part_label(402, "B-12-0X") == "402 B-12-0X"
    assert format_part_label("901", "DTC-14") == "901 DTC-14"
    assert format_part_label("101", "") == "101"
    # Idempotent if prefix already exists
    assert format_part_label(401, "401 A-20-0X") == "401 A-20-0X"


def test_legacy_mappings():
    # 9-Okt list mappings
    assert map_legacy_to_v3(1) == 102  # Bottom stretcher front/back
    assert map_legacy_to_v3(3) == 101  # Leg
    assert map_legacy_to_v3(6) == 401  # Drawer front
    assert map_legacy_to_v3(8) == 402  # Drawer box side
    assert map_legacy_to_v3(10) == 405  # Drawer base
    assert map_legacy_to_v3(11) == 501  # Door panel
    assert map_legacy_to_v3(20) == 601  # Top panel

    # 13-Okt list mappings
    assert map_legacy_to_v3("①") == 102
    assert map_legacy_to_v3("③") == 101
    assert map_legacy_to_v3("④") == 401
    assert map_legacy_to_v3("⑤") == 402
    assert map_legacy_to_v3("⑥") == 201
    assert map_legacy_to_v3("⑦") == 601
    assert map_legacy_to_v3("⑪") == 403
    assert map_legacy_to_v3("⑫") == 404
    assert map_legacy_to_v3("⑬") == 405
    assert map_legacy_to_v3("⑯") == 901
    assert map_legacy_to_v3("⑰") == 902


def test_search_part_by_name():
    p402 = find_part_by_name("drawer box side")
    assert p402 is not None
    assert p402["part_no"] == 402

    p101 = find_part_by_name("leg")
    assert p101 is not None
    assert p101["part_no"] == 101


def test_drawer_box_v3_rules_and_labels():
    # Dresser drawer test: W=870, H=180, Case Depth=450
    res = derive_drawer_box(
        w_front=870.0,
        h_front=180.0,
        case_depth=450.0,
        qty=1,
        front_mat="A-20-0X",
        box_mat="B-12-0X",
        bottom_mat="B-6-0X"
    )

    # 1. Slide length
    assert res["side_length_d"] == 350.0  # 450 - 100 = 350

    # 2. Part labels conform to 3-digit + material format
    assert res["front"].label == "401 A-20-0X"
    assert res["side"].label == "402 B-12-0X"
    assert res["inner_front"].label == "403 B-12-0X"
    assert res["back"].label == "404 B-12-0X"
    assert res["bottom"].label == "405 B-6-0X"
    assert res["slide"].label == "901 DTC-350"

    # 3. v2.3 Locked Formula Dimensions
    # Side: D=350, H=180 - 30 = 150
    assert res["side"].l == 350.0
    assert res["side"].w == 150.0

    # Inner front & back: W = 870 - 64 = 806, H = 180 - 30 = 150
    assert res["inner_front"].l == 806.0
    assert res["inner_front"].w == 150.0
    assert res["back"].l == 806.0
    assert res["back"].w == 150.0

    # Bottom: (870 - 54 = 816) x (350 - 7 = 343)
    assert res["bottom"].l == 816.0
    assert res["bottom"].w == 343.0


def test_door_v3():
    res = derive_door(opening_w=800.0, opening_h=600.0, num_doors=2, door_mat="C-18-2X")
    door = res["door_panel"]
    hinge = res["hinge"]

    assert door.label == "501 C-18-2X"
    assert door.l == (800.0 / 2) - 2.0  # 398.0
    assert door.w == 600.0 - 2.0        # 598.0

    assert hinge.label == "902 DTC-HINGE"
    assert hinge.qty == 4.0  # 2 doors * 2 hinges


def test_bed_anatomy_v3():
    bed = derive_bed_anatomy(overall_l=2140.0, overall_w=1690.0, overall_h=1000.0)
    assert bed["side_rail"].label == "806 A"
    assert bed["side_rail"].l == 2140.0  # full exterior penetration
    assert bed["center_rail"].label == "808 A"
    assert bed["center_leg"].label == "809 A"
    assert bed["kd_bracket"].label == "907 KD-BRACKET"
    assert bed["floor_glides"].label == "904 GLIDE-25"


def test_buffet_casegoods_v3():
    buffet = derive_buffet_casegoods(overall_l=1650.0, overall_w=450.0, overall_h=820.0)
    labels = [p.label for p in buffet["parts"]]

    assert "101 A" in labels
    assert "201 A" in labels
    assert "206 A" in labels
    assert "601 C-18-1X" in labels
    assert "301 C-18-1X" in labels
    assert "302 B-9-1X" in labels


if __name__ == "__main__":
    test_catalog_completeness()
    test_format_part_label()
    test_legacy_mappings()
    test_search_part_by_name()
    test_drawer_box_v3_rules_and_labels()
    test_door_v3()
    test_bed_anatomy_v3()
    test_buffet_casegoods_v3()
    print("ALL TESTS PASSED SUCCESSFULLY!")
