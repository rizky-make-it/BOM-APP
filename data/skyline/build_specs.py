"""SKYLINE CABINET: 2 pintu. Sumber: daftar potong drafter 'SKYLINE (1)-CG 29.pdf' (A-H, QTY/DOOR SET) x 2 pintu (Rizky, 21 Okt 2026).
Hardware dikosongkan (Rizky isi sendiri). Badan lemari tidak ada di gambar -> tidak dihitung."""
import json, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")); sys.path.insert(0, ROOT)
from core.panel_rules import to_e0
DOORS = 2
# (huruf, nama, L, W, T, qty per door set, bahan, exposed)
SOLID = [("A", "Door stile", 2110, 43, 23, 2), ("B", "Door top/bottom rail", 445, 43, 23, 2), ("C", "Door centre stile", 2064, 89, 23, 1),
         ("D", "Door mid rail", 198, 89, 23, 6), ("E", "Panel bevel strip short", 158, 40, 8, 16), ("F", "Panel bevel strip long", 439, 40, 8, 16)]
PANEL = [("G", "Door panel plywood", 449, 158, 7, 4), ("H", "Door panel plywood (wide)", 459, 158, 7, 4)]
solid = [dict(label=f"{k} / A", component=n, l=float(l), w=float(w), t=float(t), qty=q * DOORS, material="MINDI", exposed="Y", curved="N", tier_override="B",
              note=f"[STATED] daftar potong drafter {k}: {l}x{w}x{t}, {q}/pintu x {DOORS} pintu; bahan SOLID WOOD [ASSUMED] jenis MINDI") for k, n, l, w, t, q in SOLID]
BODY = [  # diukur dari garis DWG (model space), tebal ikut RULES 18 (gambar 24/30)
    ("Side panel", "LND-MDF-E0-18-MSF", 2090, 481, 2, 1, "[MEASURED] tinggi 0-2090, kedalaman 31-512 dari tampak samping; gambar tebal 24 -> RULES 18"),
    ("Top", "LND-PLY-E0-18-MDF", 1000, 521, 1, 1, "[MEASURED] 1000 x 521 (tebal gambar 30 -> RULES 18)"),
    ("Bottom", "LND-PLY-E0-18", 952, 481, 1, 0, "[MEASURED] 952 = 1000-2x24 dinding; kedalaman 481"),
    ("Shelf", "LND-PLY-E0-18-MSF", 952, 481, 3, 1, "[MEASURED] 3 rak di tinggi 396-420, 963-987, 1529-1553 (4 ruang ~525 sama tinggi panel pintu); tebal gambar 24 -> RULES 18"),
]
body = [dict(label=f"{n}", component=n, panel_type=to_e0(pt), l=float(l), w=float(w), t=18.0, qty=q, exposed_faces=ef, note=nt + "; [ASSUMED] peran/veneer per meeting rule, belakang/back panel TIDAK ada di gambar -> tidak dihitung") for n, pt, l, w, q, ef, nt in BODY]
panels = [dict(label=f"{k} / PLY", component=n, panel_type=to_e0("LND-PLY-E0-6-MSF"), l=float(l), w=float(w), t=6.0, qty=q * DOORS, exposed_faces=1,
               note=f"[STATED] {k}: {l}x{w}x{t} PLYWOOD, {q}/pintu x {DOORS}; [ASSUMED] 7 mm tidak ada di rate card -> E0-6 (terdekat), 1 muka veneer (muka depan pintu)") for k, n, l, w, t, q in PANEL]
spec = dict(header=dict(item_code="SKYLINE-DOOR", item_name="SKYLINE CABINET (2 DOORS + BODY)", collection="SKYLINE", overall_l=1000.0, overall_w=521.0, overall_h=2200.0, order_qty=1,
                        drawing_link="SKYLINE CABINET.dwg", finish_recipe="NC NATURAL", flatpack_yn="N",
                        notes="2 pintu @ 489 x 2110 x 23 (DWG: 2 pintu 489 + 489 = 980; daftar potong PDF). Badan 1000x2200 (kaki 80) diukur dari garis DWG. Back panel TIDAK ada di gambar. Hardware diisi Rizky nanti."),
            solid_parts=solid, panel_parts=panels + body, hardware_parts=[],
            _provenance=dict(stated="ukuran A-H dan qty/pintu dari PDF drafter; 2 pintu dari Rizky", assumed=["solid wood = MINDI", "7 mm plywood -> E0-6", "exposed_faces 1", "finish NC NATURAL", "tebal tidak dipaksa RULES: daftar drafter dipakai apa adanya untuk kayu"]))
json.dump(spec, open(os.path.join(os.path.dirname(__file__), "skyline_door_spec.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("ok", len(solid), len(panels))
