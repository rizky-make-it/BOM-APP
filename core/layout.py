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
    # PANEL TYPE codes like LND-PLY-E2-12-MDF need ~19 chars
    if (ws.column_dimensions["B"].width or 0) < 20:
        ws.column_dimensions["B"].width = 20


def compact_items_sheet(ws, n_items):
    _hide(ws, ITEMS_FIRST, ITEMS_LAST, n_items)


def count_pack_rows(spec):
    """Spec has no per-box data yet, so only the overall-size carton row (row 11) is shown."""
    return 1
