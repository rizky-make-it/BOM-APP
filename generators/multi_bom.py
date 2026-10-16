"""
Multi-Item BOM Workbook Generator for Living Ikon standard.
Generates 1 single workbook containing B41, B51, B61 with Front View images and ITEMS rollup.
"""

import sys
import os
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Any

import openpyxl
from openpyxl.drawing.image import Image as XLImage

try:
    from bom_app.config import GOLDEN_MASTER_PATH, DEFAULT_RATES
    from bom_app.models.item import BOMSpecification, ItemHeader, SolidPart, PanelPart, HardwarePart
    from bom_app.core.costing_engine import calculate_bom_costing
    from bom_app.core.writer import enable_cached_writer, clear_active_cache
except (ImportError, ModuleNotFoundError):
    from config import GOLDEN_MASTER_PATH, DEFAULT_RATES
    from models.item import BOMSpecification, ItemHeader, SolidPart, PanelPart, HardwarePart
    from core.costing_engine import calculate_bom_costing
    from core.writer import enable_cached_writer, clear_active_cache

SO_PATH = r"C:\Program Files\LibreOffice\program\soffice.exe"

def get_workbook_rates() -> Dict[str, float]:
    rates = {}
    wb = openpyxl.load_workbook(GOLDEN_MASTER_PATH, data_only=True)
    ws = wb["RATES"]
    for r in ws.iter_rows(values_only=True):
        if isinstance(r[0], str) and re.fullmatch(r'PLY-\d+-[A-Z]{3}', r[0]):
            vals = [x for x in r[1:4] if isinstance(x, (int, float))]
            if vals:
                rates[r[0]] = float(vals[0])
    return rates

def sort_by_part_number(item):
    label = getattr(item, 'label', str(item))
    m = re.search(r'\d+', label)
    if m:
        num = int(m.group(0))
        if num in (601, 7, 20):
            return (0, 0, label)
        return (0, num, label)
    return (1, 999, label)

def build_multi_bom(specs: List[Dict[str, Any]], output_path: str):
    wb = openpyxl.load_workbook(GOLDEN_MASTER_PATH, data_only=False)
    ws_items = wb["ITEMS"]
    
    # Rates from updated GOLDEN_MASTER
    custom_rates = get_workbook_rates()

    cached_map = {}

    # Setup each item tab
    for idx, item_dict in enumerate(specs):
        if isinstance(item_dict, BOMSpecification):
            spec: BOMSpecification = item_dict
            front_img_path = None
        elif isinstance(item_dict, dict) and "spec" in item_dict:
            spec: BOMSpecification = item_dict["spec"]
            front_img_path = item_dict.get("front_img_path", None)
        else:
            spec: BOMSpecification = item_dict
            front_img_path = None

        # Sort components by part number ascending
        spec.solid_parts.sort(key=sort_by_part_number)
        spec.panel_parts.sort(key=sort_by_part_number)
        spec.hardware_parts.sort(key=sort_by_part_number)

        row_num = 6 + idx
        header = spec.header
        item_code = header.item_code

        # 1. Cost calculation
        cost_data = calculate_bom_costing(spec, custom_rates)

        # 2. Worksheet creation/reuse
        if item_code in wb.sheetnames:
            ws = wb[item_code]
        elif idx == 0 and "LV453-B61" in wb.sheetnames and item_code != "LV453-B61":
            # We can clone from TEMPLATE
            ws = wb.copy_worksheet(wb["TEMPLATE"])
            ws.title = item_code
        else:
            ws = wb.copy_worksheet(wb["TEMPLATE"])
            ws.title = item_code

        ws.views.sheetView[0].showGridLines = True

        # 3. Handle Front View Image
        if hasattr(ws, "_images"):
            ws._images.clear()
        
        if front_img_path and os.path.exists(front_img_path):
            img = XLImage(front_img_path)
            # Scale to fit box neatly (~300px width)
            aspect = img.height / img.width
            img.width = 300
            img.height = int(300 * aspect)
            ws.add_image(img, "K1")

        # 4. Populate ITEMS row
        ws_items[f"A{row_num}"] = idx + 1
        ws_items[f"B{row_num}"] = header.collection.split("/")[0].strip()
        ws_items[f"C{row_num}"] = item_code
        ws_items[f"D{row_num}"] = header.item_name
        ws_items[f"E{row_num}"] = header.overall_l
        ws_items[f"F{row_num}"] = header.overall_w
        ws_items[f"G{row_num}"] = header.overall_h
        ws_items[f"H{row_num}"] = header.order_qty
        ws_items[f"I{row_num}"] = header.drawing_link
        ws_items[f"W{row_num}"] = header.collection.split("/")[-1].strip() if "/" in header.collection else "Bedroom"
        ws_items[f"X{row_num}"] = header.notes or f"Koleksi {header.collection} — {header.item_name}"

        # Populate ITEMS formulas for row_num
        ws_items[f"J{row_num}"] = f"=IF($C{row_num}=\"\",\"\",IF(ISERROR(INDIRECT(\"'\"&$C{row_num}&\"'!C1\")),\"no tab yet\",IF(N(Y{row_num})+N(AA{row_num})=0,\"tab empty\",IF(N(T{row_num})>0,\"check inputs\",\"costed\"))))"
        ws_items[f"K{row_num}"] = f"=IF(OR($J{row_num}=\"\",$J{row_num}=\"no tab yet\",$J{row_num}=\"tab empty\"),\"\",IFERROR(INDIRECT(\"'\"&$C{row_num}&\"'!D87\")+INDIRECT(\"'\"&$C{row_num}&\"'!D88\"),\"\"))"
        ws_items[f"L{row_num}"] = f"=IF(OR($J{row_num}=\"\",$J{row_num}=\"no tab yet\",$J{row_num}=\"tab empty\"),\"\",IFERROR(INDIRECT(\"'\"&$C{row_num}&\"'!D89\"),\"\"))"
        ws_items[f"M{row_num}"] = f"=IF(OR($J{row_num}=\"\",$J{row_num}=\"no tab yet\",$J{row_num}=\"tab empty\"),\"\",IFERROR(SUM(INDIRECT(\"'\"&$C{row_num}&\"'!D90:D93\")),\"\"))"
        ws_items[f"N{row_num}"] = f"=IF(OR($J{row_num}=\"\",$J{row_num}=\"no tab yet\",$J{row_num}=\"tab empty\"),\"\",IFERROR(INDIRECT(\"'\"&$C{row_num}&\"'!D94\"),\"\"))"
        ws_items[f"O{row_num}"] = f"=IF(OR($J{row_num}=\"\",$J{row_num}=\"no tab yet\",$J{row_num}=\"tab empty\"),\"\",IFERROR(INDIRECT(\"'\"&$C{row_num}&\"'!D95\"),\"\"))"
        ws_items[f"P{row_num}"] = f"=IF(OR($J{row_num}=\"\",$J{row_num}=\"no tab yet\",$J{row_num}=\"tab empty\"),\"\",IFERROR(INDIRECT(\"'\"&$C{row_num}&\"'!D97\")+INDIRECT(\"'\"&$C{row_num}&\"'!D98\"),\"\"))"
        ws_items[f"Q{row_num}"] = f"=IF(OR($J{row_num}=\"\",$J{row_num}=\"no tab yet\",$J{row_num}=\"tab empty\"),\"\",IFERROR(INDIRECT(\"'\"&$C{row_num}&\"'!D99\"),\"\"))"
        ws_items[f"R{row_num}"] = f"=IF(AND(ISNUMBER(H{row_num}),ISNUMBER(Q{row_num})),H{row_num}*Q{row_num},\"\")"
        ws_items[f"S{row_num}"] = f"=IFERROR(INDIRECT(\"'\"&$C{row_num}&\"'!D86\")+0,\"\")"
        ws_items[f"T{row_num}"] = f"=IFERROR(INDIRECT(\"'\"&$C{row_num}&\"'!D102\")+0,\"\")"
        ws_items[f"Y{row_num}"] = f"=IFERROR(INDIRECT(\"'\"&$C{row_num}&\"'!D82\")+0,\"\")"
        ws_items[f"Z{row_num}"] = f"=IFERROR(INDIRECT(\"'\"&$C{row_num}&\"'!D84\")+0,\"\")"
        ws_items[f"AA{row_num}"] = f"=IFERROR(INDIRECT(\"'\"&$C{row_num}&\"'!D89\")+INDIRECT(\"'\"&$C{row_num}&\"'!D94\"),\"\")"

        # Cache values for ITEMS
        cached_map[("ITEMS", f"J{row_num}")] = "costed"
        cached_map[("ITEMS", f"K{row_num}")] = cost_data["timber_cost"] + cost_data["fasteners_cost"]
        cached_map[("ITEMS", f"L{row_num}")] = cost_data["panels_cost"]
        cached_map[("ITEMS", f"M{row_num}")] = cost_data["finishing_total"]
        cached_map[("ITEMS", f"N{row_num}")] = cost_data["hardware_cost"]
        cached_map[("ITEMS", f"O{row_num}")] = cost_data["pack_cost"]
        cached_map[("ITEMS", f"P{row_num}")] = cost_data["misc_cost"] + cost_data["overhead_cost"]
        cached_map[("ITEMS", f"Q{row_num}")] = cost_data["unit_cost"]
        cached_map[("ITEMS", f"R{row_num}")] = cost_data["unit_cost"] * header.order_qty
        cached_map[("ITEMS", f"S{row_num}")] = cost_data["carton_m3"]
        cached_map[("ITEMS", f"T{row_num}")] = 0
        cached_map[("ITEMS", f"Y{row_num}")] = cost_data["solid_vol"]
        cached_map[("ITEMS", f"Z{row_num}")] = cost_data["exposed_face_m2"]
        cached_map[("ITEMS", f"AA{row_num}")] = cost_data["panels_cost"] + cost_data["hardware_cost"]

        # 5. Populate Product Sheet Header
        ws["C1"] = item_code
        ws["D4"] = header.drawing_link
        ws["D11"] = header.overall_l
        ws["E11"] = header.overall_w
        ws["F11"] = header.overall_h
        ws["G11"] = 1

        cached_map[(item_code, "G1")] = header.overall_l
        cached_map[(item_code, "C2")] = header.item_name
        cached_map[(item_code, "G2")] = header.overall_w
        cached_map[(item_code, "C3")] = header.collection
        cached_map[(item_code, "G3")] = header.overall_h
        cached_map[(item_code, "C4")] = header.order_qty
        cached_map[(item_code, "G4")] = header.drawing_link
        cached_map[(item_code, "C7")] = header.notes or f"Koleksi {header.collection} — {header.item_name}"

        # 6. Solid Wood (Rows 18-42)
        for s_idx, (part, calc) in enumerate(zip(spec.solid_parts, cost_data["solid_rows"]), 18):
            ws[f"A{s_idx}"] = float(s_idx - 17)
            ws[f"B{s_idx}"] = part.material
            ws[f"C{s_idx}"] = part.label
            ws[f"D{s_idx}"] = part.component
            ws[f"E{s_idx}"] = part.l
            ws[f"F{s_idx}"] = part.w
            ws[f"G{s_idx}"] = part.t
            ws[f"H{s_idx}"] = part.qty
            ws[f"I{s_idx}"] = part.exposed
            ws[f"J{s_idx}"] = part.curved
            ws[f"K{s_idx}"] = part.tier_override
            ws[f"L{s_idx}"] = part.note

            cached_map[(item_code, f"M{s_idx}")] = calc["vol"]
            cached_map[(item_code, f"N{s_idx}")] = calc["face"]
            cached_map[(item_code, f"O{s_idx}")] = calc["tier"]
            cached_map[(item_code, f"R{s_idx}")] = calc["check"]
            cached_map[(item_code, f"S{s_idx}")] = calc["rate"]
            cached_map[(item_code, f"T{s_idx}")] = calc["cost"]

        for r in range(18 + len(spec.solid_parts), 43):
            ws[f"A{r}"] = float(r - 17)
            for c_let in ["B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]:
                ws[f"{c_let}{r}"] = None

        # 7. Panels (Rows 46-60)
        for p_idx, (part, calc) in enumerate(zip(spec.panel_parts, cost_data["panel_rows"]), 46):
            ws[f"A{p_idx}"] = float(p_idx - 45)
            ws[f"B{p_idx}"] = part.panel_type
            ws[f"C{p_idx}"] = part.label
            ws[f"D{p_idx}"] = part.component
            ws[f"E{p_idx}"] = part.l
            ws[f"F{p_idx}"] = part.w
            ws[f"G{p_idx}"] = part.t
            ws[f"H{p_idx}"] = part.qty
            ws[f"I{p_idx}"] = part.exposed_faces
            ws[f"L{p_idx}"] = part.note

            cached_map[(item_code, f"M{p_idx}")] = calc["vol"]
            cached_map[(item_code, f"N{p_idx}")] = calc["face"]
            cached_map[(item_code, f"O{p_idx}")] = calc["yield_cut"]
            cached_map[(item_code, f"P{p_idx}")] = calc["sheets"]
            cached_map[(item_code, f"Q{p_idx}")] = calc["waste_pct"]
            cached_map[(item_code, f"R{p_idx}")] = calc["check"]
            cached_map[(item_code, f"S{p_idx}")] = calc["rate"]
            cached_map[(item_code, f"T{p_idx}")] = calc["cost"]

        for r in range(46 + len(spec.panel_parts), 61):
            ws[f"A{r}"] = float(r - 45)
            for c_let in ["B", "C", "D", "E", "F", "G", "H", "I", "L"]:
                ws[f"{c_let}{r}"] = None

        # 8. Hardware (Rows 64-78)
        for h_idx, (part, calc) in enumerate(zip(spec.hardware_parts, cost_data["hw_rows"]), 64):
            ws[f"A{h_idx}"] = float(h_idx - 63)
            ws[f"B{h_idx}"] = part.item_master_code
            ws[f"C{h_idx}"] = part.label
            ws[f"D{h_idx}"] = part.description
            ws[f"E{h_idx}"] = part.vendor
            ws[f"H{h_idx}"] = part.qty
            ws[f"I{h_idx}"] = part.uom
            ws[f"L{h_idx}"] = part.note
            ws[f"S{h_idx}"] = part.unit_price
            ws[f"T{h_idx}"] = f"=IF(OR(H{h_idx}=\"\",S{h_idx}=\"\"),\"\",H{h_idx}*S{h_idx})"
            cached_map[(item_code, f"T{h_idx}")] = calc["cost"]

        for r in range(64 + len(spec.hardware_parts), 79):
            ws[f"A{r}"] = float(r - 63)
            for c_let in ["B", "C", "D", "E", "H", "I", "L", "S", "T"]:
                ws[f"{c_let}{r}"] = None

        # 9. Summary Cache Block (D82-D102)
        cached_map[(item_code, "D82")] = cost_data["solid_vol"]
        cached_map[(item_code, "D83")] = cost_data["panel_sheets"]
        cached_map[(item_code, "D84")] = cost_data["exposed_face_m2"]
        cached_map[(item_code, "D85")] = 1
        cached_map[(item_code, "D86")] = cost_data["carton_m3"]
        cached_map[(item_code, "D87")] = cost_data["timber_cost"]
        cached_map[(item_code, "D88")] = cost_data["fasteners_cost"]
        cached_map[(item_code, "D89")] = cost_data["panels_cost"]
        cached_map[(item_code, "D90")] = cost_data["fin_mat_cost"]
        cached_map[(item_code, "D91")] = cost_data["sand_mat_cost"]
        cached_map[(item_code, "D92")] = cost_data["sand_lab_cost"]
        cached_map[(item_code, "D93")] = cost_data["fin_lab_cost"]
        cached_map[(item_code, "D94")] = cost_data["hardware_cost"]
        cached_map[(item_code, "D95")] = cost_data["pack_cost"]
        cached_map[(item_code, "D96")] = cost_data["direct_cost"]
        cached_map[(item_code, "D97")] = cost_data["misc_cost"]
        cached_map[(item_code, "D98")] = cost_data["overhead_cost"]
        cached_map[(item_code, "D99")] = cost_data["unit_cost"]
        cached_map[(item_code, "D100")] = cost_data["carton_m2"]
        cached_map[(item_code, "D101")] = cost_data["unit_cost"] * header.order_qty
        cached_map[(item_code, "D102")] = 0

    # If original LV453-B61 was in template but not in specs or replaced, remove if necessary
    spec_codes = [
        s.header.item_code if isinstance(s, BOMSpecification) else (s["spec"].header.item_code if isinstance(s, dict) and "spec" in s else s.header.item_code)
        for s in specs
    ]
    if "LV453-B61" in wb.sheetnames and "LV453-B61" not in spec_codes:
        wb.remove(wb["LV453-B61"])

    raw_path = output_path.replace(".xlsx", "_raw.xlsx")
    enable_cached_writer(cached_map)
    wb.save(raw_path)
    clear_active_cache()

    # Recalculate with LibreOffice headless
    work_dir = os.path.dirname(os.path.abspath(output_path))
    rc_dir = os.path.join(work_dir, "rc_multi")
    shutil.rmtree(rc_dir, ignore_errors=True)
    os.makedirs(rc_dir, exist_ok=True)
    
    subprocess.run([SO_PATH, "--headless", "--convert-to", "xlsx", "--outdir", rc_dir, raw_path], check=True, timeout=240)
    recalc_file = os.path.join(rc_dir, os.path.basename(raw_path))
    shutil.copy(recalc_file, output_path)
    os.remove(raw_path)
    shutil.rmtree(rc_dir, ignore_errors=True)
    print(f"[SUCCESS] Multi-item BOM created and verified: {output_path}")

if __name__ == "__main__":
    pass
