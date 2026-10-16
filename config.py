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

# Standard Factory Rates (PLV BOM Rate Card Column D Active - 16 Okt 2026)
DEFAULT_RATES = {
    # Solid Mindi Timber (Column D Active)
    "MINDI_A": 18057965.09,
    "MINDI_AC": 21620953.31,
    "MINDI_B": 14818884.89,
    "MINDI_C": 13199344.79,
    "MINDI_D": 11579804.69,
    # Solid Teak (Column D Active)
    "TEAK_A": 27507965.09,
    "TEAK_AC": 34040953.31,
    "TEAK_B": 21568884.89,
    "TEAK_C": 18599344.79,
    "TEAK_D": 15629804.69,
    "MERANTI": 18196184.39,
    "LAB_CARP": 4000000.0,
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
    # === OFFICIAL LND- CODES (Consmos Landed Kudus E2 - 14 Okt 2026) ===
    "LND-PLY-E2-18": 383023.65,
    "LND-PLY-E2-15": 329955.43,
    "LND-PLY-E2-12": 264326.72,
    "LND-PLY-E2-9": 205624.58,
    "LND-PLY-E2-6": 144919.21,
    "LND-PLY-E2-3": 96966.55,
    "LND-PLY-E2-18-MSF": 530732.67,
    "LND-PLY-E2-18-MDF": 678441.69,
    "LND-PLY-E2-15-MSF": 477664.45,
    "LND-PLY-E2-15-MDF": 625373.47,
    "LND-PLY-E2-12-MSF": 412035.74,
    "LND-PLY-E2-12-MDF": 559744.76,
    "LND-PLY-E2-9-MSF": 353333.60,
    "LND-PLY-E2-9-MDF": 501042.62,
    "LND-PLY-E2-6-MSF": 292628.23,
    "LND-PLY-E2-6-MDF": 440337.25,
    "LND-PLY-E2-3-MSF": 244675.57,
    "LND-PLY-E2-3-MDF": 392384.59,
    "LND-MDF-E2-18": 289199.00,
    "LND-MDF-E2-15": 239226.95,
    "LND-MDF-E2-12": 190208.96,
    "LND-MDF-E2-9": 145197.85,
    "LND-MDF-E2-6": 94351.97,
    "LND-MDF-E2-3": 52200.90,
    "LND-MDF-E2-18-MSF": 436908.02,
    "LND-MDF-E2-18-MDF": 584617.04,
    "LND-MDF-E2-15-MSF": 386935.97,
    "LND-MDF-E2-12-MSF": 337917.98,
    "LND-MDF-E2-9-MSF": 292906.87,
    "LND-MDF-E2-6-MSF": 242060.99,
    "LND-MAR-15": 378564.60,
    "LND-MAR-18": 448044.40,
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
    # Rates constants (Column D Active - 16 Okt 2026)
    "FASTENERS_RATE": 1000000.0,  # IDR per m3 solid wood (Column D)
    "FIN_MAT_RATE": 37000.0,      # IDR per m2 exposed (Column D)
    "SAND_MAT_RATE": 10235.64,    # IDR per m2 exposed (Column D)
    "SAND_LAB_RATE": 20000.0,     # IDR per m2 exposed (Column D)
    "FIN_LAB_RATE": 45000.0,      # IDR per m2 exposed (Column D)
    "CARTON_M2_RATE": 40000.0,    # IDR per m2 carton (Column D)
    "PACK_LAB_RATE": 50000.0,     # IDR per m3 carton (Column D)
    "MISC_PCT": 0.05,             # 5%
    "OH_PCT": 0.1299,             # 12.99%
}
