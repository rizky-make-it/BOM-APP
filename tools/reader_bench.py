"""Reader benchmark for the BOM engine: AutoCAD (accoreconsole) vs CADCraft (MCP) as DWG readers/writers.
python tools/reader_bench.py --sections A,B,C,D [--out DIR] [--n 15]
A  synthetic ground truth (known WCS coordinates, 6 drawing planes)        -> who reads geometry CORRECTLY
B  repeated reads of the same files                                        -> stability / determinism
C  every original DWG on this PC, full 3D comparison                       -> robustness + agreement
D  CADCraft opens + saves, AutoCAD reads the result                        -> can CADCraft write a deliverable DWG
Results: OUT/bench_<section>.json (+ printed summary). Never touches the originals."""
import argparse, collections, glob, hashlib, json, os, random, re, shutil, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acad_core as C, acad_read, cc_read

HERE = os.path.dirname(os.path.abspath(__file__))


def vsig(p, r=3):
    p = tuple(p)
    return tuple(round(float(c), r) for c in p[:3])


def close(A, B, tol=0.05):
    if len(A) != len(B): return False
    free = list(B)
    for a in A:
        j = next((j for j, b in enumerate(free) if max(abs(a[k] - b[k]) for k in range(3)) <= tol), None)
        if j is None: return False
        free.pop(j)
    return True


def greedy_match(truth, pool, tol=0.05):
    pool = list(pool); ok = 0
    for t in truth:
        j = next((j for j, g in enumerate(pool) if close(t, g, tol)), None)
        if j is not None: pool.pop(j); ok += 1
    return ok


def cc_raw_polys(dwg):
    m = cc_read.MCP()
    try:
        w = m.call("open", dict(path=dwg)); out = []
        for e in cc_read._all(m, "LWPOLYLINE"):
            g = e["geometry"]; out.append(([(v["p"]["x"], v["p"]["y"]) for v in g.get("vertices", [])], g.get("elevation", 0.0) or 0.0))
        lines = [(cc_read._xyz(e["geometry"]["a"]), cc_read._xyz(e["geometry"]["b"])) for e in cc_read._all(m, "LINE")]
        return out, lines, w.get("warnings", [])
    finally:
        m.close()


# ---------------------------------------------------------------- A
def sec_a(work):
    import ezdxf
    from ezdxf.math import OCS, Vec3
    random.seed(7); doc = ezdxf.new("R2018"); msp = doc.modelspace(); truth = collections.OrderedDict(); ltruth = []
    normals = collections.OrderedDict([("XZ (0,-1,0)", (0, -1, 0)), ("XY (0,0,1)", (0, 0, 1)), ("YZ (1,0,0)", (1, 0, 0)), ("XZ back (0,1,0)", (0, 1, 0)), ("YZ back (-1,0,0)", (-1, 0, 0)), ("tilted (.6,0,.8)", (0.6, 0, 0.8))])
    for pi, (name, n) in enumerate(normals.items()):
        o = OCS(Vec3(n)); truth[name] = []
        for i in range(4):
            w = random.randrange(100, 900, 10); h = random.randrange(100, 900, 10); x0 = 1200 * i; y0 = 1200 * pi + 100; el = 250 * i + 40
            pts = [(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)]
            msp.add_lwpolyline(pts, close=True, dxfattribs={"extrusion": n, "elevation": el})
            truth[name].append([vsig(o.to_wcs(Vec3(x, y, el))) for x, y in pts])
    for i in range(12):
        a = tuple(random.randrange(-3000, 3000, 5) for _ in range(3)); b = tuple(random.randrange(-3000, 3000, 5) for _ in range(3))
        msp.add_line(a, b); ltruth.append([vsig(a), vsig(b)])
    dxf = os.path.join(work, "truth.dxf"); dwg = os.path.join(work, "truth.dwg"); doc.saveas(dxf)
    ok, log, why = C.run(dxf, ["FILEDIA", "0", "CMDECHO", "0", "_.SAVEAS", "2018", dwg.replace("\\", "/")], timeout=120)
    if not os.path.exists(dwg): return dict(error="DXF->DWG failed: " + why)
    a = acad_read.read(dwg); a_polys = [[vsig(p) for p in pl["pts"]] for pl in a["polylines"]]; a_lines = [[vsig(l[0]), vsig(l[1])] for l in a["lines"]]
    raw, cc_lines_raw, warn = cc_raw_polys(dwg)
    variants = {"AutoCAD": a_polys,
                "CADCraft (assume XZ y=-elev)": [[vsig((x, -el, y)) for x, y in v] for v, el in raw],
                "CADCraft (assume XY z=elev)": [[vsig((x, y, el)) for x, y in v] for v, el in raw]}
    res = {k: {} for k in variants}
    for k, pool in variants.items():
        for name, T in truth.items(): res[k][name] = [greedy_match(T, pool), len(T)]
    res["AutoCAD"]["3D lines"] = [greedy_match(ltruth, a_lines), len(ltruth)]
    cc_lines = [[vsig(x), vsig(y)] for x, y in cc_lines_raw]
    for k in list(variants)[1:]: res[k]["3D lines"] = [greedy_match(ltruth, cc_lines), len(ltruth)]
    # does CADCraft report anything when it cannot know the plane?
    return dict(result=res, cadcraft_warnings=warn, acad_polys=len(a_polys), cc_polys=len(raw))


# ---------------------------------------------------------------- B
def sec_b(files, n):
    out = {}
    for f in files:
        if not os.path.exists(f): out[os.path.basename(f) + " | SKIPPED"] = dict(error="file not found: " + f); continue
        for name, fn in (("AutoCAD", acad_read.read), ("CADCraft", cc_read.read_compat)):
            ok = 0; fails = []; ts = []; sigs = set()
            for i in range(n):
                t0 = time.time()
                try:
                    d = fn(f); ts.append(time.time() - t0); ok += 1
                    sigs.add((len(d["lines"]), len(d["polylines"]), len(d["dims"]), round(sum(l[0][0] + l[1][2] for l in d["lines"]), 3)))
                except Exception as e:
                    fails.append(str(e)[-90:])
            out[f"{os.path.basename(f)} | {name}"] = dict(ok=ok, n=n, mean_s=round(sum(ts) / max(len(ts), 1), 2), max_s=round(max(ts or [0]), 2), distinct_outputs=len(sigs), fails=fails[:2])
    return out


# ---------------------------------------------------------------- C
def corpus():
    roots = ["C:/Users/Admin/Desktop/LIVINGIKON", "C:/Users/Admin/Downloads", "C:/Users/Admin/Documents", "C:/Users/Admin/AppData/Local/hermes/cache/documents",
             "C:/Users/Admin/AppData/Local/hermes/cache/scratch/sky/std"]
    bad = ("Hasil-DWG", "components", "numbering", "tagged", "_labels", "cmp_", "truth", "skyline.dwg", "l11.dwg", "Hermes Vault")
    seen = {}; 
    for r in roots:
        for f in glob.glob(r + "/**/*.dwg", recursive=True):
            f = f.replace("\\", "/")
            if any(b in f for b in bad) or os.path.getsize(f) > 60_000_000: continue
            h = hashlib.md5(open(f, "rb").read()).hexdigest()
            seen.setdefault(h, f)
    return sorted(seen.values())


def vkey(p, step=0.01):
    """grid key whose cell BOUNDARY sits at 0.25 of a cell: AutoCAD dumps 4 decimals (rtos), CADCraft full precision; drafter values often sit exactly on x.xx5, which a plain round() would split."""
    import math
    return tuple(math.floor(float(c) / step + 0.75) for c in tuple(p)[:3])


def sig_set(d):
    lines = collections.Counter(tuple(sorted((vkey(l[0]), vkey(l[1])))) for l in d["lines"])
    polys = collections.Counter(tuple(sorted(vkey(p, 0.1) for p in pl["pts"])) for pl in d["polylines"] if len(pl["pts"]) > 1)
    dims = collections.Counter(round(x["value"] or 0, 1) for x in d["dims"])
    ldr = collections.Counter(" ".join(re.sub(r"\\P", " ", x["text"]).split()).upper() for x in d["leaders"] if x.get("text"))
    return dict(lines=lines, polys=polys, dims=dims, leaders=ldr)


def sec_c(files):
    rows = []
    for f in files:
        r = dict(file=os.path.basename(f), kb=os.path.getsize(f) // 1024)
        a = c = None
        try: a = acad_read.read(f); r["acad_s"] = a["_seconds"]
        except Exception as e: r["acad_err"] = str(e)[-100:]
        try: c = cc_read.read_compat(f); r["cc_s"] = c["_seconds"]
        except Exception as e: r["cc_err"] = str(e)[-100:]
        if a and c:
            A, B = sig_set(a), sig_set(c)
            for k in A:
                inter = sum((A[k] & B[k]).values()); r[k] = [inter, sum(A[k].values()), sum(B[k].values())]   # same, acad total, cc total
        rows.append(r); print(json.dumps(r, ensure_ascii=False), flush=True)
    return rows


# ---------------------------------------------------------------- D
def count_solids(dwg, work, tag):
    dxf = os.path.join(work, f"{tag}.dxf")
    if os.path.exists(dxf): os.remove(dxf)
    C.run(dwg, ["FILEDIA", "0", "CMDECHO", "0", "_.SAVEAS", "DXF", "16", dxf.replace("\\", "/")], timeout=150)
    if not os.path.exists(dxf): return None
    return len(re.findall(r"\n\s*3DSOLID\s*\r?\n", open(dxf, encoding="latin-1").read()))


def sec_d(files, work):
    rows = []
    for i, f in enumerate(files):
        r = dict(file=os.path.basename(f)); saved = os.path.join(work, f"rt_{i}.dwg")
        try:
            m = cc_read.MCP()
            try:
                w = m.call("open", dict(path=f)); r["cc_open_warnings"] = w.get("warnings", []); m.call("save", dict(path=saved.replace("\\", "/")))
            finally: m.close()
        except Exception as e:
            r["cc_save_err"] = str(e)[-100:]; rows.append(r); continue
        r["saved_kb"] = os.path.getsize(saved) // 1024 if os.path.exists(saved) else None
        try:
            a0 = acad_read.read(f); a1 = acad_read.read(saved)
        except Exception as e:
            r["acad_cannot_read_saved"] = str(e)[-120:]; rows.append(r); continue
        A, B = sig_set(a0), sig_set(a1)
        for k in A: r[k] = [sum((A[k] & B[k]).values()), sum(A[k].values()), sum(B[k].values())]
        vp = lambda d: sum(len(l["viewports"]) for l in d["layouts"])
        r["layouts"] = [len(a0["layouts"]), len(a1["layouts"])]; r["viewports"] = [vp(a0), vp(a1)]
        r["solids"] = [count_solids(f, work, f"o{i}"), count_solids(saved, work, f"s{i}")]
        rows.append(r); print(json.dumps(r, ensure_ascii=False), flush=True)
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--sections", default="A,B,C,D"); ap.add_argument("--out", default="C:/Users/Admin/AppData/Local/hermes/cache/scratch/bench"); ap.add_argument("--n", type=int, default=15)
    ap.add_argument("--files", nargs="*"); a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    S = a.sections.split(",")
    big = a.files or ["C:/Users/Admin/AppData/Local/hermes/cache/documents/doc_279be0992feb_lexi 3.dwg", "C:/Users/Admin/Desktop/LIVINGIKON/SIENNA COLLECTION/DWG/LV446-L11 1 DRAWER & SHELF TBL.dwg"]
    if "A" in S: r = sec_a(a.out); json.dump(r, open(os.path.join(a.out, "bench_A.json"), "w"), indent=1); print("== A"); print(json.dumps(r, indent=1))
    if "B" in S: r = sec_b(big, a.n); json.dump(r, open(os.path.join(a.out, "bench_B.json"), "w"), indent=1); print("== B"); print(json.dumps(r, indent=1))
    if "C" in S:
        fs = corpus(); print("== C", len(fs), "file unik"); r = sec_c(fs); json.dump(r, open(os.path.join(a.out, "bench_C.json"), "w"), indent=1)
    if "D" in S:
        fs = a.files or big + ["C:/Users/Admin/AppData/Local/hermes/cache/scratch/sky/skyline.dwg", "C:/Users/Admin/Desktop/LIVINGIKON/SIENNA COLLECTION/DWG/LV463-B01 QUEEN BED.dwg"]
        print("== D"); r = sec_d(fs, a.out); json.dump(r, open(os.path.join(a.out, "bench_D.json"), "w"), indent=1)
