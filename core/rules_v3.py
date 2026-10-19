"""
BOM Construction Rules & Part Schema v3.0 (October 2026 Mandate)
3-Digit Part Numbering System (101-999) + Strict Factory Rules v2.3.

Label Format: [PART_NO] [MAT_CODE], e.g.:
- 401 A-20-0X (Drawer front)
- 402 B-12-0X (Drawer box side)
- 403 B-12-0X (Drawer box front)
- 404 B-12-0X (Drawer box back)
- 405 B-6-0X  (Drawer base)
- 901 DTC-14  (Drawer slide)
"""

from typing import Dict, Any, List, Optional
try:
    from ..models.item import SolidPart, PanelPart, HardwarePart
    from .part_catalog_v3 import (
        PART_CATALOG_V3, FAMILIES_V3, format_part_label, map_legacy_to_v3, get_part
    )
except (ImportError, ValueError):
    from models.item import SolidPart, PanelPart, HardwarePart
    from core.part_catalog_v3 import (
        PART_CATALOG_V3, FAMILIES_V3, format_part_label, map_legacy_to_v3, get_part
    )

SPECIES_MAP = {
    "M": "MINDI",
    "T": "TEAK",
    "O": "OAK",
    "W": "WALNUT",
    "G": "GEMELINA",
    "A": "ASH",
    "J": "JOHAR",
}

def get_standard_glide_length(case_depth: float) -> float:
    """
    Fit to nearest standard catalog DTC drawer glide sizes: 300, 350, 400, 450 mm.
    """
    usable_depth = case_depth - 100.0
    if usable_depth >= 450.0:
        return 450.0
    elif usable_depth >= 400.0:
        return 400.0
    elif usable_depth >= 350.0:
        return 350.0
    elif usable_depth >= 300.0:
        return 300.0
    else:
        return 250.0

def derive_drawer_box(
    w_front: float,
    h_front: float,
    case_depth: float,
    side_length: Optional[float] = None,
    qty: int = 1,
    side_wall_thickness: float = 12.0,
    front_mat: str = "A-20-0X",
    box_mat: str = "B-12-0X",
    bottom_mat: str = "B-6-0X"
) -> Dict[str, Any]:
    """
    Standar Resmi Pabrik Tala Living v2.3 - Penomoran 3-Digit v3:
    1. 401 Drawer front: W_front x H_front
    2. 402 Drawer box side: D x (H_front - 30 mm)
    3. 403 Drawer box front: (W_front - 64 mm) x (H_front - 30 mm)
    4. 404 Drawer box back: (W_front - 64 mm) x (H_front - 30 mm)
    5. 405 Drawer base: (W_front - 54 mm) x (D - 7 mm)
    6. 901 Drawer slide: DTC soft close fitting D mm
    """
    d_side = side_length or get_standard_glide_length(case_depth)
    side_h = h_front - 30.0
    inner_front_h = h_front - 30.0
    inner_front_w = w_front - 40.0 - (2.0 * side_wall_thickness)  # W_front - 64 mm
    bottom_w = inner_front_w + 10.0                               # W_front - 54 mm
    bottom_d = d_side - 7.0

    # 1. Drawer Front (401)
    front = PanelPart(
        label=format_part_label(401, front_mat),
        component="Drawer front",
        panel_type="MDF-18-MDF" if "MDF" in front_mat or "C" in front_mat else "SOLID_WOOD",
        l=w_front,
        w=h_front,
        t=18.0,
        qty=qty,
        exposed_faces=2,
        note=f"Part 401 | W_front={w_front} x H_front={h_front}"
    )

    # 2. Drawer Box Side (402) - Plywood 12 mm E0
    side = PanelPart(
        label=format_part_label(402, box_mat),
        component="Drawer box side",
        panel_type="LND-PLY-E0-12",
        l=d_side,
        w=side_h,
        t=side_wall_thickness,
        qty=qty * 2,
        exposed_faces=0,
        note=f"Part 402 | D={d_side}mm x (H-30={side_h}mm)"
    )

    # 3. Drawer Box Front (403) - Plywood 12 mm E0
    inner_front = PanelPart(
        label=format_part_label(403, box_mat),
        component="Drawer box front",
        panel_type="LND-PLY-E0-12",
        l=inner_front_w,
        w=inner_front_h,
        t=side_wall_thickness,
        qty=qty,
        exposed_faces=0,
        note=f"Part 403 | (W-64={inner_front_w}mm) x (H-30={inner_front_h}mm)"
    )

    # 4. Drawer Box Back (404) - Plywood 12 mm E0
    back = PanelPart(
        label=format_part_label(404, box_mat),
        component="Drawer box back",
        panel_type="LND-PLY-E0-12",
        l=inner_front_w,
        w=inner_front_h,
        t=side_wall_thickness,
        qty=qty,
        exposed_faces=0,
        note=f"Part 404 | (W-64={inner_front_w}mm) x (H-30={inner_front_h}mm)"
    )

    # 4b. Combined Drawer Box Front/Back (jika dirangkum)
    box_front_back = PanelPart(
        label=format_part_label(403, box_mat),
        component="Drawer box front/back",
        panel_type="LND-PLY-E0-12",
        l=inner_front_w,
        w=inner_front_h,
        t=side_wall_thickness,
        qty=qty * 2,
        exposed_faces=0,
        note=f"Part 403/404 | (W-64={inner_front_w}mm) x (H-30={inner_front_h}mm)"
    )

    # 5. Drawer Base (405) - Plywood 6 mm E0
    bottom = PanelPart(
        label=format_part_label(405, bottom_mat),
        component="Drawer base",
        panel_type="LND-PLY-E0-6",
        l=bottom_w,
        w=bottom_d,
        t=6.0,
        qty=qty,
        exposed_faces=0,
        note=f"Part 405 | Dado 5mm: (W-54={bottom_w}mm) x (D-7={bottom_d}mm)"
    )

    # 6. Drawer Slide (901) - DTC Soft close
    slide_inch = int(d_side / 25.4)
    slide = HardwarePart(
        label=format_part_label(901, f"DTC-{int(d_side)}"),
        description=f"Rel laci DTC soft close {slide_inch}\" ({int(d_side)} mm)",
        qty=float(qty),
        unit_price=61396.2,
        uom="set",
        item_master_code="HARDWARE",
        vendor="Sukey / DTC",
        note=f"Part 901 | DTC slide D={d_side}mm"
    )

    return {
        "side_length_d": d_side,
        "front": front,
        "side": side,
        "inner_front": inner_front,
        "back": back,
        "box_front_back": box_front_back,
        "bottom": bottom,
        "slide": slide
    }

def derive_door(
    opening_w: float,
    opening_h: float,
    num_doors: int = 1,
    door_mat: str = "C-18-2X"
) -> Dict[str, Any]:
    """
    Pintu & Engsel Sistem 3-Digit:
    - 501 Door panel: (opening_w / num_doors - 2) x (opening_h - 2)
    - 902 Door hinge: DTC soft close hinge (2 pcs per door, 3 if H > 900)
    """
    door_w = (opening_w / num_doors) - 2.0
    door_h = opening_h - 2.0
    
    door_panel = PanelPart(
        label=format_part_label(501, door_mat),
        component="Door panel",
        panel_type="LND-MDF-E0-18-MDF",
        l=door_w,
        w=door_h,
        t=18.0,
        qty=num_doors,
        exposed_faces=2,
        note=f"Part 501 | Opening / {num_doors} - 2mm"
    )

    hinges_per_door = 3 if door_h > 900.0 else 2
    total_hinges = hinges_per_door * num_doors
    hinge = HardwarePart(
        label=format_part_label(902, "DTC-HINGE"),
        description="Engsel sendok DTC soft close (clip-on)",
        qty=float(total_hinges),
        unit_price=12500.0,
        uom="pcs",
        item_master_code="HARDWARE",
        vendor="Sukey / DTC",
        note=f"Part 902 | {hinges_per_door} pcs per door (H={door_h}mm)"
    )

    return {
        "door_panel": door_panel,
        "hinge": hinge
    }

def derive_joint_deduction(overall_span: float, left_post: float = 40.0, right_post: float = 40.0) -> float:
    """
    Joint deduction for rails spanning between two corner posts:
    net_length = overall_span - (left_post + right_post)
    """
    return overall_span - (left_post + right_post)

def derive_bed_anatomy(
    overall_l: float,
    overall_w: float,
    overall_h: float,
    mattress_l: float = 2000.0,
    mattress_w: float = 1500.0,
    post_w: float = 80.0,
    post_t: float = 50.0,
    species: str = "MINDI"
) -> Dict[str, Any]:
    """
    Deterministic Bed Construction Rules (3-Digit v3):
    - 806 Bed side rail: mattress_l + 40mm + 2*post_t (2140 mm)
    - 808 Bed center rail: mattress_l + 40mm
    - 809 Center support leg: height = rail bottom - clearance
    - 811 Bed slat: wood slats or 812 bought-in bed base
    - 904 Floor glide
    - 907 KD fitting (bed bracket)
    """
    side_rail_l = mattress_l + 40.0 + (2.0 * post_t)  # e.g. 2140 mm
    stretcher_w = overall_w - (2.0 * post_w)

    side_rail = SolidPart(
        label=format_part_label(806, "A"),
        component="Bed side rail",
        l=side_rail_l,
        w=180.0,
        t=35.0,
        qty=2,
        material=species,
        exposed="Y",
        note=f"Part 806 | Full exterior length {side_rail_l}mm"
    )

    center_rail = SolidPart(
        label=format_part_label(808, "A"),
        component="Bed center rail",
        l=mattress_l + 40.0,
        w=70.0,
        t=35.0,
        qty=1,
        material=species,
        exposed="N",
        note="Part 808 | Center spine support"
    )

    center_leg = SolidPart(
        label=format_part_label(809, "A"),
        component="Center support leg",
        l=220.0,
        w=60.0,
        t=60.0,
        qty=2,
        material=species,
        exposed="N",
        note="Part 809 | Middle support legs"
    )

    kd_bracket = HardwarePart(
        label=format_part_label(907, "KD-BRACKET"),
        description="Bed rail bracket KD fitting set",
        qty=1.0,
        unit_price=45000.0,
        uom="set",
        item_master_code="HARDWARE",
        note="Part 907 | 4 corner brackets"
    )

    floor_glides = HardwarePart(
        label=format_part_label(904, "GLIDE-25"),
        description="Floor glide plastic 25mm",
        qty=6.0,
        unit_price=1200.0,
        uom="pcs",
        item_master_code="HARDWARE",
        note="Part 904 | 4 corner legs + 2 center legs"
    )

    return {
        "side_rail_length": side_rail_l,
        "stretcher_width": stretcher_w,
        "side_rail": side_rail,
        "center_rail": center_rail,
        "center_leg": center_leg,
        "kd_bracket": kd_bracket,
        "floor_glides": floor_glides
    }

def derive_buffet_casegoods(
    overall_l: float,
    overall_w: float,
    overall_h: float,
    leg_section: float = 45.0,
    top_thickness: float = 25.0,
    leg_clear_h: float = 270.0,
    door_count: int = 2,
    bay_count: int = 3,
    dominant_species: str = "MINDI"
) -> Dict[str, Any]:
    """
    Standar Konstruksi Casegoods & Buffet v2.3 dipetakan ke 3-Digit v3:
    - 101 Leg
    - 201 Top rail front/back
    - 206 Bottom rail front/back
    - 205 Drawer runner rail
    - 301 Side panel
    - 302 Back panel
    - 303 Back panel frame
    - 307 Divider
    - 308 Shelf, fixed
    - 601 Top panel
    """
    l_clear = overall_l - (2.0 * leg_section)
    w_clear = overall_w - (2.0 * leg_section)
    leg_h = overall_h - top_thickness
    body_h = overall_h - leg_clear_h - top_thickness

    parts: List[Any] = []

    # 1. 101 Leg (4 pcs)
    parts.append(SolidPart(
        label=format_part_label(101, "A"),
        component="Leg",
        l=leg_h,
        w=leg_section,
        t=leg_section,
        qty=4,
        material=dominant_species,
        exposed="Y",
        note=f"Part 101 | 4 corner posts {leg_section}x{leg_section}"
    ))

    # 2. 201 Top rail front/back (2 pcs)
    parts.append(SolidPart(
        label=format_part_label(201, "A"),
        component="Top rail front/back",
        l=l_clear,
        w=40.0,
        t=25.0,
        qty=2,
        material=dominant_species,
        exposed="Y",
        note=f"Part 201 | Front & back apron rail {l_clear}mm"
    ))

    # 3. 206 Bottom rail front/back (2 pcs)
    parts.append(SolidPart(
        label=format_part_label(206, "A"),
        component="Bottom rail front/back",
        l=l_clear,
        w=40.0,
        t=25.0,
        qty=2,
        material=dominant_species,
        exposed="Y",
        note=f"Part 206 | Bottom front & back rail {l_clear}mm"
    ))

    # 4. 601 Top panel (1 pc)
    parts.append(PanelPart(
        label=format_part_label(601, "C-18-1X"),
        component="Top panel",
        panel_type="LND-PLY-E0-18-MSF",
        l=overall_l,
        w=overall_w,
        t=top_thickness,
        qty=1,
        exposed_faces=1,
        note=f"Part 601 | Daun atas {overall_l}x{overall_w}"
    ))

    # 5. 301 Side panel (2 pcs)
    parts.append(PanelPart(
        label=format_part_label(301, "C-18-1X"),
        component="Side panel",
        panel_type="LND-PLY-E0-18-MSF",
        l=w_clear,
        w=body_h,
        t=18.0,
        qty=2,
        exposed_faces=1,
        note=f"Part 301 | Sisi samping {w_clear}x{body_h}"
    ))

    # 6. 302 Back panel (1 pc or divided per bay)
    parts.append(PanelPart(
        label=format_part_label(302, "B-9-1X"),
        component="Back panel",
        panel_type="LND-PLY-E0-9",
        l=l_clear,
        w=body_h,
        t=9.0,
        qty=1,
        exposed_faces=1,
        note=f"Part 302 | Panel belakang {l_clear}x{body_h}"
    ))

    return {
        "l_clear": l_clear,
        "w_clear": w_clear,
        "leg_h": leg_h,
        "body_h": body_h,
        "door_h": 500.0,
        "door_w": round(l_clear / bay_count, 1),
        "parts": parts
    }

def map_drawing_code_to_rate(drawing_code: str, dominant_species: str = "MINDI") -> Dict[str, str]:
    """
    Materials Syntax: <Group><Thickness> <Faces>
    e.g. B12 1X -> PLY-12-MSF, B12 0X -> PLY-12-RAW, C18 2X -> MDF-18-MDF
    """
    code = drawing_code.strip().upper().replace("-", " ")
    parts = code.split()
    if not parts:
        return {"rate_code": drawing_code, "material": "OTHER"}

    main_part = parts[0]
    face_part = parts[1] if len(parts) > 1 else "0X"
    species_char = dominant_species[0].upper() if dominant_species else "M"

    if main_part == "A":
        return {"rate_code": f"{dominant_species}_B", "material": "SOLID_WOOD"}
    elif main_part == "A1":
        return {"rate_code": f"{dominant_species}_B", "material": "SOLID_WOOD_LAMINATED"}

    prefix = "PLY" if main_part.startswith("B") else ("MDF" if main_part.startswith("C") else "PLY")
    thickness = main_part[1:] if len(main_part) > 1 else "18"

    if face_part == "0X":
        rate_code = f"{prefix}-{thickness}-RAW"
    elif face_part == "1X":
        rate_code = f"{prefix}-{thickness}-{species_char}SF"
    elif face_part == "2X":
        rate_code = f"{prefix}-{thickness}-{species_char}DF"
    else:
        rate_code = f"{prefix}-{thickness}-RAW"

    return {
        "rate_code": rate_code,
        "material": prefix,
        "thickness": thickness,
        "faces": face_part
    }

def calculate_3zone_finishing(
    overall_l: float,
    overall_w: float,
    body_h: float,
    drawer_count: int = 0,
    drawer_d: float = 350.0,
    drawer_inner_w: float = 641.0,
    drawer_inner_h: float = 170.0,
    drawer_box_h: float = 190.0,
) -> Dict[str, float]:
    """
    3-Zone Finishing Surface Area Calculation (Revised Factory Standard v2.3).
    """
    # 1. Exterior
    ext_top = (overall_l * overall_w) / 1e6
    ext_front = (overall_l * body_h) / 1e6
    ext_side = (body_h * overall_w * 2.0) / 1e6
    tot_exterior = ext_top + ext_front + ext_side

    # 2. Interior
    int_back_panel = (overall_l * body_h) / 1e6
    int_drawer_inside = 0.0
    int_drawer_rails = 0.0
    int_drawer_base = 0.0
    int_drawer_back = 0.0

    if drawer_count > 0:
        perimeter_unfolded = 2.0 * (drawer_inner_w + drawer_d)
        int_drawer_inside = (perimeter_unfolded * drawer_box_h * drawer_count) / 1e6
        int_drawer_rails = (drawer_d * drawer_box_h * (2 * drawer_count)) / 1e6
        int_drawer_base = (drawer_inner_w * drawer_d * drawer_count) / 1e6
        int_drawer_back = (drawer_d * (drawer_box_h - 40.0) * drawer_count) / 1e6

    tot_interior = int_back_panel + int_drawer_inside + int_drawer_rails + int_drawer_base + int_drawer_back

    # 3. Sealer Only
    sealer_back = (overall_l * body_h) / 1e6
    sealer_side = (body_h * overall_w * 2.0) / 1e6
    sealer_top = (overall_l * overall_w) / 1e6
    tot_sealer = sealer_back + sealer_side + sealer_top

    return {
        "exterior_m2": round(tot_exterior, 4),
        "interior_m2": round(tot_interior, 4),
        "sealer_only_m2": round(tot_sealer, 4),
        "total_finishing_m2": round(tot_exterior + tot_interior + tot_sealer, 4)
    }
