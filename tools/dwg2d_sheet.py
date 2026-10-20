"""2D sheet: add BOM balloons + part table to the drafter's OWN tallboy drawing (copy of lexi 3), in model space
(XZ plane, same as the drafter's views), then plot the drafter's layout '4 dw tallboy' from AutoCAD headless.
Balloon numbers = rows of tallboy_2d_statement.json (one number per label+size)."""
import os, sys, json, shutil, tempfile, math, datetime
sys.path.insert(0, r"C:/Users/Admin/Desktop/BOM-APP/tools")
import acad_core as C

W = os.path.join(os.environ["LOCALAPPDATA"], "Temp")
OUT = r"C:/Users/Admin/Documents/Hasil-DWG/2d"; os.makedirs(OUT, exist_ok=True)
st = json.load(open(os.path.join(W, "tallboy_2d_statement.json")))
stamp = datetime.datetime.now().strftime("%H%M%S")
out_dwg = os.path.join(OUT, "tallboy_2d_bom.dwg"); out_pdf = os.path.join(OUT, "tallboy_2d_bom.pdf")
for f in (out_dwg, out_pdf):
    if os.path.exists(f):
        try: os.remove(f)
        except OSError:
            out_dwg = os.path.join(OUT, f"tallboy_2d_bom_{stamp}.dwg"); out_pdf = os.path.join(OUT, f"tallboy_2d_bom_{stamp}.pdf"); break
w = tempfile.mkdtemp(prefix="bom2d_"); src = os.path.join(w, "src.dwg"); shutil.copy(os.path.join(W, "lexi3.dwg"), src)

# Drawing is in the XZ plane: entities get extrusion (0,-1,0) via OCS. Simplest: entmake with 210 = (0 -1 0) and OCS coords.
# For extrusion (0,-1,0) the OCS: Ax = (0,0,1)?? Avoid OCS math: use 3D-capable entities instead:
#  LINE with 3D points (world), CIRCLE needs OCS -> use a 3D POLYLINE circle approx? Simpler: TEXT/CIRCLE with 210 (0 -1 0):
#  world (x, y, z) -> OCS for N=(0,-1,0): Ax = Wy x N = (0,1,0)x(0,-1,0) = (0,0,0) -> degenerate, so Ax = Wz x N = (0,0,1)x(0,-1,0) = (1,0,0).
#  Ay = N x Ax = (0,-1,0)x(1,0,0) = (0,0,1). So OCS(x', y') = (world x, world z), elevation = -world y... with y = 0 plane -> z' = 0.
def ocs_pt(x, z, y=0.0):
    return f"(list {x:.2f} {z:.2f} {-y:.2f})"

L = ["FILEDIA", "0", "CMDECHO", "0", "EXPERT", "5",
     "_.-LAYER", "_M", "BOM-BALLOON", "_C", "1", "BOM-BALLOON", "", "_.-LAYER", "_M", "BOM-TABLE", "_C", "7", "BOM-TABLE", ""]
def circle(x, z, r, layer="BOM-BALLOON"):
    return f'(entmake (list (cons 0 "CIRCLE") (cons 8 "{layer}") (cons 10 {ocs_pt(x, z)}) (cons 40 {r}) (cons 210 (list 0.0 -1.0 0.0))))'
def text(x, z, s, h, layer="BOM-TABLE", mc=False):
    s = str(s).replace('"', "'")
    j = f' (cons 72 1) (cons 73 2) (cons 11 {ocs_pt(x, z)})' if mc else ""
    return f'(entmake (list (cons 0 "TEXT") (cons 8 "{layer}") (cons 10 {ocs_pt(x, z)}) (cons 40 {h}) (cons 1 "{s}"){j} (cons 210 (list 0.0 -1.0 0.0))))'
def line(x1, z1, x2, z2, layer="BOM-BALLOON"):
    return f'(entmake (list (cons 0 "LINE") (cons 8 "{layer}") (cons 10 (list {x1:.2f} 0.0 {z1:.2f})) (cons 11 (list {x2:.2f} 0.0 {z2:.2f}))))'

R_B = 18.0; H_T = 14.0           # balloon radius / text height in drawing units (mm, views are 1:1 in model)
n_bal = 0
# Balloon placement without stacking: anchors sorted by height; balloons on two vertical rails (left of the section
# column x=25560 and right x=26690), each rail a ladder with >= 2.2*R_B spacing, nearest rail by anchor x.
anchors = []
for i, row in enumerate(st, 1):
    x, z, fw, fh = row["faces"][0]
    anchors.append((i, x + fw / 2, z + fh / 2))
COL_X0, COL_X1 = 25645, 26600
RAIL = {"L": COL_X0 - 175, "R": COL_X1 + 175}
STEP = R_B * 2.4
for side in ("L", "R"):
    pick = [a_ for a_ in anchors if (a_[1] < (COL_X0 + COL_X1) / 2) == (side == "L")]
    pick.sort(key=lambda a_: a_[2])
    placed = []
    for (i, cx, cz) in pick:
        bz = cz
        if placed and bz < placed[-1] + STEP:
            bz = placed[-1] + STEP
        placed.append(bz)
        bx = RAIL[side]
        d = math.hypot(bx - cx, bz - cz) or 1
        ex, ez = bx - (bx - cx) / d * R_B, bz - (bz - cz) / d * R_B
        L += [line(cx, cz, ex, ez), circle(cx, cz, 3), circle(bx, bz, R_B), text(bx, bz, i, H_T, "BOM-BALLOON", True)]
        n_bal += 1
# part table to the right of the drawing (x > 26700), top at z 4100
tx, tz = 26900, 4250; rh = 50; cw = [50, 290, 150, 50, 290]; tw = sum(cw)
hdr = ["NO", "LABEL (gambar)", "UKURAN (mm)", "QTY", "PERAN (tebakan, perlu cek)"]
rows_n = len(st) + 2
def tl(x1, z1, x2, z2): return line(x1, z1, x2, z2, "BOM-TABLE")
L += [tl(tx, tz, tx + tw, tz), tl(tx + tw, tz, tx + tw, tz - rh * rows_n), tl(tx + tw, tz - rh * rows_n, tx, tz - rh * rows_n), tl(tx, tz - rh * rows_n, tx, tz)]
L += [tl(tx, tz - rh * k, tx + tw, tz - rh * k) for k in range(1, rows_n)]
xx = tx
for c in cw[:-1]:
    xx += c; L += [tl(xx, tz - rh, xx, tz - rh * rows_n)]
L += [text(tx + 8, tz - rh + 14, "PART LIST (label + ukuran dari gambar 2D)", 16)]
xx = tx
for c, h in zip(cw, hdr):
    L += [text(xx + 8, tz - 2 * rh + 14, h, 13)]; xx += c
for i, row in enumerate(st, 1):
    vals = [str(i), row["label"][:22], f"{row['long']} x {row['short']}", str(row["n"]), row["role"][:26]]
    xx = tx
    for c, v in zip(cw, vals):
        L += [text(xx + 8, tz - (i + 2) * rh + 14, v, 13)]; xx += c
L += [text(tx, tz - (rows_n + 1) * rh + 10, "UKURAN = bidang berlabel di potongan (STATED).", 13), text(tx, tz - (rows_n + 1) * rh - 12, "PERAN = tebakan (DERIVED), wajib dicek drafter.", 13)]
# plot MODEL space, front view (UCS X 90 + PLAN), window around the tallboy drawing + table, fit to A3 landscape
x1, z1, x2, z2 = 25330, 100, 27770, 4420   # tallboy sections + table, stops before the next drawing
L += ["_.TILEMODE", "1", "_.VPOINT", "0,-1,0", "_.UCS", "_V",
      "_.-PLOT", "_Y", "Model", "DWG To PDF.pc3", C.PAPER_A3, "_M", "_P", "_N", "_W", f"{x1},{z1}", f"{x2},{z2}", "_F", "_C",
      "_Y", ".", "_Y", "_A", out_pdf.replace(chr(92), "/"), "_N", "_Y",
      "_.UCS", "_W", "_.SAVEAS", "2018", out_dwg.replace(chr(92), "/")]
ok, log, why = C.run(src, L, timeout=240, workdir=w)
good, det = C.pdf_has_content(out_pdf)
print(f"run: {why} | balloons {n_bal} | rows {len(st)}"); print("PDF:", good, det, out_pdf); print("DWG:", os.path.exists(out_dwg))
open(os.path.join(OUT, "tallboy_2d_bom.log"), "w", encoding="utf-8").write(log)
if not ok or not good:
    print("\n".join([l for l in log.splitlines() if l.strip()][-15:]))
