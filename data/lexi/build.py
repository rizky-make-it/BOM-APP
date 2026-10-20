"""Build LEXI BOM workbook from data/lexi/*_spec.json (specs come from the drafter's 2D drawing via build_specs.py)."""
import json, os, sys, datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from generators.multi_bom import build_multi_bom
from models.item import BOMSpecification, ItemHeader, SolidPart, PanelPart, HardwarePart
specs = []
for code in json.load(open("data/lexi/_order.json")):
    d = json.load(open(f"data/lexi/{code.lower().replace('-', '_')}_spec.json", encoding="utf-8"))
    specs.append({"spec": BOMSpecification(ItemHeader(**d["header"]), [SolidPart(**x) for x in d["solid_parts"]],
                                           [PanelPart(**x) for x in d["panel_parts"]], [HardwarePart(**x) for x in d["hardware_parts"]])})
out = sys.argv[1] if len(sys.argv) > 1 else f"LEXI COLLECTION BOM {datetime.datetime.now():%Y%m%d-%H%M%S}.xlsx"
build_multi_bom(specs, out)
