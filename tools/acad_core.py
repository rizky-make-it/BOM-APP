"""Stable AutoCAD core-console runner for BOM-APP (headless, server-grade).

- run(dwg, lines, timeout): copies nothing, runs accoreconsole on `dwg` with a CRLF script, kills it on timeout,
  returns (ok, log_text, reason). Detects hangs (timeout), "Unknown command", "; error:" lines.
- plot_layout(dwg, layout, pdf, paper=..., timeout=...): plots one layout to PDF via `-PLOT` with the exact
  LAYOUT prompt sequence (one answer per script line, no LISP), then verifies the PDF really has content.
- kill_stray(): kills leftover acad.exe / accoreconsole.exe.
- health_check(): small end-to-end job (new drawing, text, layout, plot) -> dict with pass/fail per step.

Usage: python tools/acad_core.py --check            (health check)
       python tools/acad_core.py --plot x.dwg --layout SHEET --pdf out.pdf
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ACAD_DIR = r"C:\Program Files\Autodesk\AutoCAD 2021"
CORE = os.path.join(ACAD_DIR, "accoreconsole.exe")
PAPER_A3 = "ISO full bleed A3 (420.00 x 297.00 MM)"
PAPER_A4 = "ISO full bleed A4 (297.00 x 210.00 MM)"
CRLF = chr(13) + chr(10)


def write_script(path, lines):
    # MUST be binary CRLF: text mode doubles CR and AutoCAD then hangs on shifted prompts.
    with open(path, "wb") as f:
        f.write((CRLF.join(lines) + CRLF).encode("utf-8"))


def kill_stray():
    subprocess.run(["taskkill", "/IM", "accoreconsole.exe", "/F"], capture_output=True)
    subprocess.run(["taskkill", "/IM", "acad.exe", "/F"], capture_output=True)


def _read_log(path):
    if not os.path.exists(path):
        return ""
    raw = open(path, "rb").read()
    for enc in ("utf-16", "utf-8", "cp1252"):
        try:
            return raw.decode(enc)
        except Exception:
            pass
    return raw.decode("latin-1", "replace")


def run(dwg, lines, timeout=120, workdir=None):
    """Run a script on dwg. Returns (ok, log, reason)."""
    workdir = workdir or tempfile.mkdtemp(prefix="acadcore_")
    scr = os.path.join(workdir, "job.scr")
    logp = os.path.join(workdir, "job.log")
    write_script(scr, list(lines) + ["_.QUIT", "Y"])
    t0 = time.time()
    try:
        with open(logp, "wb") as f:
            subprocess.run([CORE, "/i", dwg, "/s", scr, "/l", "en-US"], stdout=f, stderr=subprocess.STDOUT, timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        timed_out = True
        kill_stray()
    log = _read_log(logp)
    dt = time.time() - t0
    bad = [l.strip() for l in log.splitlines()
           if "Unknown command" in l or "; error:" in l or "Yes or No, please" in l or "Point or option keyword required" in l]
    if timed_out:
        return False, log, f"timeout after {timeout}s (AutoCAD was waiting for input); last lines: {log[-400:]!r}"
    if bad:
        return False, log, "AutoCAD reported: " + " | ".join(bad[:4])
    return True, log, f"ok in {dt:.0f}s"


def plot_lines(layout, pdf, paper=PAPER_A3, scale="1:1"):
    """Exact -PLOT answers for a LAYOUT (paper space). Order matters; model space has a different sequence."""
    pdf = pdf.replace("\\", "/")
    return [
        "FILEDIA", "0", "CMDECHO", "0", "BACKGROUNDPLOT", "0",
        "_.LAYOUT", "_S", layout,                  # make the layout current first
        "_.-PLOT",
        "_Y",                                      # Detailed plot configuration?
        layout,                                    # layout name
        "DWG To PDF.pc3",                          # output device
        paper,                                     # paper size
        "_M",                                      # paper units: millimeters
        "_L",                                      # orientation: landscape
        "_N",                                      # plot upside down?
        "_L",                                      # plot area: Layout
        scale,                                     # plot scale
        "0,0",                                     # plot offset
        "_Y",                                      # plot with plot styles?
        ".",                                       # plot style table: none
        "_Y",                                      # plot with lineweights?
        "_N",                                      # scale lineweights with plot scale?
        "_N",                                      # plot paper space first?
        "_N",                                      # hide paperspace objects?
        pdf,                                       # file name (PDF device never asks "write to file?")
        "_N",                                      # save changes to page setup?
        "_Y",                                      # proceed with plot?
    ]


def pdf_has_content(pdf, min_bytes=3000):
    if not os.path.exists(pdf) or os.path.getsize(pdf) < min_bytes:
        return False, f"missing or tiny ({os.path.getsize(pdf) if os.path.exists(pdf) else 0} B)"
    try:
        import pymupdf
        d = pymupdf.open(pdf)
        p = d[0]
        txt = len(str(p.get_text()).strip())
        draw = len(p.get_drawings())
        d.close()
        if txt == 0 and draw == 0:
            return False, "PDF has no text and no vector drawings (blank page)"
        return True, f"text={txt} chars, drawings={draw}"
    except ImportError:
        return True, "size ok (pymupdf not installed for deep check)"


def plot_layout(dwg, layout, pdf, paper=PAPER_A3, timeout=180):
    """Plot `layout` of `dwg` to `pdf`. Returns (ok, reason). Never touches `dwg` (reads it; QUIT without save)."""
    if os.path.exists(pdf):
        try:
            os.remove(pdf)
        except OSError:
            return False, f"output locked by another program: {pdf}"
    ok, log, reason = run(dwg, plot_lines(layout, pdf, paper), timeout=timeout)
    for _ in range(20):                                        # the PDF writer can lag a little behind QUIT
        if os.path.exists(pdf) and os.path.getsize(pdf) > 0:
            break
        time.sleep(0.5)
    good, why = pdf_has_content(pdf)
    if not good:
        return False, f"plot ran ({reason}) but PDF check failed: {why}"
    return True, f"{reason}; {why}"


def health_check():
    """New drawing -> text + rectangle in model, layout with viewport -> plot -> verify. Returns dict."""
    kill_stray()
    w = tempfile.mkdtemp(prefix="acadhc_")
    dwg = os.path.join(w, "hc.dwg")
    pdf = os.path.join(w, "hc.pdf")
    res = {"accoreconsole_exists": os.path.exists(CORE), "steps": {}}
    if not res["accoreconsole_exists"]:
        return res
    # step 1: build a drawing from scratch (template acadiso.dwt) and save
    seed = os.path.join(ACAD_DIR, "UserDataCache", "en-us", "Template", "acadiso.dwt")
    if not os.path.exists(seed):
        seed = next((os.path.join(r, f) for r, _, fs in os.walk(ACAD_DIR) for f in fs if f.lower() == "acadiso.dwt"), None)
    res["template"] = seed
    shutil.copy(seed, dwg) if seed else None
    lines = ["FILEDIA", "0", "CMDECHO", "0",
             "_.RECTANG", "0,0", "500,300",
             "_.-TEXT", "20,320", "25", "0", "BOM-APP HEALTH CHECK",
             "_.LAYOUT", "_S", "Layout1",
             "_.-VPORTS", "20,40", "380,250",
             "_.MSPACE", "_.ZOOM", "_E", "_.PSPACE",
             "_.SAVEAS", "2018", dwg.replace("\\", "/")]
    ok, log, reason = run(dwg, lines, timeout=120)
    res["steps"]["write_and_save"] = {"ok": ok and os.path.exists(dwg), "detail": reason}
    # step 2: plot
    ok2, why = plot_layout(dwg, "Layout1", pdf)
    res["steps"]["plot_pdf"] = {"ok": ok2, "detail": why}
    # step 3: no stray processes
    out = subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()
    stray = out.count("accoreconsole.exe") + out.count("acad.exe")
    res["steps"]["no_stray_process"] = {"ok": stray == 0, "detail": f"{stray} process(es) left"}
    res["pass"] = all(s["ok"] for s in res["steps"].values())
    res["workdir"] = w
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--plot")
    ap.add_argument("--layout", default="SHEET")
    ap.add_argument("--pdf")
    ap.add_argument("--paper", default=PAPER_A3)
    a = ap.parse_args()
    if a.check:
        r = health_check()
        print(json.dumps(r, indent=1, ensure_ascii=False))
        sys.exit(0 if r.get("pass") else 1)
    if a.plot:
        ok, why = plot_layout(a.plot, a.layout, a.pdf or os.path.splitext(a.plot)[0] + ".pdf", a.paper)
        print("OK" if ok else "FAIL", why)
        sys.exit(0 if ok else 1)
    ap.print_help()
