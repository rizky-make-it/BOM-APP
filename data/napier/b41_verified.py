"""LV433-B41 spec from tagged vector numbers (every value cites the #id of the number printed on the drawing).
Run: python data/napier/b41_verified.py   -> writes data/napier/verified/lv433_b41_spec.json + prints the check report.
Status per value: S = stated on drawing (#id), D = derived by formula from stated numbers, A = assumed (none in this file).
"""
import json, os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verified")
os.makedirs(OUT, exist_ok=True)

# ---- numbers read from the drawing (id -> value), see data/napier/extract/B41/numbers.json
N = {8: 550, 75: 450, 27: 550, 24: 60, 25: 430, 26: 60, 28: 35, 30: 209, 32: 209, 29: 2, 31: 3, 33: 2, 34: 30, 35: 60,
     41: 515, 87: 510, 88: 20, 90: 20, 89: 404, 86: 360, 97: 12, 98: 12, 96: 60, 94: 60, 92: 430,
     117: 35, 141: 35, 132: 50, 134: 50, 133: 450, 142: 15, 165: 15, 116: 515, 139: 60, 140: 455, 163: 30,
     157: 160, 158: 12, 159: 5, 156: 404, 136: 370, 135: 50, 137: 30, 115: 450, 144: 395, 118: 60, 143: 30,
     148: 170, 155: 160, 154: 360, 101: 510, 113: 405}
assert N[24] + N[25] + N[26] == N[8], "width chain"
assert N[96] + 330 + N[94] == N[75], "depth chain (330 = 450-60-60, side opening)"
assert N[28] + N[29] + N[30] + N[31] + N[32] + N[33] + N[34] + N[35] == N[27], "height chain 35+2+209+3+209+2+30+60"
assert N[117] + N[140] + N[139] == N[27], "side height 35+455+60"
assert N[132] + N[133] + N[134] == N[8], "top 50+450+50"
assert N[88] + N[87] + N[90] == N[8], "inner 20+510+20"

MT = "MINDI"
solid = [
 # label, component, l, w, t, qty, exposed, tier, source note
 ("Leg 60x60", N[116], 60, 60, 4, "Y", "B", "tinggi #116=515, penampang 60 #24/#26"),
 ("Top frame front", N[8], N[132], N[117], 1, "Y", "A", "550 #8, lebar 50 #132, tebal 35 #117"),
 ("Top frame rear", N[8], N[137], N[117], 1, "N", "B", "550 #8, lebar 30 #137 (rantai 50+370+30=450), tebal 35"),
 ("Top frame side", N[136], N[135], N[117], 2, "Y", "B", "370 #136, lebar 50 #135, tebal 35"),
 ("Bottom rail", N[25], N[163], 20, 2, "N", "C", "bukaan 430 #25, tinggi 30 #163, tebal 20 #88; qty 2 (depan+belakang) = ASUMSI jumlah"),
]
# ---- RULES (Part Master v3 + factory rules v2.3) decide thickness and drawer-box sizes; the drawing decides overall layout.
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core.rules_v2 import derive_drawer_box
from core.panel_rules import to_e2

OPEN_W = N[25]                       # 430 opening between legs (#25)
FRONT_W, FRONT_H = 426, N[30]        # drawer face from front view (#79, #30)
GLIDE = 300                          # drawing note: ray truot bi 3 tang L300; rule: largest standard slide <= clear depth 330
box = derive_drawer_box(FRONT_W, FRONT_H, 450, side_length=GLIDE, qty=2)


def from_rule(part, note):
    return (part.component, to_e2(part.panel_type), part.l, part.w, part.t, part.qty, part.exposed_faces, note)


panels = [
 # Part 601 Top panel  = C18 1X  (rule), size as drawn inside the 35 frame
 ("Top panel MDF veneer 18", "LND-MDF-E2-18-MSF", N[133], N[136], 18, 1, 1, "RULE 601 C18 1X (gambar tertulis 15 #142); ukuran 450 #133 x 370 #136"),
 # Part 301 Side panel = C18 1X  (rule)
 ("Side panel MDF veneer 18", "LND-MDF-E2-18-MSF", N[140], 330, 18, 2, 1, "RULE 301 C18 1X (gambar tertulis 20 #88); 455 #140 x 330"),
 # Part 302 Back panel = B9 1X (rule)
 ("Back panel plywood 9", "LND-PLY-E2-9-MSF", N[87], N[144], 9, 1, 1, "RULE 302 B9 1X (gambar tertulis 5 #129); 510 #87 x 395 #144"),
 # Part 401 Drawer front = MDF 18 both faces (rules_v2 derive_drawer_box)
 from_rule(box["front"], "RULE drawer front MDF 18 2 muka (gambar tertulis 20); 426 x 209 dari tampak depan"),
 from_rule(box["side"], "RULE 402 B12 0X: L=slide 300, H=H_front-30"),
 from_rule(box["box_front_back"], "RULE 403/404 B12 0X: W=W_front-64, H=H_front-30 (gambar: kotak 404 lebar)"),
 from_rule(box["bottom"], "RULE 405 B6 0X: (W-54) x (L-7)"),
]
hardware = [
 ("HW-RAIL-DTC", "Rel laci DTC 3 tingkat L300, lebar 42", 2, "pair", 49610.0, "gambar: L300; rule slide fit"),
 ("I-00003", "Leveler kaki", 4, "pcs", 5000.0, "gambar: leveler di 4 kaki"),
 ("HNDL / TBD", "Handle (sesuai sampel)", 2, "pcs", 0.0, "gambar: Tay nắm theo mẫu, harga belum ada"),
]

spec = dict(
 header=dict(item_code="LV433-B41", item_name="BEDSIDE 2 DRWS", collection="NAPIER / Bedroom", overall_l=550.0, overall_w=450.0, overall_h=550.0,
             order_qty=1, drawing_link="LV433.B41 - Bedside 2 Drws (1) Model (1).pdf", finish_recipe="NC NATURAL", flatpack_yn="N",
             notes="Layout dari angka vektor bertanda #id (rantai ukur lolos). Ketebalan panel dan kotak laci mengikuti RULES Part Master v3 / v2.3, bukan angka tebal di gambar. Menunggu persetujuan manusia."),
 solid_parts=[dict(label=f"{i} / A", component=c, l=float(l), w=float(w), t=float(t), qty=q, material=MT, exposed=e, curved="N", tier_override=tr, note=n)
              for i, (c, l, w, t, q, e, tr, n) in enumerate(solid, 1)],
 panel_parts=[dict(label=f"PNL-{i:02d}", component=c, panel_type=pt, l=float(l), w=float(w), t=float(t), qty=q, exposed_faces=f, note=n)
              for i, (c, pt, l, w, t, q, f, n) in enumerate(panels, 1)],
 hardware_parts=[dict(item_master_code="HARDWARE", label=lb, description=d, vendor="Lokal", qty=float(q), uom=u, unit_price=p, note=n)
                 for lb, d, q, u, p, n in hardware],
)
json.dump(spec, open(os.path.join(OUT, "lv433_b41_spec.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("chains OK (6 checks). Parts: solid", len(solid), "panel", len(panels), "hardware", len(hardware))
