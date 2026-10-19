"""Post-commit automation (Rizky, 19 Oct 2026): push to GitHub, then log the commit into the Obsidian vault.

Called by .git/hooks/post-commit. Never fails the commit: every error is caught and written to the vault log.
Install on a new clone: sh tools/install_hooks.sh
"""
import datetime
import os
import re
import subprocess
import sys

VAULT = r"C:\Users\Admin\Documents\Hermes Vault"


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, encoding="utf-8", errors="replace")


def main():
    h = git("log", "-1", "--format=%h").stdout.strip()
    subj = git("log", "-1", "--format=%s").stdout.strip()
    nfiles = len([l for l in git("show", "--name-only", "--format=", "HEAD").stdout.splitlines() if l.strip()])

    p = git("push", "origin", "HEAD")
    if p.returncode == 0:
        status = "pushed"
    else:
        status = "PUSH GAGAL: " + (p.stderr.strip().splitlines() or ["?"])[-1][:120]
    print(f"[post-commit] {h} {status}")

    if not os.path.isdir(VAULT):
        print("[post-commit] vault tidak ditemukan, log dilewati")
        return
    now = datetime.datetime.now()
    log = os.path.join(VAULT, "07-Log", now.strftime("%Y-%m-%d") + ".md")
    os.makedirs(os.path.dirname(log), exist_ok=True)
    if not os.path.exists(log):
        open(log, "w", encoding="utf-8", newline="\n").write(f"# Log {now.strftime('%d %b %Y')} (BOM-APP)\n")
    line = f"- {now.strftime('%H:%M')} commit `{h}` ({nfiles} file, {status}): {subj[:160]}\n"
    with open(log, "a", encoding="utf-8", newline="\n") as f:
        f.write(line)

    idx = os.path.join(VAULT, "00-Index.md")
    if os.path.exists(idx):
        s = open(idx, encoding="utf-8").read()
        s2 = re.sub(r"(commit terakhir )`[0-9a-f]{7,}`", r"\g<1>`" + h + "`", s, count=1)
        if s2 != s:
            open(idx, "w", encoding="utf-8", newline="\n").write(s2)


def rebuild_graph():
    """Refresh vault/10-Auto (knowledge graph) from the latest specs, rates and git history."""
    here = os.path.dirname(os.path.abspath(__file__))
    r = subprocess.run([sys.executable, os.path.join(here, "build_vault_graph.py")], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=280)
    tail = (r.stdout.strip().splitlines() or ["?"])
    print("[post-commit] graph:", tail[0][:120] if r.returncode == 0 else "GAGAL " + (r.stderr.strip().splitlines() or ["?"])[-1][:120])


if __name__ == "__main__":
    try:
        main()
        rebuild_graph()
    except Exception as e:  # never block a commit
        print("[post-commit] error:", e)
    sys.exit(0)
