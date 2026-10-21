"""Headless test of BOMTAG v2 auto-suggest (bt-suggest) on Skyline: click points on known components -> does the suggestion follow the drafter's label?
python tools/test_bomtag_suggest.py"""
import os, shutil, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acad_core as C

R = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
W = os.path.join(os.environ["LOCALAPPDATA"], "hermes", "cache", "scratch", "bomtag_test"); os.makedirs(W, exist_ok=True)
LSP = os.path.join(R, "tools", "lisp", "bomtag.lsp").replace("\\", "/")
src = os.path.join(os.environ["LOCALAPPDATA"], "hermes", "cache", "scratch", "sky", "skyline.dwg"); dwg = os.path.join(W, "sugg.dwg"); shutil.copy(src, dwg)
# (label of the case, WCS click point, measured long, measured short)
cases = [
    ("rak PERMANENT (potongan depan, ujung panah drafter)", (-22116, -6135, 0), 952, 24),
    ("rak ADJUSTABLE #1", (-22057, -6702, 0), 952, 24),
    ("rak ADJUSTABLE #2", (-22057, -7268, 0), 952, 24),
    ("pintu kayu SOLID WOOD (tampak depan)", (-16990, -1754, 0), 2110, 43),
    ("panel PLYWOOD pintu", (-16638, -2112, 0), 449, 158),
    ("klik di tempat kosong tanpa label", (-20000, -500, 0), 100, 50),
]
L = ["FILEDIA", "0", "CMDECHO", "0", f'(load "{LSP}")']
for i, (n, p, l, w) in enumerate(cases):
    L.append(f'(princ (strcat "\\nSUG{i}=" (vl-princ-to-string (bt-suggest (list {p[0]} {p[1]} {p[2]}) {l}.0 {w}.0))))')
ok, log, why = C.run(dwg, L, timeout=150)
print("ran:", ok, why)
got = {}
for l in log.splitlines():
    m = re.search(r"SUG(\d)=(.*)", l)
    if m and "princ" not in l: got.setdefault(int(m.group(1)), m.group(2).strip().rstrip('"').replace("\\n", ""))
for i, (n, *_r) in enumerate(cases): print(f"{n:55} -> {got.get(i, '(tidak ada keluaran)')}")
