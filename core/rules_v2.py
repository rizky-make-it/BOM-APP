"""
BOM Rules & Part Schema v2 Engine.
Implementation of ground-truth rules from BOM rules and part schema v2.xlsx.
"""

from typing import Dict, Any, List, Optional
from ..models.item import SolidPart, PanelPart, HardwarePart

def get_standard_glide_length(case_depth: float) -> float:
    """
    Rule 6 & 7: Drawer side length rule
    Fit to nearest standard catalog DTC drawer glide sizes: 300, 350, 400, 450 mm.
    """
    usable_depth = case_depth - 100.0  # case depth minus clearance & frame
    if usable_depth >= 450.0:
        return 450.0
    elif usable_depth >= 400.0:
        return 400.0
    elif usable_depth >= 350.0:
        return 350.0
    elif usable_depth >= 300.0:
        return 300.0
    else:
        return 250.0  # minimum DTC-10"

def derive_drawer_box(
    w_front: float,
    h_front: float,
    case_depth: float,
    side_length: Optional[float] = None,
    qty: int = 1
) -> Dict[str, Any]:
    """
    Rules 1-7: Derivation of drawer box components from Drawer Front (W x H) and Case Depth.
    """
    d_side = side_length or get_standard_glide_length(case_depth)

    # 1. Drawer Front (AD) - MDF 18 mm veneer both faces (MDF-18-MDF)
    front = PanelPart(
        label="④ / AD",
        component="Drawer front",
        panel_type="MDF-18-MDF",
        l=w_front,
        w=h_front,
        t=18.0,
        qty=qty,
        exposed_faces=2,
        note="Role AD | Rule 1: W_front x H_front"
    )

    # 2. Drawer Side (K) - Plywood 12 mm MRD (PLY-12-MRD)
    # Size: D x (H_front - 20 mm)
    side = PanelPart(
        label="⑤ / K",
        component="Drawer side",
        panel_type="PLY-12-MRD",
        l=d_side,
        w=h_front - 20.0,
        t=12.0,
        qty=qty * 2,
        exposed_faces=0,
        note=f"Role K | Rule 2: D ({d_side}mm) x (H - 20mm)"
    )

    # 3. Inner Front (AL) - Plywood 12 mm MRD
    # Size: (W_front - 64 mm) x (H_front - 20 mm)
    inner_front = PanelPart(
        label="⑪ / AL",
        component="Drawer inner front",
        panel_type="PLY-12-MRD",
        l=w_front - 64.0,
        w=h_front - 20.0,
        t=12.0,
        qty=qty,
        exposed_faces=0,
        note="Role AL | Rule 3: (W - 64mm) x (H - 20mm)"
    )

    # 4. Drawer Back (L) - Plywood 12 mm MRD
    # Size: (W_front - 64 mm) x (H_front - 36 mm)
    back = PanelPart(
        label="⑫ / L",
        component="Drawer back",
        panel_type="PLY-12-MRD",
        l=w_front - 64.0,
        w=h_front - 36.0,
        t=12.0,
        qty=qty,
        exposed_faces=0,
        note="Role L | Rule 4: (W - 64mm) x (H - 36mm) rests on bottom"
    )

    # 5. Drawer Bottom (M) - Plywood 6 mm MRD
    # Size: (W_front - 54 mm) x (D - 7 mm)
    bottom = PanelPart(
        label="⑬ / M",
        component="Drawer bottom",
        panel_type="PLY-6-MRD",
        l=w_front - 54.0,
        w=d_side - 7.0,
        t=6.0,
        qty=qty,
        exposed_faces=0,
        note="Role M | Rule 5: (W - 54mm) x (D - 7mm) in 5mm dado groove"
    )

    # 6. Slide - DTC Soft close
    slide_inch = int(d_side / 25.4)
    slide = HardwarePart(
        label="⑯",
        description=f"Rel laci DTC soft close {slide_inch}\" ({int(d_side)} mm)",
        qty=float(qty),
        unit_price=61396.2,  # default DTC slide
        uom="set",
        item_master_code="HARDWARE",
        vendor="Sukey / DTC",
        note=f"Rule 8: Longest DTC slide fitting D={d_side}mm"
    )

    return {
        "side_length_d": d_side,
        "front": front,
        "side": side,
        "inner_front": inner_front,
        "back": back,
        "bottom": bottom,
        "slide": slide
    }

def derive_door(opening_w: float, opening_h: float, num_doors: int = 1) -> PanelPart:
    """
    Rule 11: Door size from opening
    height = (opening_h / num_doors) - 2mm
    width = (opening_w / num_doors) - 2mm
    """
    door_w = (opening_w / num_doors) - 2.0
    door_h = opening_h - 2.0
    return PanelPart(
        label="⑮ / A",
        component="Door",
        panel_type="MDF-18-MDF",
        l=door_w,
        w=door_h,
        t=18.0,
        qty=num_doors,
        exposed_faces=2,
        note=f"Role A | Rule 11: Door opening / {num_doors} - 2mm"
    )

def map_drawing_code_to_rate(drawing_code: str, dominant_species: str = "MINDI") -> Dict[str, str]:
    """
    Materials Sheet: Syntax <Group><Thickness> <Faces>
    e.g. B12 1X -> PLY-12-MSF (on mindi)
         B12 0X -> PLY-12-RAW
         C18 2X -> MDF-18-MDF
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
