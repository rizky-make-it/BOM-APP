"""
Mathematical Costing Engine for Factory BOM Calculation.
Calculates solid timber tier volumes, kerf panel nesting, finishing pool, and packaging.
"""

from typing import Dict, Any
try:
    from ..config import DEFAULT_RATES, SHEET_L, SHEET_W, SHEET_KERF, CARTON_ADD
    from ..models.item import BOMSpecification
except (ImportError, ValueError):
    from config import DEFAULT_RATES, SHEET_L, SHEET_W, SHEET_KERF, CARTON_ADD
    from models.item import BOMSpecification

def calculate_bom_costing(spec: BOMSpecification, custom_rates: Dict[str, float] = None) -> Dict[str, Any]:
    rates = {**DEFAULT_RATES, **(custom_rates or {})}
    header = spec.header

    # 1. Solid Wood (+ METAL hollow priced per metre, reported separately)
    try:
        from .hollow import is_metal, price_per_m, resolve_code
    except (ImportError, ValueError):
        from core.hollow import is_metal, price_per_m, resolve_code
    tot_solid_vol = 0.0
    tot_solid_face = 0.0
    tot_timber_cost = 0.0
    tot_metal_cost = 0.0
    tot_metal_m = 0.0
    solid_calc_rows = []
    metal_calc_rows = []

    wood_row, metal_row = 18, 34
    for part in spec.solid_parts:
        v = (part.l * part.w * part.t / 1e9) * part.qty
        f = (part.l * part.w / 1e6) * part.qty if part.exposed == 'Y' else 0.0
        if is_metal(part.material):
            length_m = part.l / 1000.0 * part.qty
            rate = price_per_m(rates, part.w, part.t, part.material)      # IDR per metre
            cost = length_m * rate
            tot_metal_cost += cost
            tot_metal_m += length_m
            tot_solid_face += f
            metal_calc_rows.append({"row": metal_row, "code": resolve_code(rates, part.material, part.w, part.t),
                                    "length_m": length_m, "face": (part.l * part.w / 1e6) * part.qty,
                                    "rate": rate, "cost": cost, "check": "OK" if rate else "hollow code?"})
            metal_row += 1
            continue
        tier = part.tier_override
        rate_key = f"{part.material}_{tier.replace('-CURVED', 'C')}"  # A-CURVED -> AC
        rate = rates.get(rate_key, rates.get("MINDI_B", 16465427.66))
        cost = v * rate

        tot_solid_vol += v
        tot_solid_face += f
        tot_timber_cost += cost

        solid_calc_rows.append({
            "row": wood_row,
            "vol": v,
            "face": (part.l * part.w / 1e6) * part.qty,
            "tier": tier,
            "rate": rate,
            "cost": cost,
            "check": "OK"
        })
        wood_row += 1

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
        tot_metal_cost +
        fasteners_cost +
        tot_panel_cost +
        tot_finishing_cost +
        tot_hw_cost +
        pack_cost
    )
    # direct_cost = TOTAL COST (sum of lines); unit_cost = DIRECT COST IDR (total + misc) = HPP.
    # Overhead was removed (Rizky, 23 Okt 2026); target price = HPP in USD x TARGET_X.
    misc_cost = direct_cost * rates["MISC_PCT"]
    unit_cost = direct_cost + misc_cost
    usd_cost = unit_cost / rates["FX_TARGET"]
    target_price_usd = usd_cost * rates["TARGET_X"]

    return {
        "solid_vol": tot_solid_vol,
        "panel_sheets": tot_panel_sheets,
        "exposed_face_m2": tot_exposed_face,
        "carton_m3": box_m3,
        "carton_m2": box_m2,
        "timber_cost": tot_timber_cost,
        "metal_cost": tot_metal_cost,
        "metal_m": tot_metal_m,
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
        "unit_cost": unit_cost,
        "usd_cost": usd_cost,
        "target_price_usd": target_price_usd,
        "open_checks": 0,
        "solid_rows": solid_calc_rows,
        "metal_rows": metal_calc_rows,
        "panel_rows": panel_calc_rows,
        "hw_rows": hw_calc_rows
    }
