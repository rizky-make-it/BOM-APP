"""Components (from tools/dwg2d_components) -> BOM-APP spec.json, filling gaps with core/construction logic.

python tools/dwg2d_to_spec.py <item>_components.json --collection LEXI --out data/from_dwg/
Rules:
  - every row gets a part_no (Part Master v3); thickness / family / veneer faces follow RULES per part (core/construction)
  - a size the drawing did not state is DERIVED by construction logic, never left empty; the formula is kept in `note`
  - metal rows -> SolidPart with material = HOLLOW-AxBxWALL (own METAL section in the workbook, priced per metre)
  - hardware rows -> HardwarePart; drawer slides added per drawer from the standard glide length
  - status STATED / DERIVED / CHECK and the source label handle stay in `note` so every number is traceable
"""
import argparse, json, os, re, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from core import construction as K

MMAP = json.load(open(os.path.join(ROOT, "data", "material_map.json"), encoding="utf-8"))
METAL_PARTS = {101, 102, 103, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210}


def build_spec(comp_json, collection, item_code=None, item_name=None, overall=None):
    c = json.load(open(comp_json, encoding="utf-8"))
    rows = c["components"]; dims = {int(k): v for k, v in c["drawing_dimensions_mm"].items()}
    item = item_code or c["item"]; name = item_name or c["name"]
    # overall size: the three largest distinct dims that look like overall (>= 300) unless given
    big = sorted([d for d in dims if d >= 200], reverse=True)
    if overall:
        L, W, H = overall
    else:
        L = big[0] if big else 0; W = next((d for d in big if d < L), L); H = next((d for d in big if d < W), W)
    header = dict(item_code=item, item_name=name, collection=collection, overall_l=float(L), overall_w=float(W), overall_h=float(H), order_qty=1,
                  drawing_link=os.path.basename(c["source_dwg"]), finish_recipe="NC NATURAL", flatpack_yn="N",
                  notes=f"Spec dibangun otomatis dari DWG drafter ({c['generated'][:10]}); ukuran keseluruhan {L}x{W}x{H} DERIVED dari dimensi gambar: CONFIRM.")
    solid, panels, hw = [], [], []
    frame_span = max([r["l"] for r in rows if r["code"].startswith("MT-") and r["no"] in (201, 202)] + [0])
    frame_sec = max([r["t"] for r in rows if r["code"].startswith("MT-")] + [0])
    case_depth = W if W else 450
    # ---- drawers by construction logic: the drawing's drawer faces (401 front, 402/403/404 box walls, 405 base) only tell us
    #      the OPENING (front width x height) and how many drawers; the box itself comes from the factory formula.
    dr_rows = [r for r in rows if r["no"] in (401, 402, 403, 404, 405)]
    fronts = [r for r in rows if r["no"] == 401]
    # opening width = widest 401 face or the frame span; height = tallest 'standing' drawer wall / front height
    open_w = max([max(r["l"], r["w"]) for r in fronts if r["w"]] + [frame_span or 0]) or L
    # drawer height = the standing front faces (401 seen from the edge: L x ? ) -> their L is the height; box walls (402) are shorter
    h401 = [r["l"] for r in fronts if not r["w"] and r["l"] < open_w]
    h402 = [r["l"] for r in rows if r["no"] == 402 and not r["w"]]
    open_h = max(h401) if h401 else (max(h402) + 30 if h402 else 0)      # box wall = H_front - 30 (factory rule) -> invert
    n_drawers = 0
    if fronts and open_h:
        # count: distinct drawer bases (405) or standing box walls (402) / 2, else 1
        bases = sum(int(r["qty"]) for r in rows if r["no"] == 405)
        n_drawers = max(1, bases) if bases else 1
    drawers = []
    rows_used = set()
    if n_drawers:
        from core.construction import drawer_parts
        for no, comp, l, w, t, q, f in drawer_parts(open_w, open_h, case_depth, qty=n_drawers):
            pt, fp = K.panel_code(no, "B", 0, t)
            panels.append(dict(label=f"{no} / B-{int(t)}-0X", component=comp, panel_type=pt, l=float(max(l, w)), w=float(min(l, w)), t=float(t), qty=int(q), exposed_faces=0,
                               note=f"[DERIVED] kotak laci dari rumus pabrik: {f}; {fp}"))
        t, f_t = K.thickness(401, 18); pt, fp = K.panel_code(401, "C", 1, t)
        panels.append(dict(label="401 / C-18-1X", component="DRAWER FRONT", panel_type=pt, l=float(open_w), w=float(open_h), t=t, qty=n_drawers, exposed_faces=1,
                           note=f"[DERIVED] muka laci = bukaan {open_w:g} x {open_h:g} (dari bidang laci di gambar); {f_t}; {fp}"))
        drawers = [dict(qty=n_drawers)]
        rows_used = {r["row"] for r in dr_rows}
    for r in rows:
        if r["row"] in rows_used:
            continue
        no, code, st = r["no"], r["code"], r["status"]
        trace = f"[{st}] tag {r['row']}: {r['note'][:70]}"
        if code.startswith("MT-"):
            a, b = code[3:].split("x")
            mat = f"HOLLOW-{a}x{b}x{MMAP['metal']['wall_default']}"
            solid.append(dict(label=f"{no} / {code}", component=r["name"], l=float(r["l"]), w=float(b), t=float(a), qty=int(r["qty"]), material=mat,
                              exposed="Y", curved="N", tier_override="B", note=trace + f"; hollow {a}x{b} dinding {MMAP['metal']['wall_default']} (HOLLOW_WALL)"))
            continue
        if code in MMAP["solid"]:
            t = r["t"] or min(r["l"], r["w"]) if r["w"] else r["t"]
            solid.append(dict(label=f"{no} / {code}", component=r["name"], l=float(r["l"]), w=float(r["w"] or 0), t=float(t or 0), qty=int(r["qty"]),
                              material=MMAP["solid"][code]["material"], exposed="Y", curved="N", tier_override="B", note=trace))
            continue
        if code.startswith("HW-") or code in ("D1", "D2"):
            h = MMAP["hardware"].get(code, dict(description=r["name"], vendor="?", uom="pcs", unit_price=0.0, note=""))
            hw.append(dict(item_master_code="HARDWARE", label=f"{no} / {code}", description=h["description"], vendor=h["vendor"], qty=float(r["qty"]), uom=h["uom"],
                           unit_price=float(h["unit_price"]), note=trace + "; " + h["note"]))
            continue
        # panel
        m = re.match(r"([BC])-(\d+)-(\d)X", code)
        fam_lbl, t_lbl, faces_lbl = (m.group(1), float(m.group(2)), int(m.group(3))) if m else ("B", float(r["t"] or 18), 1)
        t, f_t = K.thickness(no, t_lbl)
        ptype, f_p = K.panel_code(no, fam_lbl, faces_lbl, t)
        l, w = float(r["l"]), float(r["w"] or 0)
        formula = ""
        if not w:
            # construction logic: panel sits between frame members or spans the opening
            if no in (308, 310, 601, 306):
                w, formula = K.width_from_span(frame_span + 2 * frame_sec if frame_span else L, frame_sec, inside=True) if frame_span else (W, "= kedalaman keseluruhan")
            elif no in (302, 801):
                w, formula = (l, "panel persegi = bentang yang terbaca") if l < 1.5 * (frame_span or l) else K.width_from_span(frame_span or L, frame_sec, inside=True)
            elif no in (402, 403, 404):
                w, formula = (float(K.glide_length(case_depth)[0]), f"panjang sisi laci = rel standar untuk D {case_depth}")
            elif no == 401:
                w, formula = (frame_span or L, "muka laci = bukaan rangka")
            else:
                w, formula = (frame_span or W, "= bentang rangka (default)")
            st = "DERIVED"
        panels.append(dict(label=f"{no} / {code}", component=r["name"], panel_type=ptype, l=max(l, w), w=min(l, w), t=t, qty=int(r["qty"]),
                           exposed_faces=K.RULE_FACES.get(no, faces_lbl), note=trace + (f"; lebar {w:g}: {formula}" if formula else "") + f"; {f_t}; {f_p}"))
    # drawer slides: one set per drawer front
    n_dr = sum(int(r["qty"]) for r in drawers)
    if n_dr:
        gl, f_g = K.glide_length(case_depth); h = MMAP["hardware"]["D2"]
        hw.append(dict(item_master_code="HARDWARE", label="901 / D2", description=f'{h["description"]} {gl} mm', vendor=h["vendor"], qty=float(n_dr), uom=h["uom"],
                       unit_price=float(h["unit_price"]), note=f"[DERIVED] {n_dr} laci x 1 set; {f_g}; {h['note']}"))
    # sheet limit: 8 metal rows. Metal is priced per metre, so rows of the same hollow code can be merged by LENGTH CLASS
    # without changing cost: keep the 7 longest distinct rows, fold the rest into one "SUPPORTS (various)" row whose
    # length = total metres / qty (cost identical: sum of L x qty is preserved).
    metal = [p for p in solid if p["material"].startswith("HOLLOW-")]
    if len(metal) > 8:
        metal.sort(key=lambda p: -p["l"] * p["qty"])
        keep, rest = metal[:7], metal[7:]
        tot = sum(p["l"] * p["qty"] for p in rest); q = sum(p["qty"] for p in rest)
        codes = {p["material"] for p in rest}
        if len(codes) == 1:
            merged = dict(label="210 / MT", component="SUPPORTS (various, merged)", l=round(tot / q, 1), w=rest[0]["w"], t=rest[0]["t"], qty=q, material=rest[0]["material"],
                          exposed="Y", curved="N", tier_override="B", note="[DERIVED] " + "; ".join(f"{p['component']} {p['l']:g}x{p['qty']}" for p in rest) + f"; total {tot/1000:.2f} m, dihitung per meter jadi biaya sama")
            solid = [p for p in solid if not p["material"].startswith("HOLLOW-")] + keep + [merged]
        else:
            # two hollow sizes in the overflow: merge per code
            solid = [p for p in solid if not p["material"].startswith("HOLLOW-")] + keep
            for code in sorted(codes):
                grp = [p for p in rest if p["material"] == code]; tot = sum(p["l"] * p["qty"] for p in grp); q = sum(p["qty"] for p in grp)
                solid.append(dict(label="210 / MT", component=f"SUPPORTS {code[7:]} (merged)", l=round(tot / q, 1), w=grp[0]["w"], t=grp[0]["t"], qty=q, material=code,
                                  exposed="Y", curved="N", tier_override="B", note="[DERIVED] " + "; ".join(f"{p['component']} {p['l']:g}x{p['qty']}" for p in grp) + f"; total {tot/1000:.2f} m"))
            if sum(1 for p in solid if p["material"].startswith("HOLLOW-")) > 8:
                keep2 = [p for p in solid if p["material"].startswith("HOLLOW-")][:8]
                solid = [p for p in solid if not p["material"].startswith("HOLLOW-")] + keep2
    return dict(header=header, solid_parts=solid, panel_parts=panels, hardware_parts=hw,
                _provenance=dict(source=c["source_dwg"], components_json=os.path.abspath(comp_json), part_list=c["part_list"],
                                 check_rows=[r["row"] for r in rows if r["status"] == "CHECK"], derived_rows=[r["row"] for r in rows if r["status"] == "DERIVED"]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("components"); ap.add_argument("--collection", default="FROM-DWG"); ap.add_argument("--out", default=os.path.join(ROOT, "data", "from_dwg"))
    ap.add_argument("--overall", help="LxWxH override, e.g. 550x550x550")
    a = ap.parse_args()
    ov = tuple(float(v) for v in a.overall.lower().split("x")) if a.overall else None
    spec = build_spec(a.components, a.collection, overall=ov)
    os.makedirs(a.out, exist_ok=True)
    fn = os.path.join(a.out, spec["header"]["item_code"].lower().replace("-", "_") + "_spec.json")
    json.dump(spec, open(fn, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"{fn}: solid {len(spec['solid_parts'])} panel {len(spec['panel_parts'])} hw {len(spec['hardware_parts'])} | CHECK rows {spec['_provenance']['check_rows']}")
    for p in spec["solid_parts"]: print(f"  S {p['component']:<28} {p['l']:>6.0f} x {p['w']:>4.0f} x {p['t']:>3.0f} x{p['qty']:<2} {p['material']}")
    for p in spec["panel_parts"]: print(f"  P {p['component']:<28} {p['l']:>6.0f} x {p['w']:>4.0f} x {p['t']:>3.0f} x{p['qty']:<2} {p['panel_type']}")
    for p in spec["hardware_parts"]: print(f"  H {p['description']:<28} x{p['qty']:.0f}")
