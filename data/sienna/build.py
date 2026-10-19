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
    "LV463-B01": "LV463-B01_0.png", "LV463-B02": "LV463-B02_0.png"}.items()}
specs = []
for code in json.load(open("data/sienna/_order.json")):
    d = json.load(open(f"data/sienna/{code.lower().replace('-', '_')}_spec.json", encoding="utf-8"))
    spec = BOMSpecification(ItemHeader(**d["header"]), [SolidPart(**x) for x in d["solid_parts"]],
                            [PanelPart(**x) for x in d["panel_parts"]], [HardwarePart(**x) for x in d["hardware_parts"]])
    specs.append({"spec": spec, "front_img_path": FRONT.get(code)})
gallery = {"title": "SIENNA COLLECTION — SUITE GAMBAR & RENDER 3D",
           "subtitle": "Koleksi Mebel Kayu Mindi Solid, Multiplek Veneer & Aksen Metal Brass",
           "items": [("LV463-B42 — 2 DRAWERS & SHELF BEDSIDE (550 x 400 x 550 mm)", f"{IMG}/GAMBAR KOLEKSI_0.png"),
                     ("LV463-B51 — 2 OVER 4 DRAWERS TALLBOY (900 x 450 x 1200 mm)", f"{IMG}/GAMBAR KOLEKSI_1.png"),
                     ("LV463-B71 — MIRROR (1000 x 26 x 1000 mm)", f"{IMG}/GAMBAR KOLEKSI_2.png"),
                     ("LV463-D01 — RECTANGULAR DINNING TABLE (2200 x 1000 x 760 mm)", f"{IMG}/GAMBAR KOLEKSI_3.png")]}
out = f"SIENNA COLLECTION BOM {datetime.datetime.now():%Y%m%d-%H%M%S}.xlsx"
build_multi_bom(specs, out)  # output has no TEMPLATE/LISTS/PART LIST REFERENCE/GAMBAR KOLEKSI
