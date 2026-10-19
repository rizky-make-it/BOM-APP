"""Build NAPIER COLLECTION BOM from data/napier/*_spec.json (specs come from data/napier/build_specs.py).
Run from repo root:  python data/napier/build.py"""
import json, os, sys, datetime
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT); os.chdir(ROOT)
from models.item import ItemHeader, SolidPart, PanelPart, HardwarePart, BOMSpecification
from generators.multi_bom import build_multi_bom

specs = []
for code in json.load(open("data/napier/_order.json")):
    d = json.load(open(f"data/napier/lv433_{code[-3:].lower()}_spec.json", encoding="utf-8"))
    spec = BOMSpecification(ItemHeader(**d["header"]), [SolidPart(**x) for x in d["solid_parts"]],
                            [PanelPart(**x) for x in d["panel_parts"]], [HardwarePart(**x) for x in d["hardware_parts"]])
    img = f"data/napier/render/{code[-3:]}.png"
    specs.append({"spec": spec, "front_img_path": img if os.path.exists(img) else None})
out = f"NAPIER COLLECTION BOM {datetime.datetime.now():%Y%m%d-%H%M%S}.xlsx"
build_multi_bom(specs, out)
