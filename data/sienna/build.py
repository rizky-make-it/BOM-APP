"""Build SIENNA COLLECTION BOM from data/sienna/*_spec.json (+ renders in data/sienna/img).
Run from repo root:  python data/sienna/build.py"""
import json, os, sys, datetime
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT); os.chdir(ROOT)
from models.item import ItemHeader, SolidPart, PanelPart, HardwarePart, BOMSpecification
from generators.multi_bom import build_multi_bom

IMG = "data/sienna/img"
FRONT = {c: f"{IMG}/{f}" for c, f in {
    "LV463-B42": "LV463-B42_0.png", "LV463-B51": "LV463-B51_0.png", "LV463-B71": "LV463-B71_0.png",
    "LV463-D01": "LV463-D01_0.png", "LV463-B61": "LV463-B61_0.png",
    "LV463-B01": "LV463-B01_0.png", "LV463-B02": "LV463-B02_0.png",
    "LV446-L02": "LV446-L02_0.png", "LV446-L31": "LV446-L31_0.png"}.items()}
specs = []
for code in json.load(open("data/sienna/_order.json")):
    d = json.load(open(f"data/sienna/{code.lower().replace('-', '_')}_spec.json", encoding="utf-8"))
    spec = BOMSpecification(ItemHeader(**d["header"]), [SolidPart(**x) for x in d["solid_parts"]],
                            [PanelPart(**x) for x in d["panel_parts"]], [HardwarePart(**x) for x in d["hardware_parts"]])
    specs.append({"spec": spec, "front_img_path": FRONT.get(code)})
out = f"SIENNA COLLECTION BOM {datetime.datetime.now():%Y%m%d-%H%M%S}.xlsx"
build_multi_bom(specs, out)  # output has no TEMPLATE/LISTS/PART LIST REFERENCE/GAMBAR KOLEKSI
