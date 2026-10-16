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
    # Panels (Plywood per sheet, Landed Kudus E2 - 16 Okt 2026)
    "PLY-18-MSF": 540993.87,
    "PLY-12-MSF": 428870.08,
    "PLY-9-MSF": 370772.51,
    "PLY-6-MSF": 299944.44,
    "PLY-3-MSF": 245426.73,
    "PLY-18-RAW": 393284.85,
    "PLY-15-RAW": 342610.26,
    "PLY-12-RAW": 281161.06,
    "PLY-9-RAW": 223063.49,
    "PLY-6-RAW": 152235.42,
    "PLY-3-RAW": 97717.71,
    # Special Drawer Box Panels (E2 Landed Kudus)
    "PLY-12-MRD": 281161.06,
    "PLY-6-MRD": 152235.42,
    # MDF Panels (E2 Landed Kudus - 16 Okt 2026)
    "MDF-18-MDF": 533505.54,
    "MDF-18-MSF": 385796.52,
    "MDF-18-RAW": 238087.50,
    "MDF-15-RAW": 193906.25,
    "MDF-12-RAW": 151525.00,
    "MDF-9-RAW": 131768.42,
    "MDF-6-RAW": 85337.93,
    "MDF-3-RAW": 48288.18,
    # Hardware & Bought-In (16 Okt 2026 Landed Rates)
    "DTC-SLIDE-14": 49500.0,
    "DTC-SLIDE-16": 49500.0,
    "DTC-SLIDE-18": 49500.0,
    "DTC-SLIDE-10": 49500.0,
    "DTC-HINGE": 10800.0,
    "HW-RAIL-DTC": 49500.0,
    "HW-HINGE-DTC": 10800.0,
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
