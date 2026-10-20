"""One command: DWG (drafter 2D, labelled) -> components (tags + schedule PDF) -> spec.json -> costed BOM workbook.

python tools/dwg2bom.py <dwg> --item CODE --name NAME [--collection X] [--overall LxWxH] [--out DIR]
"""
import argparse, datetime, json, os, subprocess, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..")); sys.path.insert(0, ROOT)
ap = argparse.ArgumentParser(); ap.add_argument("dwg"); ap.add_argument("--item", required=True); ap.add_argument("--name", default="")
ap.add_argument("--collection", default="FROM-DWG"); ap.add_argument("--overall"); ap.add_argument("--out", default=os.path.join(ROOT, "data", "from_dwg"))
a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
py = sys.executable
r = subprocess.run([py, os.path.join(ROOT, "tools", "dwg2d_components.py"), a.dwg, "--item", a.item, "--name", a.name, "--out", a.out], capture_output=True, text=True)
print(r.stdout.splitlines()[0] if r.stdout else r.stderr[-800:])
if r.returncode: sys.exit(r.returncode)
cmd = [py, os.path.join(ROOT, "tools", "dwg2d_to_spec.py"), os.path.join(a.out, f"{a.item}_components.json"), "--collection", a.collection, "--out", a.out]
if a.overall: cmd += ["--overall", a.overall]
r = subprocess.run(cmd, capture_output=True, text=True); print(r.stdout.strip() or r.stderr[-800:])
if r.returncode: sys.exit(r.returncode)
from generators.multi_bom import build_multi_bom
from models.item import BOMSpecification, ItemHeader, SolidPart, PanelPart, HardwarePart
d = json.load(open(os.path.join(a.out, a.item.lower().replace("-", "_") + "_spec.json"), encoding="utf-8"))
spec = BOMSpecification(ItemHeader(**d["header"]), [SolidPart(**x) for x in d["solid_parts"]], [PanelPart(**x) for x in d["panel_parts"]], [HardwarePart(**x) for x in d["hardware_parts"]])
xlsx = os.path.join(a.out, f"{a.item} BOM from DWG {datetime.datetime.now():%Y%m%d-%H%M%S}.xlsx")
build_multi_bom([{"spec": spec}], xlsx)
print("workbook:", xlsx)
