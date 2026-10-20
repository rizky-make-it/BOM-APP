"""Shop drawing v2 from headless AutoCAD: consistent third-angle sheet.

One scale for every view (incl. 3D), third-angle layout (TOP above FRONT, RIGHT SIDE right of FRONT, aligned axes),
true hidden lines (dashed) computed from the solid boxes, overall dimensions on all three views, balloons only on parts
visible in that view and on EVERY copy of a repeated part, view labels with viewing direction, one line style (no fills).

python tools/acad_fill_sheet.py --dwg src.dwg --solids solids.json --numbering numbering.json --out DIR
       [--scale 8] [--item-code X] [--name X] [--collection X] [--template templates/TALA_A3.dwt]
"""
import argparse, collections, datetime, json, math, os, shutil, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acad_core as C
from shapely.geometry import LineString, Polygon, box as sbox
from shapely.ops import unary_union

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAT = {"101": "Solid wood Mindi (A)", "102": "Solid wood Mindi (A)", "202": "Solid wood Mindi (A)", "207": "Solid wood Mindi (A)",
       "301": "MDF veneer E0 1F (C-18-1X)*", "302": "Plywood veneer Mindi 1F", "306": "Plywood veneer Mindi 1F",
       "307": "Plywood veneer Mindi 1F", "308": "Plywood veneer Mindi 1F", "299": "belum diketahui"}
CONF = {"high": "YAKIN", "medium": "CUKUP", "low": "RAGU"}
SCALES = (5, 6, 8, 10, 12.5, 15, 20, 25)
VIEW_AREA = (14, 44, 258, 283)        # left part of the sheet for the three orthographic views
RIGHT = (262, 44, 408, 283)           # right column: 3D view, table, notes
PAD = 24                              # room around each view for dims (8) and balloons (16)
C45, S45 = math.cos(math.radians(40)) * 0.45, math.sin(math.radians(40)) * 0.45


def text(x, y, s, h=2.2, layer="SHEET-TEXT", just=None):
    s = str(s).replace("\\", "/").replace('"', "'")
    j = f' (cons 72 1) (cons 73 2) (cons 11 (list {x:.2f} {y:.2f} 0))' if just == "MC" else ""
    return f'(entmake (list (cons 0 "TEXT") (cons 8 "{layer}") (cons 7 "TALA") (cons 10 (list {x:.2f} {y:.2f} 0)) (cons 40 {h}) (cons 1 "{s}"){j}))'


def line(x1, y1, x2, y2, layer="PART", lts=None):
    extra = f' (cons 6 "HIDDEN") (cons 48 {lts})' if lts else ""
    return f'(entmake (list (cons 0 "LINE") (cons 8 "{layer}") (cons 10 (list {x1:.3f} {y1:.3f} 0)) (cons 11 (list {x2:.3f} {y2:.3f} 0)){extra}))'


def circle(x, y, r, layer="SHEET-BALLOON"):
    return f'(entmake (list (cons 0 "CIRCLE") (cons 8 "{layer}") (cons 10 (list {x:.3f} {y:.3f} 0)) (cons 40 {r})))'


def segs(geom):
    if geom.is_empty:
        return []
    out = []
    for g in getattr(geom, "geoms", [geom]):
        if g.geom_type != "LineString":
            continue
        c = list(g.coords)
        out += [(c[i], c[i + 1]) for i in range(len(c) - 1)]
    return out


def merge_items(rows):
    g = collections.OrderedDict()
    for r in sorted(rows, key=lambda r: (r["pn"], tuple(-round(v) for v in r["dims"]))):
        g.setdefault((r["pn"], tuple(round(v, 1) for v in r["dims"])), []).append(r)
    items = []
    for n, (key, rs) in enumerate(g.items(), 1):
        worst = min((r["conf"] for r in rs), key=lambda c: {"low": 0, "medium": 1, "high": 2}[c])
        items.append(dict(no=n, pn=key[0], name=rs[0]["name"], dims=key[1], qty=len(rs), conf=worst,
                          handles=[r["handle"].upper() for r in rs], mat=MAT.get(key[0], "?")))
    return items


VIEWS = {
    "FRONT": dict(u="x", v="z", near=lambda b: -b["y0"], label="TAMPAK DEPAN"),
    "SIDE":  dict(u="y", v="z", near=lambda b: b["x1"], label="TAMPAK SAMPING KANAN (dilihat dari kanan)"),
    "TOP":   dict(u="x", v="y", near=lambda b: b["z1"], label="TAMPAK ATAS (depan di bawah)"),
}


def ortho(S, hs, view, k, ox, oy, o3):
    """Visible / hidden edge segments and the visible region per handle, in paper mm (third angle)."""
    vd = VIEWS[view]; u, v = vd["u"], vd["v"]
    rect = {h: sbox(ox + k * (S[h][u + "0"] - o3[u]), oy + k * (S[h][v + "0"] - o3[v]),
                    ox + k * (S[h][u + "1"] - o3[u]), oy + k * (S[h][v + "1"] - o3[v])) for h in hs}
    near = {h: vd["near"](S[h]) for h in hs}
    vis, hid, region = [], [], {}
    for h in hs:
        occ = [rect[g] for g in hs if g != h and near[g] > near[h] + 0.01]
        edges = LineString(list(rect[h].exterior.coords))
        if not occ:
            vis += segs(edges); region[h] = rect[h]; continue
        occ_u = unary_union(occ).buffer(0.001)
        vis += segs(edges.difference(occ_u)); hid += segs(edges.intersection(occ_u)); region[h] = rect[h].difference(occ_u)
    return vis, hid, region


def oblique(S, hs, k, ox, oy, o3):
    def P(x, y, z):
        return (ox + k * ((x - o3["x"]) + (y - o3["y"]) * C45), oy + k * ((z - o3["z"]) + (y - o3["y"]) * S45))
    faces = {}
    for h in hs:
        b = S[h]
        faces[h] = [Polygon([P(b["x0"], b["y0"], b["z0"]), P(b["x1"], b["y0"], b["z0"]), P(b["x1"], b["y0"], b["z1"]), P(b["x0"], b["y0"], b["z1"])]),
                    Polygon([P(b["x0"], b["y0"], b["z1"]), P(b["x1"], b["y0"], b["z1"]), P(b["x1"], b["y1"], b["z1"]), P(b["x0"], b["y1"], b["z1"])]),
                    Polygon([P(b["x1"], b["y0"], b["z0"]), P(b["x1"], b["y1"], b["z0"]), P(b["x1"], b["y1"], b["z1"]), P(b["x1"], b["y0"], b["z1"])])]
    near = {h: (-S[h]["y0"], S[h]["x1"], S[h]["z1"]) for h in hs}
    out, region = [], {}
    for h in hs:
        occ = [f for g in hs if g != h and near[g] > near[h] for f in faces[g]]
        own = unary_union(faces[h]); edges = unary_union([LineString(list(f.exterior.coords)) for f in faces[h]])
        if not occ:
            out += segs(edges); region[h] = own; continue
        occ_u = unary_union(occ).buffer(0.001)
        out += segs(edges.difference(occ_u)); region[h] = own.difference(occ_u)
    return out, region


def place_balloons(anchors, bx0, by0, bx1, by1):
    """anchors: [(no, (x, y))]. Balloons sit on the rectangle ring, nearest side, >= 8 mm apart. Returns [(no, anchor, pos)]."""
    sides = {"L": [], "R": [], "T": [], "B": []}
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
    for no, (x, y) in anchors:
        dx, dy = (x - cx) / max(1, bx1 - bx0), (y - cy) / max(1, by1 - by0)
        horiz = abs(dx) >= abs(dy)
        sides[("R" if dx > 0 else "L") if horiz else ("T" if dy > 0 else "B")].append(((y if horiz else x), no, (x, y)))
    out = []
    for sd, lst in sides.items():
        if not lst:
            continue
        lst.sort()
        lo, hi = (by0, by1) if sd in "LR" else (bx0, bx1)
        m = len(lst); step = 8.0
        mid = sum(t[0] for t in lst) / m
        start = min(max(mid - step * (m - 1) / 2, lo), max(lo, hi - step * (m - 1)))
        for i, (_, no, anc) in enumerate(lst):
            t = start + i * step
            out.append((no, anc, (bx0, t) if sd == "L" else (bx1, t) if sd == "R" else (t, by1) if sd == "T" else (t, by0)))
    return out


def balloon_cmds(no, anc, pos):
    (axp, ayp), (bxp, byp) = anc, pos
    d = math.hypot(bxp - axp, byp - ayp) or 1
    ex, ey = bxp - (bxp - axp) / d * 3.5, byp - (byp - ayp) / d * 3.5
    return [line(axp, ayp, ex, ey, "SHEET-BALLOON"), circle(axp, ayp, 0.5), circle(bxp, byp, 3.5), text(bxp, byp, no, 3.0, "SHEET-BALLOON", "MC")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dwg", required=True); ap.add_argument("--solids", required=True); ap.add_argument("--numbering", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--scale", type=float, default=0)
    ap.add_argument("--item-code", default="-"); ap.add_argument("--name", default="UNIT K1"); ap.add_argument("--collection", default="LEXI (belum dikonfirmasi)")
    ap.add_argument("--template", default=os.path.join(ROOT, "templates", "TALA_A3.dwt"))
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    base = os.path.splitext(os.path.basename(a.numbering))[0]
    rows = json.load(open(a.numbering, encoding="utf-8"))
    S = {s["handle"].upper(): s for s in json.load(open(a.solids, encoding="utf-8"))["solids"]}
    items = merge_items(rows)
    no_of = {h: it["no"] for it in items for h in it["handles"]}
    hs = [r["handle"].upper() for r in rows]
    o3 = {ax: min(S[h][ax + "0"] for h in hs) for ax in "xyz"}
    W = max(S[h]["x1"] for h in hs) - o3["x"]; D = max(S[h]["y1"] for h in hs) - o3["y"]; H = max(S[h]["z1"] for h in hs) - o3["z"]

    ax0, ay0, ax1, ay1 = VIEW_AREA
    G = 2 * PAD
    need = max((W + D) / (ax1 - ax0 - G - 2 * PAD), (H + D) / (ay1 - ay0 - G - 2 * PAD))
    scale = a.scale or next((sc for sc in SCALES if sc >= need), SCALES[-1])
    k = 1 / scale
    fx, fy = ax0 + PAD, ay0 + PAD
    sx = fx + W * k + G
    ty = fy + H * k + G
    origin = {"FRONT": (fx, fy), "SIDE": (sx, fy), "TOP": (fx, ty)}
    extent = {"FRONT": (W, H), "SIDE": (D, H), "TOP": (W, D)}

    stamp = datetime.datetime.now().strftime("%H%M%S")
    out_dwg = os.path.join(a.out, f"{base}.dwg"); out_pdf = os.path.join(a.out, f"{base}.pdf")
    for f in (out_dwg, out_pdf):
        if os.path.exists(f):
            try:
                os.remove(f)
            except OSError:
                out_dwg = os.path.join(a.out, f"{base}_{stamp}.dwg"); out_pdf = os.path.join(a.out, f"{base}_{stamp}.pdf"); break

    w = tempfile.mkdtemp(prefix="fill_"); src = os.path.join(w, "src.dwg"); shutil.copy(a.dwg, src)
    parts = os.path.join(w, "parts.dwg").replace("\\", "/")
    sel = "(setq ss (ssadd)) " + " ".join(f'(if (handent "{h}") (ssadd (handent "{h}") ss))' for h in hs)
    ok, log, why = C.run(src, ["FILEDIA", "0", "CMDECHO", "0", sel, "_.-WBLOCK", parts, "", "0,0,0", "!ss", ""], timeout=120, workdir=w)
    print("A extract:", why, "| parts.dwg", os.path.exists(parts))
    if not os.path.exists(parts):
        print(log[-1200:]); sys.exit(1)

    sheet = os.path.join(w, "sheet.dwg"); shutil.copy(a.template, sheet)
    L = ["FILEDIA", "0", "CMDECHO", "0", "ATTDIA", "0", "ATTREQ", "0", "EXPERT", "5",
         "_.TILEMODE", "1", "_.-LAYER", "_S", "PART", "", "_.-INSERT", "*" + parts, "0,0,0", "1", "0",
         "_.TILEMODE", "0", "_.LAYOUT", "_S", "SHEET", "_.PSPACE",
         '(setq e (entnext)) (while e (setq d (entget e)) (if (and (= (cdr (assoc 0 d)) "VIEWPORT") (/= (cdr (assoc 69 d)) 1)) (entdel e)) (setq e (entnext e)))']
    n_vis = n_hid = 0; bc = collections.Counter(); ring = 16
    for nm in ("FRONT", "SIDE", "TOP"):
        ox, oy = origin[nm]; eu, ev = extent[nm]
        vis, hid, region = ortho(S, hs, nm, k, ox, oy, o3)
        L += [line(*p, *q, "PART") for p, q in vis] + [line(*p, *q, "PART-HIDDEN", 0.6) for p, q in hid]
        n_vis += len(vis); n_hid += len(hid)
        u, v = VIEWS[nm]["u"], VIEWS[nm]["v"]
        anchors = []
        for h in hs:
            r = region[h]
            full = k * k * (S[h][u + "1"] - S[h][u + "0"]) * (S[h][v + "1"] - S[h][v + "0"])
            if not r.is_empty and r.area > max(1.0, 0.15 * full):
                pt = r.representative_point(); anchors.append((no_of[h], (pt.x, pt.y)))
        for no, anc, pos in place_balloons(anchors, ox - ring, oy - ring, ox + eu * k + ring, oy + ev * k + ring):
            L += balloon_cmds(no, anc, pos); bc[nm] += 1
        L += [text(ox + eu * k / 2, oy - ring - 7, VIEWS[nm]["label"], 2.8, "SHEET-TEXT", "MC")]
    L += ["_.-LAYER", "_S", "SHEET-DIM", "", "DIMSCALE", "1", "DIMTXT", "2.5", "DIMASZ", "2.0", "DIMEXO", "1", "DIMEXE", "1.2", "DIMDEC", "0", "DIMTXSTY", "TALA"]
    def dim(p1, p2, loc, val):
        return ["_.DIMLINEAR", f"{p1[0]:.3f},{p1[1]:.3f}", f"{p2[0]:.3f},{p2[1]:.3f}", "_T", f"{val:.0f}", f"{loc[0]:.3f},{loc[1]:.3f}"]
    L += dim((fx, fy), (fx + W * k, fy), (fx + W * k / 2, fy - 8), W)
    L += dim((fx, fy), (fx, fy + H * k), (fx - 8, fy + H * k / 2), H)
    L += dim((sx, fy), (sx + D * k, fy), (sx + D * k / 2, fy - 8), D)
    L += dim((sx + D * k, fy), (sx + D * k, fy + H * k), (sx + D * k + 8, fy + H * k / 2), H)
    L += dim((fx, ty + D * k), (fx + W * k, ty + D * k), (fx + W * k / 2, ty + D * k + 8), W)
    L += dim((fx, ty), (fx, ty + D * k), (fx - 8, ty + D * k / 2), D)
    rx0, ry0, rx1, ry1 = RIGHT
    iw, ih = (W + D * C45) * k, (H + D * S45) * k
    iox, ioy = rx0 + (rx1 - rx0 - iw) / 2, ry1 - 12 - ih
    o_segs, o_region = oblique(S, hs, k, iox, ioy, o3)
    L += [line(*p, *q, "PART") for p, q in o_segs]
    anchors = []
    for h in hs:
        r = o_region[h]
        if not r.is_empty and r.area > 2.0:
            pt = r.representative_point(); anchors.append((no_of[h], (pt.x, pt.y)))
    for no, anc, pos in place_balloons(anchors, iox - 10, ioy - 10, iox + iw + 10, ioy + ih + 10):
        L += balloon_cmds(no, anc, pos); bc["ISO"] += 1
    L += [text(iox + iw / 2, ioy - 17, "3D VIEW (skala sama)", 2.8, "SHEET-TEXT", "MC")]
    cw = [7, 12, 36, 46, 25, 8, 12]; rh = 5.2; tw = sum(cw)
    tx, ty_ = rx0, ioy - 26
    rows_n = len(items) + 2; by_ = ty_ - rh * rows_n
    L += [line(tx, ty_, tx + tw, ty_, "SHEET-TABLE"), line(tx + tw, ty_, tx + tw, by_, "SHEET-TABLE"), line(tx + tw, by_, tx, by_, "SHEET-TABLE"), line(tx, by_, tx, ty_, "SHEET-TABLE")]
    L += [line(tx, ty_ - rh * i, tx + tw, ty_ - rh * i, "SHEET-TABLE") for i in range(1, rows_n)]
    xx = tx
    for wdt in cw[:-1]:
        xx += wdt; L += [line(xx, ty_ - rh, xx, by_, "SHEET-TABLE")]
    L += [text(tx + 2, ty_ - rh + 1.6, "PART LIST", 2.8)]
    xx = tx
    for wdt, hd in zip(cw, ["NO", "PART NO", "NAMA PART", "BAHAN", "P x L x T (mm)", "QTY", "YAKIN"]):
        L += [text(xx + 1.2, ty_ - 2 * rh + 1.6, hd, 2.0)]; xx += wdt
    for r_, it in enumerate(items, 2):
        d = it["dims"]; vals = [str(it["no"]), it["pn"], it["name"][:30], it["mat"][:36], f"{d[0]:g} x {d[1]:g} x {d[2]:g}", str(it["qty"]), CONF[it["conf"]]]
        xx = tx
        for wdt, v in zip(cw, vals):
            L += [text(xx + 1.2, ty_ - (r_ + 1) * rh + 1.6, v, 2.0)]; xx += wdt
    notes = ["CATATAN (draf otomatis dari model 3D):", "- Proyeksi sudut ketiga; semua tampak dan 3D pada satu skala.",
             "- Garis putus-putus = tepi tersembunyi. Nomor balon = NO di tabel; part kembar diberi nomor sama.",
             "- Ukuran dari model; tebal akhir mengikuti RULES pabrik. Kotak laci tidak ada di model (rumus pabrik).",
             "- * Panel samping: aturan meeting MDF veneer E0 1 muka; label gambar: plywood.",
             "- YAKIN / CUKUP / RAGU = keyakinan nomor otomatis; RAGU wajib dicek drafter."]
    for i, s_ in enumerate(notes):
        L += [text(tx, by_ - 6 - i * 4.2, s_, 2.0)]
    today = datetime.date.today().strftime("%d %b %Y")
    vals = {"DRAWN": "BOM-APP (otomatis)", "CHECKED": "-", "APPROVED": "-", "COLLECTION": a.collection, "PRODUCT": a.name, "DESC": "OVER VIEW + PART LIST",
            "UNIT": "mm", "ITEM_CODE": a.item_code, "DIM": f"{W:.0f} x {D:.0f} x {H:.0f}", "REV": "00", "SCALE": f"1:{scale:g} (semua tampak)", "DATE_PAGE": f"{today}  /  01 of 01"}
    q = lambda v: '"' + str(v).replace("\\", "/").replace('"', "'") + '"'
    L += ['(setq tb (ssname (ssget "_X" (list (cons 0 "INSERT") (cons 2 "TB_TALA"))) 0))',
          '(setq at (entnext tb)) (while (and at (= (cdr (assoc 0 (entget at))) "ATTRIB")) (setq d (entget at) tg (cdr (assoc 2 d))) '
          + " ".join(f'(if (= tg "{t}") (entmod (subst (cons 1 {q(v)}) (assoc 1 d) d)))' for t, v in vals.items()) + ' (setq at (entnext at)))', '(entupd tb)']
    L += ["_.REGENALL"] + C.plot_lines("SHEET", out_pdf)[6:] + ["_.SAVEAS", "2018", out_dwg.replace("\\", "/")]
    ok, log, why = C.run(sheet, L, timeout=240, workdir=w)
    good, det = C.pdf_has_content(out_pdf)
    print(f"B fill+plot: {why} | scale 1:{scale:g} | edges visible {n_vis}, hidden {n_hid} | balloons {dict(bc)}")
    print("PDF:", good, det, "|", out_pdf); print("DWG:", os.path.exists(out_dwg), "|", out_dwg)
    open(os.path.join(a.out, f"{base}.log"), "w", encoding="utf-8").write(log)
    if not ok or not good:
        print("\n".join([l for l in log.splitlines() if l.strip()][-20:])); sys.exit(1)


if __name__ == "__main__":
    main()
