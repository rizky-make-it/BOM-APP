"""Turn the labelled 2D faces of the tallboy drawing into a STATED part list.
Rules: a face is a part 'section' (thickness x length) or a part 'elevation' (w x h). Group by label + size, dedupe
faces that are the same part seen in two views only when sizes say so. Keep it simple & transparent: print the table
and write tallboy_2d_statement.json for the sheet step."""
import os, json, collections, re
W = os.path.join(os.environ["LOCALAPPDATA"], "Temp")
rows = json.load(open(os.path.join(W, "tallboy_2d_labels.json")))
norm = {"WD-MINDI": "SOLID WOOD MINDI", "PLY-MINDI 1F": "PLYWOOD VENEER MINDI 1F", "PLYWOOD  VENEER MINDI 1F": "PLYWOOD VENEER MINDI 1F"}
for r in rows:
    r["label"] = norm.get(r["label"], r["label"])
# ignore slivers (hatch/joint artefacts): both sides < 8 mm or area tiny
clean = [r for r in rows if not (min(r["w"], r["h"]) < 5 or (r["w"] < 50 and r["h"] < 50 and r["label"] != "SOLID WOOD MINDI"))]
g = collections.OrderedDict()
for r in clean:
    key = (r["label"], max(r["w"], r["h"]), min(r["w"], r["h"]))
    g.setdefault(key, []).append(r)

def guess(label, L, t):
    """Role guess from the drafter's label + the two visible sizes. STATED = size/label; DERIVED = role."""
    if label == "PLYWOOD 6MM" and t <= 9: return "Drawer bottom (ply 6) - seen on edge", "DERIVED"
    if label == "PLYWOOD 12MM" and t == 109 and L in (816, 326): return "Drawer side/back (ply 12), h 109", "DERIVED"
    if label == "PLYWOOD 12MM" and (L, t) == (910, 421): return "Drawer box plan (ply 12) 910 x 421 - top view of box", "DERIVED"
    if label.startswith("PLYWOOD VENEER") and (L, t) == (950, 20): return "Top panel 950 x 20 (section)", "DERIVED"
    if label.startswith("PLYWOOD VENEER") and (L, t) == (745, 20): return "Side panel 745 deep x 20 (section)", "DERIVED"
    if label.startswith("PLYWOOD VENEER") and (L, t) == (450, 20): return "Side panel depth 450 x 20 (section)", "DERIVED"
    if label.startswith("PLYWOOD VENEER") and t == 9: return "Back panel 9 mm (section)", "DERIVED"
    if label == "SOLID WOOD MINDI" and t == 40 and L >= 1040: return "Leg / post 40 x 40, length " + str(L), "DERIVED"
    if label == "SOLID WOOD MINDI" and (L, t) in ((370, 40), (392, 40)): return "Rail 40 mm, length " + str(L), "DERIVED"
    if label == "SOLID WOOD MINDI" and (L, t) == (870, 20): return "Front rail / stretcher 870 x 20", "DERIVED"
    if label == "SOLID WOOD MINDI" and (L, t) == (870, 295): return "Drawer front 870 x 295 (solid wood)", "DERIVED"
    if label == "SOLID WOOD MINDI" and t <= 40 and L <= 40: return "Rail / post section " + f"{L} x {t}", "DERIVED"
    return "?", "UNKNOWN"

print(f"{'n':>2}  {'label (STATED)':<26} {'size seen':<12} role (DERIVED)")
out = []
for (lab, L, t), rs in sorted(g.items(), key=lambda kv: (kv[0][0], -kv[0][1])):
    role, st = guess(lab, L, t)
    print(f"{len(rs):>2}  {lab:<26} {L:>5} x {t:<4}  {role}")
    out.append(dict(label=lab, long=L, short=t, n=len(rs), role=role, status=st, faces=[(r['x'], r['z'], r['w'], r['h']) for r in rs]))
json.dump(out, open(os.path.join(W, "tallboy_2d_statement.json"), "w"), indent=1)
