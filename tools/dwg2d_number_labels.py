"""Label numbering v3 (concept: do not add balloons; number the drafter's own labels).

python tools/dwg2d_number_labels.py <dwg> --item CODE --name NAME --out DIR
 - Reads every MULTILEADER text in model space (the drafter's material labels), groups identical texts -> part numbers.
 - In headless AutoCAD, on a COPY: prefixes each MULTILEADER text with "[n] " (same leader, same position, same style).
   Done through the ActiveX-free path: entmod of the MLEADER's MTEXT content (group 304) when possible, else
   via (command "_.MLEADEREDIT")... fallback = small TEXT placed at the leader's text position, layer BOM-NO.
 - Adds a part table (NO, LABEL, QTY) in the drafter's own paper layout (first layout) at a free corner, and plots that
   layout to PDF. Writes JSON: number -> label, qty, each label's position (x, z) and the leader tip.
Speed target: one DWG in < 15 s. Accuracy: zero geometry added except the "[n]" prefix and the table.
"""
import argparse, collections, datetime, json, os, shutil, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acad_core as C
import dwg_reader as R
import ezdxf


def read_labels(dwg):
    dxf = os.path.join(tempfile.mkdtemp(), "l.dxf"); R.dwg_to_dxf(dwg, dxf)
    d = ezdxf.readfile(dxf); m = d.modelspace()
    labels = []
    for e in m:
        if e.dxftype() != "MULTILEADER":
            continue
        try:
            raw = e.context.mtext.default_content
            txt = ezdxf.tools.text.plain_mtext(raw).strip()
        except Exception:
            continue
        tip = None
        try:
            for ld in e.context.leaders:
                for ln in ld.lines:
                    if ln.vertices:
                        tip = ln.vertices[0]; break
                if tip: break
        except Exception:
            pass
        bp = e.context.mtext.insert if hasattr(e.context.mtext, "insert") else e.context.base_point
        labels.append(dict(handle=e.dxf.handle.upper(), text=" ".join(txt.split()), raw=raw,
                           tip=[round(tip.x), round(tip.y), round(tip.z)] if tip else None, text_pos=[round(bp.x), round(bp.y), round(bp.z)]))
    layouts = [l.name for l in d.layouts if l.name != "Model"]
    dims = collections.Counter()
    for e in m:
        if e.dxftype() == "DIMENSION":
            try:
                v = e.get_measurement(); dims[round(v)] += 1
            except Exception:
                pass
    return labels, layouts, {k: v for k, v in dims.items() if k > 0}


def norm(t):
    return " ".join(t.upper().replace("- ", "-").split())


def main():
    t0 = time.time()
    ap = argparse.ArgumentParser(); ap.add_argument("dwg"); ap.add_argument("--item", required=True); ap.add_argument("--name", default="")
    ap.add_argument("--out", required=True); ap.add_argument("--layout", default="")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    labels, layouts, dims = read_labels(a.dwg)
    if not labels:
        print("no MULTILEADER labels in model space"); sys.exit(1)
    groups = collections.OrderedDict()
    for lb in labels:
        groups.setdefault(norm(lb["text"]), []).append(lb)
    # part numbers: order by first appearance top-to-bottom? keep drafter order by text (metal first, then ply) -> alphabetical is predictable
    numbered = {k: i for i, k in enumerate(sorted(groups, key=lambda k: (0 if k.startswith("MT") else 1, k)), 1)}
    base = f"{a.item}_labels"; out_pdf = os.path.join(a.out, base + ".pdf"); out_dwg = os.path.join(a.out, base + ".dwg")
    for f in (out_pdf, out_dwg):
        if os.path.exists(f):
            try: os.remove(f)
            except OSError: pass
    w = tempfile.mkdtemp(prefix="num_"); src = os.path.join(w, "src.dwg"); shutil.copy(a.dwg, src)
    L = ["FILEDIA", "0", "CMDECHO", "0", "EXPERT", "5", "_.-LAYER", "_M", "BOM-NO", "_C", "5", "BOM-NO", ""]
    # 1) prefix each label text in place: MULTILEADER stores its MTEXT in group 304 of the entity's extended data block;
    #    entmod on 304 works in AutoCAD 2018+ for MLEADER. Verify per entity and count successes.
    L += ['(setq okn 0 failn 0)']
    for k, lst in groups.items():
        n = numbered[k]
        for lb in lst:
            L += [f'(setq e (handent "{lb["handle"]}"))',
                  f'(if e (progn (setq d (entget e)) (setq a304 (assoc 304 d)) (if (and a304 (/= (substr (cdr a304) 1 1) "[")) (progn (setq d2 (subst (cons 304 (strcat "[{n}] " (cdr a304))) a304 d)) (if (entmod d2) (setq okn (1+ okn)) (setq failn (1+ failn)))) (setq failn (1+ failn)))) (setq failn (1+ failn)))']
    L += ['(princ (strcat "\\nPREFIX_OK=" (itoa okn) " FAIL=" (itoa failn)))', "_.REGENALL"]
    # 2) table on the drafter's layout: place at paper top-left free area (we use paper coords; table 110 x rows*5 mm)
    lay = a.layout or (layouts[0] if layouts else "")
    rows = [(numbered[k], lst[0]["text"], len(lst)) for k, lst in groups.items()]
    rows.sort()
    if lay:
        # Drafter sheets are laid out in paper space (often inches, several sheets side by side). We plot a WINDOW
        # around the first sheet (its title text + viewports) and put the table in the free band above its views.
        L += [f'(setvar "CTAB" "{lay}")', "_.PSPACE"]
        # find sheet 1 extent from paper-space viewports left of the first big gap
        import ezdxf as _e
        dxf = os.path.join(tempfile.mkdtemp(), "p.dxf"); R.dwg_to_dxf(a.dwg, dxf)
        dd = _e.readfile(dxf); ly = dd.layouts.get(lay)
        vps = [(e.dxf.center.x - e.dxf.width / 2, e.dxf.center.y - e.dxf.height / 2, e.dxf.center.x + e.dxf.width / 2, e.dxf.center.y + e.dxf.height / 2)
               for e in ly if e.dxftype() == "VIEWPORT" and e.dxf.id != 1]
        vps = [v for v in vps if (v[2] - v[0]) < 0.6 * max(x[2] for x in vps)]   # drop the whole-page viewport
        xs = sorted(set(round(v[0], 1) for v in vps)); gaps = [(xs[i + 1] - xs[i], xs[i]) for i in range(len(xs) - 1)]
        cut = max(gaps)[1] + max(gaps)[0] / 2 if gaps and max(gaps)[0] > 3 else 1e9
        s1 = [v for v in vps if v[0] < cut]
        sx0, sy0, sx1, sy1 = min(v[0] for v in s1), min(v[1] for v in s1), max(v[2] for v in s1), max(v[3] for v in s1)
        unit = 1.0 if (sx1 - sx0) > 100 else 25.4          # mm sheets vs inch sheets
        k = 1 / unit                                         # paper units per mm
        tx, ty = sx0, sy1 + 2.4 * 25.4 * k                   # table above the views (title band of the sheet is ~0.5 in)
        rh = 4.6 * k; cw = [8 * k, 62 * k, 10 * k]; tw = sum(cw); rn = len(rows) + 2; by = ty - rh * rn
        def pl(x1, y1, x2, y2): return f'(entmake (list (cons 0 "LINE") (cons 8 "BOM-NO") (cons 10 (list {x1:.4f} {y1:.4f} 0)) (cons 11 (list {x2:.4f} {y2:.4f} 0))))'
        def pt(x, y, s_, h=2.4): return f'(entmake (list (cons 0 "TEXT") (cons 8 "BOM-NO") (cons 10 (list {x:.4f} {y:.4f} 0)) (cons 40 {h * k:.4f}) (cons 1 "{str(s_).replace(chr(34), chr(39))}")))'
        L += [pl(tx, ty, tx + tw, ty), pl(tx + tw, ty, tx + tw, by), pl(tx + tw, by, tx, by), pl(tx, by, tx, ty)]
        L += [pl(tx, ty - rh * i, tx + tw, ty - rh * i) for i in range(1, rn)]
        xx = tx
        for c in cw[:-1]:
            xx += c; L += [pl(xx, ty - rh, xx, by)]
        L += [pt(tx + 1.2 * k, ty - rh + 1.3 * k, f"{a.item} {a.name} - PART LABELS  ([n] = nomor pada label drafter)", 2.6)]
        xx = tx
        for c, h in zip(cw, ["NO", "LABEL (drafter)", "LABELS"]):
            L += [pt(xx + 1.2 * k, ty - 2 * rh + 1.3 * k, h)]; xx += c
        for i, (n, txt, q) in enumerate(rows):
            xx = tx
            for c, v in zip(cw, [f"[{n}]", txt[:38], q]):
                L += [pt(xx + 1.2 * k, ty - (i + 3) * rh + 1.3 * k, v)]; xx += c
        nx = tx + tw + 4 * k
        L += [pt(nx, ty - 2 * rh + 1.3 * k, "LABELS = jumlah label di gambar, bukan jumlah part.", 2.0),
              pt(nx, ty - 3 * rh + 1.3 * k, "Dimensi gambar: " + ", ".join(f"{kk}" + (f" x{v}" if v > 1 else "") for kk, v in sorted(dims.items())), 2.0),
              pt(nx, ty - 4 * rh + 1.3 * k, f"BOM-APP {datetime.date.today():%d %b %Y}; nomor [n] ditulis di depan label drafter.", 2.0),
              pt(nx, ty - 5 * rh + 1.3 * k, "JSON pendamping untuk AI: nomor, label, posisi tiap label.", 2.0)]
        sheets = []
        # sheets: split only at gaps wider than the drafter's own sheet title width (> 40% of the widest viewport)
        srt = sorted(vps, key=lambda v: v[0]); widest = max(v[2] - v[0] for v in srt)
        for v in srt:
            if sheets and v[0] - sheets[-1]["x1"] <= 0.4 * widest:
                sh = sheets[-1]; sh["x1"] = max(sh["x1"], v[2]); sh["y0"] = min(sh["y0"], v[1]); sh["y1"] = max(sh["y1"], v[3])
            else:
                sheets.append(dict(x0=v[0], x1=v[2], y0=v[1], y1=v[3]))
        pdfs = []
        for si, sh in enumerate(sheets, 1):
            pdf_i = out_pdf.replace(".pdf", f"_p{si}.pdf")
            if os.path.exists(pdf_i):
                os.remove(pdf_i)
            top = ty + 4 * k if si == 1 else sh["y1"] + 2.6 * 25.4 * k
            wx0, wy0 = sh["x0"] - 8 * k, sh["y0"] - 12 * k; wx1, wy1 = sh["x1"] + 8 * k, top
            if si == 1:
                wx1 = max(wx1, tx + tw + 8 * k)
            L += ["_.-PLOT", "_Y", lay, "DWG To PDF.pc3", C.PAPER_A3, "_M", "_L", "_N", "_W", f"{wx0:.3f},{wy0:.3f}", f"{wx1:.3f},{wy1:.3f}", "_F", "_C",
                  "_Y", ".", "_Y", "_N", "_N", "_N", pdf_i.replace(chr(92), "/"), "_N", "_Y"]
            pdfs.append(pdf_i)
    L += ["_.SAVEAS", "2018", out_dwg.replace("\\", "/")]
    ok, log, why = C.run(src, L, timeout=180, workdir=w)
    if lay and pdfs:
        import pymupdf
        doc = pymupdf.open()
        for f_ in pdfs:
            if os.path.exists(f_) and os.path.getsize(f_) > 1000:
                doc.insert_pdf(pymupdf.open(f_))
        if len(doc):
            doc.save(out_pdf)
        for f_ in pdfs:
            try: os.remove(f_)
            except OSError: pass
    pref = next((l.strip() for l in log.splitlines() if l.startswith("PREFIX_OK")), "PREFIX_OK=? FAIL=?")
    good, det = C.pdf_has_content(out_pdf) if lay else (False, "no layout")
    js = dict(item=a.item, name=a.name, source_dwg=os.path.abspath(a.dwg), generated=datetime.datetime.now().isoformat(timespec="seconds"),
              concept="drafter labels numbered in place: '[n] ' prefix on each MULTILEADER; no added balloons",
              parts=[dict(no=numbered[k], label=lst[0]["text"], label_count=len(lst), occurrences=[dict(handle=x["handle"], tip_xyz=x["tip"], text_xyz=x["text_pos"]) for x in lst]) for k, lst in groups.items()],
              drawing_dimensions_mm=dims, layout_plotted=lay, prefix_result=pref, seconds=round(time.time() - t0, 1))
    json.dump(js, open(os.path.join(a.out, base + ".json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    open(os.path.join(a.out, base + ".log"), "w", encoding="utf-8").write(log)
    print(f"{why} | {pref} | labels {len(labels)} -> {len(groups)} part numbers | PDF {good} {det} | {time.time() - t0:.1f}s")
    for n, txt, q in rows:
        print(f"  [{n}] {txt}  x{q}")
    if not ok or not good:
        print("\n".join([l for l in log.splitlines() if l.strip()][-10:])); sys.exit(1)


if __name__ == "__main__":
    main()
