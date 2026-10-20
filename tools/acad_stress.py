"""Stress test for the headless AutoCAD path: N mixed jobs in a row, each timed, each verified, stray processes checked.
Usage: python tools/acad_stress.py --n 50 --out DIR [--label closed|open]
Jobs rotate: health check, read solids (acad_solids) on two DWGs, plot a layout. Writes stress_<label>.json + .md."""
import argparse, datetime, json, os, subprocess, sys, time, tempfile, shutil
sys.path.insert(0, os.path.dirname(__file__))
import acad_core as C

T = os.path.join(os.environ["LOCALAPPDATA"], "Temp")
JOBS_SRC = {
    "lexi3": os.path.join(T, "lexi3.dwg"),
    "L02": os.path.join(T, "l02_input.dwg"),
    "sheet": r"C:/Users/Admin/Documents/Hasil-DWG/acad/lexi_k1_sheet_vpon.dwg",
}
PY = sys.executable
TOOLS = os.path.dirname(os.path.abspath(__file__))


def stray():
    out = subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()
    return out.count("accoreconsole.exe")


def job_health(w):
    r = C.health_check()
    return r["pass"], "; ".join(f"{k}:{v['detail']}" for k, v in r["steps"].items())


def job_solids(w, name):
    dwg = os.path.join(w, name + ".dwg"); shutil.copy(JOBS_SRC[name], dwg)
    out = os.path.join(w, name + ".json")
    p = subprocess.run([PY, os.path.join(TOOLS, "acad_solids.py"), dwg, "--json", out], capture_output=True, text=True, timeout=240)
    if not os.path.exists(out):
        return False, "no json: " + (p.stdout + p.stderr)[-200:]
    d = json.load(open(out))
    n = len(d.get("solids", []))
    exp = {"lexi3": 72, "L02": 22}[name]
    return n == exp, f"readable solids {n} (expected {exp})"


def job_plot(w):
    pdf = os.path.join(w, "plot.pdf")
    ok, why = C.plot_layout(JOBS_SRC["sheet"], "SHEET", pdf)
    return ok, why


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=50); ap.add_argument("--out", required=True); ap.add_argument("--label", default="closed")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    kinds = ["health", "solids:lexi3", "plot", "solids:L02", "plot"]
    rows = []
    t_all = time.time()
    for i in range(a.n):
        k = kinds[i % len(kinds)]
        w = tempfile.mkdtemp(prefix="stress_")
        t0 = time.time()
        try:
            if k == "health":
                ok, why = job_health(w)
            elif k.startswith("solids"):
                ok, why = job_solids(w, k.split(":")[1])
            else:
                ok, why = job_plot(w)
        except subprocess.TimeoutExpired:
            ok, why = False, "python-level timeout"; C.kill_stray()
        except Exception as e:
            ok, why = False, f"exception: {e}"[:200]; C.kill_stray()
        dt = time.time() - t0
        s = stray()
        rows.append(dict(i=i + 1, job=k, ok=bool(ok), seconds=round(dt, 1), stray_after=s, detail=why[:200]))
        print(f"{i+1:>3} {k:<13} {'OK ' if ok else 'FAIL'} {dt:5.1f}s stray={s} {why[:90]}", flush=True)
        shutil.rmtree(w, ignore_errors=True)
    total = time.time() - t_all
    summary = dict(label=a.label, n=a.n, passed=sum(r["ok"] for r in rows), failed=[r for r in rows if not r["ok"]],
                   stray_events=sum(1 for r in rows if r["stray_after"]), total_seconds=round(total), when=datetime.datetime.now().isoformat(timespec="seconds"),
                   per_job={k: dict(n=sum(1 for r in rows if r["job"] == k), ok=sum(1 for r in rows if r["job"] == k and r["ok"]),
                                   avg_s=round(sum(r["seconds"] for r in rows if r["job"] == k) / max(1, sum(1 for r in rows if r["job"] == k)), 1),
                                   max_s=max([r["seconds"] for r in rows if r["job"] == k] or [0])) for k in kinds})
    json.dump(dict(summary=summary, rows=rows), open(os.path.join(a.out, f"stress_{a.label}.json"), "w"), indent=1)
    md = [f"# Uji ketahanan AutoCAD headless ({a.label}) - {summary['when']}", "", f"Lulus **{summary['passed']} / {a.n}**, proses sisa: {summary['stray_events']} kejadian, total {summary['total_seconds']} s.", "",
          "| Pekerjaan | n | lulus | rata-rata s | maks s |", "|---|---|---|---|---|"]
    for k, v in summary["per_job"].items():
        md.append(f"| {k} | {v['n']} | {v['ok']} | {v['avg_s']} | {v['max_s']} |")
    if summary["failed"]:
        md += ["", "## Gagal"] + [f"- #{r['i']} {r['job']}: {r['detail']}" for r in summary["failed"]]
    open(os.path.join(a.out, f"stress_{a.label}.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    print(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
