"""Vector extraction + annotated crops for one drawing (steps 1, 2, 4 of the production reading flow).

  python data/napier/extract_vector.py "<pdf>" <tag>
Writes data/napier/extract/<tag>/
  numbers.json   every numeric label with page, id, value, x, y (PDF points) - exact, from the text layer
  p<N>_<q>.png   page crops (2x2 grid, 260 dpi) with a red id tag next to each number
"""
import json, os, re, sys
import pymupdf
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DPI = 260


def run(pdf, tag):
    out = os.path.join(ROOT, "data", "napier", "extract", tag)
    os.makedirs(out, exist_ok=True)
    doc = pymupdf.open(pdf)
    nums, k = [], 0
    scale = DPI / 72
    for pi, pg in enumerate(doc):
        pix = pg.get_pixmap(dpi=DPI)
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        dr = ImageDraw.Draw(im)
        try:
            font = ImageFont.truetype("arialbd.ttf", 22)
        except Exception:
            font = ImageFont.load_default()
        for w in pg.get_text("words"):
            x0, y0, x1, y1, txt = w[:5]
            if not re.fullmatch(r"R?\d+(?:[.,]\d+)?", txt):
                continue
            k += 1
            nums.append(dict(id=k, page=pi + 1, value=txt, x=round((x0 + x1) / 2, 1), y=round((y0 + y1) / 2, 1), w=round(x1 - x0, 1), h=round(y1 - y0, 1)))
            px, py = x1 * scale + 2, y0 * scale - 2
            label = f"#{k}"
            tw = dr.textlength(label, font=font)
            dr.rectangle((px, py, px + tw + 4, py + 26), fill=(255, 255, 255), outline=(220, 0, 0))
            dr.text((px + 2, py), label, fill=(220, 0, 0), font=font)
        W, H = im.size
        for qi, (a, b) in enumerate([(0, 0), (1, 0), (0, 1), (1, 1)]):
            box = (int(a * W * 0.46), int(b * H * 0.46), int(W * (0.54 + a * 0.46)), int(H * (0.54 + b * 0.46)))
            im.crop(box).save(os.path.join(out, f"p{pi + 1}_{'LR'[a]}{'TB'[b]}.png"))
    json.dump(nums, open(os.path.join(out, "numbers.json"), "w"), indent=1)
    return out, nums


if __name__ == "__main__":
    o, n = run(sys.argv[1], sys.argv[2])
    print(o, len(n), "numbers tagged")
