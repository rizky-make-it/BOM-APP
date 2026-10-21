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
import dwg2d_read as D2
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
    """all XZ faces (labelled or not) + labels + dims, read by AutoCAD (tools/acad_read via dwg2d_read)"""
    res = D2.read(dwg)
    return res, list(res["faces"])


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
    ap.add_argument("--manual", help="JSON {comps:[...], tags:[{row,x,y,tx,ty}]}: labels placed by BOM-APP for a DWG without drafter leaders (XY plane)")
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
    # ---- metal frame: one pass per hollow section found in the drafter's labels (MT-SQUARE 20X20, MT-HOLLOW 80X40 ...).
    #      Bars = thin rectangles with one side == a or b of the section; squares/rects a x b = cross-sections.
    comps = []
    metal_sections = sorted({tuple(sorted((material(lb)[1], int(material(lb)[2].split("x")[1])))) for lb in lab.values() if material(lb)[0] == "metal"})
    if not metal_sections:
        metal_sections = [tuple(sorted(int(v) for v in a.metal.lower().split("x")))]
    panel_faces_set = {f for f, lb in lab.items() if material(lb)[0] != "metal"}
    # which labelled metal faces belong to which section (for the bar test we also accept unlabelled faces)
    metal_face_sec = {f: tuple(sorted((material(lb)[1], int(material(lb)[2].split("x")[1])))) for f, lb in lab.items() if material(lb)[0] == "metal"}
    for (ma, mb) in metal_sections:
        def is_sec(w, h): return (near(w, ma, 3) and near(h, mb, 3)) or (near(w, mb, 3) and near(h, ma, 3))
        def is_bar(w, h): return ((near(w, ma, 3) or near(w, mb, 3)) != (near(h, ma, 3) or near(h, mb, 3))) and max(w, h) > 60
        def is_plan(v):
            return sum(1 for (x, z, w, h) in v["f"] if is_sec(w, h)) >= 4 and abs((v["x1"] - v["x0"]) - (v["z1"] - v["z0"])) < 0.35 * max(v["x1"] - v["x0"], 1)
        per_view = []
        for v in views:
            vert = collections.Counter(); horz = collections.Counter(); plan_v = is_plan(v)
            for (x, z, w, h) in v["f"]:
                f_ = (x, z, w, h)
                if f_ in panel_faces_set or not is_bar(w, h): continue
                if f_ in metal_face_sec and metal_face_sec[f_] != (ma, mb): continue
                if len(metal_sections) > 1 and f_ not in metal_face_sec:
                    # unlabelled bar: assign to the section whose thin side matches best
                    thin = min(w, h)
                    if not (near(thin, ma, 3) or near(thin, mb, 3)): continue
                    if any(near(thin, o, 3) for s_ in metal_sections if s_ != (ma, mb) for o in s_) and not near(thin, ma, 1): continue
                if plan_v: horz[max(w, h)] += 1
                elif h > w: vert[h] += 1
                else: horz[w] += 1
            if vert or horz: per_view.append(dict(v=v, vert=vert, horz=horz, plan=plan_v))
        legs_h = collections.Counter()
        for pv_ in per_view:
            if pv_["plan"]: continue
            for h, n in pv_["vert"].items(): legs_h[h] = max(legs_h[h], n)
        code = f"MT-{ma}x{mb}"
        if legs_h:
            hL = max(legs_h); nL = legs_h[hL]
            comps.append(dict(no=101, name=PARTS[101], l=hL, w=mb, t=ma, qty=nL * 2, code=code, status="DERIVED",
                              note=f"batang tegak {hL} terlihat {nL}x di satu tampak; x2 untuk pasangan depan/belakang", src="geometry"))
            for h, n in legs_h.items():
                if h < hL - 5:
                    comps.append(dict(no=209, name=PARTS[209], l=h, w=mb, t=ma, qty=n * 2, code=code, status="DERIVED", note=f"batang tegak pendek {h} terlihat {n}x; x2", src="geometry"))
        horz_all = collections.Counter()
        for pv_ in per_view:
            for w, n in pv_["horz"].items(): horz_all[w] = max(horz_all[w], n)
        Lmax = max(horz_all, default=0)
        for w, n in sorted(horz_all.items(), key=lambda t: -t[0]):
            if near(w, Lmax, 8):
                comps.append(dict(no=201, name=PARTS[201] + " / " + PARTS[202], l=w, w=mb, t=ma, qty=n * 2, code=code, status="DERIVED",
                                  note=f"rail rangka {w}: terlihat {n}x di satu tampak; x2 untuk pasangan sisi", src="geometry"))
            else:
                comps.append(dict(no=210, name=PARTS[210], l=w, w=mb, t=ma, qty=n * 2, code=code, status="DERIVED",
                                  note=f"batang pendek {w}: terlihat {n}x; x2", src="geometry"))
    ma, mb = metal_sections[0]


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
    def pos_name(A):
        """part_no from material kind + thickness + where the labelled face sits in its view (0 = undecided)"""
        t = A["t"]; v = views[A["vi"]]; vw = v["x1"] - v["x0"]; vh = v["z1"] - v["z0"]
        spans_w = A["w"] >= 0.8 * vw; full_h = A["h"] >= 0.8 * vh; standing = A["h"] > A["w"]
        if A["code"] in ("A", "A1"):                                   # solid wood: section drives the name
            long_, short_ = max(A["w"], A["h"]), min(A["w"], A["h"])
            if standing and full_h: return 101                         # leg / post
            if long_ >= 0.8 * vw and short_ >= 100: return 806 if vw > 1500 else 201   # bed side rail / top rail
            if long_ >= 0.8 * vw: return 201                            # rail along the view
            if short_ <= 50 and long_ >= 150: return 210               # cross bar / support
            return 199
        if t <= 6: return 405                                          # drawer base
        if t == 12 and A["code"].endswith("0X"): return 402 if standing else 404   # drawer box side (standing) / front-back
        if t == 12 and A["code"].endswith("1X"): return 308 if spans_w else 310    # shelf / fixed horizontal panel
        if t == 9: return 302 if (standing and full_h) or spans_w else 401          # back panel / drawer front (9 mm veneer)
        if t >= 15 and standing and (full_h or A["h"] >= 600): return 801 if vw > 1500 else 301   # headboard / side panel
        if t >= 15 and vw > 1500: return 804 if A["h"] >= 150 else 310                           # bed: footboard panel / deck
        if t >= 15: return 601 if spans_w and A["z"] + A["h"] >= v["z1"] - 30 else (308 if spans_w else 401)
        return 0

    for i, A in enumerate(items):
        if i in used or A["edge"] is False: continue
        for j, B in enumerate(items):
            if j <= i or j in used or not B["edge"] or B["vi"] == A["vi"] or B["code"] != A["code"]: continue
            if abs(A["z"] - B["z"]) <= 10 and abs(A["h"] - B["h"]) <= 10:     # same height row in two perpendicular sections
                la, lb = max(A["w"], A["h"]), max(B["w"], B["h"])
                if A["h"] > A["w"]:                       # vertical edges: the two spacings give L & W? use their lengths as height
                    continue
                comps.append(dict(no=pos_name(A), name="?", l=max(la, lb), w=min(la, lb), t=A["t"], qty=1, code=A["code"], status="STATED",
                                  note=f"tepi {la} di tampak {A['vi']} + tepi {lb} di tampak {B['vi']} pada baris tinggi yang sama", src="pair"))
                used.update((i, j)); break
    # vertical edges (panels standing): pair copies in one view = same part, count; height = h; length from matching horizontal edge in another view at same z-row
    for i, A in enumerate(items):
        if i in used or not A["edge"] or A["h"] <= A["w"]: continue
        twins = [j for j, B in enumerate(items) if j not in used and B["edge"] and B["code"] == A["code"] and abs(B["h"] - A["h"]) <= 6 and abs(B["z"] - A["z"]) <= 10 and B["h"] > B["w"]]
        # width from a horizontal edge of same code & z-row in any view
        horiz = [B for j, B in enumerate(items) if B["edge"] and B["code"] == A["code"] and B["w"] > B["h"] and abs(B["z"] - A["z"]) <= A["h"] + 10]
        Wd = max((B["w"] for B in horiz), default=0)
        comps.append(dict(no=pos_name(A), name="?", l=max(A["h"], Wd), w=min(A["h"], Wd), t=A["t"], qty=len(twins), code=A["code"], status="STATED" if Wd else "CHECK",
                          note=f"panel tegak tinggi {A['h']}, {len(twins)} buah pada baris tinggi yang sama" + (f"; lebar {Wd} dari tepi datar" if Wd else "; lebar belum terbaca"), src="pair"))
        used.update(twins)
    for i, A in enumerate(items):
        if i in used: continue
        used.add(i)
        if A["edge"]:
            comps.append(dict(no=pos_name(A), name="?", l=max(A["w"], A["h"]), w=0, t=A["t"], qty=1, code=A["code"], status="CHECK", note=f"hanya tepi {max(A['w'], A['h'])} x t{A['t']} (tampak {A['vi']})", src="label"))
        else:
            comps.append(dict(no=pos_name(A), name="?", l=max(A["w"], A["h"]), w=min(A["w"], A["h"]), t=A["t"], qty=1, code=A["code"], status="STATED", note=f"bidang berlabel {A['w']} x {A['h']}", src="label"))
    # names by part-list rule (thickness + shape); 0 = needs a human
    for c in comps:
        if c["no"]:
            c["name"] = PARTS.get(c["no"], c["name"]); continue
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
    MAN = json.load(open(a.manual, encoding="utf-8")) if a.manual else None
    if MAN:
        comps = MAN["comps"]
        for i, c in enumerate(comps, 1): c["row"] = i
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
    # label handles: straight from AutoCAD (res["leaders"])
    edits = []; unmatched = []
    for m in res["leaders"]:
        txt = m["text"]; tip = m["tip"]
        th = float(m["th"] or 15.0)
        lp = m["landing"]; dirx = 1 if float(m["dir"][0]) >= 0 else -1
        dl = float(m["dogleg"] or 0.0)
        land = (lp[0] + dirx * dl, lp[2])            # end of the dogleg = where the drafter's text sat
        tx_dir = dirx
        pt = (tip[0], tip[2])
        inside = [f for f in faces if f[0] <= pt[0] <= f[0] + f[2] and f[1] <= pt[1] <= f[1] + f[3]]
        f = min(inside, key=lambda f: f[2] * f[3]) if inside else min(faces, key=lambda f: math.hypot(max(f[0] - pt[0], 0, pt[0] - f[0] - f[2]), max(f[1] - pt[1], 0, pt[1] - f[1] - f[3])))
        c = comp_for_label(txt, *f)
        if c is None:
            unmatched.append(txt); continue
        edits.append((m["handle"].upper(), c["row"], land, th, tx_dir))
    base = f"{a.item}_components"; out_pdf = os.path.join(a.out, base + ".pdf"); out_dwg = os.path.join(a.out, base + ".dwg")
    for f_ in (out_pdf, out_dwg):
        if os.path.exists(f_):
            try: os.remove(f_)
            except OSError: pass
    w_ = tempfile.mkdtemp(prefix="cmp_"); src = os.path.join(w_, "src.dwg"); shutil.copy(a.dwg, src)
    L = ["FILEDIA", "0", "CMDECHO", "0", "EXPERT", "5", "_.-LAYER", "_M", "BOM-NO", "_C", "5", "BOM-NO", "", "(setq okn 0 failn 0)"]
    def kn_box(x, z, n, h, dirx):
        side = 2.2 * h; cx = x + dirx * (side / 2); cz = z
        x0, x1, z0, z1 = cx - side / 2, cx + side / 2, cz - side / 2, cz + side / 2
        ex = "(cons 210 (list 0.0 -1.0 0.0))"
        box = f'(entmake (list (cons 0 "LWPOLYLINE") (cons 100 "AcDbEntity") (cons 8 "BOM-NO") (cons 100 "AcDbPolyline") (cons 90 4) (cons 70 1) (cons 43 {0.08 * h:.2f}) (cons 10 (list {x0:.2f} {z0:.2f})) (cons 10 (list {x1:.2f} {z0:.2f})) (cons 10 (list {x1:.2f} {z1:.2f})) (cons 10 (list {x0:.2f} {z1:.2f})) {ex}))'
        txt = f'(entmake (list (cons 0 "TEXT") (cons 8 "BOM-NO") (cons 10 (list {cx:.2f} {cz:.2f} 0.0)) (cons 40 {1.25 * h:.2f}) (cons 1 "{n}") (cons 72 1) (cons 73 2) (cons 11 (list {cx:.2f} {cz:.2f} 0.0)) {ex}))'
        return [box, txt]
    for hnd, n, land, th, dirx in edits:
        L += [f'(setq e (handent "{hnd}"))',
              f'(if e (progn (setq d (entget e)) (setq a304 (assoc 304 d)) (if a304 (if (entmod (subst (cons 304 " ") a304 d)) (setq okn (1+ okn)) (setq failn (1+ failn))) (setq failn (1+ failn)))) (setq failn (1+ failn)))']
        L += kn_box(land[0], land[1], n, th, dirx)
    if MAN:    # tags we place ourselves (XY plane): leader line from the target point to a boxed number
        for tg in MAN["tags"]:
            h = float(tg.get("h", 30)); side = 2.2 * h; cx, cy = tg["tx"], tg["ty"]
            L.append(f'(entmake (list (cons 0 "LINE") (cons 8 "BOM-NO") (cons 10 (list {tg["x"]:.2f} {tg["y"]:.2f} 0.0)) (cons 11 (list {cx:.2f} {cy:.2f} 0.0))))')
            L.append(f'(entmake (list (cons 0 "CIRCLE") (cons 8 "BOM-NO") (cons 10 (list {tg["x"]:.2f} {tg["y"]:.2f} 0.0)) (cons 40 {0.15 * h:.2f})))')
            L.append(f'(entmake (list (cons 0 "LWPOLYLINE") (cons 100 "AcDbEntity") (cons 8 "BOM-NO") (cons 100 "AcDbPolyline") (cons 90 4) (cons 70 1) (cons 10 (list {cx - side / 2:.2f} {cy - side / 2:.2f})) (cons 10 (list {cx + side / 2:.2f} {cy - side / 2:.2f})) (cons 10 (list {cx + side / 2:.2f} {cy + side / 2:.2f})) (cons 10 (list {cx - side / 2:.2f} {cy + side / 2:.2f}))))')
            L.append(f'(entmake (list (cons 0 "TEXT") (cons 8 "BOM-NO") (cons 10 (list {cx:.2f} {cy:.2f} 0.0)) (cons 40 {0.95 * h:.2f}) (cons 1 "{tg["row"]}") (cons 72 1) (cons 73 2) (cons 11 (list {cx:.2f} {cy:.2f} 0.0))))')
    L += ['(princ (strcat "\\nPREFIX_OK=" (itoa okn) " FAIL=" (itoa failn)))', "_.REGENALL"]
    # table on sheet 1 of the drafter layout (same placement logic as dwg2d_number_labels)
    # layouts/viewports/frames straight from AutoCAD (res["layouts"]): first layout that has viewports
    lay_objs = [l for l in res["layouts"] if l["viewports"]]
    lay = lay_objs[0]["name"] if lay_objs else ""
    pdfs = []
    if lay:
        ly = lay_objs[0]
        vps = [tuple(v) for v in ly["viewports"]]
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
        L += ["_.-LAYOUT", "_N", TL, f'(setvar "CTAB" "{TL}")', "_.PSPACE",
              # the new layout comes with a default model viewport whose border plots as a stray rectangle: erase it
              '(progn (setq ss (ssget "_X" (list (cons 0 "VIEWPORT") (cons 410 "' + TL + '")))) (if ss (progn (setq i 0) (while (< i (sslength ss)) (setq en (ssname ss i)) (if (/= (cdr (assoc 69 (entget en))) 1) (entdel en)) (setq i (1+ i))))))']
        kk = 1.0
        tx, ty = 15.0, 258.0
        rh = 7.0; cw = [16, 84, 40, 12, 34, 24, 180]; tw = sum(cw); rn = len(comps) + 1; by = ty - rh * rn
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
            xx += c; L += [pl(xx, ty, xx, by)]
        # explanatory line lives ABOVE the table (outside the grid), never inside a row
        L += [pt(tx, ty + 2.5, "Tag keynote (angka berbingkai) di gambar = baris tabel ini.  PART NO = Part Master v3 BOM-APP (3 digit).  BAHAN = kode tabel bahan pabrik.", 2.8)]
        xx = tx
        for c, h in zip(cw, ["TAG", "PART NO  NAMA (Part Master v3)", "L x W x T", "QTY", "BAHAN", "STATUS", "CATATAN"]):
            L += [pt(xx + 2, ty - rh + 2, h, 3.2)]; xx += c
        for i, c in enumerate(comps):
            size = f"{c['l']} x {c['w']} x {c['t']}" if c["w"] else f"L {c['l']} x ? x {c['t']}"
            xx = tx
            for cwid, v in zip(cw, [f"{c['row']}", f"{c['no'] or '?'}  {c['name']}", size, c["qty"], c["code"], c["status"], c["note"][:68]]):
                L += [pt(xx + 2, ty - (i + 2) * rh + 2, v, 3.2)]; xx += cwid
        L += [pt(tx, by - 7, "STATED = ukuran dari bidang berlabel drafter.  DERIVED = dihitung dari geometri tampak.  CHECK = belum pasti, perlu konfirmasi drafter.", 3.0),
              pt(tx, by - 13, "Dimensi di gambar: " + ", ".join(f"{d_}" + (f" x{v}" if v > 1 else "") for d_, v in sorted(dims.items())), 3.0),
              pt(tx, by - 19, f"Nomor part = Part Master v{_PM['version']} ({_PM['updated']}). Standar label drafter: docs/STANDAR-GAMBAR-BOM.md.", 3.0)]
        pdf_t = out_pdf.replace(".pdf", "_p0.pdf")
        if os.path.exists(pdf_t): os.remove(pdf_t)
        L += ["_.-PLOT", "_Y", TL, "DWG To PDF.pc3", C.PAPER_A3, "_M", "_L", "_N", "_W", "0,0", "420,297", "1:1", "_C", "_Y", ".", "_Y", "_N", "_N", "_N", pdf_t.replace(chr(92), "/"), "_N", "_Y"]
        L += [f'(setvar "CTAB" "{lay}")', "_.PSPACE"]
        pdfs.append(pdf_t)
        # drafter's own sheet frames (closed 4-point polylines in paper space that enclose viewports) = exact plot windows
        frames = []
        for fr in [tuple(f) for f in ly["frames"]]:
            if any(v[0] >= fr[0] - 0.01 and v[2] <= fr[2] + 0.01 and v[1] >= fr[1] - 0.01 and v[3] <= fr[3] + 0.01 for v in vps):
                frames.append(fr)
        frames.sort()
        if len(frames) == len(sheets):
            for sh, fr in zip(sheets, frames):
                sh["win"] = fr
        for si, sh in enumerate(sheets, 1):
            pdf_i = out_pdf.replace(".pdf", f"_p{si}.pdf")
            if os.path.exists(pdf_i): os.remove(pdf_i)
            if "win" in sh:
                wx0, wy0, wx1, wy1 = sh["win"]          # plot exactly the drafter's frame -> fills the page, nothing stray
            else:
                top = sh["y1"] + 2.6 * 25.4 * k
                wx0, wy0 = sh["x0"] - 8 * k, sh["y0"] - 12 * k; wx1, wy1 = sh["x1"] + 8 * k, top
            L += [f'(command "_.-PLOT" "_Y" "{lay}" "DWG To PDF.pc3" "{C.PAPER_A3}" "_M" "_L" "_N" "_W" "{wx0:.3f},{wy0:.3f}" "{wx1:.3f},{wy1:.3f}" "_F" "_C" "_Y" "." "_Y" "_N" "_N" "_N" "{pdf_i.replace(chr(92), "/")}" "_N" "_Y")']
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
              part_list=f"Part Master v{_PM['version']} ({_PM['updated']}, {_PM['total_parts']} parts) + factory material codes", components=comps, tags=[dict(handle=e_[0], row=e_[1], x=e_[2][0], z=e_[2][1], h=e_[3], dir=e_[4]) for e_ in edits], labels_rewritten=len(edits), labels_unmatched=unmatched,
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
