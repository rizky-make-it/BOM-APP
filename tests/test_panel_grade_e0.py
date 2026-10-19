"""Panel grade lock: every plywood / MDF rate used by the engine must be the E0 landed price."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import re
import openpyxl
from config import DEFAULT_RATES as R, GOLDEN_MASTER_PATH, PANEL_GRADE
from core.panel_rules import check_panel


def test_grade_constant():
    assert PANEL_GRADE == "E0"


def test_workbook_panel_grade_cell_is_e0():
    ws = openpyxl.load_workbook(GOLDEN_MASTER_PATH)["RATES"]
    vals = [r[2] for r in ws.iter_rows(values_only=True) if r[0] == "PANEL_GRADE"]
    assert vals == ["E0"]


def test_plain_rates_are_e0_landed():
    for t in (3, 6, 9, 12, 15, 18):
        assert f"LND-PLY-E0-{t}" in R and f"LND-MDF-E0-{t}" in R
        assert f"PLY-{t}-RAW" not in R  # legacy codes are converted by to_e0, never priced separately


def test_veneered_plywood_equal_e0_landed_veneered():
    for t in (3, 6, 9, 12, 18):  # PLY-15-MSF is not used by any item
        assert R[f"LND-PLY-E0-{t}-MSF"] > R[f"LND-PLY-E0-{t}"]


def test_no_other_grade_in_default_rates():
    bad = [k for k in R if re.search(r"-(E2|CARB)-", k)]
    assert not bad, bad


def test_checker_rejects_other_grades():
    assert check_panel({"panel_type": "LND-PLY-E2-18", "t": 18, "label": ""})
    assert not check_panel({"panel_type": "LND-PLY-E0-18", "t": 18, "label": ""})
    assert check_panel({"panel_type": "PLY-18-RAW", "t": 18, "label": ""})  # legacy code flagged


def test_to_e0_mapping():
    from core.panel_rules import to_e0
    assert to_e0("PLY-18-RAW") == "LND-PLY-E0-18"
    assert to_e0("PLY-18-MSF") == "LND-PLY-E0-18-MSF"
    assert to_e0("PLY-12-MDF") == "LND-PLY-E0-12-MDF"
    assert to_e0("MDF-9-RAW") == "LND-MDF-E0-9"
    assert to_e0("LND-PLY-E0-6") == "LND-PLY-E0-6"


def test_all_spec_json_use_e0_codes():
    import glob, json
    root = os.path.join(os.path.dirname(__file__), "..", "data")
    files = glob.glob(os.path.join(root, "**", "*_spec.json"), recursive=True)
    assert files
    for f in files:
        for p in json.load(open(f, encoding="utf-8")).get("panel_parts", []):
            assert p["panel_type"].startswith(("LND-PLY-E0-", "LND-MDF-E0-")), (f, p["panel_type"])


def test_napier_specs_use_e0_codes():
    import glob, json
    files = glob.glob(os.path.join(os.path.dirname(__file__), "..", "data", "napier", "lv433_*_spec.json"))
    assert len(files) == 11
    for f in files:
        for p in json.load(open(f, encoding="utf-8"))["panel_parts"]:
            assert p["panel_type"].startswith(("LND-PLY-E0-", "LND-MDF-E0-")), (f, p["panel_type"])
