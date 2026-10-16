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
    # Panels (Plywood per sheet, Consmos Landed Kudus E2 - 14 Okt 2026)
    "PLY-18-MSF": 530732.67,
    "PLY-12-MSF": 412035.74,
    "PLY-9-MSF": 353333.60,
    "PLY-6-MSF": 292628.23,
    "PLY-3-MSF": 244675.57,
    "PLY-18-RAW": 383023.65,
    "PLY-15-RAW": 329955.43,
    "PLY-12-RAW": 264326.72,
    "PLY-9-RAW": 205624.58,
    "PLY-6-RAW": 144919.21,
    "PLY-3-RAW": 96966.55,
    # Special Drawer Box Panels (E2 Landed Kudus)
    "PLY-12-MRD": 264326.72,
    "PLY-6-MRD": 144919.21,
    # MDF Panels (Consmos E2 Landed Kudus - 14 Okt 2026)
    "MDF-18-MDF": 584617.04,
    "MDF-18-MSF": 436908.02,
    "MDF-18-RAW": 289199.00,
    "MDF-15-RAW": 239226.95,
    "MDF-12-RAW": 190208.96,
    "MDF-9-RAW": 145197.85,
    "MDF-6-RAW": 94351.97,
    "MDF-3-RAW": 52200.90,
    # Marine Plywood (Consmos 14 Okt 2026)
    "PLY-15-MAR": 378564.60,
    "PLY-18-MAR": 448044.40,
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
