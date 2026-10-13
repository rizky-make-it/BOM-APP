"""
BOM Application Configuration & Constants.
"""

from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
GOLDEN_MASTER_PATH = APP_ROOT / "data" / "GOLDEN_MASTER.xlsx"
RULES_V2_PATH = APP_ROOT / "data" / "BOM_rules_and_part_schema_v2.xlsx"

# Standard sheet and timber limits
SHEET_L = 2440.0  # mm
SHEET_W = 1220.0  # mm
SHEET_KERF = 5.0  # mm
CARTON_ADD = 40.0  # mm

# Standard Factory Rates (PLV BOM Rate Card 2026-09-29 + Rules v2 additions)
DEFAULT_RATES = {
    # Solid Mindi Timber
    "MINDI_A": 20064405.66,
    "MINDI_B": 16465427.66,
    "MINDI_C": 14665938.66,
    "MINDI_D": 12866449.66,
    # Solid Teak
    "TEAK_A": 32000000.0,
    "TEAK_B": 28000000.0,
    "TEAK_C": 24000000.0,
    "TEAK_D": 20000000.0,
    # Panels (Plywood per sheet)
    "PLY-18-MSF": 442709.0,
    "PLY-12-MSF": 362709.0,
    "PLY-9-MSF": 295056.0,
    "PLY-18-RAW": 295000.0,
    "PLY-12-RAW": 215000.0,
    "PLY-9-RAW": 172500.0,
    "PLY-6-RAW": 115000.0,
    "PLY-3-RAW": 75000.0,
    # Special Drawer Box Panels (Meranti / Furniture Grade from Rules v2)
    "PLY-12-MRD": 215000.0,
    "PLY-6-MRD": 115000.0,
    # MDF Panels (Rules v2)
    "MDF-18-MDF": 590418.04,
    "MDF-18-MSF": 442709.02,
    "MDF-18-RAW": 295000.0,
    # Hardware & Bought-In (Rules v2)
    "DTC-SLIDE-14": 61396.2,
    "DTC-SLIDE-16": 68000.0,
    "DTC-SLIDE-10": 55000.0,
    "DTC-HINGE": 25000.0,
    "SLAT-BASE-QUEEN": 400000.0,  # USD 25 @ 16,000
    "SLAT-BASE-KING": 624000.0,   # USD 39 @ 16,000
    # Rates constants
    "FASTENERS_RATE": 1750614.0,  # IDR per m3 solid wood
    "FIN_MAT_RATE": 38844.57,     # IDR per m2 exposed
    "SAND_MAT_RATE": 12794.54,    # IDR per m2 exposed
    "SAND_LAB_RATE": 39477.20,    # IDR per m2 exposed
    "FIN_LAB_RATE": 88755.0,      # IDR per m2 exposed
    "CARTON_M2_RATE": 49033.47,   # IDR per m2 carton
    "PACK_LAB_RATE": 45543.0,     # IDR per m3 carton
    "MISC_PCT": 0.05,             # 5%
    "OH_PCT": 0.1299,             # 12.99%
}
