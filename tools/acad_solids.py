"""Read every 3DSOLID of a DWG with the REAL AutoCAD engine (accoreconsole), one by one.

AutoCAD itself walks the drawing database (entnext), so nothing depends on a pre-built selection set.
Each solid is reported with handle + space (Model / layout name); solids that live in a layout are read by
switching to that layout first. A solid MASSPROP cannot read is listed as failed (never silently dropped).
Usage: python tools/acad_solids.py <file.dwg> [--json out.json]
"""
import argparse
import json
import os
import re
import subprocess
import tempfile

CRLF = chr(13) + chr(10)
ACAD = r"C:\Program Files\Autodesk\AutoCAD 2021\accoreconsole.exe"

# One line only (script mode feeds it line by line). No VLA calls, so no security prompt.
LISP = (r'(defun c:SOL ( / e ed n sp) (setq e (entnext) n 0) (while e (setq ed (entget e)) '
        r'(if (= (cdr (assoc 0 ed)) "3DSOLID") (progn '
        r'(setq sp (if (assoc 410 ed) (cdr (assoc 410 ed)) "Model")) '
        r'(if (/= (getvar "CTAB") sp) (setvar "CTAB" sp)) '
        r'(princ (strcat "\n@@S" (itoa n) " " (cdr (assoc 5 ed)) " " (vl-string-translate " " "_" sp))) '
        r'(command "_.MASSPROP" e "" "N") (princ "\n@@END") (setq n (1+ n)))) '
        r'(setq e (entnext e))) (princ (strcat "\n@@TOTAL=" (itoa n))) (princ))')


def _write(path, lines):
    """AutoCAD scripts need exact CRLF; text mode on Windows would double the CR and shift every command."""
    with open(path, "wb") as f:
        f.write((CRLF.join(lines) + CRLF).encode("ascii"))


def _run(dwg, scr, timeout):
    log = scr + ".log"
    with open(log, "wb") as f:
        subprocess.run([ACAD, "/i", dwg, "/s", scr, "/l", "en-US"], stdout=f, stderr=subprocess.STDOUT, timeout=timeout)
    b = open(log, "rb").read()
    t = b.decode("utf-16-le", errors="ignore") if b.count(b"\x00") > len(b) // 4 else b.decode("latin1")
    return t.replace("\r", "")


def parse(t):
    total = re.search(r"@@TOTAL=(\d+)", t)
    rows, failed = [], []
    for blk in t.split("\n@@S")[1:]:
        head = blk.split("\n")[0].split()
        if len(head) < 2 or not head[0].isdigit():
            continue
        i, handle, space = int(head[0]), head[1], (head[2] if len(head) > 2 else "?")
        bb = re.search(r"X:\s*([-\d.]+)\s*--\s*([-\d.]+)\s*\n\s*Y:\s*([-\d.]+)\s*--\s*([-\d.]+)\s*\n\s*Z:\s*([-\d.]+)\s*--\s*([-\d.]+)", blk)
        vol = re.search(r"Volume:\s*([-\d.]+)", blk)
        if not bb:
            failed.append({"i": i, "handle": handle, "space": space, "why": "MASSPROP tidak memberi hasil"})
            continue
        x0, x1, y0, y1, z0, z1 = map(float, bb.groups())
        rows.append({"i": i, "handle": handle, "space": space, "x0": x0, "x1": x1, "y0": y0, "y1": y1, "z0": z0, "z1": z1,
                     "sx": round(x1 - x0, 3), "sy": round(y1 - y0, 3), "sz": round(z1 - z0, 3),
                     "vol": float(vol.group(1)) if vol else None})
    return {"solids_in_file": int(total.group(1)) if total else None, "solids_read": len(rows),
            "solids_failed": failed, "solids": rows}


def run(dwg, workdir=None, timeout=600):
    w = workdir or tempfile.mkdtemp(prefix="acad_")
    src = os.path.join(w, "in.dwg")
    with open(dwg, "rb") as a, open(src, "wb") as b:
        b.write(a.read())
    scr = os.path.join(w, "per.scr")
    _write(scr, ["FILEDIA 0", "CMDECHO 0", LISP, "SOL", "_.QUIT Y"])
    return parse(_run(src, scr, timeout))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dwg")
    ap.add_argument("--json")
    a = ap.parse_args()
    r = run(a.dwg)
    if a.json:
        json.dump(r, open(a.json, "w"), indent=1)
    print(f"solid di file {r['solids_in_file']}, terbaca {r['solids_read']}, gagal {len(r['solids_failed'])}")
    for s in r["solids"]:
        dims = sorted((s["sx"], s["sy"], s["sz"]), reverse=True)
        print(f"  #{s['i']:>2} {s['handle']:>5} [{s['space']}] {dims[0]:>7.1f} x {dims[1]:>6.1f} x {dims[2]:>6.1f}  vol {s['vol']:.0f}  x {s['x0']:.0f}..{s['x1']:.0f}  y {s['y0']:.0f}..{s['y1']:.0f}  z {s['z0']:.0f}..{s['z1']:.0f}")
    for f in r["solids_failed"]:
        print("  GAGAL", f)
