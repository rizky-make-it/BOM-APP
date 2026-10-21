"""BOMTAG JSON (from the AutoCAD command BOMEXPORT) -> <item>_components.json, the same file dwg2d_components writes, so dwg2d_to_spec / dwg2bom run unchanged.
python tools/bomtag_import.py <drawing>_bomtag.json --item CODE --name NAME [--dwg SOURCE.dwg] [--out DIR]
Rules: one component row per tag NUMBER (the drafter reuses a number for identical parts); the first tag with that number sets the data; two different specs under one number are reported
and the row becomes CHECK. A tag marked CHECK by BOMTAG stays CHECK. Nothing is guessed: sizes and qty are exactly what the drafter typed."""
import argparse, datetime, json, os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def convert(tags, item, name, dwg=""):
    pm = json.load(open(os.path.join(ROOT, "data", "part_master_v3.json"), encoding="utf-8")); parts = pm["parts"] if isinstance(pm, dict) else pm
    rows = {}; conflicts = []
    for t in tags:
        r = int(t["row"]); spec = (t["part_no"], round(t["l"], 1), round(t["w"], 1), round(t["t"], 1), t["code"])
        if r in rows:
            if rows[r]["_spec"] != spec:
                conflicts.append(f"nomor {r}: {rows[r]['_spec']} vs {spec}"); rows[r]["status"] = "CHECK"
            continue
        rows[r] = dict(row=r, no=int(t["part_no"]), name=t["name"], l=t["l"], w=t["w"], t=t["t"], qty=int(t["qty"]), code=t["code"], status=t["status"],
                       note=f"[DRAFTER TAG {r}] diketik/diukur oleh drafter lewat BOMTAG; tag {t['status']}", src="bomtag", _spec=spec)
    comps = [{k: v for k, v in c.items() if k != "_spec"} for _, c in sorted(rows.items())]
    return dict(item=item, name=name, source_dwg=os.path.abspath(dwg) if dwg else "", generated=datetime.datetime.now().isoformat(timespec="seconds"), reader="BOMTAG (drafter)",
                part_list=f"Part Master v{pm.get('version', '3')} ({pm.get('updated', '')}, {len(parts)} parts) + factory material codes", components=comps, labels_rewritten=len(tags), labels_unmatched=[],
                drawing_dimensions_mm={}, views=0, faces=0, conflicts=conflicts)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("json"); ap.add_argument("--item", required=True); ap.add_argument("--name", default=""); ap.add_argument("--dwg", default=""); ap.add_argument("--out", default=".")
    a = ap.parse_args(); tags = json.load(open(a.json, encoding="utf-8"))["tags"]; out = convert(tags, a.item, a.name, a.dwg); os.makedirs(a.out, exist_ok=True)
    fn = os.path.join(a.out, f"{a.item}_components.json"); json.dump(out, open(fn, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"{fn}: {len(out['components'])} baris dari {len(tags)} tag; CHECK {sum(1 for c in out['components'] if c['status'] == 'CHECK')}; konflik {len(out['conflicts'])}")
    for c in out["conflicts"]: print("  KONFLIK", c)
