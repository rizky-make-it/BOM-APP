"""Auto-compact layout: hide unused template rows so each sheet matches the real item count.

Formulas in hidden rows are kept (they stay blank), so totals and re-use of the sheet are unaffected.
To add a component later: unhide the rows (select rows around it > Unhide) and type in the first hidden row.
"""

SOLID_FIRST, SOLID_LAST = 18, 42
PANEL_FIRST, PANEL_LAST = 46, 60
HW_FIRST, HW_LAST = 64, 78
PACK_FIRST, PACK_LAST = 11, 14
ITEMS_FIRST, ITEMS_LAST = 6, 53


def _hide(ws, first, last, used):
    """Show rows first..first+used-1, hide the rest up to last (always keep >= 1 row visible)."""
    keep = max(used, 1)
    for r in range(first, last + 1):
        ws.row_dimensions[r].hidden = r >= first + keep


def compact_item_sheet(ws, n_solid, n_panel, n_hw, n_pack=1):
    _hide(ws, SOLID_FIRST, SOLID_LAST, n_solid)
    _hide(ws, PANEL_FIRST, PANEL_LAST, n_panel)
    _hide(ws, HW_FIRST, HW_LAST, n_hw)
    _hide(ws, PACK_FIRST, PACK_LAST, n_pack)
    # PANEL TYPE codes like LND-PLY-E0-12-MDF need ~19 chars
    if (ws.column_dimensions["B"].width or 0) < 20:
        ws.column_dimensions["B"].width = 20


def compact_items_sheet(ws, n_items):
    _hide(ws, ITEMS_FIRST, ITEMS_LAST, n_items)


def count_pack_rows(spec):
    """Spec has no per-box data yet, so only the overall-size carton row (row 11) is shown."""
    return 1


# ---------------------------------------------------------------- missing-price highlight
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import PatternFill, Font

MISSING_FILL = PatternFill(start_color="FFC7A0", end_color="FFC7A0", fill_type="solid")  # orange
MISSING_FONT = Font(color="9C2B00", bold=True)


def _rule(ws, rng, formula):
    ws.conditional_formatting.add(rng, FormulaRule(formula=[formula], fill=MISSING_FILL, font=MISSING_FONT, stopIfTrue=False))


def highlight_missing_item_sheet(ws):
    """Orange when a used line has no price yet (blank, 0 or 'rate?')."""
    _rule(ws, "S18:T42", 'AND($E18<>"",OR(S18="",S18=0,S18="rate?"))')    # solid wood rate / cost
    _rule(ws, "S46:T60", 'AND($E46<>"",OR(S46="",S46=0,S46="rate?"))')    # panels
    _rule(ws, "S64:T78", 'AND($D64<>"",OR(S64="",S64=0))')                # hardware unit price / line total


def highlight_missing_rates(ws):
    """RATES: a code + description with an empty Value cell."""
    _rule(ws, "C5:C400", 'AND($A5<>"",$A5<>"code",$B5<>"",$C5="")')  # incl. CURVE_ALLOW and METAL rows


# ---------------------------------------------------------------- slim output (no helper sheets)
import re as _re
from copy import copy as _copy
from openpyxl.worksheet.formula import ArrayFormula as _AF

DROP_SHEETS = ("TEMPLATE", "LISTS", "PART LIST REFERENCE", "GAMBAR KOLEKSI")
_NORM_LABEL = {  # LISTS row -> (RATES code, description, unit)
    3: ("NORM_TIER_A_MIN_LEN", "Tier A minimum component length", "mm"),
    4: ("NORM_TIER_D_MAX_VOL", "Tier D maximum component volume", "m³"),
    5: ("NORM_TIER_D_MAX_LEN", "Tier D maximum component length", "mm"),
    6: ("NORM_SHEET_L", "Board sheet length", "mm"),
    7: ("NORM_SHEET_W", "Board sheet width", "mm"),
    8: ("NORM_SHEET_KERF", "Saw kerf between nested panels", "mm"),
    9: ("NORM_CARTON_ADD", "Carton allowance added to each overall size", "mm"),
    10: ("NORM_NARROW_MAX_SECTION", "Narrow part: maximum section", "mm"),
    11: ("NORM_NARROW_MAX_LEN", "Narrow part: maximum length", "mm"),
}


def strip_helper_sheets(wb):
    """Remove TEMPLATE / LISTS / PART LIST REFERENCE / GAMBAR KOLEKSI from an OUTPUT workbook.
    LISTS norms are moved into RATES (section NORMS) and every formula is re-pointed, so nothing breaks."""
    if "LISTS" in wb.sheetnames and "RATES" in wb.sheetnames:
        lists, rates = wb["LISTS"], wb["RATES"]
        start = rates.max_row + 2
        rates.cell(start, 1, "NORMS (moved from the old LISTS sheet). Blue = base figure, formulas on every item tab follow.")
        ref_row = next((r for r in range(1, rates.max_row + 1) if str(rates.cell(r, 1).value or "").startswith("METAL (added")), None)
        for c in range(1, 7):
            if ref_row:
                rates.cell(start, c)._style = _copy(rates.cell(ref_row, c)._style)
        mapping = {}
        for i, (lrow, (code, desc, unit)) in enumerate(_NORM_LABEL.items(), start + 1):
            val = lists.cell(lrow, 6).value
            rates.cell(i, 1, code); rates.cell(i, 2, desc); rates.cell(i, 3, val)
            rates.cell(i, 4, unit); rates.cell(i, 5, "Norm (moved from old list, row %d)" % lrow)
            for c in range(1, 6):
                if ref_row:
                    rates.cell(i, c)._style = _copy(rates.cell(ref_row + 1, c)._style)
            rates.cell(i, 3).number_format = "General"
            mapping[f"$F${lrow}"] = f"RATES!$C${i}"
        pat = _re.compile(r"LISTS!(\$F\$\d+)")
        for ws in wb:
            for row in ws.iter_rows():
                for c in row:
                    v = c.value
                    t = v.text if isinstance(v, _AF) else v
                    if isinstance(t, str) and "LISTS!" in t:
                        new = pat.sub(lambda m: mapping.get(m.group(1), m.group(0)), t)
                        if isinstance(v, _AF):
                            v.text = new
                        else:
                            c.value = new
    for name in DROP_SHEETS:
        if name in wb.sheetnames:
            del wb[name]
