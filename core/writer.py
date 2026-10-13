"""
OpenPyXL writer patch to inject <v> cached values into formula cells.
Ensures instant mobile spreadsheet rendering (Telegram, WPS Office Mobile, QuickOffice).
Safe with both lxml and stdlib xml implementations.
"""

from openpyxl.worksheet._writer import write_cell
import openpyxl.worksheet._writer as writer_mod
from openpyxl.xml.functions import Element, SubElement
from openpyxl.worksheet.formula import ArrayFormula, DataTableFormula
from openpyxl.cell.rich_text import CellRichText
from openpyxl.cell._writer import _set_attributes
from openpyxl.compat import safe_string

_active_cache_map = {}

def set_active_cache(cache_map):
    global _active_cache_map
    _active_cache_map = cache_map

def clear_active_cache():
    global _active_cache_map
    _active_cache_map = {}

def custom_write_cell(xf, worksheet, cell, styled=None):
    value, attributes = _set_attributes(cell, styled)
    el = Element('c', attributes)
    if value is None or value == '':
        xf.write(el)
        return

    cached_val = _active_cache_map.get((worksheet.title, cell.coordinate), None)

    if cell.data_type == 'f':
        attrib = {}
        if isinstance(value, ArrayFormula):
            attrib = dict(value)
            value = value.text
        elif isinstance(value, DataTableFormula):
            attrib = dict(value)
            value = None

        formula = SubElement(el, 'f', attrib)
        if value is not None and not attrib.get('t') == 'dataTable':
            formula.text = value[1:] if str(value).startswith('=') else str(value)
            value = None

        if cached_val is not None:
            if isinstance(cached_val, str):
                el.set('t', 'str')
            elif isinstance(cached_val, (int, float)):
                el.set('t', 'n')
            v_el = SubElement(el, 'v')
            v_el.text = safe_string(cached_val)
        xf.write(el)
        return

    if cell.data_type == 's':
        if isinstance(value, CellRichText):
            el.append(value.to_tree())
        else:
            inline_string = Element('is')
            text = Element('t')
            text.text = value
            inline_string.append(text)
            el.append(inline_string)
    else:
        cell_content = SubElement(el, 'v')
        if value is not None:
            cell_content.text = safe_string(value)

    xf.write(el)

def enable_cached_writer(cache_map):
    set_active_cache(cache_map)
    writer_mod.write_cell = custom_write_cell
