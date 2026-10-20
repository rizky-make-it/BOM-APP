"""DWG -> parts reader (no PDF needed).

DWG --(LibreDWG dwg2dxf)--> DXF --(ezdxf)--> per-view line sets --(shapely polygonize)--> closed faces = parts.
Every number is tagged STATED (printed as a dimension / leader label) or DERIVED (measured from geometry).

Usage:  python tools/dwg_reader.py <file.dwg> [--json out.json] [--png out.png]
LibreDWG is downloaded once into  %LOCALAPPDATA%/Temp/libredwg-0.14  (not installed into the system).
"""
import argparse
import collections
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

LIB_URL = "https://github.com/LibreDWG/libredwg/releases/download/0.14/libredwg-0.14-win64.zip"
LIB_DIR = os.path.join(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()), "Temp", "libredwg-0.14")


def ensure_libredwg():
    exe = os.path.join(LIB_DIR, "dwg2dxf.exe")
    if os.path.exists(exe):
        return exe
    os.makedirs(LIB_DIR, exist_ok=True)
    z = os.path.join(LIB_DIR, "lib.zip")
    urllib.request.urlretrieve(LIB_URL, z)
    zipfile.ZipFile(z).extractall(LIB_DIR)
    os.remove(z)
    return exe


def dwg_to_dxf(dwg, out_dxf):
    exe = ensure_libredwg()
    subprocess.run([exe, "-y", "-o", out_dxf, dwg], capture_output=True, text=True)
    if not os.path.exists(out_dxf):
        raise RuntimeError("dwg2dxf gagal: " + dwg)


def _clean(t):
    t = t.replace(chr(92) + "P", " ").replace(chr(92) + "L", "").replace(chr(92) + "l", "")
    t = re.sub(r"\[ACFHQTW][^;]*;", "", t)   # formatting codes that end with ';'
    return re.sub(r"[{}]", "", t).strip()


def read(dxf_path):
    import ezdxf
    d = ezdxf.readfile(dxf_path)
    m = d.modelspace()
    out = {"dxf_version": d.dxfversion, "labels": [], "dimensions": [], "views": []}
    for e in m.query("MULTILEADER"):
        try:
            out["labels"].append(_clean(e.context.mtext.default_content))
        except Exception:
            pass
    for e in m:
        if e.dxftype() in ("MTEXT", "TEXT"):
            out["labels"].append(_clean(e.text if e.dxftype() == "MTEXT" else e.dxf.text))
    dims = collections.Counter()
    for e in m.query("DIMENSION"):
        try:
            p1, p2 = e.dxf.defpoint2, e.dxf.defpoint3
            v = round(math.dist((p1.x, p1.y, p1.z), (p2.x, p2.y, p2.z)))
            if v > 0:
                dims[v] += 1
        except Exception:
            pass
    out["dimensions"] = sorted(dims.items(), reverse=True)  # (mm, how many times measured)

    from shapely.geometry import LineString
    from shapely.ops import polygonize, unary_union
    for i, ins in enumerate(m.query("INSERT")):
        segs = []
        for v in ins.virtual_entities():
            if v.dxftype() == "LINE":
                a, b = v.dxf.start, v.dxf.end
                segs.append(((a.x, a.y, a.z), (b.x, b.y, b.z)))
        if not segs:
            continue
        # choose the 2 axes with variation (flat view); the third is constant
        rng = [max(p[k] for s in segs for p in s) - min(p[k] for s in segs for p in s) for k in range(3)]
        ax = sorted(sorted(range(3), key=lambda k: -rng[k])[:2])
        names = "XYZ"
        lines = [LineString([(s[0][ax[0]], s[0][ax[1]]), (s[1][ax[0]], s[1][ax[1]])]) for s in segs
                 if (abs(s[0][ax[0]] - s[1][ax[0]]) + abs(s[0][ax[1]] - s[1][ax[1]])) > 1e-6]
        x0 = min(l.bounds[0] for l in lines)
        y0 = min(l.bounds[1] for l in lines)
        faces = []
        for poly in polygonize(unary_union(lines)):
            minx, miny, maxx, maxy = poly.bounds
            w, h = maxx - minx, maxy - miny
            rect = abs(poly.area - w * h) < 0.02 * max(w * h, 1)
            faces.append({"x": round(minx - x0, 1), "y": round(miny - y0, 1), "w": round(w, 1), "h": round(h, 1),
                          "rect": bool(rect), "area": round(poly.area, 1)})
        faces.sort(key=lambda f: (f["x"], f["y"]))
        out["views"].append({"index": i + 1, "block": ins.dxf.name, "axes": names[ax[0]] + names[ax[1]], "segments": len(segs),
                             "width": round(max(l.bounds[2] for l in lines) - x0, 1), "height": round(max(l.bounds[3] for l in lines) - y0, 1),
                             "faces": faces})
    return out


def assemble(o, rail_h=20.0):
    """Turn the elevation faces into an assembly: posts, recessed boards (board + gap = rail height), levels.
    A board sitting inside a rail frame appears as two stacked faces (board on top, gap below) whose heights add up to the rail."""
    dims = {v for v, _ in o["dimensions"]}
    out = {"boards": [], "posts": [], "rails_seen": []}
    front = max(o["views"], key=lambda v: len(v["faces"]))
    F = front["faces"]
    for top in F:
        if top["w"] < 100 or top["h"] >= rail_h:
            continue
        for gap in F:
            if gap is top or abs(gap["x"] - top["x"]) > 0.5 or abs(gap["w"] - top["w"]) > 0.5:
                continue
            if abs(gap["y"] + gap["h"] - top["y"]) < 0.5 and abs(gap["h"] + top["h"] - rail_h) < 0.5:
                out["boards"].append({"thickness": top["h"], "recess_below": gap["h"], "width": top["w"], "x_from": top["x"],
                                      "x_to": top["x"] + top["w"], "top_level_z": top["y"] + top["h"],
                                      "width_status": "STATED" if round(top["w"]) in dims else "DERIVED",
                                      "thickness_status": "DERIVED (flush-top board inside a 20 mm rail)"})
    cols = collections.defaultdict(list)
    for f in F:
        if abs(f["w"] - rail_h) < 0.5:
            cols[f["x"]].append(f)
    for x, fs in sorted(cols.items()):
        z0 = min(f["y"] for f in fs); z1 = max(f["y"] + f["h"] for f in fs)
        out["posts"].append({"x": x, "z_from": z0, "z_to": z1, "length": z1 - z0, "section": f"{rail_h:g}x{rail_h:g}",
                             "length_status": "STATED" if round(z1 - z0) in dims else "DERIVED"})
    out["boards"].sort(key=lambda b: -b["top_level_z"])
    return out


def compare_with_spec(asm, spec_json):
    d = json.load(open(spec_json, encoding="utf-8"))
    rows = []
    want_boards = sorted(((p["w"] if p["l"] >= p["w"] else p["l"], p["t"]) for p in d["panel_parts"] if p["t"] < 20), reverse=True)
    got = sorted(((b["width"], b["thickness"]) for b in asm["boards"]), reverse=True)
    rows.append(("papan (lebar, tebal)", "spec", sorted({(round(a), round(b)) for a, b in want_boards})))
    rows.append(("papan (lebar, tebal)", "DWG", sorted({(round(a), round(b)) for a, b in got})))
    posts = sorted({p["length"] for p in asm["posts"]})
    rows.append(("tiang tertinggi (mm)", "DWG", posts))
    rows.append(("tiang di spec (mm)", "spec", sorted({p["l"] for p in d["solid_parts"] if "post" in p["component"].lower()})))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dwg")
    ap.add_argument("--json")
    ap.add_argument("--spec", help="spec JSON to compare against")
    a = ap.parse_args()
    t = tempfile.mkdtemp()
    dxf = os.path.join(t, "x.dxf")
    dwg_to_dxf(a.dwg, dxf)
    r = read(dxf)
    asm = assemble(r)
    r["assembly"] = asm
    if a.json:
        json.dump(r, open(a.json, "w", encoding="utf-8"), indent=1)
    print("labels:", r["labels"])
    print("dimensions (mm, kali):", r["dimensions"])
    print("views:", [(v["index"], v["axes"], len(v["faces"])) for v in r["views"]])
    print("PAPAN (duduk di dalam rangka, rata atas):")
    for b in asm["boards"]:
        print(f"  tebal {b['thickness']:g} (celah bawah {b['recess_below']:g}) lebar {b['width']:g} x {b['x_from']:g}..{b['x_to']:g} permukaan atas z={b['top_level_z']:g} | lebar {b['width_status']}")
    print("TIANG / KOLOM 20x20:")
    for p in asm["posts"]:
        print(f"  x={p['x']:g}  z {p['z_from']:g}..{p['z_to']:g}  panjang {p['length']:g} ({p['length_status']})")
    if a.spec:
        print("PERBANDINGAN dengan spec:")
        for k, who, v in compare_with_spec(asm, a.spec):
            print(f"  {k:<24} {who:<5} {v}")
    shutil.rmtree(t, ignore_errors=True)


if __name__ == "__main__":
    main()
