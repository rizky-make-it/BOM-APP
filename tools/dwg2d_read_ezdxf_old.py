"""Generic 2D reader: all labelled faces of a DWG (XZ plane), grouped by label+size, with view columns.
Usage: python tools/dwg2d_read.py <dwg> [--out statement.json]   (no hard-coded x window)"""
import os, sys, json, tempfile, collections, math, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dwg_reader as R, ezdxf
from ezdxf.math import Vec3
from shapely.geometry import LineString, Point
from shapely.ops import unary_union, polygonize


def read(dwg, plane=(0, -1, 0)):
    dxf = os.path.join(tempfile.mkdtemp(), "l.dxf"); R.dwg_to_dxf(dwg, dxf)
    d = ezdxf.readfile(dxf); m = d.modelspace()
    def wcs(e):
        ocs = e.ocs()
        if e.dxftype() == "LINE":
            P = [e.dxf.start, e.dxf.end]
        else:
            P = [Vec3(p[0], p[1], e.dxf.elevation) for p in e.get_points("xy")]
            if e.closed: P.append(P[0])
        return [ocs.to_wcs(p) for p in P]
    segs = []
    for e in m:
        if e.dxftype() in ("LINE", "LWPOLYLINE"):
            ex = tuple(round(v) for v in e.dxf.extrusion) if e.dxf.hasattr("extrusion") else (0, 0, 1)
            if ex != plane:
                continue
            P = wcs(e)
            for a, b in zip(P, P[1:]):
                if a.distance(b) > 0.5:
                    segs.append(LineString([(a.x, a.z), (b.x, b.z)]))
    faces = [f for f in polygonize(unary_union(segs)) if f.area > 30]
    labels = []
    for e in m:
        if e.dxftype() != "MULTILEADER":
            continue
        try: txt = ezdxf.tools.text.plain_mtext(e.context.mtext.default_content).strip().replace("\n", " ")
        except Exception: txt = "?"
        tips = []
        try:
            for ld in e.context.leaders:
                for ln in ld.lines:
                    if ln.vertices: tips.append(ln.vertices[0])
        except Exception: pass
        for t in tips:
            labels.append((txt, t.x, t.z))
    rows = []
    for txt, tx, tz in labels:
        pt = Point(tx, tz)
        inside = [f for f in faces if f.contains(pt)]
        if inside:
            f = min(inside, key=lambda f: f.area); how = "inside"
        else:
            f = min(faces, key=lambda f: f.distance(pt)) if faces else None; how = f"near {f.distance(pt):.0f}" if f else "none"
        if f is None:
            continue
        b = f.bounds; w, h = b[2] - b[0], b[3] - b[1]
        rows.append(dict(label=txt, w=round(w), h=round(h), x=round(b[0]), z=round(b[1]), how=how))
    dims = collections.Counter(); dim_pts = []
    for e in m:
        if e.dxftype() == "DIMENSION":
            try:
                v = e.get_measurement(); dims[round(v) if isinstance(v, (int, float)) else str(v)] += 1
                for attr in ("defpoint", "defpoint2", "defpoint3", "text_midpoint"):
                    if e.dxf.hasattr(attr):
                        w = e.ocs().to_wcs(getattr(e.dxf, attr)); dim_pts.append((w.x, w.z))
            except Exception: pass
    return dict(n_segments=len(segs), n_faces=len(faces), n_labels=len(labels), rows=rows, dims=dict(dims), dim_pts=dim_pts)


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
    print(f"segments {res['n_segments']}, faces {res['n_faces']}, labels {res['n_labels']}; dims {dict(sorted(res['dims'].items(), key=lambda t: t[0] if isinstance(t[0], int) else 0))}")
    print(f"{'n':>2}  {'label (STATED)':<26} size seen")
    for r in st:
        print(f"{r['n']:>2}  {r['label']:<26} {r['long']} x {r['short']}")
    if a.out:
        json.dump(dict(source=a.dwg, dims=res["dims"], statement=st), open(a.out, "w"), indent=1)
