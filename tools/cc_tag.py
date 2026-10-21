"""Label a DWG through CADCraft MCP: boxed number tags (leader + square + number) on the model-space views + a schedule sheet plotted to PDF.
python tools/cc_tag.py <dwg> --spec spec.json --out DIR --item CODE --name NAME
spec.json = {"comps":[{row,no,name,l,w,t,qty,code,status,note}], "tags":[{"row":n,"tip":[x,y],"box":[x,y],"side":[sx,sy]}], "h":40}"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cc_read

def tag_dwg(m, spec):
    H = spec.get("h", 40); S = 2.2 * H
    ex = lambda c, a: m.call("execute", dict(command=c, params=a))
    for t in spec["tags"]:
        (tx, ty), (cx, cy), (sx, sy) = t["tip"], t["box"], t["side"]
        ex("line", dict(points=[[tx, ty], [cx + sx * S / 2, cy + sy * S / 2]]))
        ex("rectang", dict(p1=[cx - S / 2, cy - S / 2], p2=[cx + S / 2, cy + S / 2]))
        ex("text", dict(at=[cx, cy], text=str(t["row"]), height=0.9 * H, justify="MC"))

def schedule_pdf(m, comps, item, name, pdf, date):
    m.call("new_drawing", dict(metric=True))
    ex = lambda c, a: m.call("execute", dict(command=c, params=a))
    ln = lambda *p: ex("line", dict(points=[list(q) for q in p]))
    tx = lambda x, y, s, h=2.6: ex("text", dict(at=[x, y], text=str(s), height=h, justify="BL"))
    ln((10, 10), (410, 10), (410, 287), (10, 287), (10, 10)); ln((10, 32), (410, 32))
    for xk in (120, 230, 300, 360): ln((xk, 10), (xk, 32))
    chk = sum(1 for c in comps if c["status"] == "CHECK")
    for x, y, s, h in [(13, 25, "TALA LIVING", 4), (13, 18, "Keynote & Schedule Komponen", 3), (13, 13, "Dibaca/dilabel: CADCraft MCP + BOM-APP", 2.2),
                       (123, 25, "ITEM", 2.2), (123, 18, item, 4), (123, 13, name[:36], 2.8), (233, 25, "STATUS", 2.2), (233, 18, f"{len(comps)-chk}/{len(comps)} pasti", 3), (233, 13, f"{chk} CHECK", 2.8),
                       (303, 25, "TANGGAL", 2.2), (303, 18, date, 3), (363, 25, "SHEET", 2.2), (363, 16, f"{item}-02", 4)]: tx(x, y, s, h)
    cw = [12, 84, 34, 9, 44, 19, 190]; X0, Y0, RH = 14, 268, 7.5; rn = len(comps) + 1
    tx(X0 + 1, Y0 + 10, f"KEYNOTE & SCHEDULE KOMPONEN - {name or item}", 5)
    tx(X0 + 1, Y0 + 3, "TAG = angka berbingkai di gambar. PART NO = Part Master v3. STATED = dari label/daftar potong drafter, DERIVED = diukur dari garis, CHECK = perlu konfirmasi.", 2.2)
    for i in range(rn + 1): ln((X0, Y0 - i * RH), (X0 + sum(cw), Y0 - i * RH))
    x = X0
    for c in cw + [0]:
        ln((x, Y0), (x, Y0 - rn * RH)); x += c
    x = X0
    for c, h in zip(cw, ["TAG", "PART NO  NAMA", "L x W x T", "QTY", "BAHAN", "STATUS", "CATATAN"]): tx(x + 1.5, Y0 - RH + 2.3, h); x += c
    for i, c in enumerate(comps):
        size = f"{c['l']:g} x {c['w']:g} x {c['t']:g}" if c.get("w") else f"{c['l']:g} x ? x {c['t']:g}"
        vals = [c["row"], f"{c['no']}  {c['name']}", size, c["qty"], str(c["code"]), c["status"], c["note"]]
        x = X0
        for w, v in zip(cw, vals):
            tx(x + 1.5, Y0 - (i + 2) * RH + 2.3, str(v)[: int((w - 3) / 2.15)]); x += w
    r = m.call("execute", dict(command="plot", params=dict(path=pdf, layout="Model", paper="A3", landscape=True, fit=True)))
    return r

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("dwg"); ap.add_argument("--spec", required=True); ap.add_argument("--out", required=True); ap.add_argument("--item", required=True); ap.add_argument("--name", default="")
    a = ap.parse_args(); spec = json.load(open(a.spec, encoding="utf-8")); os.makedirs(a.out, exist_ok=True)
    import datetime
    m = cc_read.MCP()
    try:
        m.call("open", dict(path=a.dwg)); tag_dwg(m, spec)
        out_dwg = os.path.join(a.out, f"{a.item}_cadcraft_tagged.dwg"); m.call("save", dict(path=out_dwg).copy())
        r = schedule_pdf(m, spec["comps"], a.item, a.name, os.path.join(a.out, f"{a.item}_schedule.pdf").replace("\\", "/"), f"{datetime.date.today():%d %b %Y}")
        print(out_dwg, r)
    finally:
        m.close()
