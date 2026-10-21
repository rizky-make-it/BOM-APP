"""Headless test of the visible-progress feature: tag 3 of the 4 labelled shelves on Skyline, run bt-show, save, then inspect the drawing independently.
python tools/test_bomtag_show.py"""
import json, os, re, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acad_core as C, cc_read

R = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
W = os.path.join(os.environ["LOCALAPPDATA"], "hermes", "cache", "scratch", "bomtag_test"); os.makedirs(W, exist_ok=True)
LSP = os.path.join(R, "tools", "lisp", "bomtag.lsp").replace("\\", "/")
src = os.path.join(os.environ["LOCALAPPDATA"], "hermes", "cache", "scratch", "sky", "skyline.dwg"); dwg = os.path.join(W, "show.dwg"); shutil.copy(src, dwg)
out = os.path.join(W, "show_out.dwg").replace("\\", "/")
if os.path.exists(out.replace("/", os.sep)): os.remove(out.replace("/", os.sep))
# the three shelf bands drawn by the drafter (x 31..512 of the front section, 24 mm thick): box = (xmin ymin xmax ymax z) in WCS
X0 = -22810.5
bands = [(-6159.0, -6135.0), (-6726.0, -6702.0), (-7292.0, -7268.0)]
L = ["FILEDIA", "0", "CMDECHO", "0", f'(load "{LSP}")', "_.UCS", "_W"]
for i, (y0, y1) in enumerate(bands, 1):
    code, t = ("B-18-1X", 18) if i < 3 else ("B-12-1X", 12)           # 3rd: 24 < 3 x 12 is false -> STATED; make it CHECK with thickness 9
    if i == 3: code, t = "B-18-1X", 18
    L.append(f'(setq *bt-box* (list {X0 + 24} {y0} {X0 + 976} {y1} 0.0))')
    L.append(f'(princ (strcat "\\nTAG{i}=" (bt-add {i} "{"308" if i == 1 else "309"}" 952.0 {481.0 if i == 1 else 24.0} {t}.0 {1 if i == 1 else 2} "{code}" (list {X0 + 400} {(y0 + y1) / 2} 0.0) (list {X0 + 400} {y0 - 140} 0.0) 40.0)))')
L.append('(princ (strcat "\\nSHOW=" (vl-princ-to-string (bt-show))))')
L += ["_.SAVEAS", "2018", out]
ok, log, why = C.run(dwg, L, timeout=300)
print("AutoCAD ran:", ok, why)
for l in log.splitlines():
    if re.search(r"TAG\d=|SHOW=|BOMSHOW:", l) and "princ" not in l and l.strip().startswith(("TAG", "SHOW", "BOMSHOW")): print("  ", l.strip()[:160])
m = cc_read.MCP()
try:
    m.call("open", dict(path=out))
    cnt = {}
    for typ in ("Solid", "Circle", "Text", "Line"):
        try: ents = cc_read._all(m, typ)
        except Exception: ents = []
        for e in ents: cnt[(typ, e["layer"])] = cnt.get((typ, e["layer"]), 0) + 1
    print("independent reader (CADCraft) counts by (type, layer):", {f"{k[0]}@{k[1]}": v for k, v in sorted(cnt.items()) if k[1].startswith("BOM-")})
finally:
    m.close()
