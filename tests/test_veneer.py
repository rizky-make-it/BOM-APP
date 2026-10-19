import os, sys, shutil, subprocess, tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import openpyxl
from config import DEFAULT_RATES as R, GOLDEN_MASTER_PATH, veneer_m2, veneer_face

SO = r"C:\Program Files\LibreOffice\program\soffice.exe"


def test_veneer_m2_matches_vendor_model():
    assert abs(veneer_m2(0.6) - 18826.67) < 0.01
    assert abs(veneer_m2(1.0) - 23377.78) < 0.01
    assert abs(veneer_m2(1.2) - 25653.33) < 0.01


def test_face_increases_with_thickness():
    assert veneer_face(0.6) < veneer_face(1.0) < veneer_face(1.2)


def test_default_msf_uses_06mm_face():
    assert abs(R["LND-PLY-E2-18-MSF"] - (R["LND-PLY-E2-18"] + veneer_face(0.6))) < 0.01
    assert abs(R["LND-PLY-E2-18-MDF"] - (R["LND-PLY-E2-18"] + 2 * veneer_face(0.6))) < 0.01


def test_variants_exist_and_order():
    for t in (3, 6, 9, 12, 15, 18):
        k = f"LND-PLY-E2-{t}-MSF"
        assert R[k] < R[k + "-V10"] < R[k + "-V12"]


def test_config_equals_workbook_after_recalc():
    if not os.path.exists(SO):
        return
    d = tempfile.mkdtemp()
    src = os.path.join(d, "gm.xlsx")
    shutil.copy(GOLDEN_MASTER_PATH, src)
    subprocess.run([SO, "--headless", "--convert-to", "xlsx", "--outdir", os.path.join(d, "o"), src], check=True, timeout=240, capture_output=True)
    ws = openpyxl.load_workbook(os.path.join(d, "o", "gm.xlsx"), data_only=True)["RATES"]
    wb = {r[0]: r[2] for r in ws.iter_rows(values_only=True) if isinstance(r[0], str) and isinstance(r[2], (int, float))}
    for k in ("LND-PLY-E2-18-MSF", "LND-PLY-E2-18-MDF", "LND-PLY-E2-18-MSF-V10", "LND-PLY-E2-12-MSF-V12", "LND-MDF-E2-18-MSF-V12"):
        assert abs(wb[k] - R[k]) < 0.05, (k, wb[k], R[k])
    assert abs(wb["VEN_FACE_10"] - veneer_face(1.0)) < 0.05


def test_missing_panel_code_raises():
    from core.costing_engine import calculate_bom_costing
    from models.item import ItemHeader, PanelPart, BOMSpecification
    import pytest
    spec = BOMSpecification(ItemHeader("X", "X", "T", 100, 100, 100), [], [PanelPart("p", "c", "NOPE-1", 100, 100, 18, 1)], [])
    with pytest.raises(KeyError):
        calculate_bom_costing(spec, dict(R))
