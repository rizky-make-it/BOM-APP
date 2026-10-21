"""Read a DWG through CADCraft (cadcraft-cli mcp, stdio JSON-RPC). Same idea as acad_read.read(): returns lines, polylines, dims, leaders.
Usage: python tools/cc_read.py <dwg> [--out json]"""
import json, os, subprocess, sys, time
CLI = os.environ.get("CADCRAFT_CLI", "C:/Users/Admin/tools/cadcraft/cadcraft-0.8.0-windows-x64-portable/cadcraft-cli.exe")

class MCP:
    def __init__(self):
        self.p = subprocess.Popen([CLI, "mcp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1); self.n = 0
        self._send(dict(jsonrpc="2.0", id=0, method="initialize", params=dict(protocolVersion="2024-11-05", capabilities={}, clientInfo=dict(name="bom-app", version="1")))); self.p.stdout.readline()
    def _send(self, o): self.p.stdin.write(json.dumps(o) + "\n"); self.p.stdin.flush()
    def call(self, name, args):
        self.n += 1; self._send(dict(jsonrpc="2.0", id=self.n, method="tools/call", params=dict(name=name, arguments=args)))
        r = json.loads(self.p.stdout.readline()); return json.loads(r["result"]["content"][0]["text"])
    def close(self): self.p.terminate()

def _xyz(p): return [p["x"], p["y"], p.get("z", 0.0)]
def _all(m, typ):
    out, off = [], 0
    while True:
        r = m.call("query_entities", dict(type=typ, limit=2000, offset=off)); out += r["entities"]; off += r["returned"]
        if off >= r["count"] or not r["returned"]: return out

def read(dwg):
    t0 = time.time(); m = MCP()
    try:
        w = m.call("open", dict(path=dwg).copy()); info = m.call("inspect_drawing", {})
        d = dict(lines=[], polylines=[], dims=[], leaders=[], mtext=[], warnings=w.get("warnings", []), counts=info.get("counts", {}), layouts=info.get("layouts", []))
        for e in _all(m, "LINE"):
            g = e["geometry"]; d["lines"].append([_xyz(g["a"]), _xyz(g["b"]), e["layer"]])
        seen = set()
        for typ in ("POLYLINE", "LWPOLYLINE", "Polyline"):
            try:
                for e in _all(m, typ):
                    if e["handle"] in seen: continue
                    seen.add(e["handle"])
                    g = e["geometry"]; pts = [_xyz(v["p"] if "p" in v else v) for v in (g.get("points") or g.get("vertices") or []) if isinstance(v, dict)]
                    d["polylines"].append(dict(pts=pts, closed=int(bool(g.get("closed"))), layer=e["layer"], kind=e["type"]))
            except Exception: pass
        for e in _all(m, "DIMENSION"):
            g = e["geometry"]; d["dims"].append(dict(value=g.get("measurement"), text=g.get("text", ""), def1=_xyz(g["p13"]), def2=_xyz(g["p14"]), layer=e["layer"]))
        for e in _all(m, "MULTILEADER"):
            g = e["geometry"]; tx = g.get("text") or {}; ls = g.get("leaders") or [[]]
            d["leaders"].append(dict(handle=e["handle"], text=(tx.get("contents") or "").strip(), tip=_xyz(ls[0][0]) if ls and ls[0] else None, landing=_xyz(g["landing"]), dogleg=g.get("dogleg"), th=tx.get("height"), layer=e["layer"]))
        for e in _all(m, "MTEXT"):
            g = e["geometry"]; d["mtext"].append(dict(text=g.get("contents", ""), insert=_xyz(g["insert"])))
        d["_reader"] = "CADCraft MCP"; d["_seconds"] = round(time.time() - t0, 1); return d
    finally:
        m.close()

if __name__ == "__main__":
    r = read(sys.argv[1]); print({k: (len(v) if isinstance(v, list) else v) for k, v in r.items()})
    if "--out" in sys.argv: json.dump(r, open(sys.argv[sys.argv.index("--out") + 1], "w"))


def read_compat(dwg):
    """CADCraft MCP -> the same dict shape as acad_read.read(), so dwg2d_read / dwg2d_components can run unchanged.
    Polylines come as OCS without the extrusion normal: assume the drafter plane (XZ -> normal (0,-1,0), XY -> (0,0,1)), picked from where the LINEs lie."""
    t0 = time.time(); m = MCP()
    try:
        m.call("open", dict(path=dwg)); d = dict(lines=[], polylines=[], dims=[], leaders=[], model_leaders=[], paper_leaders=[], layouts=[])
        for e in _all(m, "LINE"):
            g = e["geometry"]; d["lines"].append([_xyz(g["a"]), _xyz(g["b"]), e["layer"]])
        n_xz = sum(1 for l in d["lines"] if abs(l[0][1]) < 1e-3 and abs(l[1][1]) < 1e-3); n_xy = sum(1 for l in d["lines"] if abs(l[0][2]) < 1e-3 and abs(l[1][2]) < 1e-3)
        xz = n_xz >= n_xy
        for e in _all(m, "LWPOLYLINE"):
            g = e["geometry"]; el = g.get("elevation", 0.0) or 0.0
            pts = [[v["p"]["x"], -el, v["p"]["y"]] if xz else [v["p"]["x"], v["p"]["y"], el] for v in g.get("vertices", [])]
            d["polylines"].append(dict(pts=pts, closed=int(bool(g.get("closed"))), layer=e["layer"]))
        for e in _all(m, "DIMENSION"):
            g = e["geometry"]
            d["dims"].append(dict(value=g.get("measurement"), text=g.get("text", ""), def1=_xyz(g["defpt"]), def2=_xyz(g.get("p14") or g["p13"]), textpos=_xyz(g.get("textMid") or g["defpt"]), layer=e["layer"]))
        for e in _all(m, "MULTILEADER"):
            g = e["geometry"]; tx = g.get("text") or {}; ls = g.get("leaders") or [[]]
            if not ls or not ls[0]: continue
            lan = _xyz(g["landing"]); ins = _xyz(tx["insert"]) if tx.get("insert") else lan
            d["leaders"].append(dict(handle=e["handle"], text=(tx.get("contents") or "").strip(), tip=_xyz(ls[0][0]), landing=lan, textpos=ins, dogleg=g.get("dogleg") or 0.0,
                                     dir=[1 if ins[0] >= lan[0] else -1, 0, 0], th=tx.get("height") or 0.0, layer=e["layer"]))
        d["_reader"] = "CADCraft MCP"; d["_seconds"] = round(time.time() - t0, 1); d["_source"] = os.path.abspath(dwg); return d
    finally:
        m.close()
