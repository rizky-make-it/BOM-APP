"""2D reader v2 for the drafter's tallboy drawing: build closed faces from loose LINE/LWPOLYLINE segments
(shapely polygonize), per view column, then attach MULTILEADER labels (arrow tip inside face) and list
the labelled faces with sizes. Also locate the view columns and their titles."""
import os, sys, json, tempfile, collections, math
sys.path.insert(0, r"C:/Users/Admin/Desktop/BOM-APP/tools")
import dwg_reader as R, ezdxf
from ezdxf.math import Vec3
from shapely.geometry import LineString, Point
from shapely.ops import unary_union, polygonize

W = os.path.join(os.environ["LOCALAPPDATA"], "Temp")
dxf = os.path.join(tempfile.mkdtemp(), "l.dxf"); R.dwg_to_dxf(os.path.join(W, "lexi3.dwg"), dxf)
d = ezdxf.readfile(dxf); m = d.modelspace()
X0, X1 = 22500, 27500

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
    if e.dxftype() in ("LINE", "LWPOLYLINE") and e.dxf.hasattr("extrusion") and tuple(round(v) for v in e.dxf.extrusion) == (0, -1, 0):
        P = wcs(e)
        if not any(X0 <= p.x <= X1 for p in P): continue
        for a, b in zip(P, P[1:]):
            if a.distance(b) > 0.5: segs.append(LineString([(a.x, a.z), (b.x, b.z)]))
print("segments:", len(segs))
faces = list(polygonize(unary_union(segs)))
faces = [f for f in faces if f.area > 50]
print("faces built:", len(faces))

# view columns from faces
xs = sorted(f.bounds[0] for f in faces)
cols = []
for f in sorted(faces, key=lambda f: f.bounds[0]):
    if cols and f.bounds[0] - cols[-1]["x1"] <= 250:
        cols[-1]["x1"] = max(cols[-1]["x1"], f.bounds[2]); cols[-1]["faces"].append(f)
        cols[-1]["z0"] = min(cols[-1]["z0"], f.bounds[1]); cols[-1]["z1"] = max(cols[-1]["z1"], f.bounds[3])
    else:
        cols.append(dict(x0=f.bounds[0], x1=f.bounds[2], z0=f.bounds[1], z1=f.bounds[3], faces=[f]))
# titles
titles = []
for e in m:
    if e.dxftype() == "MTEXT":
        p = e.dxf.insert
        if X0 <= p.x <= X1: titles.append((p.x, p.z, ezdxf.tools.text.plain_mtext(e.text).strip()[:20]))
for i, c in enumerate(cols):
    t = [tt[2] for tt in titles if c["x0"] - 200 <= tt[0] <= c["x1"] + 200 and c["z0"] - 400 <= tt[1] <= c["z1"] + 200]
    print(f"view col {i}: x {c['x0']:.0f}..{c['x1']:.0f} ({c['x1']-c['x0']:.0f} wide), z {c['z0']:.0f}..{c['z1']:.0f} ({c['z1']-c['z0']:.0f} high), faces {len(c['faces'])}, titles {t}")

# labels
labels = []
for e in m:
    if e.dxftype() != "MULTILEADER": continue
    try: txt = ezdxf.tools.text.plain_mtext(e.context.mtext.default_content).strip().replace("\n", " ")
    except Exception: txt = "?"
    tips = []
    try:
        for ld in e.context.leaders:
            for ln in ld.lines:
                if ln.vertices: tips.append(ln.vertices[0])
    except Exception: pass
    for t in tips:
        if X0 <= t.x <= X1: labels.append((txt, t.x, t.z))
print("\nlabels:", len(labels))
rows = []
for txt, tx, tz in labels:
    pt = Point(tx, tz)
    inside = [f for f in faces if f.contains(pt)]
    if inside:
        f = min(inside, key=lambda f: f.area); how = "inside"
    else:
        f = min(faces, key=lambda f: f.distance(pt)); how = f"near {f.distance(pt):.0f}"
    b = f.bounds; w, h = b[2] - b[0], b[3] - b[1]
    col = next((i for i, c in enumerate(cols) if c["x0"] - 1 <= b[0] <= c["x1"] + 1), -1)
    rows.append(dict(label=txt, w=round(w), h=round(h), area=round(f.area), rect=abs(f.area - w * h) < 0.05 * w * h, view=col, how=how, x=round(b[0]), z=round(b[1])))
g = collections.Counter((r["label"], r["w"], r["h"], r["view"]) for r in rows)
print("\nlabelled faces (count, label, w x h in view, view col):")
for (lab, w, h, v), n in sorted(g.items(), key=lambda t: (t[0][3], -t[1])):
    print(f"  {n:>2}  {lab:<28} {w:>5} x {h:<5} view {v}")
json.dump(rows, open(os.path.join(W, "tallboy_2d_labels.json"), "w"), indent=1)
