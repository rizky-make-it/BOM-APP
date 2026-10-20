"""2D drafter drawing -> BOM-APP spec JSON (the output BOM-APP can read).

Input : tallboy_2d_statement.json (STATED label+size rows from tools/dwg2d_statement.py) + the drafter's dimensions.
Output: data/lexi/lexi_tb4_spec.json in the exact shape of data/sienna/*_spec.json (header, solid_parts, panel_parts,
        hardware_parts), ready for the engine and the workbook generator.

Honesty rules (written into every note):
  STATED  = number/label printed on the drafter's 2D drawing
  DERIVED = computed from STATED by a factory rule (RULES thickness, derive_drawer_box, standard glide)
  ASSUMED = my reading of the drawing where it is silent; listed at the end for the drafter to confirm
Thickness follows RULES (Part Master v3): top/side C18 1X (MDF veneer E0 18, 1 face), back B9 1X (ply 9 veneer 1 face),
drawer front MDF 18 two... (meeting: drawer front MDF 1 face), drawer box via derive_drawer_box (ply 12 / base 6).
"""
import json, os, sys
sys.path.insert(0, r"C:/Users/Admin/Desktop/BOM-APP"); os.chdir(r"C:/Users/Admin/Desktop/BOM-APP")
from core.rules_v2 import derive_drawer_box
from dataclasses import asdict

# ---- STATED facts from the drafter's 2D drawing (tallboy 4 laci, lexi 3.dwg, SECTION A/B/C + views)
W_OVERALL, D_OVERALL, H_OVERALL = 950, 450, 1100     # STATED: dims 950 / 450 ; height from leg 1040+... -> STATED 1100? see ASSUMED
LEG_SECTION = 40                                     # STATED: 40 x 40 solid wood mindi
LEG_LEN = 1060                                       # STATED: 1060 (one post reads 1040: ASSUMED front/back differ or draw error)
TOP_T, SIDE_T, BACK_T = 20, 20, 9                    # STATED on drawing (RULES override below)
RAIL_392, RAIL_370 = 392, 370                        # STATED rail lengths (sections 40 x 40 / 40 x 25 / 40 x 20)
DRAWER_W, DRAWER_H, N_DRAWERS = 870, 350, 4          # STATED: opening 870, drawer face height 350 x4, drawer front 870 x 295 solid
BOX_W_PLAN, BOX_D_PLAN = 910, 421                    # STATED: drawer box plan 910 x 421 (ply 12) -> inner box width ~816, depth 415/421
CASE_INNER_W = W_OVERALL - 2 * LEG_SECTION           # 870 DERIVED = matches STATED 870
ASSUMED = []

def A(msg):
    ASSUMED.append(msg); return msg

header = dict(item_code="LEXI-TB4", item_name="4 DRAWER TALLBOY", collection="LEXI / Bedroom",
              overall_l=float(W_OVERALL), overall_w=float(D_OVERALL), overall_h=float(H_OVERALL), order_qty=1,
              drawing_link="lexi 3.dwg (layout '4 dw tallboy'; model SECTION A/B/C x 25645-26600)",
              finish_recipe="NC NATURAL", flatpack_yn="N",
              notes=A("Item code LEXI-TB4 dan koleksi LEXI sementara (tidak ada di gambar): CONFIRM. Tinggi 1100 = kaki 1060 + top 20 + ... : CONFIRM."))

solid = []
def S(label, comp, l, w, t, qty, note, exposed="Y", tier="B"):
    solid.append(dict(label=label, component=comp, l=float(l), w=float(w), t=float(t), qty=int(qty), material="MINDI",
                      exposed=exposed, curved="N", tier_override=tier, note=note))

S("3 / A", "LEG", LEG_LEN, LEG_SECTION, LEG_SECTION, 4, "STATED: solid wood mindi 40x40, L 1060 (satu tiang terbaca 1040: " + A("kaki 1040 vs 1060, dipakai 1060") + ")", tier="A")
S("15 / A", "SIDE RAIL", RAIL_392, 40, 40, 6, "STATED: 392 x 40 x 40 x6 (rel samping antar kaki, 3 per sisi)")
S("14 / A", "FRONT RAIL", DRAWER_W, 40, 20, 5, "DERIVED: rel depan antar laci = bukaan 870 (STATED) x 40 x 20; 5 rel untuk 4 laci (" + A("jumlah rel depan 5 dan penampang 40x20") + ")")
S("16 / A", "BACK RAIL", RAIL_370, 40, 25, 3, "STATED: 370 x 40 x 25 x3 (penampang 40x25 terbaca di potongan)")
S("1 / A", "BOTTOM STRETCHER FRONT / BACK", DRAWER_W, 20, 40, 1, "STATED: 870 x 20 di bawah laci terbawah")
S("6 / A", "FRONT DRAWER (solid)", DRAWER_W, 295, 20, N_DRAWERS, "STATED: muka laci solid wood mindi 870 x 295; tebal 20 " + A("tebal muka laci solid 20 (gambar tidak tegas)") + ". RULES untuk muka laci MDF tidak dipakai karena gambar menyatakan SOLID WOOD")

panels = []
def P(label, comp, ptype, l, w, t, qty, faces, note):
    panels.append(dict(label=label, component=comp, panel_type=ptype, l=float(l), w=float(w), t=float(t), qty=int(qty), exposed_faces=int(faces), note=note))

P("20 / C-18-1X", "TOP PANEL", "LND-MDF-E0-18-MSF", W_OVERALL, D_OVERALL, 18, 1, 1, "STATED 950 x 450 x 20 veneer mindi 1F; RULES: MDF veneer E0 18 mm 1 muka (tebal gambar 20 diabaikan)")
P("13 / C-18-1X", "SIDE PANEL", "LND-MDF-E0-18-MSF", LEG_LEN - 40, D_OVERALL - 2 * LEG_SECTION, 18, 2, 1,
  "STATED tebal 20 veneer 1F, kedalaman 745? (dua angka: 745 dan 450): " + A("side panel dipakai (1060-40) x (450-80)=370 lebar antar kaki; angka 745 di gambar belum dipahami") + "; RULES: MDF veneer E0 18 1 muka")
P("12 / B-9-1X", "BACK PANEL", "LND-PLY-E0-9-MSF", CASE_INNER_W, LEG_LEN - 40, 9, 1, 1, "STATED 9 mm veneer 1F; lebar = bukaan 870 (DERIVED), tinggi 1020 (DERIVED, antar rel atas-bawah); RULES: ply E0 9 veneer 1 muka")

# drawer boxes by factory rule from the STATED opening 870 x 350, case depth 450
box = derive_drawer_box(w_front=DRAWER_W, h_front=DRAWER_H, case_depth=D_OVERALL, qty=N_DRAWERS)
box_parts = []
# Same convention as the Sienna specs: 3 rows per drawer set = side (x2/drawer), box front/back (x2/drawer), base (x1/drawer)
for key, comp, label in (("side", "SIDE DRAWER", "8 / B-12-0X"), ("box_front_back", "DRAWER BOX FRONT/BACK", "7 / B-12-0X"), ("bottom", "DRAWER BASE", "10 / B-6-0X")):
    d = asdict(box[key]); d["component"] = comp; d["label"] = label
    d["note"] = "DERIVED derive_drawer_box(870 x 350, case 450): " + d["note"] + " | gambar: dinding laci ply 12 h 109 (L 816 / 326), dasar ply 6 (824 / 335), kedalaman 415-421"
    box_parts.append(d)
panels += box_parts

hardware = [
    dict(item_master_code="HARDWARE", label="D2 / DTC-14", description='DRAWER RAIL DTC 14" (356 MM) soft close', vendor="Sukey / DTC", qty=float(N_DRAWERS), uom="set", unit_price=61396.2,
         note="DERIVED: 4 laci x 1 set; panjang rel 14\" dari glide standar kedalaman 450 (" + A("rel laci 14 inch") + "); harga dari item Sienna B61"),
    dict(item_master_code="HARDWARE", label="HNDL", description="Handle laci", vendor="Lokal", qty=float(N_DRAWERS), uom="pcs", unit_price=0.0,
         note=A("handle tidak terlihat di gambar: qty 4, harga kosong")),
]

spec = dict(header=header, solid_parts=solid, panel_parts=panels, hardware_parts=hardware,
            _provenance=dict(source="lexi 3.dwg (drafter 2D)", method="tools/dwg2d_labels.py + dwg2d_statement.py -> this builder",
                             stated_rows=22, assumed=ASSUMED))
os.makedirs("data/lexi", exist_ok=True)
json.dump(spec, open("data/lexi/lexi_tb4_spec.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
json.dump(["LEXI-TB4"], open("data/lexi/_order.json", "w"))
print("spec written: solid", len(solid), "panel", len(panels), "hw", len(hardware)); print("ASSUMED:", *ASSUMED, sep="\n - ")
