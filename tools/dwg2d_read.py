"""2D reader on top of tools/acad_read.py: AutoCAD itself is the reader (no DWG->DXF converter, no ezdxf).

read(dwg) -> dict(n_segments, n_faces, n_labels, rows, dims, dim_pts, faces, leaders, layouts, seconds, reader)
  rows    : one per leader -> labelled face (label, w, h, x, z, how, handle)
  faces   : closed faces from loose LINE/LWPOLYLINE in the XZ plane (drafter's 2D views), as (x, z, w, h)
  leaders : MULTILEADER data straight from AutoCAD (handle, text, tip, landing, dogleg, dir, th, textpos)
Usage: python tools/dwg2d_read.py <dwg> [--out statement.json]
"""
import argparse, collections, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acad_read
from shapely.geometry import LineString, Point
from shapely.ops import unary_union, polygonize

_MT = re.compile(r"\\[A-Za-z][^;\\{}]*;|\\[lLoOkKpPxX~]|[{}]")


def plain_mtext(t):
    t = t.replace("\\P", " ")
    t = _MT.sub("", t)
    return " ".join(t.split())


def read(dwg):
    if os.environ.get("BOM_READER") == "cc":
        import cc_read; d = cc_read.read_compat(dwg)
    else:
        d = acad_read.read(dwg)
    # drawing plane: drafter style 1 draws 2D views in XZ (y == 0); styles 2/3 draw flat in XY (z == 0). Pick the plane
    # that holds more line vertices; P maps a 3D point to (u, v) in that plane.
    n_xz = sum(1 for l in d["lines"] if abs(l[0][1]) < 1e-3 and abs(l[1][1]) < 1e-3)
    n_xy = sum(1 for l in d["lines"] if abs(l[0][2]) < 1e-3 and abs(l[1][2]) < 1e-3)
    plane = "XZ" if n_xz >= n_xy else "XY"
    P = (lambda p: (p[0], p[2])) if plane == "XZ" else (lambda p: (p[0], p[1]))
    off = 1 if plane == "XZ" else 2                      # index of the coordinate that must be ~0
    segs = []
    for l in d["lines"]:
        a, b = l[0], l[1]
        if abs(a[off]) < 1e-3 and abs(b[off]) < 1e-3:
            ua, ub = P(a), P(b)
            if (ua[0] - ub[0]) ** 2 + (ua[1] - ub[1]) ** 2 > 0.25:
                segs.append(LineString([ua, ub]))
    for pl in d["polylines"]:
        Pts = pl["pts"] + ([pl["pts"][0]] if pl["closed"] and pl["pts"] else [])
        if any(abs(p[off]) > 1e-3 for p in Pts):
            continue
        for a, b in zip(Pts, Pts[1:]):
            ua, ub = P(a), P(b)
            if (ua[0] - ub[0]) ** 2 + (ua[1] - ub[1]) ** 2 > 0.25:
                segs.append(LineString([ua, ub]))
    polys = [f for f in polygonize(unary_union(segs)) if f.area > 30]
    faces = [(round(b[0]), round(b[1]), round(b[2] - b[0]), round(b[3] - b[1])) for b in (f.bounds for f in polys)]
    # labels from all three drafter styles, normalised to: handle, text, tip (3D), landing, dogleg, dir, th, style
    leaders = [dict(handle=m["handle"], text=plain_mtext(m["text"]), raw=m["text"], tip=m["tip"], landing=m["landing"], textpos=m["textpos"],
                    dogleg=m["dogleg"], dir=m["dir"], th=m["th"], layer=m["layer"], style="mleader") for m in d["leaders"]]
    for m in d.get("model_leaders", []):
        if not m["text"]:
            continue
        leaders.append(dict(handle=m["handle"], text=plain_mtext(m["text"]), raw=m["text"], tip=m["tip"], landing=m["tail"], textpos=m["tail"],
                            dogleg=0.0, dir=[1 if m["tail"][0] >= m["tip"][0] else -1, 0, 0], th=m["th"] or 15.0, layer="", style="leader+text", text_handle=m["text_handle"]))
    for m in d.get("paper_leaders", []):
        if not m["text"] or m["viewport"] == 0:
            continue
        leaders.append(dict(handle=m["handle"], text=plain_mtext(m["text"]), raw=m["text"], tip=m["tip_model"], landing=m["tip_model"], textpos=m["tip_model"],
                            dogleg=0.0, dir=[1, 0, 0], th=0.0, layer="", style="paper", text_handle=m["text_handle"], layout=m["layout"], tip_paper=m["tip_paper"], tail_paper=m["tail_paper"]))
    rows = []
    for m in leaders:
        pt = Point(*P(m["tip"]))
        inside = [f for f in polys if f.contains(pt)]
        if inside:
            f = min(inside, key=lambda f: f.area); how = "inside"
        elif polys:
            f = min(polys, key=lambda f: f.distance(pt)); how = f"near {f.distance(pt):.0f}"
        else:
            continue
        b = f.bounds
        rows.append(dict(label=m["text"], w=round(b[2] - b[0]), h=round(b[3] - b[1]), x=round(b[0]), z=round(b[1]), how=how, handle=m["handle"]))
    dims = collections.Counter(); dim_pts = []
    for x in d["dims"]:
        v = x["value"]
        if v and v > 0:
            dims[round(v)] += 1
        for k in ("def1", "def2", "textpos"):
            p = x.get(k)
            if p and abs(p[off]) < 1e-3:
                dim_pts.append(P(p))
    return dict(n_segments=len(segs), n_faces=len(faces), n_labels=len(leaders), rows=rows, dims=dict(dims), dim_pts=dim_pts,
                faces=faces, leaders=leaders, layouts=d["layouts"], seconds=d["_seconds"], reader=d["_reader"], plane=plane)


def statement(rows):
    g = collections.OrderedDict()
    for r in rows:
        if min(r["w"], r["h"]) < 4:
            continue
        key = (r["label"], max(r["w"], r["h"]), min(r["w"], r["h"]))
        g.setdefault(key, []).append(r)
    return [dict(label=k[0], long=k[1], short=k[2], n=len(v), faces=[(r["x"], r["z"], r["w"], r["h"]) for r in v]) for k, v in sorted(g.items(), key=lambda kv: (kv[0][0], -kv[0][1]))]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("dwg"); ap.add_argument("--out")
    a = ap.parse_args()
    res = read(a.dwg); st = statement(res["rows"])
    print(f"{res['reader']} {res['seconds']}s: segments {res['n_segments']}, faces {res['n_faces']}, labels {res['n_labels']}; dims {dict(sorted(res['dims'].items()))}")
    for r in st:
        print(f"{r['n']:>2}  {r['label']:<26} {r['long']} x {r['short']}")
    if a.out:
        json.dump(dict(source=a.dwg, dims=res["dims"], statement=st), open(a.out, "w"), indent=1)
