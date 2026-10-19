"""
BOM Application Configuration & Constants.
"""

from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
GOLDEN_MASTER_PATH = APP_ROOT / "data" / "GOLDEN_MASTER.xlsx"
RULES_V2_PATH = APP_ROOT / "data" / "BOM_rules_and_part_schema_v2.xlsx"

# PANEL RULE (locked 19 Oct 2026): ALL plywood and MDF use grade E2 (landed Kudus).
# Do not add E0 / CARB prices to DEFAULT_RATES. See core/panel_rules.py and tests/test_panel_grade_e2.py.
PANEL_GRADE = "E2"

# Standard sheet and timber limits
SHEET_L = 2440.0  # mm
SHEET_W = 1220.0  # mm
SHEET_KERF = 5.0  # mm
CARTON_ADD = 40.0  # mm

# Standard Factory Rates (PLV BOM Rate Card, active column C - 16 Okt 2026)
DEFAULT_RATES = {
    # Solid Mindi Timber (rate card col C)
    "MINDI_A": 18057965.09,
    "MINDI_AC": 21620953.31,
    "MINDI_B": 14818884.89,
    "MINDI_C": 13199344.79,
    "MINDI_D": 11579804.69,
    # Solid Teak (rate card col C)
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


# ---------------------------------------------------------------------------------------------
# VENEER (locked 19 Oct 2026). Same formulas as the VENEER block in data/GOLDEN_MASTER.xlsx RATES.
# Face veneer cost is built from log price, slicing yield and vendor fee, per thickness 0.6 / 1.0 / 1.2 mm.
# Default board codes (-MSF, -MDF) use 0.6 mm. Codes with -V10 / -V12 use 1.0 / 1.2 mm.
# tests/test_veneer.py checks this block against the workbook formulas (via LibreOffice).
# ---------------------------------------------------------------------------------------------
VENEER = {
    "log_price": 3_200_000.0,   # IDR/m3 mindi log (CONFIRM; log_mindi in the old card is 3,000,000)
    "slice_yield": 0.30,        # vendor slicing yield
    "flitch_w": 160.0,          # mm, before trimming
    "trim_w": 150.0,            # mm, after trimming
    "slice_fee": 12_000.0,      # IDR per m2 of usable veneer (CONFIRM: billed on usable m2)
    "glue_tape": 10_424.0,      # IDR/m2 (rate card glue_tape)
    "press_labour": 57_142.86,  # IDR per face (rate card ven_labour)
}
THICKNESS_MM = {"": 0.6, "V06": 0.6, "V10": 1.0, "V12": 1.2}


def veneer_m2(thickness_mm: float, v: dict = None) -> float:
    """IDR per m2 of usable veneer = wood + slicing fee."""
    v = v or VENEER
    eff = v["slice_yield"] * v["trim_w"] / v["flitch_w"]
    return v["log_price"] * (thickness_mm / 1000.0) / eff + v["slice_fee"]


def veneer_face(thickness_mm: float, v: dict = None) -> float:
    """IDR added per board face (veneer + glue/tape on one full 2440x1220 sheet + pressing labour)."""
    v = v or VENEER
    return (veneer_m2(thickness_mm, v) + v["glue_tape"]) * (SHEET_L * SHEET_W / 1e6) + v["press_labour"]


def _apply_veneer(rates: dict) -> None:
    import re as _re
    face = {s: veneer_face(t) for s, t in THICKNESS_MM.items()}
    for key in list(rates):
        m = _re.fullmatch(r"(PLY-\d+|MDF-\d+|LND-PLY-E2-\d+|LND-MDF-E2-\d+)-(MSF|MDF)(-V10|-V12)?", key)
        if not m:
            continue
        base_code, kind = m.group(1), m.group(2)
        base = rates.get(base_code + "-RAW") if base_code.startswith(("PLY-", "MDF-")) else rates.get(base_code)
        if base is None:
            continue
        n = 1 if kind == "MSF" else 2
        rates[key] = round(base + n * face[""], 2)
    # explicit 1.0 / 1.2 mm variants
    for key in [k for k in rates if _re.fullmatch(r"LND-(PLY|MDF)-E2-\d+-(MSF|MDF)", k)]:
        n = 1 if key.endswith("MSF") else 2
        for suf, th in (("V10", 1.0), ("V12", 1.2)):
            rates[f"{key}-{suf}"] = round(rates[key] + n * (veneer_face(th) - face[""]), 2)
    # legacy PLY-x-MDF double face (not previously in the table)
    for t in (3, 6, 9, 12, 15, 18):
        if f"PLY-{t}-RAW" in rates:
            rates.setdefault(f"PLY-{t}-MDF", round(rates[f"PLY-{t}-RAW"] + 2 * face[""], 2))


_apply_veneer(DEFAULT_RATES)
