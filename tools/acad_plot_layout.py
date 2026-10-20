import sys, os
sys.path.insert(0, r"C:/Users/Admin/Desktop/BOM-APP/tools")
import acad_core as C
W = os.path.join(os.environ["LOCALAPPDATA"], "Temp"); src = os.path.join(W, "lexi3.dwg")
out = r"C:/Users/Admin/Documents/Hasil-DWG/drafter"; os.makedirs(out, exist_ok=True)
for lay in sys.argv[1:] or ["1 drawer bs lex", "4 dw tallboy"]:
    pdf = os.path.join(out, lay.replace(" ", "_") + ".pdf").replace("\\", "/")
    if os.path.exists(pdf):
        os.remove(pdf)
    # quick plot: layout's own page setup, PDF device, file name, no save, proceed
    lines = ["FILEDIA", "0", "CMDECHO", "0", "BACKGROUNDPLOT", "0", f'(setvar "CTAB" "{lay}")',
             f'(command "_.-PLOT" "_N" "{lay}" "" "DWG To PDF.pc3" "{pdf}" "_N" "_Y")']
    ok, log, why = C.run(src, lines, timeout=120)
    print(lay, "->", why, "|", C.pdf_has_content(pdf))
    if not ok:
        print("\n".join([l for l in log.splitlines() if l.strip()][-12:]))
