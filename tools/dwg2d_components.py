"""DWG (drafter 2D) -> component list in factory PART LIST terms, written back as labels + table + JSON.

python tools/dwg2d_components.py <dwg> --item CODE --name NAME --out DIR [--h H --w W --d D]

Each component = part-list NO + NAME + L x W x T + factory material code, with a status:
  STATED  : size read from a labelled face in the drawing (two dims) + thickness from the drafter's material label
  DERIVED : third dim / count / name from geometry of the views (metal bars from the frame outline, overall dims)
  CHECK   : rule could not decide (name '?' or size from one view only)
Material code = factory PART LIST table 2 (A/A1 solid, B ply, C MDF: thickness-veneer faces, D1 hinge, D2 drawer rail);
metal hollow is NOT in that list -> code 'MT-<a>x<b>' flagged CHECK.
Writes <item>_components.{json,dwg,pdf}: every drafter label rewritten to '[NO] NAME / L x W x T / CODE' (drafter text kept
as last line), part table on sheet 1, all sheets in one PDF.
"""
import argparse, collections, datetime, json, math, os, re, shutil, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acad_core as C
import dwg_reader as R
import dwg2d_read as D2
import ezdxf
from ezdxf.math import Vec3
from shapely.geometry import LineString, Point
from shapely.ops import unary_union, polygonize

# Part numbering = Part Master v3 (data/part_master_v3.json, the latest part list in BOM-APP): 3-digit part_no + name.
_PM = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "part_master_v3.json"), encoding="utf-8"))
PARTS = {int(p["part_no"]): p["name"].upper() for p in _PM["parts"]}
PART_DEFAULT_CODE = {int(p["part_no"]): p["default_mat_code"] for p in _PM["parts"]}
ALIAS = {}
for p in _PM["parts"]:
    for nm in [p["name"]] + [x.strip() for x in p.get("also_called", "").split(";") if x.strip()]:
        ALIAS[" ".join(nm.upper().split())] = int(p["part_no"])


def material(label):
    """drafter label -> (kind, t, code, check)"""
    u = " ".join(label.upper().replace("-", " ").split())
    m = re.search(r"(\d+)\s*X\s*(\d+)", u)
    if u.startswith("MT") and m:
        a, b = sorted((int(m.group(1)), int(m.group(2))))
        return "metal", a, f"MT-{a}x{b}", "kode metal tidak ada di PART LIST"
    if "HANDLE" in u:
        return "hw", 0, "HW-HANDLE", "hardware, bukan kode A-D"
    m = re.search(r"(PLY|PLYWOOD|MDF)\s*(\d+)", u)
    if m:
        t = int(m.group(2)); fam = "B" if m.group(1).startswith("PLY") else "C"
        f = re.search(r"(\d)\s*F", u); faces = int(f.group(1)) if f else (1 if "VENEER" in u else 0)
        return "panel", t, f"{fam}-{t}-{faces}X", ""
    m = re.search(r"(WD|SOLID)", u)
    if m:
        t = int(re.search(r"(\d+)", u).group(1)) if re.search(r"\d+", u) else 0
        return "solid", t, "A", ""
    return "?", 0, "?", "label tidak dikenali"


def read_all(dwg):
    """all XZ faces (labelled or not) + labels + dims"""
    res = D2.read(dwg)
    dxf = os.path.join(tempfile.mkdtemp(), "l.dxf"); R.dwg_to_dxf(dwg, dxf)
    d = ezdxf.readfile(dxf); m = d.modelspace(); segs = []
    for e in m:
        if e.dxftype() in ("LINE", "LWPOLYLINE"):
            ex = tuple(round(v) for v in e.dxf.extrusion) if e.dxf.hasattr("extrusion") else (0, 0, 1)
            if ex != (0, -1, 0):
                continue
            ocs = e.ocs()
            P = [e.dxf.start, e.dxf.end] if e.dxftype() == "LINE" else [ocs.to_wcs(Vec3(p[0], p[1], e.dxf.elevation)) for p in e.get_points("xy")] + ([ocs.to_wcs(Vec3(e.get_points("xy")[0][0], e.get_points("xy")[0][1], e.dxf.elevation))] if e.closed else [])
            for a, b in zip(P, P[1:]):
                if a.distance(b) > 0.5:
                    segs.append(LineString([(a.x, a.z), (b.x, b.z)]))
    faces = [f.bounds for f in polygonize(unary_union(segs)) if f.area > 30]
    return res, [(round(b[0]), round(b[1]), round(b[2] - b[0]), round(b[3] - b[1])) for b in faces]


def cluster_views(faces, gap=120):
    views = []
    for (x, z, w, h) in sorted(faces):
        for v in views:
            if x <= v["x1"] + gap and x + w >= v["x0"] - gap and z <= v["z1"] + gap and z + h >= v["z0"] - gap:
                v["x0"] = min(v["x0"], x); v["x1"] = max(v["x1"], x + w); v["z0"] = min(v["z0"], z); v["z1"] = max(v["z1"], z + h); v["f"].append((x, z, w, h)); break
        else:
            views.append(dict(x0=x, x1=x + w, z0=z, z1=z + h, f=[(x, z, w, h)]))
    merged = True
    while merged:
        merged = False
        for i in range(len(views)):
            for j in range(i + 1, len(views)):
                A, B = views[i], views[j]
                if A["x0"] <= B["x1"] + gap and A["x1"] >= B["x0"] - gap and A["z0"] <= B["z1"] + gap and A["z1"] >= B["z0"] - gap:
                    A["x0"] = min(A["x0"], B["x0"]); A["x1"] = max(A["x1"], B["x1"]); A["z0"] = min(A["z0"], B["z0"]); A["z1"] = max(A["z1"], B["z1"]); A["f"] += B["f"]
                    views.pop(j); merged = True; break
            if merged: break
    return views


def near(a, b, tol=6):
    return abs(a - b) <= tol


def main():
    t0 = time.time()
    ap = argparse.ArgumentParser(); ap.add_argument("dwg"); ap.add_argument("--item", required=True); ap.add_argument("--name", default="")
    ap.add_argument("--out", required=True); ap.add_argument("--metal", default="20x20")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    res, faces = read_all(a.dwg)
    views = cluster_views(faces)
    dims = {k: v for k, v in res["dims"].items() if isinstance(k, int) and k > 0}
    # labelled faces: material per face (drop 'near' > 40 mm: unreliable)
    lab = {}
    for r in res["rows"]:
        if r["how"] != "inside" and float(r["how"].split()[-1]) > 40:
            continue
        lab[(r["x"], r["z"], r["w"], r["h"])] = r["label"]
    # ---- metal frame from hollow cross-sections (drafter draws sections, bars are not faces)
    ma, mb = sorted(int(v) for v in a.metal.lower().split("x"))
    comps = []
    sq = [(x, z, w, h, v) for v in views for (x, z, w, h) in v["f"] if near(w, ma, 3) and near(h, ma, 3)]
    # plan section = view with >= 4 squares forming a rectangle -> legs count & frame span
    plan = [v for v in views if sum(1 for (x, z, w, h) in v["f"] if near(w, ma, 3) and near(h, ma, 3)) >= 4 and abs((v["x1"] - v["x0"]) - (v["z1"] - v["z0"])) < 0.35 * (v["x1"] - v["x0"])]
    H = max([k for k in dims if 200 <= k <= 2500], default=0)
    if plan:
        pv = plan[0]; span_x = pv["x1"] - pv["x0"]; span_z = pv["z1"] - pv["z0"]
        comps.append(dict(no=101, name=PARTS[101], l=H, w=mb, t=ma, qty=4, code=f"MT-{ma}x{mb}", status="DERIVED",
                          note=f"4 penampang hollow di sudut potongan denah {span_x}x{span_z}; tinggi = dimensi {H}", src="section"))
        # rings: each elevation section row (pair of squares at the same z, spanning the frame) = one ring of 4 bars
        rows_z = collections.Counter()
        for v in views:
            if v is pv: continue
            zs = collections.Counter(round(z / 5) * 5 for (x, z, w, h) in v["f"] if near(w, ma, 3) and near(h, ma, 3))
            for zz, n in zs.items():
                if n >= 2: rows_z[(round((v["z0"]) / 50), zz)] += 1
        # same ring appears in front AND side section -> count distinct z rows (any view)
        rings = len({zz for (_, zz) in rows_z})
        if rings:
            comps.append(dict(no=201, name=PARTS[201], l=span_x - 2 * mb, w=mb, t=ma, qty=2 * rings, code=f"MT-{ma}x{mb}", status="DERIVED",
                              note=f"{rings} tingkat rangka (baris penampang di potongan) x 2; panjang = bentang {span_x} - 2 kaki", src="section"))
            comps.append(dict(no=202, name=PARTS[202], l=span_z - 2 * mb, w=mb, t=ma, qty=2 * rings, code=f"MT-{ma}x{mb}", status="DERIVED",
                              note=f"{rings} tingkat x 2; panjang = bentang {span_z} - 2 kaki", src="section"))
    # ---- panels: labelled faces. Face view (both dims > t) -> L x W. Edge views are paired ACROSS views:
    #      same code, same t, same z-row (section height) and same visible height -> one component, L from one view, W from the other.
    def face_label(f):
        return lab.get(f)
    items = []   # (code, t, kind, x, z, w, h, viewidx)
    for vi, v in enumerate(views):
        for f in v["f"]:
            label = face_label(f)
            if not label: continue
            kind, t, code, chk = material(label)
            if kind not in ("panel", "solid"): continue
            x, z, w, h = f
            items.append(dict(code=code, t=t, x=x, z=z, w=w, h=h, vi=vi, edge=min(w, h) <= t + 4, label=label))
    # thin faces next to a labelled void (leader on the void, bottom skin below it): snap 'PLY 6MM 446x154' to the 6 mm face touching it
    for it in [i for i in items if not i["edge"] and i["t"] <= 6]:
        v = views[it["vi"]]
        thin = [f for f in v["f"] if abs(f[3] - it["t"]) <= 1 and abs(f[1] + f[3] - it["z"]) <= 8 and f[2] >= it["w"] - 20]
        if thin:
            f = thin[0]; it.update(x=f[0], z=f[1], w=f[2], h=f[3], edge=True)
    used = set()
    for i, A in enumerate(items):
        if i in used or A["edge"] is False: continue
        for j, B in enumerate(items):
            if j <= i or j in used or not B["edge"] or B["vi"] == A["vi"] or B["code"] != A["code"]: continue
            if abs(A["z"] - B["z"]) <= 10 and abs(A["h"] - B["h"]) <= 10:     # same height row in two perpendicular sections
                la, lb = max(A["w"], A["h"]), max(B["w"], B["h"])
                if A["h"] > A["w"]:                       # vertical edges: the two spacings give L & W? use their lengths as height
                    continue
                comps.append(dict(no=0, name="?", l=max(la, lb), w=min(la, lb), t=A["t"], qty=1, code=A["code"], status="STATED",
                                  note=f"tepi {la} di tampak {A['vi']} + tepi {lb} di tampak {B['vi']} pada baris tinggi yang sama", src="pair"))
                used.update((i, j)); break
    # vertical edges (panels standing): pair copies in one view = same part, count; height = h; length from matching horizontal edge in another view at same z-row
    for i, A in enumerate(items):
        if i in used or not A["edge"] or A["h"] <= A["w"]: continue
        twins = [j for j, B in enumerate(items) if j not in used and B["edge"] and B["code"] == A["code"] and abs(B["h"] - A["h"]) <= 6 and abs(B["z"] - A["z"]) <= 10 and B["h"] > B["w"]]
        # width from a horizontal edge of same code & z-row in any view
        horiz = [B for j, B in enumerate(items) if B["edge"] and B["code"] == A["code"] and B["w"] > B["h"] and abs(B["z"] - A["z"]) <= A["h"] + 10]
        Wd = max((B["w"] for B in horiz), default=0)
        comps.append(dict(no=0, name="?", l=max(A["h"], Wd), w=min(A["h"], Wd), t=A["t"], qty=len(twins), code=A["code"], status="STATED" if Wd else "CHECK",
                          note=f"panel tegak tinggi {A['h']}, {len(twins)} buah pada baris tinggi yang sama" + (f"; lebar {Wd} dari tepi datar" if Wd else "; lebar belum terbaca"), src="pair"))
        used.update(twins)
    for i, A in enumerate(items):
        if i in used: continue
        used.add(i)
        if A["edge"]:
            comps.append(dict(no=0, name="?", l=max(A["w"], A["h"]), w=0, t=A["t"], qty=1, code=A["code"], status="CHECK", note=f"hanya tepi {max(A['w'], A['h'])} x t{A['t']} (tampak {A['vi']})", src="label"))
        else:
            comps.append(dict(no=0, name="?", l=max(A["w"], A["h"]), w=min(A["w"], A["h"]), t=A["t"], qty=1, code=A["code"], status="STATED", note=f"bidang berlabel {A['w']} x {A['h']}", src="label"))
    # names by part-list rule (thickness + shape); 0 = needs a human
    for c in comps:
        if c["no"]: continue
        t, L_, W_ = c["t"], c["l"], c["w"]
        if t <= 6 and W_: c["no"] = 405
        elif t == 12 and c["code"].endswith("0X") and W_ and W_ <= 250: c["no"] = 402 if L_ >= 400 else 404
        elif t == 9 and W_ and W_ >= 150: c["no"] = 302
        elif t >= 18 and W_ and W_ >= 300: c["no"] = 601
        elif t >= 12 and c["code"].endswith("1X") and not W_: c["no"] = 308
        elif t >= 18 and W_ and W_ < 300: c["no"] = 401
        c["name"] = PARTS.get(c["no"], "?")
        if not c["no"]: c["status"] = "CHECK"
    # merge identical rows
    merged = collections.OrderedDict()
    for c in comps:
        key = (c["no"], c["l"], c["w"], c["t"], c["code"])
        if key in merged: merged[key]["qty"] += c["qty"]
        else: merged[key] = c
    comps = list(merged.values())
    # hardware
    for (x, z, w, h), label in lab.items():
        kind, t, code, chk = material(label)
        if kind == "hw" and not any(c["code"] == code for c in comps):
            comps.append(dict(no=903, name=PARTS[903], l=max(w, h), w=0, t=0, qty=1, code=code, status="CHECK", note=chk + "; panjang dari bidang label", src="label"))
    comps.sort(key=lambda c: (c["no"] == 0, c["no"], -c["l"]))
    for i, c in enumerate(comps, 1):
        c["row"] = i
    # ---- write labels in place: each drafter MULTILEADER -> the component matched to its face
    def comp_for_label(label, x, z, w, h):
        kind, t, code, chk = material(label)
        cand = [c for c in comps if c["code"] == code]
        if not cand:
            return None
        if kind == "metal":
            if near(w, ma, 3) and near(h, ma, 3): return next((c for c in cand if c["no"] in (19, 1, 14, 15, 16)), cand[0])
            if h > w: return next((c for c in cand if c["no"] in (3, 17)), cand[0])
            return next((c for c in cand if near(c["l"], w, 8)), cand[0])
        return min(cand, key=lambda c: min(abs(c["l"] - max(w, h)), abs(c["w"] - max(w, h)), abs(c["l"] - min(w, h))))
    # label handles
    dxf = os.path.join(tempfile.mkdtemp(), "h.dxf"); R.dwg_to_dxf(a.dwg, dxf); d = ezdxf.readfile(dxf)
    edits = []; unmatched = []
    for e in d.modelspace():
        if e.dxftype() != "MULTILEADER": continue
        try:
            txt = " ".join(ezdxf.tools.text.plain_mtext(e.context.mtext.default_content).split()); tip = None
            for ld in e.context.leaders:
                for ln in ld.lines:
                    if ln.vertices: tip = ln.vertices[0]; break
                if tip: break
        except Exception: continue
        if tip is None: continue
        try:
            lp = e.context.leaders[0].last_leader_point; land = (lp.x, lp.z); th = float(e.context.char_height) * float(e.dxf.scale or 1)
            ins = e.context.mtext.insert; tx_dir = 1 if ins.x >= lp.x else -1
        except Exception:
            land, th, tx_dir = (tip.x, tip.z), 15.0, 1
        pt = (tip.x, tip.z)
        inside = [f for f in faces if f[0] <= pt[0] <= f[0] + f[2] and f[1] <= pt[1] <= f[1] + f[3]]
        f = min(inside, key=lambda f: f[2] * f[3]) if inside else min(faces, key=lambda f: math.hypot(max(f[0] - pt[0], 0, pt[0] - f[0] - f[2]), max(f[1] - pt[1], 0, pt[1] - f[1] - f[3])))
        c = comp_for_label(txt, *f)
        if c is None:
            unmatched.append(txt); continue


        edits.append((e.dxf.handle.upper(), c["row"], land, th, tx_dir))
    base = f"{a.item}_components"; out_pdf = os.path.join(a.out, base + ".pdf"); out_dwg = os.path.join(a.out, base + ".dwg")
    for f_ in (out_pdf, out_dwg):
        if os.path.exists(f_):
            try: os.remove(f_)
            except OSError: pass
    w_ = tempfile.mkdtemp(prefix="cmp_"); src = os.path.join(w_, "src.dwg"); shutil.copy(a.dwg, src)
    L = ["FILEDIA", "0", "CMDECHO", "0", "EXPERT", "5", "_.-LAYER", "_M", "BOM-NO", "_C", "5", "BOM-NO", "", "(setq okn 0 failn 0)"]
    def kn_box(x, z, n, h, dirx):
        side = 2.2 * h; cx = x + dirx * (side / 2 + 0.3 * h); cz = z
        x0, x1, z0, z1 = cx - side / 2, cx + side / 2, cz - side / 2, cz + side / 2
        ex = "(cons 210 (list 0.0 -1.0 0.0))"
        box = f'(entmake (list (cons 0 "LWPOLYLINE") (cons 100 "AcDbEntity") (cons 8 "BOM-NO") (cons 100 "AcDbPolyline") (cons 90 4) (cons 70 1) (cons 43 {0.08 * h:.2f}) (cons 10 (list {x0:.2f} {z0:.2f})) (cons 10 (list {x1:.2f} {z0:.2f})) (cons 10 (list {x1:.2f} {z1:.2f})) (cons 10 (list {x0:.2f} {z1:.2f})) {ex}))'
        txt = f'(entmake (list (cons 0 "TEXT") (cons 8 "BOM-NO") (cons 10 (list {cx:.2f} {cz:.2f} 0.0)) (cons 40 {1.25 * h:.2f}) (cons 1 "{n}") (cons 72 1) (cons 73 2) (cons 11 (list {cx:.2f} {cz:.2f} 0.0)) {ex}))'
        return [box, txt]
    for hnd, n, land, th, dirx in edits:
        L += [f'(setq e (handent "{hnd}"))',
              f'(if e (progn (setq d (entget e)) (setq a304 (assoc 304 d)) (if a304 (if (entmod (subst (cons 304 " ") a304 d)) (setq okn (1+ okn)) (setq failn (1+ failn))) (setq failn (1+ failn)))) (setq failn (1+ failn)))']
        L += kn_box(land[0], land[1], n, th, dirx)
    L += ['(princ (strcat "\\nPREFIX_OK=" (itoa okn) " FAIL=" (itoa failn)))', "_.REGENALL"]
    # table on sheet 1 of the drafter layout (same placement logic as dwg2d_number_labels)
    layouts = [l.name for l in d.layouts if l.name != "Model"]; lay = layouts[0] if layouts else ""
    pdfs = []
    if lay:
        ly = d.layouts.get(lay)
        vps = [(e.dxf.center.x - e.dxf.width / 2, e.dxf.center.y - e.dxf.height / 2, e.dxf.center.x + e.dxf.width / 2, e.dxf.center.y + e.dxf.height / 2) for e in ly if e.dxftype() == "VIEWPORT" and e.dxf.id != 1]
        vps = [v for v in vps if (v[2] - v[0]) < 0.6 * max(x[2] for x in vps)]
        srt = sorted(vps, key=lambda v: v[0]); widest = max(v[2] - v[0] for v in srt); sheets = []
        for v in srt:
            if sheets and v[0] - sheets[-1]["x1"] <= 0.4 * widest:
                sh = sheets[-1]; sh["x1"] = max(sh["x1"], v[2]); sh["y0"] = min(sh["y0"], v[1]); sh["y1"] = max(sh["y1"], v[3])
            else:
                sheets.append(dict(x0=v[0], x1=v[2], y0=v[1], y1=v[3]))
        s1 = sheets[0]; k = 1.0 if (s1["x1"] - s1["x0"]) > 100 else 1 / 25.4
        # ---- table page: own layout in mm (A3 landscape 420 x 297)
        TL = "BOM-TABLE"
        L += ["_.-LAYOUT", "_N", TL, f'(setvar "CTAB" "{TL}")', "_.PSPACE"]
        kk = 1.0
        tx, ty = 15.0, 258.0
        rh = 7.0; cw = [20, 84, 40, 12, 30, 24, 180]; tw = sum(cw); rn = len(comps) + 2; by = ty - rh * rn
        def pl(x1, y1, x2, y2): return f'(entmake (list (cons 0 "LINE") (cons 8 "BOM-NO") (cons 10 (list {x1:.3f} {y1:.3f} 0)) (cons 11 (list {x2:.3f} {y2:.3f} 0))))'
        def pt(x, y, s_, h=3.2): return f'(entmake (list (cons 0 "TEXT") (cons 8 "BOM-NO") (cons 10 (list {x:.3f} {y:.3f} 0)) (cons 40 {h:.3f}) (cons 1 "{str(s_).replace(chr(34), chr(39))}")))'
        # sheet frame + title block (architect style): frame 10 mm margin, title strip at the bottom
        L += [pl(10, 10, 410, 10), pl(410, 10, 410, 287), pl(410, 287, 10, 287), pl(10, 287, 10, 10), pl(10, 32, 410, 32)]
        for xk in (120, 230, 300, 360):
            L += [pl(xk, 10, xk, 32)]
        nsheet = len(sheets) + 1
        L += [pt(13, 27, "TALA LIVING", 4.0), pt(13, 20, "Keynote & Schedule Komponen", 3.0), pt(13, 14, "Sumber: gambar 2D drafter + BOM-APP", 2.4),
              pt(123, 27, "ITEM", 2.4), pt(123, 20, f"{a.item}", 4.0), pt(123, 14, f"{a.name}"[:40], 3.0),
              pt(233, 27, "DRAWN", 2.4), pt(233, 20, "BOM-APP (auto)", 3.0), pt(233, 14, f"{datetime.date.today():%d %b %Y}", 3.0),
              pt(303, 27, "STATUS", 2.4), pt(303, 20, f"{sum(1 for c in comps if c['status'] != 'CHECK')}/{len(comps)} pasti", 3.0), pt(303, 14, f"{sum(1 for c in comps if c['status'] == 'CHECK')} CHECK", 3.0),
              pt(363, 27, "SHEET", 2.4), pt(363, 18, f"{a.item}-{nsheet:02d}", 4.2), pt(363, 12.5, f"{nsheet} / {nsheet}", 2.4)]
        L += [pt(tx, ty + 8, f"KEYNOTE & SCHEDULE KOMPONEN  -  {a.item} {a.name}", 5.0)]
        L += [pl(tx, ty, tx + tw, ty), pl(tx + tw, ty, tx + tw, by), pl(tx + tw, by, tx, by), pl(tx, by, tx, ty)] + [pl(tx, ty - rh * i, tx + tw, ty - rh * i) for i in range(1, rn)]
        xx = tx
        for c in cw[:-1]:
            xx += c; L += [pl(xx, ty - rh, xx, by)]
        L += [pt(tx + 2, ty - rh + 2, "Tag keynote (angka berbingkai) di gambar = baris tabel ini. PART NO = Part Master v3 BOM-APP (3 digit). BAHAN = kode tabel bahan pabrik.", 3.0)]
        xx = tx
        for c, h in zip(cw, ["TAG", "PART NO  NAMA (Part Master v3)", "L x W x T", "QTY", "BAHAN", "STATUS", "CATATAN"]):
            L += [pt(xx + 2, ty - 2 * rh + 2, h, 3.2)]; xx += c
        for i, c in enumerate(comps):
            size = f"{c['l']} x {c['w']} x {c['t']}" if c["w"] else f"L {c['l']} x ? x {c['t']}"
            xx = tx
            for cwid, v in zip(cw, [f"{c['row']}", f"{c['no'] or '?'}  {c['name']}", size, c["qty"], c["code"], c["status"], c["note"][:80]]):
                L += [pt(xx + 2, ty - (i + 3) * rh + 2, v, 3.2 if cwid > 20 else 3.2)]; xx += cwid
        L += [pt(tx, by - 7, "STATED = ukuran dari bidang berlabel drafter.  DERIVED = dihitung dari geometri tampak.  CHECK = belum pasti, perlu konfirmasi drafter.", 3.0),
              pt(tx, by - 13, "Dimensi di gambar: " + ", ".join(f"{d_}" + (f" x{v}" if v > 1 else "") for d_, v in sorted(dims.items())), 3.0),
              pt(tx, by - 19, f"Nomor part = Part Master v{_PM['version']} ({_PM['updated']}). Standar label drafter: docs/STANDAR-GAMBAR-BOM.md.", 3.0)]
        pdf_t = out_pdf.replace(".pdf", "_p0.pdf")
        if os.path.exists(pdf_t): os.remove(pdf_t)
        L += ["_.-PLOT", "_Y", TL, "DWG To PDF.pc3", C.PAPER_A3, "_M", "_L", "_N", "_W", "0,0", "420,297", "1:1", "_C", "_Y", ".", "_Y", "_N", "_N", "_N", pdf_t.replace(chr(92), "/"), "_N", "_Y"]
        L += [f'(setvar "CTAB" "{lay}")', "_.PSPACE"]
        pdfs.append(pdf_t)
        for si, sh in enumerate(sheets, 1):
            pdf_i = out_pdf.replace(".pdf", f"_p{si}.pdf")
            if os.path.exists(pdf_i): os.remove(pdf_i)
            top = sh["y1"] + 2.6 * 25.4 * k
            wx0, wy0 = sh["x0"] - 8 * k, sh["y0"] - 12 * k; wx1, wy1 = sh["x1"] + 8 * k, top
            L += ["_.-PLOT", "_Y", lay, "DWG To PDF.pc3", C.PAPER_A3, "_M", "_L", "_N", "_W", f"{wx0:.3f},{wy0:.3f}", f"{wx1:.3f},{wy1:.3f}", "_F", "_C", "_Y", ".", "_Y", "_N", "_N", "_N", pdf_i.replace(chr(92), "/"), "_N", "_Y"]
            pdfs.append(pdf_i)
    L += ["_.SAVEAS", "2018", out_dwg.replace("\\", "/")]
    ok, log, why = C.run(src, L, timeout=180, workdir=w_)
    if pdfs:
        import pymupdf
        doc = pymupdf.open()
        for f_ in sorted(pdfs, key=lambda f: f.endswith("_p0.pdf")):     # drawing sheets first, table page last
            if os.path.exists(f_) and os.path.getsize(f_) > 1000: doc.insert_pdf(pymupdf.open(f_))
        if len(doc): doc.save(out_pdf)
        for f_ in pdfs:
            try: os.remove(f_)
            except OSError: pass
    pref = next((l.strip() for l in log.splitlines() if l.startswith("PREFIX_OK")), "?")
    good, det = C.pdf_has_content(out_pdf)
    js = dict(item=a.item, name=a.name, source_dwg=os.path.abspath(a.dwg), generated=datetime.datetime.now().isoformat(timespec="seconds"),
              part_list=f"Part Master v{_PM['version']} ({_PM['updated']}, {_PM['total_parts']} parts) + factory material codes", components=comps, labels_rewritten=len(edits), labels_unmatched=unmatched,
              drawing_dimensions_mm=dims, views=len(views), faces=len(faces), seconds=round(time.time() - t0, 1))
    json.dump(js, open(os.path.join(a.out, base + ".json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    open(os.path.join(a.out, base + ".log"), "w", encoding="utf-8").write(log)
    print(f"{why} | {pref} | labels rewritten {len(edits)} unmatched {len(unmatched)} | comps {len(comps)} | PDF {good} {det} | {time.time() - t0:.1f}s")
    print(f"{'NO':>3} {'NAMA':<24} {'L x W x T':<16} {'QTY':>3} {'KODE':<12} STATUS  catatan")
    for c in comps:
        size = f"{c['l']}x{c['w']}x{c['t']}" if c["w"] else f"L{c['l']} x? t{c['t']}"
        print(f"{c['no'] or '?':>3} {c['name']:<24} {size:<16} {c['qty']:>3} {c['code']:<12} {c['status']:<7} {c['note']}")
    if not ok or not good:
        print("\n".join([l for l in log.splitlines() if l.strip()][-10:])); sys.exit(1)


if __name__ == "__main__":
    main()
