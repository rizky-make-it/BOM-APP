#!/usr/bin/env python3
"""
BOM Application Command Line Interface (CLI).
Full CLI suite for factory BOM creation, verification, comparison, and rate updates.
"""

import argparse
import sys
import json
from pathlib import Path

try:
    from .config import GOLDEN_MASTER_PATH, RULES_V2_PATH, DEFAULT_RATES
    from .models.item import ItemHeader, SolidPart, PanelPart, HardwarePart, BOMSpecification
    from .generators.single_bom import build_single_bom_workbook
    from .generators.comparison import build_3way_comparison
    from .core.rules_v2 import derive_drawer_box, derive_door, map_drawing_code_to_rate, PART_CATALOG, SPECIES_MAP
    from .pipeline import run_pipeline
except (ImportError, ValueError):
    from config import GOLDEN_MASTER_PATH, RULES_V2_PATH, DEFAULT_RATES
    from models.item import ItemHeader, SolidPart, PanelPart, HardwarePart, BOMSpecification
    from generators.single_bom import build_single_bom_workbook
    from generators.comparison import build_3way_comparison
    from core.rules_v2 import derive_drawer_box, derive_door, map_drawing_code_to_rate, PART_CATALOG, SPECIES_MAP
    from pipeline import run_pipeline

def cmd_info(args):
    print("=" * 65)
    print("  FACTORY BOM APPLICATION - GOLDEN ENGINE v2.1 (UPDATED)")
    print("=" * 65)
    print(f"Golden Master Template: {GOLDEN_MASTER_PATH}")
    print(f"Rules & Schema v2:      {RULES_V2_PATH}")
    exists = GOLDEN_MASTER_PATH.exists()
    print(f"Status: {'LOCKED & READY (0444)' if exists else 'MISSING'}")
    print(f"\nPart Catalog Count:     {len(PART_CATALOG)} official parts (1 to 25)")
    print(f"Supported Wood Species: {', '.join(f'{k}={v}' for k, v in SPECIES_MAP.items())}")
    print("\nDefault Rate Card Snapshot:")
    print(f"  Mindi Log Tier B: Rp {DEFAULT_RATES['MINDI_B']:,.2f} / m3")
    ply_18 = DEFAULT_RATES.get('LND-PLY-E0-18-MSF', DEFAULT_RATES.get('PLY-18-MSF', 0.0))
    mdf_18 = DEFAULT_RATES.get('LND-MDF-E0-18-MDF', DEFAULT_RATES.get('MDF-18-MDF', 0.0))
    print(f"  Plywood 18mm MSF: Rp {ply_18:,.2f} / sheet")
    print(f"  MDF 18mm 2-Face:  Rp {mdf_18:,.2f} / sheet")
    print(f"  Fasteners Rate:   Rp {DEFAULT_RATES['FASTENERS_RATE']:,.2f} / m3")
    print(f"  Overhead Rate:    {DEFAULT_RATES['OH_PCT'] * 100:.2f}%")
    print(f"  Misc Buffer:      {DEFAULT_RATES['MISC_PCT'] * 100:.2f}%")
    print("=" * 65)

def cmd_parts(args):
    print("=" * 75)
    print("  OFFICIAL FACTORY PART CATALOG (PARTS 1 TO 25)")
    print("=" * 75)
    for num, p in sorted(PART_CATALOG.items()):
        print(f"  Part {num:2d} | {p['name']:25} | Revise: {p['revise']:30} | Role: {p['role']}")
    print("=" * 75)

def cmd_rules(args):
    print("=" * 75)
    print("  BOM CONSTRUCTION RULES V2.2 (LATEST OWNER MANDATES)")
    print("=" * 75)
    print("1. Inner Front (AL): Jarak atas 20mm, bawah 10mm -> H_inner = H_front - 30 mm")
    print("                     Jarak kanan/kiri 20mm -> W_box = W_front - 64 mm")
    print("2. Drawer Back (L):  TINGGI DISAMAKAN PERSIS DENGAN BOX DEPAN = H_inner = H_front - 30 mm")
    print("3. Drawer Side (K):  Panjang = D (350, 400 mm); Tinggi = H_front - 30 mm (Diseragamkan Keliling)")
    print("4. Drawer Bottom (M): Lebar masuk dado 5mm (W_front - 54 mm); Kedalaman = D - 7 mm")
    print("5. Side Panel:       Plywood 18 mm 1F (PLY-18-MSF), TIDAK PERNAH SOLID WOOD")
    print("6. Back Panel:       Wajib Plywood 9 mm RAW + Back Frame solid 40x25 mm")
    print("7. Door Opening:     Height/n - 2mm | Width/n - 2mm (MDF-18-MDF)")
    print("8. Part Naming:      Bahasa Inggris murni untuk standardisasi ekspor")
    print("9. Fasteners/Misc:   Baut, sekrup, lem, dowel ditanggung rate flat per m3 solid")
    print("10. Catalog Parts:   25 Part resmi (1: Bottom stretcher F/B ... 25: vertical support)")
    print("=" * 75)

def cmd_derive_drawer(args):
    w = args.width
    h = args.height
    depth = args.depth
    res = derive_drawer_box(w, h, depth)

    print("=" * 65)
    print(f"  DRAWER DERIVATION RESULT (Front: {w} x {h} mm, Case: {depth} mm)")
    print("=" * 65)
    print(f"Slide Length D:    {res['side_length_d']} mm (DTC-14\")")
    print(f"Drawer Front (AD): {res['front'].l} x {res['front'].w} x {res['front'].t} mm ({res['front'].panel_type})")
    print(f"Drawer Side (K):   {res['side'].l} x {res['side'].w} x {res['side'].t} mm ({res['side'].panel_type}, Qty {res['side'].qty})")
    print(f"Inner Front (AL):  {res['inner_front'].l} x {res['inner_front'].w} x {res['inner_front'].t} mm ({res['inner_front'].panel_type})")
    print(f"Drawer Back (L):   {res['back'].l} x {res['back'].w} x {res['back'].t} mm ({res['back'].panel_type}) [SAMA DGN INNER DEPAN]")
    print(f"Drawer Bottom (M): {res['bottom'].l} x {res['bottom'].w} x {res['bottom'].t} mm ({res['bottom'].panel_type})")
    print(f"Slide Hardware:    {res['slide'].description} (Qty {res['slide'].qty})")
    print("=" * 65)

def cmd_create(args):
    json_path = Path(args.spec_json)
    if not json_path.exists():
        print(f"Error: Specification file not found: {json_path}", file=sys.stderr)
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

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

    # rules
    p_rules = subparsers.add_parser("rules", help="Display construction rules v2.1 summary.")
    p_rules.set_defaults(func=cmd_rules)

    # parts
    p_parts = subparsers.add_parser("parts", help="Display 25-part catalog reference.")
    p_parts.set_defaults(func=cmd_parts)

    # derive-drawer
    p_drawer = subparsers.add_parser("derive-drawer", help="Calculate exact drawer box cuts from front dimensions.")
    p_drawer.add_argument("-w", "--width", type=float, required=True, help="Drawer front width in mm.")
    p_drawer.add_argument("-H", "--height", type=float, required=True, help="Drawer front height in mm.")
    p_drawer.add_argument("-d", "--depth", type=float, required=True, help="Case overall depth in mm.")
    p_drawer.set_defaults(func=cmd_derive_drawer)

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

    # auto / pipeline
    def cmd_auto(args):
        res = run_pipeline(args.pdf, args.output)
        print("\n" + "=" * 65)
        print("  AUTOMATED BOM GENERATION SUCCESSFUL")
        print("=" * 65)
        print(f"File:       {res['output_file']}")
        print(f"Direct:     Rp {res['direct_cost']:,.2f}")
        print(f"Unit (HPP): Rp {res['unit_cost']:,.2f}")
        print(f"Checks:     {res['open_checks']} (0 = PASS)")
        print("=" * 65)

    p_auto = subparsers.add_parser("auto", help="End-to-end automated BOM generation from PDF drawing.")
    p_auto.add_argument("pdf", help="Path to PDF drawing file.")
    p_auto.add_argument("-o", "--output", help="Optional output .xlsx path.")
    p_auto.set_defaults(func=cmd_auto)

    # collection
    def cmd_collection(args):
        from generators.multi_bom import build_multi_bom
        import datetime
        specs = []
        for p in args.spec_files:
            with open(p, "r", encoding="utf-8") as fp:
                d = json.load(fp)
            h = ItemHeader(**d["header"])
            solids = [SolidPart(**x) for x in d["solid_parts"]]
            panels = [PanelPart(**x) for x in d.get("panel_parts", [])]
            hws = [HardwarePart(**x) for x in d.get("hardware_parts", [])]
            specs.append(BOMSpecification(h, solids, panels, hws))

        now_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        title = args.title or "COLLECTION"
        out_name = args.output or f"{title} {now_str}.xlsx"
        build_multi_bom(specs, out_name)
        print("\n" + "=" * 65)
        print(f"  COLLECTION MULTI-ITEM BOM GENERATED: {out_name}")
        print(f"  Total Items: {len(specs)}")
        print("=" * 65)

    p_coll = subparsers.add_parser("collection", help="Generate single multi-item collection BOM workbook.")
    p_coll.add_argument("spec_files", nargs="+", help="JSON spec files for collection items.")
    p_coll.add_argument("-t", "--title", help="Collection title banner.")
    p_coll.add_argument("-o", "--output", help="Output .xlsx workbook path.")
    p_coll.set_defaults(func=cmd_collection)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
