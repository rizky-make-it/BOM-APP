"""Compare two readings of the same drawing (Gemini model A vs model B, or Gemini vs our spec JSON).
A component is 'agreed' when both sides have the same sorted (l, w, t) and the same quantity.
Everything else is listed for a human to check against the drawing.

  python data/napier/compare_reads.py data/napier/read/A.json data/napier/read/B.json
  python data/napier/compare_reads.py data/napier/read/A.json data/napier/lv433_b41_spec.json
"""
import json, sys
from collections import defaultdict


def load(path):
    d = json.load(open(path, encoding="utf-8"))
    rows = []
    if "components" in d:  # gemini read
        for c in d["components"]:
            if c["group"] == "hardware":
                continue
            rows.append(dict(name=c["name"], dims=tuple(sorted(float(c[k] or 0) for k in ("l", "w", "t"))), qty=int(c["qty"] or 0),
                             mat=c["material"], status="/".join(str(c.get(k, ""))[:3] for k in ("l_status", "w_status", "t_status", "qty_status"))))
    else:  # spec json
        for k in ("solid_parts", "panel_parts"):
            for c in d[k]:
                rows.append(dict(name=c["component"], dims=tuple(sorted(float(c[x]) for x in ("l", "w", "t"))), qty=int(c["qty"]),
                                 mat=c.get("panel_type") or c.get("material"), status="spec"))
    return rows


def compare(a_path, b_path, tol=1.0):
    A, B = load(a_path), load(b_path)
    used = set()
    agreed, only_a = [], []
    for a in A:
        hit = None
        for j, b in enumerate(B):
            if j in used:
                continue
            if all(abs(x - y) <= tol for x, y in zip(a["dims"], b["dims"])) and a["qty"] == b["qty"]:
                hit = j
                break
        if hit is None:
            only_a.append(a)
        else:
            used.add(hit)
            agreed.append((a, B[hit]))
    only_b = [b for j, b in enumerate(B) if j not in used]
    return agreed, only_a, only_b


if __name__ == "__main__":
    agreed, oa, ob = compare(sys.argv[1], sys.argv[2])
    tot = len(agreed) + len(oa) + len(ob)
    print(f"AGREED {len(agreed)}   ONLY-IN-A {len(oa)}   ONLY-IN-B {len(ob)}")
    for a, b in agreed:
        print(f"  = {a['name'][:30]:30} {a['dims']} x{a['qty']}")
    print("ONLY IN A:")
    for a in oa:
        print(f"  A {a['name'][:34]:34} {a['dims']} x{a['qty']} {a['mat']} [{a['status']}]")
    print("ONLY IN B:")
    for b in ob:
        print(f"  B {b['name'][:34]:34} {b['dims']} x{b['qty']} {b['mat']} [{b['status']}]")
