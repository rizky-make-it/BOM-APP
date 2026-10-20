"""Build the Tala shop-drawing template (DWT) with headless AutoCAD. One-time asset: templates/TALA_A3.dwt
Contents: layers, text/dim styles for 1:1 paper space, layout SHEET (A3 landscape, DWG To PDF page setup),
frame, title block as attribute block TB_TALA, 3 named viewports (off) + view titles, table style.
Usage: python tools/acad_template.py [--out templates/TALA_A3.dwt]"""
import argparse, os, shutil, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acad_core as C

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.join(C.ACAD_DIR, "UserDataCache", "en-us", "Template", "acadiso.dwt")

# paper geometry (mm). Frame 10..410 x 10..287. Title block 30 high at bottom.
FRAME = (10, 10, 410, 287)
TB_H = 30
# viewports: name -> (cx, cy, w, h)
VP = {"FRONT": (75, 215, 120, 95), "SIDE": (205, 215, 120, 95), "TOP": (75, 105, 120, 95), "ISO": (205, 105, 120, 95)}
TABLE_X, TABLE_Y = 272, 280   # top-left of part table

def lisp_block_titleblock():
    """TB_TALA block: lines + fixed labels + attributes (tags used by the filler)."""
    L = []
    L.append('(entmake (list (cons 0 "BLOCK") (cons 2 "TB_TALA") (cons 70 2) (cons 10 (list 0 0 0))))')
    def line(x1, y1, x2, y2):
        L.append(f'(entmake (list (cons 0 "LINE") (cons 8 "SHEET-FRAME") (cons 10 (list {x1} {y1} 0)) (cons 11 (list {x2} {y2} 0))))')
    W = FRAME[2] - FRAME[0]
    line(0, 0, W, 0); line(W, 0, W, TB_H); line(W, TB_H, 0, TB_H); line(0, TB_H, 0, 0)
    cols = [0, 62, 150, 250, 320, W]
    for x in cols[1:-1]:
        line(x, 0, x, TB_H)
    for y in (10, 20):
        line(62, y, W, y)
    def text(x, y, h, s, layer="SHEET-TEXT"):
        s = s.replace('"', '\\"')
        L.append(f'(entmake (list (cons 0 "TEXT") (cons 8 "{layer}") (cons 7 "TALA") (cons 10 (list {x} {y} 0)) (cons 40 {h}) (cons 1 "{s}")))')
    text(3, 21, 4.0, "TALA LIVING"); text(3, 14, 2.6, "GAMBAR KERJA / SHOP DRAWING"); text(3, 8, 2.0, "PT TALAHOME - PRODUKSI")
    fields = [(62, 20, "DRAWN BY", "DRAWN"), (62, 10, "CHECKED BY", "CHECKED"), (62, 0, "APPROVED BY", "APPROVED"),
              (150, 20, "COLLECTION", "COLLECTION"), (150, 10, "PRODUCT NAME", "PRODUCT"), (150, 0, "DESCRIPTION", "DESC"),
              (250, 20, "UNIT", "UNIT"), (250, 10, "ITEM CODE", "ITEM_CODE"), (250, 0, "DIMENSION (W x D x H)", "DIM"),
              (320, 20, "REVISION", "REV"), (320, 10, "SCALE", "SCALE"), (320, 0, "DATE / PAGE", "DATE_PAGE")]
    for x, y, lab, tag in fields:
        text(x + 1.5, y + 7.2, 1.6, lab)
        L.append(f'(entmake (list (cons 0 "ATTDEF") (cons 8 "SHEET-TEXT") (cons 7 "TALA") (cons 10 (list {x + 1.5} {y + 2.2} 0)) (cons 40 2.8) (cons 1 "-") (cons 3 "{lab}") (cons 2 "{tag}") (cons 70 0)))')
    L.append('(entmake (list (cons 0 "ENDBLK")))')
    return L


def lisp_block_balloon():
    return ['(entmake (list (cons 0 "BLOCK") (cons 2 "BALLOON") (cons 70 2) (cons 10 (list 0 0 0))))',
            '(entmake (list (cons 0 "CIRCLE") (cons 8 "SHEET-BALLOON") (cons 10 (list 0 0 0)) (cons 40 3.5)))',
            '(entmake (list (cons 0 "ATTDEF") (cons 8 "SHEET-BALLOON") (cons 7 "TALA") (cons 10 (list 0 0 0)) (cons 11 (list 0 0 0)) (cons 40 3.0) (cons 1 "0") (cons 3 "NO") (cons 2 "NO") (cons 70 0) (cons 72 1) (cons 74 2)))',
            '(entmake (list (cons 0 "ENDBLK")))']


def script(out_dwt):
    L = ["FILEDIA", "0", "CMDECHO", "0", "ATTDIA", "0", "ATTREQ", "1", "EXPERT", "5"]
    # layers
    for nm, col in (("SHEET-FRAME", 7), ("SHEET-TEXT", 7), ("SHEET-BALLOON", 1), ("SHEET-DIM", 3), ("SHEET-TABLE", 7), ("SHEET-VPORT", 8), ("PART", 7)):
        L += ["_.-LAYER", "_M", nm, "_C", str(col), nm, ""]
    L += ["_.-LAYER", "_P", "_N", "SHEET-VPORT", ""]        # viewport borders do not plot
    # text style
    L += ["_.-STYLE", "TALA", "arial.ttf", "0", "1", "0", "_N", "_N"]
    L += ["TEXTSTYLE", "TALA"]
    # dim style for paper space (dims drawn in paper space at 1:1 mm; values overridden by the filler)
    L += ["DIMTXT", "2.5", "DIMASZ", "2.0", "DIMEXO", "1.0", "DIMEXE", "1.2", "DIMGAP", "0.8", "DIMDEC", "0", "DIMTXSTY", "TALA", "DIMCLRD", "3", "DIMCLRE", "3", "DIMCLRT", "7",
          "_.-DIMSTYLE", "_S", "TALA"]
    L += lisp_block_titleblock() + lisp_block_balloon()
    # layout
    L += ["_.LAYOUT", "_R", "Layout1", "SHEET", "_.LAYOUT", "_D", "Layout2", "_.LAYOUT", "_S", "SHEET"]
    L += ["_.ERASE", "_ALL", ""]                            # default viewport
    # page setup saved into the layout via -PLOT: file name, then save page setup = Y, proceed with plot = N
    L += ["_.-PLOT", "_Y", "SHEET", "DWG To PDF.pc3", C.PAPER_A3, "_M", "_L", "_N", "_L", "1:1", "0,0", "_Y", ".", "_Y", "_N", "_N", "_N",
          os.path.join(tempfile.gettempdir(), "tpl_setup.pdf").replace("\\", "/"), "_Y", "_N"]
    L += ["_.-LAYER", "_S", "SHEET-FRAME", ""]
    x0, y0, x1, y1 = FRAME
    L += ["_.PLINE", f"{x0},{y0}", f"{x1},{y0}", f"{x1},{y1}", f"{x0},{y1}", "_C"]
    L += ["_.-INSERT", "TB_TALA", f"{x0},{y0}", "1", "1", "0"] + ["-"] * 12
    # viewports (named by XDATA-free trick: we store the name in the layer? no: order is fixed FRONT, SIDE, TOP, ISO; filler finds by center)
    L += ["_.-LAYER", "_S", "SHEET-VPORT", ""]
    for nm, (cx, cy, w, h) in VP.items():
        L += ["_.-VPORTS", f"{cx - w/2},{cy - h/2}", f"{cx + w/2},{cy + h/2}"]
        L += ['(setq d (entget (entlast))) (entmod (subst (cons 68 0) (assoc 68 d) d))']   # off; the filler turns it on
        L += ["_.-LAYER", "_S", "SHEET-TEXT", "", "_.-TEXT", "_J", "_C", f"{cx},{cy - h/2 - 6}", "3.2", "0", {"FRONT": "TAMPAK DEPAN", "SIDE": "TAMPAK SAMPING", "TOP": "TAMPAK ATAS", "ISO": "3D VIEW"}[nm], "_.-LAYER", "_S", "SHEET-VPORT", ""]
    L += ["_.-LAYER", "_S", "0", "", "_.PSPACE"]
    L += ["_.SAVEAS", "_T", out_dwt.replace("\\", "/"), "_M", "Tala shop drawing template A3"]
    return L


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=os.path.join(ROOT, "templates", "TALA_A3.dwt"))
    a = ap.parse_args(); os.makedirs(os.path.dirname(a.out), exist_ok=True)
    w = tempfile.mkdtemp(prefix="tpl_"); seed = os.path.join(w, "seed.dwg"); shutil.copy(SEED, seed)
    if os.path.exists(a.out): os.remove(a.out)
    ok, log, why = C.run(seed, script(a.out), timeout=180, workdir=w)
    print("run:", why)
    print("dwt:", os.path.exists(a.out), os.path.getsize(a.out) if os.path.exists(a.out) else 0)
    if not ok or not os.path.exists(a.out):
        tail = [l for l in log.splitlines() if l.strip()][-30:]
        print("\n".join(tail)); sys.exit(1)


if __name__ == "__main__":
    main()
