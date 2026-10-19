"""
Mathematical Costing Engine for Factory BOM Calculation.
Calculates solid timber tier volumes, kerf panel nesting, finishing pool, and packaging.
"""

from typing import Dict, Any, Tuple
try:
    from ..config import DEFAULT_RATES, SHEET_L, SHEET_W, SHEET_KERF, CARTON_ADD
    from ..models.item import BOMSpecification
except (ImportError, ValueError):
    from config import DEFAULT_RATES, SHEET_L, SHEET_W, SHEET_KERF, CARTON_ADD
    from models.item import BOMSpecification

def calculate_bom_costing(spec: BOMSpecification, custom_rates: Dict[str, float] = None) -> Dict[str, Any]:
    rates = {**DEFAULT_RATES, **(custom_rates or {})}
    header = spec.header

    # 1. Solid Wood
    tot_solid_vol = 0.0
    tot_solid_face = 0.0
    tot_timber_cost = 0.0
    solid_calc_rows = []

    for idx, part in enumerate(spec.solid_parts, 18):
        v = (part.l * part.w * part.t / 1e9) * part.qty
        f = (part.l * part.w / 1e6) * part.qty if part.exposed == 'Y' else 0.0
        tier = part.tier_override
        rate_key = f"{part.material}_{tier.replace('-CURVED', 'C')}"  # A-CURVED -> AC
        if part.material == "METAL":
            rate = rates.get(rate_key) or 0.0  # metal rate card still blank -> cost 0 until priced
        else:
            rate = rates.get(rate_key, rates.get("MINDI_B", 16465427.66))
        cost = v * rate

        tot_solid_vol += v
        tot_solid_face += f
        tot_timber_cost += cost

        solid_calc_rows.append({
            "row": idx,
            "vol": v,
            "face": (part.l * part.w / 1e6) * part.qty,
            "tier": tier,
            "rate": rate,
            "cost": cost,
            "check": "OK"
        })

    # 2. Panels
    tot_panel_sheets = 0.0
    tot_panel_cost = 0.0
    tot_panel_face = 0.0
    panel_calc_rows = []

    for idx, part in enumerate(spec.panel_parts, 46):
        v = (part.l * part.w * part.t / 1e9) * part.qty
        f = (part.l * part.w / 1e6) * part.qty * part.exposed_faces
        yield_cut = max(
            int(SHEET_L / (part.l + SHEET_KERF)) * int(SHEET_W / (part.w + SHEET_KERF)),
            int(SHEET_L / (part.w + SHEET_KERF)) * int(SHEET_W / (part.l + SHEET_KERF))
        )
        sheets = part.qty / yield_cut if yield_cut > 0 else 1.0
        if part.panel_type not in rates:
            raise KeyError(f"No price for panel type {part.panel_type!r} in the rate table. Add it to RATES / config instead of guessing.")
        rate = rates[part.panel_type]

        # Waste markup threshold logic from RATES!C97 (50%) and RATES!C98 (15%)
        used_area = part.qty * part.l * part.w
        sheet_area = int(sheets + 0.9999) * SHEET_L * SHEET_W
        waste_pct = 1.0 - (used_area / sheet_area) if sheet_area > 0 else 0.0

        if waste_pct > 0.50:
            charged_sheets = sheets * 1.15
        else:
            charged_sheets = int(sheets + 0.9999)

        cost = charged_sheets * rate
        tot_panel_sheets += charged_sheets
        tot_panel_face += f
        tot_panel_cost += cost

        panel_calc_rows.append({
            "row": idx,
            "vol": v,
            "face": (part.l * part.w / 1e6) * part.qty,
            "yield_cut": yield_cut,
            "sheets": sheets,
            "waste_pct": waste_pct,
            "rate": rate,
            "cost": cost,
            "check": "OK"
        })

    # 3. Hardware
    tot_hw_cost = 0.0
    hw_calc_rows = []

    for idx, part in enumerate(spec.hardware_parts, 64):
        cost = part.qty * part.unit_price
        tot_hw_cost += cost
        hw_calc_rows.append({
            "row": idx,
            "cost": cost
        })

    # 4. Finishing, Sanding & Fasteners
    tot_exposed_face = tot_solid_face + tot_panel_face
    fasteners_cost = tot_solid_vol * rates["FASTENERS_RATE"]

    if header.finish_recipe == "NONE (RAW)":
        fin_mat_cost = 0.0
        sand_mat_cost = 0.0
        sand_lab_cost = 0.0
        fin_lab_cost = 0.0
    else:
        fin_mat_cost = tot_exposed_face * rates["FIN_MAT_RATE"]
        sand_mat_cost = tot_exposed_face * rates["SAND_MAT_RATE"]
        sand_lab_cost = tot_exposed_face * rates["SAND_LAB_RATE"]
        fin_lab_cost = tot_exposed_face * rates["FIN_LAB_RATE"]

    tot_finishing_cost = fin_mat_cost + sand_mat_cost + sand_lab_cost + fin_lab_cost

    # 5. Packaging (Overall Dimensions + 40mm)
    box_l = header.overall_l + CARTON_ADD
    box_w = header.overall_w + CARTON_ADD
    box_h = header.overall_h + CARTON_ADD

    box_m2 = 2 * (box_l * box_w + box_l * box_h + box_w * box_h) / 1e6
    box_m3 = (box_l * box_w * box_h) / 1e9
    pack_cost = box_m2 * rates["CARTON_M2_RATE"] + box_m3 * rates["PACK_LAB_RATE"]

    # 6. Roll-up
    direct_cost = (
        tot_timber_cost +
        fasteners_cost +
        tot_panel_cost +
        tot_finishing_cost +
        tot_hw_cost +
        pack_cost
    )
    misc_cost = direct_cost * rates["MISC_PCT"]
    oh_cost = (direct_cost + misc_cost) * rates["OH_PCT"]
    unit_cost = direct_cost + misc_cost + oh_cost

    return {
        "solid_vol": tot_solid_vol,
        "panel_sheets": tot_panel_sheets,
        "exposed_face_m2": tot_exposed_face,
        "carton_m3": box_m3,
        "carton_m2": box_m2,
        "timber_cost": tot_timber_cost,
        "fasteners_cost": fasteners_cost,
        "panels_cost": tot_panel_cost,
        "fin_mat_cost": fin_mat_cost,
        "sand_mat_cost": sand_mat_cost,
        "sand_lab_cost": sand_lab_cost,
        "fin_lab_cost": fin_lab_cost,
        "finishing_total": tot_finishing_cost,
        "hardware_cost": tot_hw_cost,
        "pack_cost": pack_cost,
        "direct_cost": direct_cost,
        "misc_cost": misc_cost,
        "overhead_cost": oh_cost,
        "unit_cost": unit_cost,
        "open_checks": 0,
        "solid_rows": solid_calc_rows,
        "panel_rows": panel_calc_rows,
        "hw_rows": hw_calc_rows
    }
