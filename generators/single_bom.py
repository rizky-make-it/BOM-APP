"""
Canonical Single-Item BOM Workbook Generator.
Strictly clones from Golden Master without shifting columns or breaking formulas.
"""

import re
from pathlib import Path
import openpyxl
try:
    from ..config import GOLDEN_MASTER_PATH
    from ..models.item import BOMSpecification
    from ..core.costing_engine import calculate_bom_costing
    from ..core.writer import enable_cached_writer, clear_active_cache
except (ImportError, ValueError):
    from config import GOLDEN_MASTER_PATH
    from models.item import BOMSpecification
    from core.costing_engine import calculate_bom_costing
    from core.writer import enable_cached_writer, clear_active_cache

def sort_by_part_number(item):
    label = getattr(item, 'label', str(item))
    m = re.search(r'\d+', label)
    if m:
        return (0, int(m.group(0)), label)
    return (1, 999, label)

def build_single_bom_workbook(spec: BOMSpecification, output_path: str, custom_rates: dict = None) -> dict:
    if not GOLDEN_MASTER_PATH.exists():
        raise FileNotFoundError(f"Golden Master template missing at {GOLDEN_MASTER_PATH}")

    # Sort components by catalog part number ascending
    spec.solid_parts.sort(key=sort_by_part_number)
    spec.panel_parts.sort(key=sort_by_part_number)
    spec.hardware_parts.sort(key=sort_by_part_number)

    # Compute all values
    cost_data = calculate_bom_costing(spec, custom_rates)
    header = spec.header
    item_code = header.item_code

    # Load workbook from Golden Master
    wb = openpyxl.load_workbook(GOLDEN_MASTER_PATH, data_only=False)

    # Rename canonical product sheet (LV453-B61) to the new item_code
    if "LV453-B61" in wb.sheetnames:
        ws = wb["LV453-B61"]
        ws.title = item_code
    else:
        # Clone from TEMPLATE
        ws = wb.copy_worksheet(wb["TEMPLATE"])
        ws.title = item_code

    # Remove any leftover images from template
    if hasattr(ws, "_images"):
        ws._images.clear()

    ws.views.sheetView[0].showGridLines = True
    cached_map = {}

    # 1. Populate ITEMS sheet row 6
    ws_items = wb["ITEMS"]
    ws_items["C6"] = item_code
    ws_items["D6"] = header.item_name
    ws_items["E6"] = header.overall_l
    ws_items["F6"] = header.overall_w
    ws_items["G6"] = header.overall_h
    ws_items["H6"] = header.order_qty
    ws_items["I6"] = header.drawing_link
    ws_items["V6"] = header.spec_link
    ws_items["W6"] = header.collection.split("/")[-1].strip() if "/" in header.collection else "Bedroom"
    ws_items["X6"] = header.notes or f"Koleksi {header.collection} — {header.item_name}"

    cached_map[("ITEMS", "J6")] = "costed"
    cached_map[("ITEMS", "K6")] = cost_data["timber_cost"] + cost_data["fasteners_cost"]
    cached_map[("ITEMS", "L6")] = cost_data["panels_cost"]
    cached_map[("ITEMS", "M6")] = cost_data["finishing_total"]
    cached_map[("ITEMS", "N6")] = cost_data["hardware_cost"]
    cached_map[("ITEMS", "O6")] = cost_data["pack_cost"]
    cached_map[("ITEMS", "P6")] = cost_data["misc_cost"] + cost_data["overhead_cost"]
    cached_map[("ITEMS", "Q6")] = cost_data["unit_cost"]
    cached_map[("ITEMS", "R6")] = cost_data["unit_cost"] * header.order_qty
    cached_map[("ITEMS", "S6")] = cost_data["carton_m3"]
    cached_map[("ITEMS", "T6")] = 0
    cached_map[("ITEMS", "Y6")] = cost_data["solid_vol"]
    cached_map[("ITEMS", "Z6")] = cost_data["exposed_face_m2"]
    cached_map[("ITEMS", "AA6")] = cost_data["panels_cost"] + cost_data["hardware_cost"]

    # 2. Configure Header on Product Sheet
    ws["C1"] = item_code
    ws["D4"] = header.drawing_link

    # Packing row 11
    ws["E11"] = header.overall_l
    ws["F11"] = header.overall_w
    ws["G11"] = header.overall_h
    ws["H11"] = 1

    # Header Array Formula cache
    cached_map[(item_code, "G1")] = header.overall_l
    cached_map[(item_code, "C2")] = header.item_name
    cached_map[(item_code, "G2")] = header.overall_w
    cached_map[(item_code, "C3")] = header.collection
    cached_map[(item_code, "G3")] = header.overall_h
    cached_map[(item_code, "C4")] = header.order_qty
    cached_map[(item_code, "G4")] = header.drawing_link
    cached_map[(item_code, "G5")] = header.spec_link
    cached_map[(item_code, "C7")] = header.notes or f"Koleksi {header.collection} — {header.item_name}"

    # 3. Populate Solid Wood components (Rows 18-42)
    for idx, (part, calc) in enumerate(zip(spec.solid_parts, cost_data["solid_rows"]), 18):
        ws[f"A{idx}"] = float(idx - 17)
        ws[f"B{idx}"] = part.material
        ws[f"C{idx}"] = part.label
        ws[f"D{idx}"] = part.component
        ws[f"E{idx}"] = part.l
        ws[f"F{idx}"] = part.w
        ws[f"G{idx}"] = part.t
        ws[f"H{idx}"] = part.qty
        ws[f"I{idx}"] = part.exposed
        ws[f"J{idx}"] = part.curved
        ws[f"K{idx}"] = part.tier_override
        ws[f"L{idx}"] = part.note

        cached_map[(item_code, f"M{idx}")] = calc["vol"]
        cached_map[(item_code, f"N{idx}")] = calc["face"]
        cached_map[(item_code, f"O{idx}")] = calc["tier"]
        cached_map[(item_code, f"R{idx}")] = calc["check"]
        cached_map[(item_code, f"S{idx}")] = calc["rate"]
        cached_map[(item_code, f"T{idx}")] = calc["cost"]

    # Clear unused solid wood rows
    start_clear_solid = 18 + len(spec.solid_parts)
    for r in range(start_clear_solid, 43):
        ws[f"A{r}"] = float(r - 17)
        for c_let in ["B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]:
            ws[f"{c_let}{r}"] = None

    # 4. Populate Panels components (Rows 46-60)
    for idx, (part, calc) in enumerate(zip(spec.panel_parts, cost_data["panel_rows"]), 46):
        ws[f"A{idx}"] = float(idx - 45)
        ws[f"B{idx}"] = part.panel_type
        ws[f"C{idx}"] = part.label
        ws[f"D{idx}"] = part.component
        ws[f"E{idx}"] = part.l
        ws[f"F{idx}"] = part.w
        ws[f"G{idx}"] = part.t
        ws[f"H{idx}"] = part.qty
        ws[f"I{idx}"] = part.exposed_faces
        ws[f"L{idx}"] = part.note

        cached_map[(item_code, f"M{idx}")] = calc["vol"]
        cached_map[(item_code, f"N{idx}")] = calc["face"]
        cached_map[(item_code, f"O{idx}")] = calc["yield_cut"]
        cached_map[(item_code, f"P{idx}")] = calc["sheets"]
        cached_map[(item_code, f"Q{idx}")] = calc["waste_pct"]
        cached_map[(item_code, f"R{idx}")] = calc["check"]
        cached_map[(item_code, f"S{idx}")] = calc["rate"]
        cached_map[(item_code, f"T{idx}")] = calc["cost"]

    start_clear_panel = 46 + len(spec.panel_parts)
    for r in range(start_clear_panel, 61):
        ws[f"A{r}"] = float(r - 45)
        for c_let in ["B", "C", "D", "E", "F", "G", "H", "I", "L"]:
            ws[f"{c_let}{r}"] = None

    # 5. Populate Hardware components (Rows 64-78)
    for idx, (part, calc) in enumerate(zip(spec.hardware_parts, cost_data["hw_rows"]), 64):
        ws[f"A{idx}"] = float(idx - 63)
        ws[f"B{idx}"] = part.item_master_code
        ws[f"C{idx}"] = part.label
        ws[f"D{idx}"] = part.description
        ws[f"E{idx}"] = part.vendor
        ws[f"H{idx}"] = part.qty
        ws[f"I{idx}"] = part.uom
        ws[f"L{idx}"] = part.note
        ws[f"S{idx}"] = part.unit_price
        ws[f"T{idx}"] = f"=IF(OR(H{idx}=\"\",S{idx}=\"\"),\"\",H{idx}*S{idx})"

        cached_map[(item_code, f"T{idx}")] = calc["cost"]

    start_clear_hw = 64 + len(spec.hardware_parts)
    for r in range(start_clear_hw, 79):
        ws[f"A{r}"] = float(r - 63)
        for c_let in ["B", "C", "D", "E", "H", "I", "L", "S", "T"]:
            ws[f"{c_let}{r}"] = None

    # 6. Cache Summary Block (Rows 82-102) in Column D
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

    # Enable cached writer and save
    enable_cached_writer(cached_map)
    wb.save(output_path)
    clear_active_cache()

    return cost_data
