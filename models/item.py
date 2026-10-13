"""
Data structures for BOM items and components.
"""

from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ItemHeader:
    item_code: str
    item_name: str
    collection: str
    overall_l: float
    overall_w: float
    overall_h: float
    order_qty: int = 1
    drawing_link: str = ""
    finish_recipe: str = "NC NATURAL"
    flatpack_yn: str = "N"
    notes: str = ""
    spec_link: str = ""
    photo_link: str = ""

@dataclass
class SolidPart:
    label: str           # Format: [PART] / [CODE], e.g. '3 / A'
    component: str       # Standard component name
    l: float             # Length mm
    w: float             # Width mm
    t: float             # Thickness mm
    qty: int             # Quantity
    material: str = "MINDI"
    exposed: str = "Y"   # Y / N
    curved: str = "N"    # Y / N
    tier_override: str = "B" # A, B, C, D
    note: str = ""

@dataclass
class PanelPart:
    label: str           # Format: [PART] / [CODE], e.g. '20 / B-18-1X'
    component: str       # Standard component name
    panel_type: str      # e.g. 'PLY-18-MSF', 'PLY-9-RAW'
    l: float
    w: float
    t: float
    qty: int
    exposed_faces: int = 1 # 0, 1, 2
    note: str = ""

@dataclass
class HardwarePart:
    label: str           # e.g. 'D2 / DTC-14', 'HNDL / 128MM'
    description: str     # e.g. 'Rel laci DTC soft close 14" (356 mm)'
    qty: float
    unit_price: float
    uom: str = "set"
    item_master_code: str = "HARDWARE"
    vendor: str = "Lokal"
    note: str = ""

@dataclass
class BOMSpecification:
    header: ItemHeader
    solid_parts: List[SolidPart] = field(default_factory=list)
    panel_parts: List[PanelPart] = field(default_factory=list)
    hardware_parts: List[HardwarePart] = field(default_factory=list)
