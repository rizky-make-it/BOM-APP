"""Labelled sheet for ONE drafter DWG (2D route, headless AutoCAD), readable by humans (PDF) and by AI (JSON + DWG layer).

python tools/dwg2d_label_sheet.py <dwg> --item CODE --name NAME [--collection LEXI] --out DIR
 1. tools/dwg2d_read.py logic: faces from loose lines + leader labels -> STATED rows (label, size, count, faces)
 2. on a COPY of the DWG: layer BOM-BALLOON (circle+number per face, ladder rails left/right of the XZ drawing),
    layer BOM-TABLE (part list: NO, LABEL, SIZE, QTY), title note; everything in the drafter's XZ plane.
 3. plot model space window (VPOINT front) to A3 PDF via accoreconsole; verify PDF content.
 4. write <out>/<item>_labels.json: every balloon number -> label, size, qty, face positions, dims; plus provenance.
"""
import argparse, datetime, json, math, os, shutil, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acad_core as C
import dwg2d_read as D2

R_B, H_T = 24.0, 18.0


def ocs(x, z):
    return f"(list {x:.2f} {z:.2f} 0.0)"


def circle(x, z, r, layer):
    return f'(entmake (list (cons 0 "CIRCLE") (cons 8 "{layer}") (cons 10 {ocs(x, z)}) (cons 40 {r}) (cons 210 (list 0.0 -1.0 0.0))))'


def text(x, z, s, h, layer, mc=False):
    s = str(s).replace('"', "'")
    j = f' (cons 72 1) (cons 73 2) (cons 11 {ocs(x, z)})' if mc else ""
    return f'(entmake (list (cons 0 "TEXT") (cons 8 "{layer}") (cons 10 {ocs(x, z)}) (cons 40 {h}) (cons 1 "{s}"){j} (cons 210 (list 0.0 -1.0 0.0))))'


def line(x1, z1, x2, z2, layer):
    return f'(entmake (list (cons 0 "LINE") (cons 8 "{layer}") (cons 10 (list {x1:.2f} 0.0 {z1:.2f})) (cons 11 (list {x2:.2f} 0.0 {z2:.2f}))))'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dwg"); ap.add_argument("--item", required=True); ap.add_argument("--name", default="")
    ap.add_argument("--collection", default="LEXI"); ap.add_argument("--out", required=True)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    res = D2.read(a.dwg); st = D2.statement(res["rows"])
    if not st:
        print("no labelled faces found"); sys.exit(1)
    allf = [f for r in st for f in r["faces"]]
    x0 = min(f[0] for f in allf); x1 = max(f[0] + f[2] for f in allf)
    z0 = min(f[1] for f in allf); z1 = max(f[1] + f[3] for f in allf)
    # drawing extent incl. unlabelled geometry (dims live outside the faces): pad generously
    PADX, PADZ = 260, 220
    rail_l, rail_r = x0 - 150, x1 + 150
    L = ["FILEDIA", "0", "CMDECHO", "0", "EXPERT", "5",
         "_.-LAYER", "_M", "BOM-BALLOON", "_C", "5", "BOM-BALLOON", "", "_.-LAYER", "_LW", "0.5", "BOM-BALLOON", "", "_.-LAYER", "_M", "BOM-TABLE", "_C", "7", "BOM-TABLE", ""]
    # balloons: one per face. Faces are clustered into VIEWS (gap > 120 mm in x or z); each view gets its own
    # left/right rails so leaders stay short and never cross another view.
    anchors = []
    for i, r in enumerate(st, 1):
        for (fx, fz, fw, fh) in r["faces"]:
            anchors.append((i, fx + fw / 2, fz + fh / 2, fx, fz, fx + fw, fz + fh))
    views = []
    for t in sorted(anchors, key=lambda t: (t[1], t[2])):
        for v in views:
            if t[3] <= v["x1"] + 120 and t[5] >= v["x0"] - 120 and t[4] <= v["z1"] + 120 and t[6] >= v["z0"] - 120:
                v["x0"] = min(v["x0"], t[3]); v["x1"] = max(v["x1"], t[5]); v["z0"] = min(v["z0"], t[4]); v["z1"] = max(v["z1"], t[6]); v["a"].append(t); break
        else:
            views.append(dict(x0=t[3], x1=t[5], z0=t[4], z1=t[6], a=[t]))
    # merge overlapping views once more
    merged = True
    while merged:
        merged = False
        for i_ in range(len(views)):
            for j_ in range(i_ + 1, len(views)):
                A_, B_ = views[i_], views[j_]
                if A_["x0"] <= B_["x1"] + 120 and A_["x1"] >= B_["x0"] - 120 and A_["z0"] <= B_["z1"] + 120 and A_["z1"] >= B_["z0"] - 120:
                    A_["x0"] = min(A_["x0"], B_["x0"]); A_["x1"] = max(A_["x1"], B_["x1"]); A_["z0"] = min(A_["z0"], B_["z0"]); A_["z1"] = max(A_["z1"], B_["z1"]); A_["a"] += B_["a"]
                    views.pop(j_); merged = True; break
            if merged: break
    balloons = []
    dim_pts = res.get("dim_pts", [])
    for v in views:
        # rails sit OUTSIDE the drafter's dimensions of this view
        inview = [p for p in dim_pts if v["x0"] - 260 <= p[0] <= v["x1"] + 260 and v["z0"] - 160 <= p[1] <= v["z1"] + 160]
        dx0 = min([p[0] for p in inview] + [v["x0"]]); dx1 = max([p[0] for p in inview] + [v["x1"]])
        # never let a rail reach into a neighbouring view
        others = [o for o in views if o is not v]
        left_lim = max([o["x1"] + 60 for o in others if o["x1"] < v["x0"] and not (o["z1"] < v["z0"] or o["z0"] > v["z1"])] + [-1e9])
        right_lim = min([o["x0"] - 60 for o in others if o["x0"] > v["x1"] and not (o["z1"] < v["z0"] or o["z0"] > v["z1"])] + [1e9])
        dx0 = max(dx0, left_lim + 70); dx1 = min(dx1, right_lim - 70)
        dx1 = max(dx1, v["x1"] + 60); dx0 = min(dx0, v["x0"] - 60)
        vm = (v["x0"] + v["x1"]) / 2
        # ONE balloon per part number per view: pick the face nearest the rail side it will go to
        per_no = {}
        for t in v["a"]:
            side = "L" if t[1] < vm else "R"
            key = (t[0], side)
            if key not in per_no or (side == "L" and t[3] < per_no[key][3]) or (side == "R" and t[5] > per_no[key][5]):
                per_no[key] = t
        for side, rail in (("L", dx0 - 60), ("R", dx1 + 60)):
            pick = sorted([t for (no, sd), t in per_no.items() if sd == side], key=lambda t: t[2])
            last = None
            for (i, cx, cz, fx0, fz0, fx1, fz1) in pick:
                ax_ = fx0 if side == "L" else fx1          # anchor on the face edge facing the rail: no crossing
                az_ = cz
                bz = az_ if last is None or az_ >= last + R_B * 2.8 else last + R_B * 2.8
                last = bz
                d = math.hypot(rail - ax_, bz - az_) or 1
                ex, ez = rail - (rail - ax_) / d * R_B, bz - (bz - az_) / d * R_B
                L += [line(ax_, az_, ex, ez, "BOM-BALLOON"), circle(ax_, az_, 2.5, "BOM-BALLOON"), circle(rail, bz, R_B, "BOM-BALLOON"), text(rail, bz, i, H_T, "BOM-BALLOON", True)]
                balloons.append(dict(no=i, anchor=[round(ax_), round(az_)], balloon=[round(rail), round(bz)]))
        v["rail_l"], v["rail_r"] = dx0 - 60, dx1 + 60
    rail_r = max(v["rail_r"] for v in views)
    x0 = min(v["rail_l"] for v in views); x1 = rail_r; z0 = min(v["z0"] for v in views); z1 = max(v["z1"] for v in views)
    print("views:", len(views))
    # table right of the right rail
    tx, tz = rail_r + 80, z1 + 60
    rh = 46; cw = [55, 420, 200, 70]; tw = sum(cw); rows_n = len(st) + 2; by = tz - rh * rows_n
    L += [line(tx, tz, tx + tw, tz, "BOM-TABLE"), line(tx + tw, tz, tx + tw, by, "BOM-TABLE"), line(tx + tw, by, tx, by, "BOM-TABLE"), line(tx, by, tx, tz, "BOM-TABLE")]
    L += [line(tx, tz - rh * k, tx + tw, tz - rh * k, "BOM-TABLE") for k in range(1, rows_n)]
    xx = tx
    for c in cw[:-1]:
        xx += c; L += [line(xx, tz - rh, xx, by, "BOM-TABLE")]
    L += [text(tx + 8, tz - rh + 14, f"{a.item} {a.name} - PART LABELS", 17, "BOM-TABLE")]
    xx = tx
    for c, h in zip(cw, ["NO", "LABEL (STATED)", "UKURAN (mm)", "QTY"]):
        L += [text(xx + 8, tz - 2 * rh + 14, h, 15, "BOM-TABLE")]; xx += c
    for i, r in enumerate(st, 1):
        xx = tx
        for c, v in zip(cw, [str(i), r["label"][:30], f"{r['long']} x {r['short']}", str(r["n"])]):
            L += [text(xx + 8, tz - (i + 2) * rh + 14, v, 15, "BOM-TABLE")]; xx += c
    dims = {k: v for k, v in res["dims"].items() if isinstance(k, int) and k > 0}
    L += [text(tx, by - 18, "UKURAN = bidang yang dilabeli drafter (STATED). Dimensi gambar: " + ", ".join(f"{k}" + (f" x{v}" if v > 1 else "") for k, v in sorted(dims.items())), 13, "BOM-TABLE"),
          text(tx, by - 40, f"Dibuat {datetime.date.today():%d %b %Y} oleh BOM-APP dari {os.path.basename(a.dwg)}; nomor = NO di tabel; JSON pendamping untuk AI.", 13, "BOM-TABLE")]
    # plot
    base = f"{a.item}_labels"; out_pdf = os.path.join(a.out, base + ".pdf"); out_dwg = os.path.join(a.out, base + ".dwg")
    for f in (out_pdf, out_dwg):
        if os.path.exists(f):
            try: os.remove(f)
            except OSError: pass
    wx0, wz0, wx1, wz1 = x0 - PADX, min(z0 - PADZ, by - 60), tx + tw + 200, z1 + PADZ
    w = tempfile.mkdtemp(prefix="lbl_"); src = os.path.join(w, "src.dwg"); shutil.copy(a.dwg, src)
    L += ["_.TILEMODE", "1", "_.VPOINT", "0,-1,0", "_.UCS", "_V",
          "_.-PLOT", "_Y", "Model", "DWG To PDF.pc3", C.PAPER_A3, "_M", "_L", "_N", "_W", f"{wx0:.0f},{wz0:.0f}", f"{wx1:.0f},{wz1:.0f}", "_F", "_C",
          "_Y", ".", "_Y", "_A", out_pdf.replace("\\", "/"), "_N", "_Y", "_.UCS", "_W", "_.SAVEAS", "2018", out_dwg.replace("\\", "/")]
    ok, log, why = C.run(src, L, timeout=240, workdir=w)
    good, det = C.pdf_has_content(out_pdf)
    js = dict(item=a.item, name=a.name, collection=a.collection, source_dwg=os.path.abspath(a.dwg), generated=datetime.datetime.now().isoformat(timespec="seconds"),
              plane="XZ (drafter 2D views; x,z in mm)", parts=[dict(no=i, label=r["label"], long_mm=r["long"], short_mm=r["short"], qty=r["n"], faces_xzwh=r["faces"]) for i, r in enumerate(st, 1)],
              balloons=balloons, drawing_dimensions_mm=dims, counts=dict(segments=res["n_segments"], faces=res["n_faces"], labels=res["n_labels"]),
              status="STATED labels and sizes from the drafter's drawing; roles/thickness per BOM-APP RULES are NOT applied here")
    json.dump(js, open(os.path.join(a.out, base + ".json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    open(os.path.join(a.out, base + ".log"), "w", encoding="utf-8").write(log)
    print(f"plot: {why} | PDF {good} {det} | rows {len(st)} balloons {len(balloons)}\n{out_pdf}\n{out_dwg}\n{os.path.join(a.out, base + '.json')}")
    if not ok or not good:
        print("\n".join([l for l in log.splitlines() if l.strip()][-12:])); sys.exit(1)


if __name__ == "__main__":
    main()
