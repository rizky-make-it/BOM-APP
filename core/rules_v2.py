"""
BOM Rules & Part Schema v2 Engine (Updated with October 2026 Mandates).
Implementation of ground-truth rules from BOM rules and part schema v2.xlsx:
1. Inner front:
   - Jarak atas: 20 mm
   - Jarak bawah: 10 mm -> Tinggi Inner Front = H_front - (20 + 10) = H_front - 30 mm
   - Jarak kanan/kiri: 20 mm per sisi -> Celah samping 20mm + 20mm = 40mm
     -> Lebar Inner Front = W_front - 40 - 24 = W_front - 64 mm
2. Drawer back:
   - Ukuran tinggi DISAMAKAN dengan box depan (inner front) = H_front - 30 mm
   - Lebar = W_front - 64 mm
3. Drawer bottom:
   - Lebar masuk dado 5mm tiap sisi = Inner width + 10 mm = W_front - 54 mm
   - Kedalaman = D - 7 mm
4. Drawer side:
   - Panjang = D (300, 350, 400, 450 mm)
   - Tinggi = H_front - 20 mm
5. Expanded Part Catalog: Parts 1 to 25
6. Full wood species letters: M=Mindi, T=Teak, O=Oak, W=Walnut, G=Gemelina, A=Ash, J=Johar
"""

from typing import Dict, Any, List, Optional
from ..models.item import SolidPart, PanelPart, HardwarePart

# Official 25-part catalog mapping
PART_CATALOG = {
    1: {"name": "Bottom back stretcher", "revise": "Bottom front/ back stretcher", "role": "stretcher_back", "type": "solid"},
    2: {"name": "Side stretcher", "revise": "Side stretcher", "role": "stretcher_side", "type": "solid"},
    3: {"name": "Leg", "revise": "Leg", "role": "leg", "type": "solid"},
    4: {"name": "Drawer front", "revise": "drawer front", "role": "drawer_front", "type": "panel"},
    5: {"name": "Drawer side", "revise": "drawer box side", "role": "drawer_side", "type": "panel"},
    6: {"name": "Top front rail", "revise": "Top front rail", "role": "top_front_rail", "type": "solid"},
    7: {"name": "Top", "revise": "Top", "role": "top", "type": "panel"},
    8: {"name": "Side panel", "revise": "Side panel", "role": "side_panel", "type": "panel"},
    9: {"name": "Back panel", "revise": "Back panel", "role": "back_panel", "type": "panel"},
    10: {"name": "Back frame stile", "revise": "back panel frame", "role": "back_frame", "type": "solid"},
    11: {"name": "Drawer inner front", "revise": "drawer box front/back", "role": "drawer_box_front", "type": "panel"},
    12: {"name": "Drawer bottom", "revise": "drawer base", "role": "drawer_bottom", "type": "panel"},
    13: {"name": "Divider", "revise": "Divider", "role": "divider", "type": "panel"},
    14: {"name": "Door", "revise": "Door", "role": "door", "type": "panel"},
    15: {"name": "Drawer slide", "revise": "drawer support", "role": "drawer_slide", "type": "hardware"},
    16: {"name": "Handle", "revise": "Handle", "role": "handle", "type": "hardware"},
    17: {"name": "Back frame rail", "revise": "Back frame rail", "role": "back_frame", "type": "solid"},
    18: {"name": "Shelf", "revise": "Shelf", "role": "shelf", "type": "panel"},
    19: {"name": "Glass / mirror", "revise": "Glass / mirror", "role": "glass", "type": "hardware"},
    20: {"name": "Back support", "revise": "Back support", "role": "back_support", "type": "solid"},
    21: {"name": "side rail", "revise": "side rail", "role": "side_rail", "type": "solid"},
    22: {"name": "frame top/bottom drawer", "revise": "frame top/bottom drawer", "role": "drawer_frame_rail", "type": "solid"},
    23: {"name": "frame side drawer", "revise": "frame side drawer", "role": "drawer_frame_stile", "type": "solid"},
    24: {"name": "horizontal support", "revise": "horizontal support", "role": "horizontal_support", "type": "solid"},
    25: {"name": "vertical support", "revise": "vertical support", "role": "vertical_support", "type": "solid"},
}

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
    side_wall_thickness: float = 12.0
) -> Dict[str, Any]:
    """
    Drawer Box Derivation Rules (Updated):
    1. Inner front (AL):
       - Jarak atas: 20 mm
       - Jarak bawah: 10 mm
       -> Tinggi Inner Front = H_front - (20 + 10) = H_front - 30 mm
       - Jarak kanan/kiri: 20 mm per sisi (celah rel)
       -> Lebar Inner Front = W_front - 2 * 20mm - 2 * side_wall_thickness = W_front - 64 mm
    2. Drawer back (L):
       - Ukuran tinggi DISAMAKAN dengan box depan (inner front)!
       -> Tinggi Drawer Back = Tinggi Inner Front = H_front - 30 mm
       -> Lebar Drawer Back = Lebar Inner Front = W_front - 64 mm
    3. Drawer side (K):
       - Panjang = D (300, 350, 400, 450 mm)
       - Tinggi = H_front - 20 mm
    4. Drawer bottom (M):
       - Lebar = Inner width + 2 * 5mm dado groove = W_front - 54 mm
       - Kedalaman = D - 7 mm
    """
    d_side = side_length or get_standard_glide_length(case_depth)

    # 1. Drawer Front (AD / ④) - MDF 18 mm veneer both faces
    front = PanelPart(
        label="④ / AD",
        component="Drawer front",
        panel_type="MDF-18-MDF",
        l=w_front,
        w=h_front,
        t=18.0,
        qty=qty,
        exposed_faces=2,
        note="Role AD | W_front x H_front"
    )

    # 2. Drawer Side (K / ⑤) - Plywood 12 mm
    # Length D, Height H_front - 20 mm
    side_h = h_front - 20.0
    side = PanelPart(
        label="⑤ / K",
        component="Drawer side",
        panel_type="PLY-12-RAW",
        l=d_side,
        w=side_h,
        t=side_wall_thickness,
        qty=qty * 2,
        exposed_faces=0,
        note=f"Role K | D ({d_side}mm) x (H - 20mm={side_h}mm)"
    )

    # 3. Inner Front (AL / ⑪) - Plywood 12 mm
    # Jarak atas 20mm, bawah 10mm -> Height = H_front - 30 mm
    # Jarak kanan/kiri 20mm -> Width = W_front - 40 - 24 = W_front - 64 mm
    inner_front_h = h_front - 20.0 - 10.0  # H_front - 30 mm
    inner_front_w = w_front - 40.0 - (2 * side_wall_thickness) # W_front - 64 mm
    inner_front = PanelPart(
        label="⑪ / AL",
        component="Drawer inner front",
        panel_type="PLY-12-RAW",
        l=inner_front_w,
        w=inner_front_h,
        t=side_wall_thickness,
        qty=qty,
        exposed_faces=0,
        note=f"Role AL | Atas 20mm, Bawah 10mm (H-30={inner_front_h}mm), Kanan/Kiri 20mm (W-64={inner_front_w}mm)"
    )

    # 4. Drawer Back (L / ⑫) - Plywood 12 mm
    # Mandate: "untuk drawer back ukuran tinggi disamakan dengan box depan"
    back_h = inner_front_h  # DISAMAKAN PERSIS!
    back_w = inner_front_w
    back = PanelPart(
        label="⑫ / L",
        component="Drawer back",
        panel_type="PLY-12-RAW",
        l=back_w,
        w=back_h,
        t=side_wall_thickness,
        qty=qty,
        exposed_faces=0,
        note=f"Role L | Tinggi disamakan dengan box depan = {back_h}mm (W-64={back_w}mm)"
    )

    # 5. Drawer Bottom (M) - Plywood 6 mm
    # Width enters 5mm dado each side: inner_width + 10 mm = W_front - 54 mm
    # Depth enters front dado: D - 7 mm
    bottom_w = inner_front_w + 10.0  # W_front - 54 mm
    bottom_d = d_side - 7.0
    bottom = PanelPart(
        label="⑫ / M",
        component="Drawer bottom",
        panel_type="PLY-6-RAW",
        l=bottom_w,
        w=bottom_d,
        t=6.0,
        qty=qty,
        exposed_faces=0,
        note=f"Role M | Dado 5mm: (W-54={bottom_w}mm) x (D - 7={bottom_d}mm)"
    )

    # 6. Slide - DTC Soft close
    slide_inch = int(d_side / 25.4)
    slide = HardwarePart(
        label="⑮",
        description=f"Rel laci DTC soft close {slide_inch}\" ({int(d_side)} mm)",
        qty=float(qty),
        unit_price=61396.2,
        uom="set",
        item_master_code="HARDWARE",
        vendor="Sukey / DTC",
        note=f"Rule 8: DTC slide fitting D={d_side}mm"
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
        label="⑭ / A",
        component="Door",
        panel_type="MDF-18-MDF",
        l=door_w,
        w=door_h,
        t=18.0,
        qty=num_doors,
        exposed_faces=2,
        note=f"Role A | Door opening / {num_doors} - 2mm"
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
