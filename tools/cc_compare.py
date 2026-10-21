"""Measure CADCraft(MCP) vs AutoCAD(accoreconsole) readers on the same DWGs. python tools/cc_compare.py <dwg>... [--out json]"""
import collections, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acad_read, cc_read

def key_line(a, b, r=1):
    p, q = tuple(round(v, r) for v in a[:2]), tuple(round(v, r) for v in b[:2]); return (p, q) if p <= q else (q, p)
def key_poly(pts, r=1):
    t = tuple(tuple(round(v, r) for v in p[:2]) for p in pts); return min(t, t[::-1])
def cmp_sets(A, C):
    A, C = collections.Counter(A), collections.Counter(C); inter = sum((A & C).values())
    return dict(acad=sum(A.values()), cc=sum(C.values()), same=inter, only_acad=sum(A.values()) - inter, only_cc=sum(C.values()) - inter)

def _n(t): return " ".join(t.replace(chr(92) + "P", " ").split()).upper()

def compare(dwg):
    r = dict(file=os.path.basename(dwg))
    try: a = acad_read.read(dwg); r["acad_s"] = a["_seconds"]
    except Exception as e: a = None; r["acad_err"] = str(e)[-120:]
    try: c = cc_read.read(dwg); r["cc_s"] = c["_seconds"]; r["cc_warn"] = c["warnings"]
    except Exception as e: c = None; r["cc_err"] = str(e)[-120:]
    if a and c:
        r["lines"] = cmp_sets([key_line(l[0], l[1]) for l in a["lines"]], [key_line(l[0], l[1]) for l in c["lines"]])
        r["polys"] = cmp_sets([key_poly(p["pts"]) for p in a["polylines"] if len(p["pts"]) > 1], [key_poly(p["pts"]) for p in c["polylines"] if len(p["pts"]) > 1])
        r["dims"] = cmp_sets([round(d["value"] or 0, 1) for d in a["dims"]], [round(d["value"] or 0, 1) for d in c["dims"]])
        la = a["leaders"] + a.get("model_leaders", []) + a.get("paper_leaders", [])
        r["leader_text"] = cmp_sets([_n(x["text"]) for x in la if x.get("text")], [_n(x["text"]) for x in c["leaders"] if x["text"]])
        # tip position agreement for leaders with identical text
        byt = collections.defaultdict(list)
        for x in c["leaders"]:
            if x.get("tip"): byt[_n(x["text"])].append(x["tip"])
        ok = tot = 0
        for x in a["leaders"]:
            t = _n(x["text"]); tot += 1
            if any(abs(x["tip"][0] - q[0]) < 1 and abs(x["tip"][1] - q[1]) < 1 and abs(x["tip"][2] - q[2]) < 1 for q in byt.get(t, [])): ok += 1
        r["tips"] = dict(acad=tot, tip_match=ok)
    return r

if __name__ == "__main__":
    files = [f for f in sys.argv[1:] if f.lower().endswith(".dwg")]; res = []
    for f in files:
        x = compare(f); res.append(x); print(json.dumps(x, ensure_ascii=False), flush=True)
    if "--out" in sys.argv: json.dump(res, open(sys.argv[sys.argv.index("--out") + 1], "w"), indent=1, ensure_ascii=False)
