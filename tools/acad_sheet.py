"""Shop-drawing sheet built INSIDE AutoCAD (COM) from the real 3D solids - the 'easy version' for BOM-APP.

Input : the DWG (3D solids), solids.json (tools/acad_solids.py), numbering.json (part numbers per solid handle).
Output: <out>/<name>_sheet.dwg  (layout SHEET with 3 viewports front/right side/top, balloons, overall dimensions,
        part table, title block with attributes) and <out>/<name>_sheet.pdf (plotted by AutoCAD).
Works on a COPY of the DWG. Everything except the group's own solids is deleted in that copy.

Usage: python tools/acad_sheet.py --dwg x.dwg --solids s.json --numbering n.json --out DIR [--scale 6]
       [--item-code CODE] [--name NAME] [--collection NAME]
Needs: Windows, full AutoCAD (COM registered, e.g. AutoCAD.Application.24), pywin32. AutoCAD must NOT already be open.
"""
import argparse
import collections
import datetime
import json
import math
import os
import shutil
import sys
import tempfile
import time

import pythoncom
import win32com.client as wc

BUSY = ("rejected", "busy", "-2147418111", "-2147417846")
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    LOG.append(s)
    print(s, flush=True)


def R(fn, tries=40, wait=1.5):
    last = None
    for _ in range(tries):
        try:
            return fn()
        except Exception as e:
            last = e
            if any(b in str(e).lower() for b in BUSY):
                time.sleep(wait)
                continue
            raise
    raise last


def V3(x, y, z=0.0):
    return wc.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, (float(x), float(y), float(z)))


MAT = {"101": "Solid wood Mindi (A)", "102": "Solid wood Mindi (A)", "202": "Solid wood Mindi (A)", "207": "Solid wood Mindi (A)",
       "301": "MDF veneer E0 1 muka *", "302": "Plywood veneer Mindi 1F", "306": "Plywood veneer Mindi 1F",
       "307": "Plywood veneer Mindi 1F", "308": "Plywood veneer Mindi 1F", "299": "belum diketahui"}
CONF = {"high": "YAKIN", "medium": "CUKUP", "low": "RAGU"}


def merge_items(rows):
    groups = collections.OrderedDict()
    for r in sorted(rows, key=lambda r: (r["pn"], tuple(-round(v) for v in r["dims"]))):
        groups.setdefault((r["pn"], tuple(round(v, 1) for v in r["dims"])), []).append(r)
    items = []
    for n, (key, rs) in enumerate(groups.items(), 1):
        worst = min((r["conf"] for r in rs), key={"low": 0, "medium": 1, "high": 2}.get)
        items.append(dict(no=n, pn=key[0], name=rs[0]["name"], dims=key[1], qty=len(rs), conf=worst,
                          handles=[r["handle"] for r in rs], mat=MAT.get(key[0], "?")))
    return items


def ring(pts, center, rx, ry, gap=0.5):
    ang = sorted((math.atan2(p[1] - center[1], p[0] - center[0]), n) for n, p in pts.items())
    gap = min(gap, 2 * math.pi / max(1, len(ang)) * 0.92)
    out = []
    for i, (a, n) in enumerate(ang):
        if i and a < out[-1][0] + gap:
            a = out[-1][0] + gap
        out.append((a, n))
    return {n: (center[0] + rx * math.cos(a), center[1] + ry * math.sin(a)) for a, n in out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dwg", required=True)
    ap.add_argument("--solids", required=True)
    ap.add_argument("--numbering", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", type=float, default=6.0)
    ap.add_argument("--item-code", default="BELUM DIISI")
    ap.add_argument("--name", default="UNIT K1")
    ap.add_argument("--collection", default="LEXI (belum dikonfirmasi)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    base = os.path.splitext(os.path.basename(a.numbering))[0]
    out_dwg = os.path.join(a.out, f"{base}_sheet.dwg")
    out_pdf = os.path.join(a.out, f"{base}_sheet.pdf")
    # An old result may be open in a viewer (locked): never fight it, write to a fresh name instead.
    stamp = datetime.datetime.now().strftime("%H%M%S")
    for f in (out_dwg, out_pdf):
        if os.path.exists(f):
            try:
                os.remove(f)
            except OSError:
                out_dwg = os.path.join(a.out, f"{base}_sheet_{stamp}.dwg")
                out_pdf = os.path.join(a.out, f"{base}_sheet_{stamp}.pdf")
                log("file lama terkunci (dibuka program lain) -> hasil baru:", os.path.basename(out_pdf))
                break

    rows = json.load(open(a.numbering, encoding="utf-8"))
    S = {s["handle"].upper(): s for s in json.load(open(a.solids, encoding="utf-8"))["solids"]}
    items = merge_items(rows)
    hs = [r["handle"].upper() for r in rows]
    x0 = min(S[h]["x0"] for h in hs); x1 = max(S[h]["x1"] for h in hs)
    y0 = min(S[h]["y0"] for h in hs); y1 = max(S[h]["y1"] for h in hs)
    z0 = min(S[h]["z0"] for h in hs); z1 = max(S[h]["z1"] for h in hs)
    SX, SY, SZ = x1 - x0, y1 - y0, z1 - z0
    T = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    k = 1.0 / a.scale
    log(f"group: {len(hs)} solids, {SX:.0f} x {SY:.0f} x {SZ:.0f} mm, {len(items)} part numbers, scale 1:{a.scale:g}")

    work = os.path.join(tempfile.mkdtemp(prefix="sheet_"), "work.dwg")
    shutil.copy(a.dwg, work)

    pythoncom.CoInitialize()
    app = R(lambda: wc.Dispatch("AutoCAD.Application.24"))
    time.sleep(8)
    R(lambda: setattr(app, "Visible", True))
    # AutoCAD answers "Call was rejected" while it is still loading; wait until it accepts calls, then open our copy.
    for _ in range(40):
        try:
            app.ActiveDocument.Name
            break
        except Exception:
            time.sleep(1.5)
    doc = None
    for _ in range(10):
        try:
            d_ = app.Documents.Open(work)
            if d_ is not None and os.path.basename(work).lower() in str(d_.Name).lower():
                doc = d_
                break
        except Exception:
            pass
        time.sleep(2)
        try:
            for i in range(app.Documents.Count):
                dd = app.Documents.Item(i)
                if os.path.basename(work).lower() in str(dd.Name).lower():
                    doc = dd
                    break
        except Exception:
            pass
        if doc is not None:
            break
    if doc is None:
        raise RuntimeError("AutoCAD tidak mau membuka salinan DWG")
    R(lambda: setattr(app, "Visible", True))
    R(lambda: doc.Activate())
    log("document:", R(lambda: doc.Name), "| entities:", R(lambda: doc.ModelSpace.Count))
    R(lambda: doc.SetVariable("BACKGROUNDPLOT", 0))

    try:
        # ---- 1. keep only this group's solids
        ms = doc.ModelSpace
        keep = set(hs)
        dels = []
        for i in range(R(lambda: ms.Count)):
            e = R(lambda i=i: ms.Item(i))
            if str(R(lambda: e.Handle)).upper() not in keep:
                dels.append(e)
        for e in dels:
            R(lambda e=e: e.Delete())
        log("kept", R(lambda: ms.Count), "entities, deleted", len(dels))

        # ---- 2. layout
        # The source DWG often carries other sheets (layouts) from the drafters: remove them so only OUR sheet exists and is plotted.
        lay = None
        for _ in range(3):
            names_ = [R(lambda i=i: doc.Layouts.Item(i).Name) for i in range(R(lambda: doc.Layouts.Count))]
            for nm_ in names_:
                if nm_.lower() == "model":
                    continue
                try:
                    R(lambda nm_=nm_: doc.Layouts.Item(nm_).Delete(), tries=6)
                except Exception as e:
                    log("  (layout", nm_, "tidak bisa dihapus:", str(e)[:40] + ")")
            names_ = [R(lambda i=i: doc.Layouts.Item(i).Name) for i in range(R(lambda: doc.Layouts.Count))]
            if len([n for n in names_ if n.lower() != "model"]) == 0:
                break
        left = [n for n in names_ if n.lower() != "model"]
        if left:                      # AutoCAD always keeps one layout: reuse it
            lay = R(lambda: doc.Layouts.Item(left[0]))
            R(lambda: setattr(lay, "Name", "SHEET"))
        else:
            lay = R(lambda: doc.Layouts.Add("SHEET"))
        R(lambda: setattr(doc, "ActiveLayout", lay))
        log("layouts now:", [R(lambda i=i: doc.Layouts.Item(i).Name) for i in range(R(lambda: doc.Layouts.Count))])
        def soft(label, fn):
            try:
                R(fn, tries=6)
            except Exception as e:
                log("  (pengaturan cetak dilewati:", label, str(e)[:50] + ")")
        soft("printer", lambda: setattr(lay, "ConfigName", "DWG To PDF.pc3"))
        soft("refresh", lambda: lay.RefreshPlotDeviceInfo())
        a3 = "ISO_full_bleed_A3_(420.00_x_297.00_MM)"
        try:
            names = list(R(lambda: lay.GetCanonicalMediaNames(), tries=6))
            a3 = next((n for n in names if "A3" in n and "420" in n and "297" in n), None) or next((n for n in names if "A3" in n), a3)
        except Exception as e:
            log("  (daftar kertas tidak terbaca:", str(e)[:50] + ")")
        soft("paper", lambda: setattr(lay, "CanonicalMediaName", a3))
        soft("rotation", lambda: setattr(lay, "PlotRotation", 0))
        soft("plot type", lambda: setattr(lay, "PlotType", 5))
        soft("scale", lambda: setattr(lay, "StandardScale", 16))        # acScaleToFit off; 1:1 below
        soft("custom scale", lambda: lay.SetCustomScale(1.0, 1.0))
        soft("use standard scale", lambda: setattr(lay, "UseStandardScale", False))
        soft("plot origin", lambda: setattr(lay, "PlotOrigin", wc.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, (0.0, 0.0))))
        log("layout SHEET, paper:", a3)
        ps = R(lambda: doc.PaperSpace)
        for i in reversed(range(R(lambda: ps.Count))):
            e = R(lambda i=i: ps.Item(i))
            try:
                R(lambda e=e: e.Delete(), tries=4)      # the default viewport cannot be deleted; others can
            except Exception:
                pass

        # ---- 3. layers
        for nm, col in (("SHEET-FRAME", 7), ("SHEET-BALOON", 1), ("SHEET-DIM", 3), ("SHEET-TABLE", 7)):
            try:
                l = R(lambda nm=nm: doc.Layers.Add(nm))
                R(lambda l=l, col=col: setattr(l, "Color", col))
            except Exception as e:
                log("layer", nm, str(e)[:60])

        def on(layer, ent):
            try:
                R(lambda: setattr(ent, "Layer", layer))
            except Exception:
                pass
            return ent

        # ---- 4. frame
        for p, q in (((10, 10), (410, 10)), ((410, 10), (410, 287)), ((410, 287), (10, 287)), ((10, 287), (10, 10))):
            on("SHEET-FRAME", R(lambda p=p, q=q: ps.AddLine(V3(*p), V3(*q))))

        # ---- 5. viewports (real AutoCAD views of the solids; hidden-line when plotted)
        views = {
            "front": dict(c=(70, 232), dir=(0, -1, 0), hv=("x", "z"), w=SX, h=SZ, title="TAMPAK DEPAN"),
            "side":  dict(c=(190, 232), dir=(1, 0, 0), hv=("y", "z"), w=SY, h=SZ, title="TAMPAK SAMPING KANAN"),
            "top":   dict(c=(70, 115), dir=(0, 0, 1), hv=("x", "y"), w=SX, h=SY, title="TAMPAK ATAS"),
        }
        for name, v in views.items():
            vw, vh = v["w"] * k + 14, v["h"] * k + 14
            vp = R(lambda v=v, vw=vw, vh=vh: ps.AddPViewport(V3(*v["c"]), vw, vh))
            R(lambda vp=vp: vp.Display(True))
            R(lambda vp=vp, v=v: setattr(vp, "Direction", V3(*v["dir"])))
            R(lambda vp=vp: setattr(vp, "Target", V3(*T)))
            R(lambda vp=vp: setattr(vp, "CustomScale", k))
            R(lambda vp=vp: setattr(vp, "ShadePlot", 2))
            on("SHEET-FRAME", vp)
            v["vp"] = vp
        R(lambda: doc.Regen(1))
        log("3 viewports ok")

        # ---- 6. balloons + dimensions
        TH = {"x": T[0], "y": T[1], "z": T[2]}

        def proj(v, h, vv):
            return (v["c"][0] + k * (h - TH[v["hv"][0]]), v["c"][1] + k * (vv - TH[v["hv"][1]]))

        for name, v in views.items():
            ah, av = v["hv"]
            pts = {}
            for it in items:
                s = S[it["handles"][0].upper()]
                pts[it["no"]] = proj(v, (s[ah + "0"] + s[ah + "1"]) / 2, (s[av + "0"] + s[av + "1"]) / 2)
            rx, ry = v["w"] * k / 2 + 9.5, v["h"] * k / 2 + 9.5
            for no, (bx, by) in ring(pts, v["c"], rx, ry).items():
                ax_, ay_ = pts[no]
                d = math.hypot(bx - ax_, by - ay_) or 1.0
                ex, ey = bx - (bx - ax_) / d * 3.8, by - (by - ay_) / d * 3.8
                on("SHEET-BALOON", R(lambda: ps.AddLine(V3(ax_, ay_), V3(ex, ey))))
                on("SHEET-BALOON", R(lambda: ps.AddCircle(V3(ax_, ay_), 0.7)))
                on("SHEET-BALOON", R(lambda: ps.AddCircle(V3(bx, by), 3.8)))
                t = R(lambda: ps.AddText(str(no), V3(bx, by), 3.2))
                R(lambda: setattr(t, "Alignment", 10))
                R(lambda: setattr(t, "TextAlignmentPoint", V3(bx, by)))
                on("SHEET-BALOON", t)
            t = R(lambda: ps.AddText(v["title"], V3(v["c"][0], v["c"][1] - v["h"] * k / 2 - 15), 3.2))
            R(lambda: setattr(t, "Alignment", 1))
            R(lambda: setattr(t, "TextAlignmentPoint", V3(v["c"][0], v["c"][1] - v["h"] * k / 2 - 15)))
        fv, sv = views["front"], views["side"]

        def dim(p1, p2, tp, txt):
            d = R(lambda: ps.AddDimAligned(V3(*p1), V3(*p2), V3(*tp)))
            R(lambda: setattr(d, "TextOverride", txt))
            on("SHEET-DIM", d)

        fx0, fy0 = fv["c"][0] - SX * k / 2, fv["c"][1] - SZ * k / 2
        dim((fx0, fy0), (fx0 + SX * k, fy0), (fx0 + SX * k / 2, fy0 - 6.5), f"{SX:.0f}")
        dim((fx0 + SX * k, fy0), (fx0 + SX * k, fy0 + SZ * k), (fx0 + SX * k + 8, fy0 + SZ * k / 2), f"{SZ:.0f}")
        sx0, sy0 = sv["c"][0] - SY * k / 2, sv["c"][1] - SZ * k / 2
        dim((sx0, sy0), (sx0 + SY * k, sy0), (sx0 + SY * k / 2, sy0 - 6.5), f"{SY:.0f}")
        log("balloons + dimensions ok")

        # ---- 7. part table
        tbl = R(lambda: ps.AddTable(V3(262, 275), len(items) + 2, 7, 6.0, 20.0))
        for i, w in enumerate((7, 11, 34, 40, 28, 9, 17)):
            R(lambda i=i, w=w: tbl.SetColumnWidth(i, w))
        R(lambda: tbl.SetText(0, 0, "PART LIST"))
        for i, h in enumerate(("NO", "PART NO", "NAMA PART", "BAHAN", "P x L x T (mm)", "QTY", "YAKIN")):
            R(lambda i=i, h=h: tbl.SetText(1, i, h))
        for r_, it in enumerate(items, 2):
            d = it["dims"]
            for c_, val in enumerate((str(it["no"]), it["pn"], it["name"], it["mat"], f"{d[0]:g} x {d[1]:g} x {d[2]:g}", str(it["qty"]), CONF[it["conf"]])):
                R(lambda r_=r_, c_=c_, val=val: tbl.SetText(r_, c_, val))
        for rt in (1, 2, 4):
            try:
                R(lambda rt=rt: tbl.SetTextHeight(rt, 2.4))
            except Exception:
                pass
        on("SHEET-TABLE", tbl)
        log("table", len(items) + 2, "rows ok")

        # ---- 8. notes
        notes = ("CATATAN (draf otomatis dari model 3D)\\P"
                 "- Sumber: model 3D, nomor part = Part Master v3.\\P"
                 "- Ukuran dari model; tebal akhir mengikuti RULES pabrik.\\P"
                 "- * Panel samping: aturan meeting (MDF veneer E0 1 muka), label gambar: plywood.\\P"
                 "- Kotak laci tidak ada di model; dihitung dari rumus pabrik.\\P"
                 "- YAKIN / CUKUP / RAGU = keyakinan nomor otomatis; RAGU wajib dicek.")
        m = R(lambda: ps.AddMText(V3(262, 275 - 6.0 * (len(items) + 2) - 6), 146, notes))
        R(lambda: setattr(m, "Height", 2.4))

        # ---- 9. title block (block with attributes)
        blk = R(lambda: doc.Blocks.Add(V3(0, 0), "TB_TALA"))
        for p, q in (((0, 0), (400, 0)), ((400, 0), (400, 30)), ((400, 30), (0, 30)), ((0, 30), (0, 0))):
            R(lambda p=p, q=q: blk.AddLine(V3(*p), V3(*q)))
        for x in (62, 150, 250, 320):
            R(lambda x=x: blk.AddLine(V3(x, 0), V3(x, 30)))
        for y in (10, 20):
            R(lambda y=y: blk.AddLine(V3(62, y), V3(400, y)))
        t = R(lambda: blk.AddMText(V3(3, 27), 56, "TALA LIVING\\PGAMBAR KERJA\\P(draf otomatis)"))
        R(lambda: setattr(t, "Height", 3.0))
        fields = [(62, 20, "DRAWN BY", "DRAWN"), (62, 10, "CHECKED BY", "CHECKED"), (62, 0, "APPROVED BY", "APPROVED"),
                  (150, 20, "COLLECTION NAME", "COLLECTION"), (150, 10, "PRODUCT NAME", "PRODUCT"), (150, 0, "DESCRIPTION", "DESC"),
                  (250, 20, "UNIT", "UNIT"), (250, 10, "ITEM CODE", "ITEM_CODE"), (250, 0, "DIMENSION", "DIM"),
                  (320, 20, "REVISION", "REV"), (320, 10, "SCALE", "SCALE"), (320, 0, "PAGE", "PAGE")]
        for x, y, lab, tag in fields:
            R(lambda x=x, y=y, lab=lab: blk.AddText(lab, V3(x + 1.5, y + 7.0), 1.6))
            R(lambda x=x, y=y, lab=lab, tag=tag: blk.AddAttribute(2.8, 0, lab, V3(x + 1.5, y + 2.0), tag, "-"))
        ref = R(lambda: ps.InsertBlock(V3(10, 10), "TB_TALA", 1, 1, 1, 0))
        today = datetime.date.today().strftime("%B %d, %Y")
        vals = {"DRAWN": "BOM-APP (otomatis)", "CHECKED": "-", "APPROVED": "-", "COLLECTION": a.collection, "PRODUCT": a.name,
                "DESC": "OVER VIEW + PART LIST", "UNIT": "mm", "ITEM_CODE": a.item_code, "DIM": f"W{SX:.0f} x D{SY:.0f} x H{SZ:.0f} mm",
                "REV": "00", "SCALE": f"1:{a.scale:g}", "PAGE": "01 / 01"}
        for at in R(lambda: ref.GetAttributes()):
            tag = R(lambda: at.TagString)
            if tag in vals:
                R(lambda at=at, tag=tag: setattr(at, "TextString", vals[tag]))
        on("SHEET-FRAME", ref)
        log("title block ok; date", today)

        # ---- 10. plot + save
        R(lambda: doc.Regen(1))
        R(lambda: setattr(doc, "ActiveLayout", lay))
        ok = R(lambda: doc.Plot.PlotToFile(out_pdf, "DWG To PDF.pc3"))
        for _ in range(60):
            if os.path.exists(out_pdf) and os.path.getsize(out_pdf) > 1000:
                break
            time.sleep(1)
        log("PDF:", os.path.exists(out_pdf), os.path.getsize(out_pdf) if os.path.exists(out_pdf) else 0, "plot returned", ok)
        try:
            R(lambda: doc.SaveAs(out_dwg, 64))
        except Exception:
            R(lambda: doc.SaveAs(out_dwg))
        log("DWG:", os.path.exists(out_dwg))
    finally:
        try:
            R(lambda: doc.Close(False), tries=5)
        except Exception:
            pass
        try:
            R(lambda: app.Quit(), tries=5)
        except Exception:
            pass
    open(os.path.join(a.out, f"{base}_sheet.log.txt"), "w", encoding="utf-8").write("\n".join(LOG))


if __name__ == "__main__":
    main()
