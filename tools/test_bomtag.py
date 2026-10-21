"""Headless test of bomtag.lsp core: write tags into a COPY of a DWG with AutoCAD (accoreconsole), export JSON, run BOMCHECK, then read the saved DWG back with an independent reader.
python tools/test_bomtag.py"""
import json, os, shutil, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acad_core as C

R = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
W = os.path.join(os.environ.get("LOCALAPPDATA", "."), "hermes", "cache", "scratch", "bomtag_test"); os.makedirs(W, exist_ok=True)
LSP = os.path.join(R, "tools", "lisp", "bomtag.lsp").replace("\\", "/")


def run(name, src, ucs_cmds, calls, expect_n):
    dwg = os.path.join(W, name + ".dwg"); shutil.copy(src, dwg)
    out_dwg = os.path.join(W, name + "_tagged.dwg").replace("\\", "/"); js = os.path.join(W, name + ".json").replace("\\", "/")
    for f in (out_dwg, js):
        if os.path.exists(f): os.remove(f)
    L = ["FILEDIA", "0", "CMDECHO", "0", f'(load "{LSP}")'] + ucs_cmds + calls + [f'(princ (strcat "\\nEXPORTED=" (itoa (bt-export "{js}"))))', '(princ (strcat "\\nCHECKS=" (itoa (bt-check))))',
         "_.UCS", "_W", "_.SAVEAS", "2018", out_dwg]
    ok, log, why = C.run(dwg, L, timeout=180)
    lines = [l.strip() for l in log.splitlines()]
    res = dict(case=name, ran=ok, why=why, log_markers=[l for l in lines if l.startswith(("EXPORTED", "CHECKS", "BOMCHECK", "- ", "ADD_"))][:14])
    if os.path.exists(js.replace("/", os.sep)):
        res["json"] = json.load(open(js, encoding="utf-8"))["tags"]
    res["saved_dwg"] = os.path.exists(out_dwg.replace("/", os.sep))
    return res, out_dwg


def adds(items):
    out = []
    for i, (row, no, l, w, t, q, code, tip, box, h) in enumerate(items):
        out.append(f'(princ (strcat "\\nADD_{i}=" (bt-add {row} "{no}" {l} {w} {t} {q} "{code}" (list {tip[0]} {tip[1]} {tip[2] if len(tip) > 2 else 0.0}) (list {box[0]} {box[1]} {box[2] if len(box) > 2 else 0.0}) {h})))')
    return out


if __name__ == "__main__":
    S = "C:/Users/Admin/Desktop/LIVINGIKON/SIENNA COLLECTION/DWG/"
    sky = os.path.join(os.environ["LOCALAPPDATA"], "hermes", "cache", "scratch", "sky", "skyline.dwg")
    report = {}
    # XY plane (Skyline): UCS = World; tags in plan coordinates
    xy_items = [(1, "502", 2110, 43, 23, 4, "A", (-17436, -2700), (-17640, -2700), 40), (2, "503", 445, 43, 23, 4, "A", (-17230, -3797), (-17230, -3960), 40),
                (3, "601", 1000, 521, 18, 1, "B-18-1X", (-22250, -1679), (-22300, -1850), 40), (4, "999", 100, 50, 18, 1, "A", (-22250, -2087), (-22300, -2250), 40),
                (5, "301", 2090, 481, 18, 2, "ZZZ-9", (-22250, -2654), (-22300, -2820), 40)]
    report["XY Skyline"], dwg_xy = run("sky_xy", sky, ["_.UCS", "_W"], adds(xy_items), len(xy_items))
    # XZ plane (L11): UCS rotated to the front view (X axis = world X, Y axis = world Z): UCS _X 90
    xz_items = [(1, "101", 550, 20, 20, 4, "MT-20x20", (-4000, -1200), (-3900, -1250), 15), (2, "601", 860, 410, 18, 1, "B-18-1X", (-3500, -1100), (-3500, -1000), 15)]
    report["XZ L11"], dwg_xz = run("l11_xz", S + "LV446-L11 1 DRAWER & SHELF TBL.dwg", ["_.UCS", "_W", "_.UCS", "_X", "90"], adds(xz_items), len(xz_items))
    print(json.dumps(report, indent=1, ensure_ascii=False)[:6000])
    json.dump(dict(xy=dwg_xy, xz=dwg_xz), open(os.path.join(W, "paths.json"), "w"))
