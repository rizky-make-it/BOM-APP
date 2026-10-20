"""Fill the Tala template with one item (solids from a source DWG + numbering) and plot it, all in headless AutoCAD.

python tools/acad_fill_sheet.py --dwg src.dwg --solids solids.json --numbering numbering.json --out DIR
       [--scale 6] [--item-code X] [--name X] [--collection X] [--template templates/TALA_A3.dwt]
Output: <out>/<base>.dwg + <out>/<base>.pdf (verified to contain text + vectors) + <base>.log
"""
import argparse, collections, datetime, json, math, os, shutil, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acad_core as C
import acad_template as TPL

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAT = {"101": "Solid wood Mindi (A)", "102": "Solid wood Mindi (A)", "202": "Solid wood Mindi (A)", "207": "Solid wood Mindi (A)",
       "301": "MDF veneer E0 1F (C-18-1X)*", "302": "Plywood veneer Mindi 1F", "306": "Plywood veneer Mindi 1F",
       "307": "Plywood veneer Mindi 1F", "308": "Plywood veneer Mindi 1F", "299": "belum diketahui"}
CONF = {"high": "YAKIN", "medium": "CUKUP", "low": "RAGU"}


def q(s):
    return '"' + str(s).replace("\\", "/").replace('"', "'") + '"'


def cell_text(x, y, s, h=2.2, layer="SHEET-TEXT", just=None):
    s = str(s).replace("\\", "/").replace('"', "'")
    j = f' (cons 72 1) (cons 73 2) (cons 11 (list {x:.2f} {y:.2f} 0))' if just == "MC" else ""
    return [f'(entmake (list (cons 0 "TEXT") (cons 8 "{layer}") (cons 7 "TALA") (cons 10 (list {x:.2f} {y:.2f} 0)) (cons 40 {h}) (cons 1 "{s}"){j}))']

def merge_items(rows):
    g = collections.OrderedDict()
    for r in sorted(rows, key=lambda r: (r["pn"], tuple(-round(v) for v in r["dims"]))):
        g.setdefault((r["pn"], tuple(round(v, 1) for v in r["dims"])), []).append(r)
    items = []
    for n, (key, rs) in enumerate(g.items(), 1):
        worst = min((r["conf"] for r in rs), key={"low": 0, "medium": 1, "high": 2}.get)
        items.append(dict(no=n, pn=key[0], name=rs[0]["name"], dims=key[1], qty=len(rs), conf=worst, handles=[r["handle"].upper() for r in rs], mat=MAT.get(key[0], "?")))
    return items


def ring(pts, center, rx, ry, gap=0.55):
    """Place balloons on the rectangle (center +- rx, +- ry): each anchor goes to the nearest side, spread along it."""
    sides = {"L": [], "R": [], "T": [], "B": []}
    for n, (x, y) in pts.items():
        dx, dy = (x - center[0]) / rx, (y - center[1]) / ry
        if abs(dx) >= abs(dy):
            sides["R" if dx > 0 else "L"].append((y, n))
        else:
            sides["T" if dy > 0 else "B"].append((x, n))
    out = {}
    for sd, lst in sides.items():
        lst.sort()
        m = len(lst)
        if not m:
            continue
        span = (2 * ry if sd in "LR" else 2 * rx)
        step = min(9.0, max(8.0, span / max(1, m - 1))) if m > 1 else 0
        # spread evenly around the mean of anchors, clamped to the side
        mid = sum(v for v, _ in lst) / m
        lo = (center[1] - ry) if sd in "LR" else (center[0] - rx)
        hi = (center[1] + ry) if sd in "LR" else (center[0] + rx)
        start = min(max(mid - step * (m - 1) / 2, lo), hi - step * (m - 1))
        for i, (_, n) in enumerate(lst):
            v = start + i * step
            out[n] = (center[0] - rx, v) if sd == "L" else (center[0] + rx, v) if sd == "R" else (v, center[1] + ry) if sd == "T" else (v, center[1] - ry)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dwg", required=True); ap.add_argument("--solids", required=True); ap.add_argument("--numbering", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--scale", type=float, default=6.0)
    ap.add_argument("--item-code", default="-"); ap.add_argument("--name", default="UNIT K1"); ap.add_argument("--collection", default="LEXI (belum dikonfirmasi)")
    ap.add_argument("--template", default=os.path.join(ROOT, "templates", "TALA_A3.dwt"))
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    base = os.path.splitext(os.path.basename(a.numbering))[0]
    rows = json.load(open(a.numbering, encoding="utf-8"))
    S = {s["handle"].upper(): s for s in json.load(open(a.solids, encoding="utf-8"))["solids"]}
    items = merge_items(rows)
    hs = [r["handle"].upper() for r in rows]
    x0 = min(S[h]["x0"] for h in hs); x1 = max(S[h]["x1"] for h in hs)
    y0 = min(S[h]["y0"] for h in hs); y1 = max(S[h]["y1"] for h in hs)
    z0 = min(S[h]["z0"] for h in hs); z1 = max(S[h]["z1"] for h in hs)
    SX, SY, SZ = x1 - x0, y1 - y0, z1 - z0
    T = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    TH = {"x": T[0], "y": T[1], "z": T[2]}
    need = max(SX / (TPL.VP["FRONT"][2] - 24), SZ / (TPL.VP["FRONT"][3] - 24), SY / (TPL.VP["SIDE"][2] - 24), SY / (TPL.VP["TOP"][3] - 24))
    if need > a.scale:                     # auto-fit to the next common scale; never let a view overflow its box
        a.scale = next(sc for sc in (5, 6, 8, 10, 12.5, 15, 20, 25) if sc >= need)
    k = 1.0 / a.scale
    stamp = datetime.datetime.now().strftime("%H%M%S")
    out_dwg = os.path.join(a.out, f"{base}.dwg"); out_pdf = os.path.join(a.out, f"{base}.pdf")
    for f in (out_dwg, out_pdf):
        if os.path.exists(f):
            try: os.remove(f)
            except OSError:
                out_dwg = os.path.join(a.out, f"{base}_{stamp}.dwg"); out_pdf = os.path.join(a.out, f"{base}_{stamp}.pdf"); break

    # ---- step A: extract the group's solids into a clean DWG (WBLOCK by handle)
    w = tempfile.mkdtemp(prefix="fill_"); src = os.path.join(w, "src.dwg"); shutil.copy(a.dwg, src)
    parts = os.path.join(w, "parts.dwg").replace("\\", "/")
    sel = "(setq ss (ssadd)) " + " ".join(f'(if (handent "{h}") (ssadd (handent "{h}") ss))' for h in hs)
    L = ["FILEDIA", "0", "CMDECHO", "0", sel, '(princ (strcat "\\nSEL=" (itoa (sslength ss))))',
         "_.-WBLOCK", parts, "", "0,0,0", "!ss", ""]
    ok, log, why = C.run(src, L, timeout=120, workdir=w)
    n_sel = next((l.split("SEL=")[1].strip() for l in log.splitlines() if "SEL=" in l and not l.startswith("(")), "?")
    print("A extract:", why, "| selected", n_sel, "| parts.dwg", os.path.exists(parts))
    if not os.path.exists(parts):
        print(log[-1500:]); sys.exit(1)

    # ---- step B: template -> insert parts -> viewports -> annotations -> plot -> save
    sheet = os.path.join(w, "sheet.dwg"); shutil.copy(a.template, sheet)
    L = ["FILEDIA", "0", "CMDECHO", "0", "ATTDIA", "0", "ATTREQ", "0", "EXPERT", "5",
         "_.TILEMODE", "1", "_.-LAYER", "_S", "PART", "",
         "_.-INSERT", "*" + parts, "0,0,0", "1", "0",
         "_.TILEMODE", "0", "_.LAYOUT", "_S", "SHEET", "_.PSPACE"]
    # viewports: find by center, set view, scale, turn on, hidden-line plot
    # accoreconsole executes VPOINT/ZOOM in a paper-space viewport but the view never changes (no graphics system),
    # so viewports stay empty. Draw the orthographic projections ourselves in paper space from the solid boxes
    # (group K1 parts are all true boxes, fill ~100%), far-to-near with filled light faces for a hidden-line look.
    L += ["_.-LAYER", "_S", "PART", ""]
    order_key = {"FRONT": lambda b: -b["y1"], "SIDE": lambda b: b["x0"], "TOP": lambda b: b["z0"]}
    HV2 = {"FRONT": ("x", "z"), "SIDE": ("y", "z"), "TOP": ("x", "y")}
    for nm, (cx, cy, vw, vh) in TPL.VP.items():
        if nm == "ISO":
            continue
        ah, av = HV2[nm]
        for h in sorted(hs, key=lambda h: order_key[nm](S[h])):
            sb = S[h]
            px0 = cx + k * (sb[ah + "0"] - TH[ah]); px1 = cx + k * (sb[ah + "1"] - TH[ah])
            py0 = cy + k * (sb[av + "0"] - TH[av]); py1 = cy + k * (sb[av + "1"] - TH[av])
            if nm == "SIDE":   # looking from +X: depth axis y runs right-to-left; mirror so FRONT of furniture (y0) is on the left
                px0, px1 = cx - (px0 - cx), cx - (px1 - cx)
                px0, px1 = min(px0, px1), max(px0, px1)
            L += ['(entmake (list (cons 0 "SOLID") (cons 8 "PART-FILL") (cons 62 254) '
                  f'(cons 10 (list {px0:.3f} {py0:.3f} 0)) (cons 11 (list {px1:.3f} {py0:.3f} 0)) (cons 12 (list {px0:.3f} {py1:.3f} 0)) (cons 13 (list {px1:.3f} {py1:.3f} 0))))',
                  '(entmake (list (cons 0 "LWPOLYLINE") (cons 100 "AcDbEntity") (cons 8 "PART") (cons 100 "AcDbPolyline") (cons 90 4) (cons 70 1) '
                  f'(cons 10 (list {px0:.3f} {py0:.3f})) (cons 10 (list {px1:.3f} {py0:.3f})) (cons 10 (list {px1:.3f} {py1:.3f})) (cons 10 (list {px0:.3f} {py1:.3f}))))']
    # ISO view: simple cabinet oblique of the boxes
    cx, cy, vw, vh = TPL.VP["ISO"]; ki = k / 1.6; c45 = math.cos(math.radians(40)) * 0.45; s45 = math.sin(math.radians(40)) * 0.45
    def P(x, y, z):
        return (cx + ki * ((x - TH["x"]) + (y - TH["y"]) * c45), cy + ki * ((z - TH["z"]) + (y - TH["y"]) * s45))
    for h in sorted(hs, key=lambda h: (-S[h]["y0"], S[h]["z0"], S[h]["x0"])):
        sb = S[h]
        faces = [([P(sb["x1"], sb["y0"], sb["z0"]), P(sb["x1"], sb["y1"], sb["z0"]), P(sb["x1"], sb["y1"], sb["z1"]), P(sb["x1"], sb["y0"], sb["z1"])], 253),
                 ([P(sb["x0"], sb["y0"], sb["z1"]), P(sb["x1"], sb["y0"], sb["z1"]), P(sb["x1"], sb["y1"], sb["z1"]), P(sb["x0"], sb["y1"], sb["z1"])], 255),
                 ([P(sb["x0"], sb["y0"], sb["z0"]), P(sb["x1"], sb["y0"], sb["z0"]), P(sb["x1"], sb["y0"], sb["z1"]), P(sb["x0"], sb["y0"], sb["z1"])], 254)]
        for pts, col in faces:
            a_, b_, c_, d_ = pts
            L += [f'(entmake (list (cons 0 "SOLID") (cons 8 "PART-FILL") (cons 62 {col}) (cons 10 (list {a_[0]:.3f} {a_[1]:.3f} 0)) (cons 11 (list {b_[0]:.3f} {b_[1]:.3f} 0)) (cons 12 (list {d_[0]:.3f} {d_[1]:.3f} 0)) (cons 13 (list {c_[0]:.3f} {c_[1]:.3f} 0))))',
                  '(entmake (list (cons 0 "LWPOLYLINE") (cons 100 "AcDbEntity") (cons 8 "PART") (cons 100 "AcDbPolyline") (cons 90 4) (cons 70 1) '
                  + " ".join(f"(cons 10 (list {q_[0]:.3f} {q_[1]:.3f}))" for q_ in pts) + "))"]
    L += ["_.-LAYER", "_M", "PART-FILL", "_C", "254", "PART-FILL", "", "_.DRAWORDER", "_ALL", "", "_F"] if False else []
    L += ["_.REGENALL"]
    # hidden-line plot per viewport

    # ---- annotations in paper space
    TH = {"x": T[0], "y": T[1], "z": T[2]}
    HV = {"FRONT": ("x", "z"), "SIDE": ("y", "z"), "TOP": ("x", "y")}
    EXT = {"x": SX, "y": SY, "z": SZ}
    L += ["_.-LAYER", "_S", "SHEET-BALLOON", ""]
    for nm, (ah, av) in HV.items():
        cx, cy, vw, vh = TPL.VP[nm]
        pts = {}
        for it in items:
            s = S[it["handles"][0]]
            px = cx + k * ((s[ah + "0"] + s[ah + "1"]) / 2 - TH[ah])
            if nm == "SIDE":
                px = cx - (px - cx)
            pts[it["no"]] = (px, cy + k * ((s[av + "0"] + s[av + "1"]) / 2 - TH[av]))
        rx, ry = EXT[ah] * k / 2 + 14, EXT[av] * k / 2 + 14
        for no, (bx, by) in ring(pts, (cx, cy), rx, ry).items():
            ax_, ay_ = pts[no]
            d = math.hypot(bx - ax_, by - ay_) or 1
            ex, ey = bx - (bx - ax_) / d * 3.5, by - (by - ay_) / d * 3.5
            L += [f'(entmake (list (cons 0 "LINE") (cons 8 "SHEET-BALLOON") (cons 10 (list {ax_:.2f} {ay_:.2f} 0)) (cons 11 (list {ex:.2f} {ey:.2f} 0))))',
                  f'(entmake (list (cons 0 "CIRCLE") (cons 8 "SHEET-BALLOON") (cons 10 (list {ax_:.2f} {ay_:.2f} 0)) (cons 40 0.5)))',
                  f'(entmake (list (cons 0 "CIRCLE") (cons 8 "SHEET-BALLOON") (cons 10 (list {bx:.2f} {by:.2f} 0)) (cons 40 3.5)))'] + cell_text(bx, by, no, 3.0, "SHEET-BALLOON", "MC")
    # overall dimensions (paper space, text override with real mm)
    L += ["_.-LAYER", "_S", "SHEET-DIM", "", "DIMSCALE", "1", "DIMTXT", "2.5", "DIMASZ", "2.0"]
    fx, fy, fw, fh = TPL.VP["FRONT"]; sx_, sy_, sw, sh = TPL.VP["SIDE"]
    bx0, by0 = fx - SX * k / 2, fy - SZ * k / 2
    L += ["_.DIMLINEAR", f"{bx0:.2f},{by0:.2f}", f"{bx0 + SX * k:.2f},{by0:.2f}", "_T", f"{SX:.0f}", f"{fx:.2f},{by0 - 7:.2f}",
          "_.DIMLINEAR", f"{bx0 + SX * k:.2f},{by0:.2f}", f"{bx0 + SX * k:.2f},{by0 + SZ * k:.2f}", "_T", f"{SZ:.0f}", f"{bx0 + SX * k + 8:.2f},{fy:.2f}"]
    sb0 = sx_ - SY * k / 2
    L += ["_.DIMLINEAR", f"{sb0:.2f},{by0:.2f}", f"{sb0 + SY * k:.2f},{by0:.2f}", "_T", f"{SY:.0f}", f"{sx_:.2f},{by0 - 7:.2f}"]
    # part table
    L += ["_.-LAYER", "_S", "SHEET-TABLE", ""]
    tx, ty = TPL.TABLE_X - 14, TPL.TABLE_Y
    rows_n = len(items) + 2
    L += [f'(setq tb (vla-AddTable (vla-get-PaperSpace (vla-get-ActiveDocument (vlax-get-acad-object))) (vlax-3d-point {tx} {ty} 0) {rows_n} 7 6.0 18.0))' if False else
          f'(command "_.TABLE" "_S" "Standard" "_C" "7" "_R" "{rows_n - 2}" "{tx},{ty}" "")' if False else "(princ)"]
    # TABLE via command is dialog-driven; build with entmake-free approach: draw the table as lines + text (robust everywhere)
    cw = [7, 13, 40, 48, 26, 8, 12]; rh = 5.2
    tw = sum(cw)
    def eml(x1, y1, x2, y2, layer="SHEET-TABLE"):
        return f'(entmake (list (cons 0 "LINE") (cons 8 "{layer}") (cons 10 (list {x1:.2f} {y1:.2f} 0)) (cons 11 (list {x2:.2f} {y2:.2f} 0))))'
    by_ = ty - rh * rows_n
    L += [eml(tx, ty, tx + tw, ty), eml(tx + tw, ty, tx + tw, by_), eml(tx + tw, by_, tx, by_), eml(tx, by_, tx, ty)]
    for i in range(1, rows_n):
        L += [eml(tx, ty - rh * i, tx + tw, ty - rh * i)]
    xx = tx
    for wdt in cw[:-1]:
        xx += wdt
        L += [eml(xx, ty - rh, xx, by_)]
    L += ["_.-LAYER", "_S", "SHEET-TEXT", ""]
    L += cell_text(tx + 2, ty - rh + 1.6, "PART LIST", 2.8)
    head = ["NO", "PART NO", "NAMA PART", "BAHAN", "P x L x T (mm)", "QTY", "YAKIN"]
    xx = tx
    for wdt, hd in zip(cw, head):
        L += cell_text(xx + 1.2, ty - 2 * rh + 1.6, hd, 2.0); xx += wdt
    for r_, it in enumerate(items, 2):
        d = it["dims"]; vals = [str(it["no"]), it["pn"], it["name"], it["mat"], f"{d[0]:g} x {d[1]:g} x {d[2]:g}", str(it["qty"]), CONF[it["conf"]]]
        xx = tx
        for wdt, v in zip(cw, vals):
            L += cell_text(xx + 1.2, ty - (r_ + 1) * rh + 1.6, (v[:30] if wdt < 45 else v[:36]), 2.0); xx += wdt
    ny = ty - rh * rows_n - 6
    notes = ["CATATAN (draf otomatis dari model 3D):", "- Sumber: model 3D; nomor part = Part Master v3.", "- Ukuran dari model; tebal akhir mengikuti RULES pabrik.",
             "- * Panel samping: aturan meeting MDF veneer E0 1 muka; label gambar: plywood.", "- Kotak laci tidak ada di model; dihitung dari rumus pabrik (STD).",
             "- YAKIN / CUKUP / RAGU = keyakinan nomor otomatis; RAGU wajib dicek drafter."]
    for i, s in enumerate(notes):
        L += cell_text(tx, ny - i * 4.2, s, 2.2)
    # title block attributes
    today = datetime.date.today().strftime("%d %b %Y")
    vals = {"DRAWN": "BOM-APP (otomatis)", "CHECKED": "-", "APPROVED": "-", "COLLECTION": a.collection, "PRODUCT": a.name, "DESC": "OVER VIEW + PART LIST",
            "UNIT": "mm", "ITEM_CODE": a.item_code, "DIM": f"{SX:.0f} x {SY:.0f} x {SZ:.0f}", "REV": "00", "SCALE": f"1:{a.scale:g}", "DATE_PAGE": f"{today}  /  01 of 01"}
    L += ['(setq tb (ssname (ssget "_X" (list (cons 0 "INSERT") (cons 2 "TB_TALA"))) 0))',
          '(setq at (entnext tb)) (while (and at (= (cdr (assoc 0 (entget at))) "ATTRIB")) (setq d (entget at) tg (cdr (assoc 2 d))) '
          + " ".join(f'(if (= tg "{t}") (entmod (subst (cons 1 {q(v)}) (assoc 1 d) d)))' for t, v in vals.items())
          + ' (setq at (entnext at)))', '(entupd tb)']
    L += ["_.REGENALL"]
    L += C.plot_lines("SHEET", out_pdf)[6:]   # skip FILEDIA/CMDECHO/BACKGROUNDPLOT prefix already set? plot_lines starts with those 6 entries
    L = L[:0] + L  # keep
    L += ["_.SAVEAS", "2018", out_dwg.replace("\\", "/")]
    ok, log, why = C.run(sheet, L, timeout=240, workdir=w)
    print("B fill+plot:", why)
    good, det = C.pdf_has_content(out_pdf)
    print("PDF:", good, det, "|", out_pdf)
    print("DWG:", os.path.exists(out_dwg), "|", out_dwg)
    open(os.path.join(a.out, f"{base}.log"), "w", encoding="utf-8").write(log)
    if not ok or not good:
        tail = [l for l in log.splitlines() if l.strip()][-25:]
        print("\n".join(tail))
        sys.exit(1)


if __name__ == "__main__":
    main()
