"""Gemini drawing reader (via local 9router) for BOM-APP.

Sends every page of a working drawing (rendered at high dpi) PLUS the exact numbers extracted from the PDF text layer
to Gemini, and asks for a component list where EVERY value carries a status:
  STATED   = the number is printed on the drawing
  DERIVED  = computed from printed numbers (formula given)
  ASSUMED  = not on the drawing
Then diff_against_spec() compares the read with an existing spec JSON and lists mismatches for a human to check.

Usage (repo root):
  python data/napier/gemini_read.py "data/napier/src/LV433.B41 - ....pdf" [model]
Outputs data/napier/read/<code>__<model>.json
"""
import base64, json, os, re, sys, time, urllib.request
import pymupdf

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
from pipeline import get_9router_key

OUT = os.path.join(ROOT, "data", "napier", "read")
os.makedirs(OUT, exist_ok=True)

PROMPT = """You are a furniture BOM estimator reading a manufacturing drawing (units mm). Item: {code}.
Attached: every page of the drawing as an image, and below the raw numbers/text found in the PDF text layer (exact, trusted).

Rules:
- Use ONLY numbers visible on the drawing or computed from them. Never invent a size.
- Every size/qty carries a status: "STATED" (printed on drawing), "DERIVED" (give the formula, e.g. 1800-2*60), or "ASSUMED" (not on drawing; say why).
- Material codes on the drawing: PLY=plywood, MDF=MDF board, MSF/MDF suffix after PLY = veneer faces. Report what is written.
- Separate groups: solid wood / metal frame, panels (ply or MDF), hardware. List drawer boxes, doors, shelves, back panels, top frame, legs, rails, dividers.
- Give totals check: overall W/D/H from the drawing header and whether your parts add up (e.g. 60+1680+60 = 1800).

Return ONLY JSON:
{{"overall":{{"w":0,"d":0,"h":0}},
 "components":[{{"group":"solid|metal|panel|hardware","name":"","l":0,"w":0,"t":0,"qty":0,"material":"","l_status":"STATED|DERIVED|ASSUMED","w_status":"","t_status":"","qty_status":"","how":"formula or where on drawing","page":0}}],
 "checks":[{{"what":"","ok":true,"detail":""}}],
 "doubts":["anything you could not read with certainty"]}}

PDF TEXT LAYER (numbers and labels):
{text}
"""


def pdf_images(pdf, dpi=170):
    d = pymupdf.open(pdf)
    imgs, texts = [], []
    for i, pg in enumerate(d):
        imgs.append(base64.b64encode(pg.get_pixmap(dpi=dpi).tobytes("png")).decode())
        texts.append(f"[page {i + 1}] " + " | ".join(x.strip() for x in pg.get_text().split("\n") if x.strip()))
    return imgs, "\n".join(texts)


def ask(pdf, model="ag/gemini-3.8-flash-high", dpi=170, timeout=600):
    code = re.search(r"LV\d+\.\w+", os.path.basename(pdf)).group(0)
    imgs, text = pdf_images(pdf, dpi)
    content = [{"type": "text", "text": PROMPT.format(code=code, text=text[:12000])}]
    for b in imgs:
        content.append({"type": "image_url", "image_url": {"url": "data:image/png;base64," + b}})
    body = {"model": model, "max_tokens": 24000, "stream": True, "messages": [{"role": "user", "content": content}]}
    req = urllib.request.Request("http://127.0.0.1:20128/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "Authorization": "Bearer " + get_9router_key()})
    chunks, t0 = [], time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for line in resp:
            line = line.decode("utf-8", "replace").strip()
            if line.startswith("data:") and not line.endswith("[DONE]"):
                try:
                    chunks.append(json.loads(line[5:])["choices"][0]["delta"].get("content") or "")
                except Exception:
                    pass
    raw = "".join(chunks)
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise ValueError("no JSON: " + raw[:400])
    data = json.loads(m.group(0))
    data["_meta"] = dict(code=code, model=model, seconds=round(time.time() - t0, 1), dpi=dpi)
    fn = os.path.join(OUT, f"{code.replace('.', '-')}__{model.split('/')[-1]}.json")
    json.dump(data, open(fn, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return data, fn


if __name__ == "__main__":
    pdf = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else "ag/gemini-3.8-flash-high"
    data, fn = ask(pdf, model)
    print(fn, data["_meta"], len(data["components"]), "components")
