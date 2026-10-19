import os, sys, json, re, shutil, subprocess, tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import openpyxl
from config import GOLDEN_MASTER_PATH

SRC = os.path.join(os.path.dirname(__file__), "..", "data", "prices", "besi_hollow_hitam_2026-10-19.json")
SO = r"C:\Program Files\LibreOffice\program\soffice.exe"


def test_source_file_complete():
    d = json.load(open(SRC, encoding="utf-8"))
    assert len(d) == 297
    assert all("6M" in x["ukuran"] for x in d)


def test_rates_has_every_hollow_row_and_per_metre_is_bar_over_6():
    if not os.path.exists(SO):
        return
    t = tempfile.mkdtemp()
    shutil.copy(GOLDEN_MASTER_PATH, os.path.join(t, "g.xlsx"))
    subprocess.run([SO, "--headless", "--convert-to", "xlsx", "--outdir", os.path.join(t, "o"), os.path.join(t, "g.xlsx")],
                   check=True, timeout=240, capture_output=True)
    ws = openpyxl.load_workbook(os.path.join(t, "o", "g.xlsx"), data_only=True)["RATES"]
    got = {r[0]: r for r in ws.iter_rows(values_only=True) if isinstance(r[0], str) and r[0].startswith("HOLLOW-")}
    assert len(got) == 297
    for x in json.load(open(SRC, encoding="utf-8")):
        m = re.search(r"Hollow (\d+) x (\d+) x ([\d.]+)mm", x["ukuran"])
        code = f"HOLLOW-{m[1]}x{m[2]}x{float(m[3]):g}"
        price = int(re.sub(r"\D", "", x["harga"]))
        assert abs(got[code][2] - price / 6) < 0.01, code
        assert got[code][6] == price
