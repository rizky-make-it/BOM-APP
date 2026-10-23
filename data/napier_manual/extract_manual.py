"""Extract the INPUT cells of the manual Napier workbook (item sheets) into BOM-APP spec JSON, unchanged.
usage: python extract_manual.py <xlsx> <outdir>"""
import json, os, sys
import openpyxl

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
wb = openpyxl.load_workbook(src, data_only=True)


def num(v):
    if v in (None, ""):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def s(v):
    return "" if v is None else str(v).strip()


order, report = [], []
for ws in wb.worksheets:
    if not ws.title.startswith("LV433-"):
        continue
    code = s(ws["C1"].value)
    hdr = dict(item_code=code, item_name=s(ws["C2"].value), collection=s(ws["C3"].value) or "NAPIER",
               overall_l=num(ws["G1"].value) or 0.0, overall_w=num(ws["G2"].value) or 0.0, overall_h=num(ws["G3"].value) or 0.0,
               order_qty=int(num(ws["C4"].value) or 1), drawing_link=s(ws["G4"].value) or s(ws["D4"].value),
               finish_recipe=s(ws["C5"].value) or "NC NATURAL", flatpack_yn=s(ws["C6"].value) or "N", notes=s(ws["C7"].value))
    solid, panel, hw, metal_like = [], [], [], 0
    for r in range(18, 43):
        d, e, f, g, h = (ws.cell(r, c).value for c in (4, 5, 6, 7, 8))
        if num(e) is None or num(h) is None:
            continue
        mat = s(ws.cell(r, 2).value) or "MINDI"
        if mat.upper().startswith(("METAL", "HOLLOW")) or mat[:1].isdigit():
            metal_like += 1
        solid.append(dict(label=s(ws.cell(r, 3).value), component=s(d), l=num(e), w=num(f) or 0.0, t=num(g) or 0.0, qty=int(num(h)),
                          material=mat, exposed=s(ws.cell(r, 9).value) or "Y", curved=s(ws.cell(r, 10).value) or "N",
                          tier_override=s(ws.cell(r, 11).value) or "B", note=s(ws.cell(r, 12).value)))
    for r in range(47, 61):
        e, h = ws.cell(r, 5).value, ws.cell(r, 8).value
        if num(e) is None or num(h) is None:
            continue
        panel.append(dict(label=s(ws.cell(r, 3).value), component=s(ws.cell(r, 4).value), panel_type=s(ws.cell(r, 2).value),
                          l=num(e), w=num(ws.cell(r, 6).value) or 0.0, t=num(ws.cell(r, 7).value) or 0.0, qty=int(num(h)),
                          exposed_faces=int(num(ws.cell(r, 9).value) or 0), note=s(ws.cell(r, 12).value)))
    for r in range(64, 79):
        h = ws.cell(r, 8).value
        if num(h) is None:
            continue
        hw.append(dict(item_master_code=s(ws.cell(r, 2).value) or "HARDWARE", label=s(ws.cell(r, 3).value), description=s(ws.cell(r, 4).value),
                       vendor=s(ws.cell(r, 5).value) or "Lokal", qty=num(h), uom=s(ws.cell(r, 9).value) or "pcs",
                       unit_price=num(ws.cell(r, 19).value) or 0.0, note=s(ws.cell(r, 12).value)))
    spec = dict(header=hdr, solid_parts=solid, panel_parts=panel, hardware_parts=hw)
    fn = f"{code.lower().replace('-', '_')}_spec.json"
    json.dump(spec, open(os.path.join(out, fn), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    order.append(code)
    report.append((code, len(solid), len(panel), len(hw), metal_like, hdr["overall_l"], hdr["overall_w"], hdr["overall_h"]))
json.dump(order, open(os.path.join(out, "_order.json"), "w"))
for r in report:
    print(r)
