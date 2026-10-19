"""Panel grade lock: every plywood / MDF rate used by the engine must be the E2 landed price."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import re
import openpyxl
from config import DEFAULT_RATES as R, GOLDEN_MASTER_PATH, PANEL_GRADE
from core.panel_rules import check_panel


def test_grade_constant():
    assert PANEL_GRADE == "E2"


def test_workbook_panel_grade_cell_is_e2():
    ws = openpyxl.load_workbook(GOLDEN_MASTER_PATH)["RATES"]
    vals = [r[2] for r in ws.iter_rows(values_only=True) if r[0] == "PANEL_GRADE"]
    assert vals == ["E2"]


def test_plain_rates_equal_e2_landed():
    for t in (3, 6, 9, 12, 15, 18):
        assert abs(R[f"PLY-{t}-RAW"] - R[f"LND-PLY-E2-{t}"]) < 0.01
        assert abs(R[f"MDF-{t}-RAW"] - R[f"LND-MDF-E2-{t}"]) < 0.01


def test_veneered_plywood_equal_e2_landed_veneered():
    for t in (3, 6, 9, 12, 18):  # PLY-15-MSF is not used by any item
        assert abs(R[f"PLY-{t}-MSF"] - R[f"LND-PLY-E2-{t}-MSF"]) < 0.01


def test_no_other_grade_in_default_rates():
    bad = [k for k in R if re.search(r"-(E0|CARB)-", k)]
    assert not bad, bad


def test_checker_rejects_e0():
    assert check_panel({"panel_type": "LND-PLY-E0-18", "t": 18, "label": ""})
    assert not check_panel({"panel_type": "LND-PLY-E2-18", "t": 18, "label": ""})
    assert check_panel({"panel_type": "PLY-18-RAW", "t": 18, "label": ""})  # legacy code flagged


def test_to_e2_mapping():
    from core.panel_rules import to_e2
    assert to_e2("PLY-18-RAW") == "LND-PLY-E2-18"
    assert to_e2("PLY-18-MSF") == "LND-PLY-E2-18-MSF"
    assert to_e2("PLY-12-MDF") == "LND-PLY-E2-12-MDF"
    assert to_e2("MDF-9-RAW") == "LND-MDF-E2-9"
    assert to_e2("LND-PLY-E2-6") == "LND-PLY-E2-6"


def test_all_spec_json_use_e2_codes():
    import glob, json
    root = os.path.join(os.path.dirname(__file__), "..", "data")
    files = glob.glob(os.path.join(root, "**", "*_spec.json"), recursive=True)
    assert files
    for f in files:
        for p in json.load(open(f, encoding="utf-8")).get("panel_parts", []):
            assert p["panel_type"].startswith(("LND-PLY-E2-", "LND-MDF-E2-")), (f, p["panel_type"])
