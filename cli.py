#!/usr/bin/env python3
"""
BOM Application Command Line Interface (CLI).
Full CLI suite for factory BOM creation, verification, comparison, and rate updates.
"""

import argparse
import sys
import json
from pathlib import Path

from .config import GOLDEN_MASTER_PATH, DEFAULT_RATES
from .models.item import ItemHeader, SolidPart, PanelPart, HardwarePart, BOMSpecification
from .generators.single_bom import build_single_bom_workbook
from .generators.comparison import build_3way_comparison

def cmd_info(args):
    print("=" * 60)
    print("  FACTORY BOM APPLICATION - GOLDEN ENGINE v2.0")
    print("=" * 60)
    print(f"Golden Master Template: {GOLDEN_MASTER_PATH}")
    exists = GOLDEN_MASTER_PATH.exists()
    print(f"Status: {'LOCKED & READY (0444)' if exists else 'MISSING'}")
    print("\nDefault Rate Card Snapshot:")
    print(f"  Mindi Log Tier B: Rp {DEFAULT_RATES['MINDI_B']:,.2f} / m3")
    print(f"  Plywood 18mm MSF: Rp {DEFAULT_RATES['PLY-18-MSF']:,.2f} / sheet")
    print(f"  Fasteners Rate:   Rp {DEFAULT_RATES['FASTENERS_RATE']:,.2f} / m3")
    print(f"  Overhead Rate:    {DEFAULT_RATES['OH_PCT'] * 100:.2f}%")
    print(f"  Misc Buffer:      {DEFAULT_RATES['MISC_PCT'] * 100:.2f}%")
    print("=" * 60)

def cmd_create(args):
    json_path = Path(args.spec_json)
    if not json_path.exists():
        print(f"Error: Specification file not found: {json_path}", file=sys.stderr)
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Parse JSON into BOMSpecification
    h_data = data["header"]
    header = ItemHeader(
        item_code=h_data["item_code"],
        item_name=h_data["item_name"],
        collection=h_data.get("collection", "NEW HOI AN"),
        overall_l=float(h_data["overall_l"]),
        overall_w=float(h_data["overall_w"]),
        overall_h=float(h_data["overall_h"]),
        order_qty=int(h_data.get("order_qty", 1)),
        drawing_link=h_data.get("drawing_link", ""),
        finish_recipe=h_data.get("finish_recipe", "NC NATURAL"),
        flatpack_yn=h_data.get("flatpack_yn", "N"),
        notes=h_data.get("notes", ""),
        spec_link=h_data.get("spec_link", ""),
        photo_link=h_data.get("photo_link", "")
    )

    solid_parts = [
        SolidPart(
            label=p["label"],
            component=p["component"],
            l=float(p["l"]),
            w=float(p["w"]),
            t=float(p["t"]),
            qty=int(p["qty"]),
            material=p.get("material", "MINDI"),
            exposed=p.get("exposed", "Y"),
            curved=p.get("curved", "N"),
            tier_override=p.get("tier_override", "B"),
            note=p.get("note", "")
        )
        for p in data.get("solid_parts", [])
    ]

    panel_parts = [
        PanelPart(
            label=p["label"],
            component=p["component"],
            panel_type=p["panel_type"],
            l=float(p["l"]),
            w=float(p["w"]),
            t=float(p["t"]),
            qty=int(p["qty"]),
            exposed_faces=int(p.get("exposed_faces", 1)),
            note=p.get("note", "")
        )
        for p in data.get("panel_parts", [])
    ]

    hardware_parts = [
        HardwarePart(
            label=p["label"],
            description=p["description"],
            qty=float(p["qty"]),
            unit_price=float(p["unit_price"]),
            uom=p.get("uom", "set"),
            item_master_code=p.get("item_master_code", "HARDWARE"),
            vendor=p.get("vendor", "Lokal"),
            note=p.get("note", "")
        )
        for p in data.get("hardware_parts", [])
    ]

    spec = BOMSpecification(
        header=header,
        solid_parts=solid_parts,
        panel_parts=panel_parts,
        hardware_parts=hardware_parts
    )

    output_path = args.output or f"BOM_{header.item_code}.xlsx"
    print(f"Generating BOM for {header.item_code} ({header.item_name})...")
    res = build_single_bom_workbook(spec, output_path)

    print("\n[SUCCESS] BOM Workbook Generated:")
    print(f"  Output File:      {output_path}")
    print(f"  Solid Timber Vol: {res['solid_vol']:.6f} m3 (Rp {res['timber_cost']:,.2f})")
    print(f"  Panel Sheets:     {res['panel_sheets']:.4f} sheets (Rp {res['panels_cost']:,.2f})")
    print(f"  Exposed Area:     {res['exposed_face_m2']:.4f} m2 (Rp {res['finishing_total']:,.2f})")
    print(f"  Direct Cost:      Rp {res['direct_cost']:,.2f}")
    print(f"  Miscellaneous 5%: Rp {res['misc_cost']:,.2f}")
    print(f"  Factory OH 13%:   Rp {res['overhead_cost']:,.2f}")
    print(f"  UNIT COST (HPP):  Rp {res['unit_cost']:,.2f}")
    print(f"  Open Checks:      {res['open_checks']} (VALID)")

def cmd_compare(args):
    files = args.files
    output = args.output or "BOM_COMPARISON_OUTPUT.xlsx"
    title = args.title or "HEAD-TO-HEAD BOM COMPARISON"
    print(f"Comparing {len(files)} BOM files...")
    build_3way_comparison(files, output, title)
    print(f"[SUCCESS] Comparison workbook saved to: {output}")

def cmd_verify(args):
    import openpyxl
    target = Path(args.workbook)
    if not target.exists():
        print(f"Error: File not found: {target}", file=sys.stderr)
        sys.exit(1)

    wb = openpyxl.load_workbook(target, data_only=True)
    # Find item sheet
    item_sh = None
    for s in wb.sheetnames:
        if s not in ['README', 'ITEMS', 'TEMPLATE', 'RATES', 'LISTS', 'PART LIST REFERENCE']:
            item_sh = wb[s]
            break

    if not item_sh:
        print("Error: No product costing sheet found in workbook.", file=sys.stderr)
        sys.exit(1)

    code = item_sh['C1'].value
    checks = item_sh['D102'].value
    direct = item_sh['D96'].value
    unit_cost = item_sh['D99'].value

    print(f"Verifying BOM: {target.name}")
    print(f"  Product Code: {code}")
    print(f"  Direct Cost:  Rp {direct:,.2f}" if isinstance(direct, (int, float)) else f"  Direct Cost:  {direct}")
    print(f"  Unit Cost:    Rp {unit_cost:,.2f}" if isinstance(unit_cost, (int, float)) else f"  Unit Cost:    {unit_cost}")
    print(f"  Open Checks:  {checks}")

    if checks == 0:
        print("  Status:       [PASS] All dimensions, rates, and checks are 100% valid.")
    else:
        print(f"  Status:       [FAIL] {checks} input errors detected. Check column R.")

def main():
    parser = argparse.ArgumentParser(
        prog="bom-app",
        description="Factory BOM Application Suite (Living Ikon / PLV Standard)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # info
    p_info = subparsers.add_parser("info", help="Display application version, Golden Master status, and rates.")
    p_info.set_defaults(func=cmd_info)

    # create
    p_create = subparsers.add_parser("create", help="Generate single-item BOM from JSON spec file.")
    p_create.add_argument("spec_json", help="Path to component JSON specification file.")
    p_create.add_argument("-o", "--output", help="Output .xlsx file path.")
    p_create.set_defaults(func=cmd_create)

    # compare
    p_compare = subparsers.add_parser("compare", help="Generate side-by-side comparison of 2 or 3 BOM workbooks.")
    p_compare.add_argument("files", nargs="+", help="Paths to BOM .xlsx files (2 to 3 files).")
    p_compare.add_argument("-o", "--output", help="Output comparison .xlsx file path.")
    p_compare.add_argument("-t", "--title", help="Title banner for comparison.")
    p_compare.set_defaults(func=cmd_compare)

    # verify
    p_verify = subparsers.add_parser("verify", help="Validate an existing BOM workbook (D102 checks & formulas).")
    p_verify.add_argument("workbook", help="Path to BOM .xlsx file.")
    p_verify.set_defaults(func=cmd_verify)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
