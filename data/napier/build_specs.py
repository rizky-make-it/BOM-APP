"""NAPIER (LV433) spec generator.
Ukuran luar, kaki 60x60, tinggi badan, jumlah laci/pintu dibaca dari gambar kerja (data/napier/src).
Konstruksi casegood/meja (B41 B51 B61 D21 L31 L01 L21) = STANDAR Tala 23 Okt 2026: karkas panel (side 301, bottom 306, back 302, top 601, divider 307, shelf 308/309), laci rumus pabrik,
tanpa top frame dan rail kecil. Bed, meja makan, cermin tetap seperti gambar (dicek terpisah). Semua panel kode E0 eksplisit.
Run from repo root:  python data/napier/build_specs.py   -> lv433_*_spec.json + _order.json
"""
import json, os

OUT = os.path.dirname(os.path.abspath(__file__))
RAIL_PAIR = 49610.0      # HW-RAIL-DTC 2.75 USD x 18,040 (rate card, approved 7 Oct)
HINGE = 10824.0          # HW-HINGE-DTC 0.6 USD x 18,040
LEVELER = 5000.0         # I-00003 nylon leveler M8 (existing price)
SKIP = {7, 20, 601}      # multi_bom.sort_by_part_number treats these labels specially; skip them so rows stay in order


class Item:
    def __init__(self, code, name, room, l, w, h, drawing, flatpack="N", notes=""):
        self.h = dict(item_code=f"LV433-{code}", item_name=name, collection=f"NAPIER / {room}", overall_l=float(l),
                      overall_w=float(w), overall_h=float(h), order_qty=1, drawing_link=drawing, finish_recipe="NC NATURAL",
                      flatpack_yn=flatpack, notes=notes)
        self.s, self.p, self.hw = [], [], []
        self._ns = self._np = self._nh = 0

    def _n(self, attr):
        n = getattr(self, attr) + 1
        while n in SKIP:
            n += 1
        setattr(self, attr, n)
        return n

    def solid(self, comp, l, w, t, q, mat="MINDI", exposed="Y", tier=None, note=""):
        tier = tier or ("C" if exposed == "N" else ("A" if max(l, w, t) >= 1000 else "B"))
        self.s.append(dict(label=f"{self._n('_ns')} / A", component=comp, l=float(l), w=float(w), t=float(t), qty=q,
                           material=mat, exposed=exposed, curved="N", tier_override=tier, note=note))

    def panel(self, comp, ptype, l, w, t, q, faces, note=""):
        self.p.append(dict(label=f"PNL-{self._n('_np'):02d}", component=comp, panel_type=ptype, l=float(l), w=float(w),
                           t=float(t), qty=q, exposed_faces=faces, note=note))

    def hardware(self, label, desc, qty, uom, price, note="", vendor="Lokal"):
        self.hw.append(dict(item_master_code="HARDWARE", label=label, description=desc, vendor=vendor, qty=float(qty),
                            uom=uom, unit_price=float(price), note=note))

    def dump(self):
        d = dict(header=self.h, solid_parts=self.s, panel_parts=self.p, hardware_parts=self.hw)
        fn = f"lv433_{self.h['item_code'][-3:].lower()}_spec.json"
        json.dump(d, open(os.path.join(OUT, fn), "w", encoding="utf-8"), indent=1, ensure_ascii=False)


SIDE_T, TOP_T, BACK_T = 18, 18, 9      # RULES (Part Master v3): side C18 1X, top C18 1X, back B9
LEG = 60                               # kaki / tiang sudut 60x60 (gambar Napier, tetap kayu solid)
MSF18, PLY18, PLY9, MDF2F18 = "LND-MDF-E0-18-MSF", "LND-PLY-E0-18", "LND-PLY-E0-9", "LND-MDF-E0-18-MDF"


def top_and_legs(it, W, D, leg_h):
    """Standar: 4 kaki kayu solid + 1 top panel 601 (tanpa top frame dan rail kecil)."""
    it.solid("Leg 60x60", leg_h, LEG, LEG, 4, tier="B", note="STATED kaki 60x60, tinggi dari gambar")
    it.panel("Top panel MDF veneer 18", MSF18, W, D, TOP_T, 1, 1, "601 | RULES top MDF 18 1 muka; ukuran luar dari gambar (menggantikan top frame 35 + panel 15)")


def carcass(it, W, D, body_h, divider=False, door_unit=False):
    """Karkas panel: 2 side 301, bottom 306, back 302 (+ divider 307). Lebar dalam = W - 2 x 60 (di antara kaki)."""
    wi, di = W - 2 * LEG, D - 2 * LEG
    it.panel("Side panel MDF veneer 18", MSF18, body_h, di, SIDE_T, 2, 1, f"301 | RULES MDF 18 1 muka; tinggi {body_h:g} STATED, lebar {D:g}-2x{LEG} DERIVED")
    it.panel("Bottom panel plywood 18", PLY18, wi, di, 18, 1, 0, f"306 | RULES ply 18 polos; {W:g}-2x{LEG} x {D:g}-2x{LEG} DERIVED")
    it.panel("Back panel plywood 9", PLY9, wi, body_h, BACK_T, 1, 0, f"302 | RULES ply 9; {W:g}-2x{LEG} x {body_h:g} DERIVED (muka luar belakang dianggap polos, ASSUMED)")
    if divider:
        faces = 2 if door_unit else 0
        pt = MDF2F18 if door_unit else PLY18
        it.panel("Divider plywood 18", pt, body_h, di - BACK_T, 18, 1, faces,
                 f"307 | RULES ply 18; muka veneer = {faces} (ASSUMED: {'pintu dibuka = terlihat' if door_unit else 'di belakang laci'}, tanya Rizky); {body_h:g} x ({di:g}-9)")
    return wi, di


def drawers_std(it, n, face_w, face_h, d_side, slide_note="Gambar: rel DTC 3 tingkat L300"):
    """Laci: muka MDF 18 (1 muka) + kotak laci RULES pabrik (inner W-64, H-30, base W-54 x D-7), 3 baris per set."""
    it.panel("Drawer face MDF veneer 18", MSF18, face_w, face_h, 18, n, 1, "401 | STATED ukuran muka dari gambar; MDF 18 1 muka (RULES)")
    it.panel("Drawer box side", "LND-PLY-E0-12", d_side, face_h - 30, 12, 2 * n, 0, f"402 | panjang rel {d_side:g} STATED gambar, tinggi H-30 = {face_h - 30:g}")
    it.panel("Drawer box front/back", "LND-PLY-E0-12", face_w - 64, face_h - 30, 12, 2 * n, 0, f"403 | RULES: W-64 = {face_w - 64:g}, H-30")
    it.panel("Drawer bottom", "LND-PLY-E0-6", face_w - 54, d_side - 7, 6, n, 0, f"405 | RULES: W-54 x D-7 = {face_w - 54:g} x {d_side - 7:g}")
    it.hardware("HW-RAIL-DTC", "Rel laci DTC 3 tingkat L300 (lebar 42 mm)", n, "pair", RAIL_PAIR, slide_note)


def std_notes(it, drawing):
    it.h["notes"] = (f"Dari gambar {drawing[:9]}: ukuran luar, kaki, jumlah laci/pintu dan tinggi badan STATED. "
                     "Konstruksi = STANDAR Tala (karkas panel 301/306/302/601, laci rumus pabrik), bukan rangka rel gambar. Divider/belakang/muka veneer ASSUMED.")


# ----------------------------------------------------------------------------------------------- BEDSIDE / TALLBOY / DRESSER
b = Item("B41", "BEDSIDE 2 DRWS", "Bedroom", 550, 450, 550, "LV433.B41 - Bedside 2 Drws (1) Model (1).pdf")
top_and_legs(b, 550, 450, 515); carcass(b, 550, 450, 455)
drawers_std(b, 2, 426, 209, 300)
b.hardware("HNDL / TBD", "Handle (sesuai sampel)", 2, "pcs", 0.0, "Harga handle belum ada")
b.hardware("I-00003", "Nylon leveler glides M8", 4, "pcs", LEVELER, "Leveler kaki")
std_notes(b, "LV433.B41 - Bedside"); b.dump()

t = Item("B51", "TALLBOY 4 DRWS", "Bedroom", 950, 450, 1100, "LV433.B51 - Tallboy 4 Drws Model (1).pdf")
top_and_legs(t, 950, 450, 1065); carcass(t, 950, 450, 1005)
drawers_std(t, 4, 826, 241, 300)
t.hardware("HNDL / TBD", "Handle (sesuai sampel)", 8, "pcs", 0.0, "2 handle per laci, harga belum ada")
t.hardware("I-00003", "Nylon leveler glides M8", 4, "pcs", LEVELER, "Leveler kaki")
std_notes(t, "LV433.B51 - Tallboy"); t.dump()

d = Item("B61", "DRESSER 6 DRWS", "Bedroom", 1500, 450, 800, "LV433.B61 - Dresser 6 Drws Model (1).pdf")
top_and_legs(d, 1500, 450, 765); carcass(d, 1500, 450, 705, divider=True)
drawers_std(d, 6, 675, 222, 300)
d.hardware("HNDL / TBD", "Handle (sesuai sampel)", 6, "pcs", 0.0, "Harga handle belum ada")
d.hardware("I-00003", "Nylon leveler glides M8", 5, "pcs", LEVELER, "4 sudut + 1 tengah")
std_notes(d, "LV433.B61 - Dresser"); d.dump()


# ----------------------------------------------------------------------------------------------- BUFFET + TV (pintu)
def doors_unit(code, name, room, H, leg_h, body_h, door_h, drawing):
    u = Item(code, name, room, 1800, 450, H, drawing)
    top_and_legs(u, 1800, 450, leg_h)
    wi, di = carcass(u, 1800, 450, body_h, divider=True, door_unit=True)
    u.panel("Adjustable shelf plywood 18", "LND-PLY-E0-18-MSF", (wi - 18) / 2, di - BACK_T - 5, 18, 2, 1,
            f"309 | RULES ply 18 1 muka; ({wi:g}-18)/2 x ({di:g}-9-5) DERIVED, 1 rak per ruang")
    u.panel("Door MDF veneer 18", MDF2F18, door_h, 409, 18, 4, 2, "501 | STATED 4 pintu 409 lebar; MDF 18 2 muka (RULES)")
    u.hardware("HW-HINGE-DTC", "Engsel bật soft close DTC, cup 35 mm 165 derajat", 8, "pcs", HINGE, "2 engsel per pintu")
    u.hardware("HNDL / TBD", "Handle (sesuai sampel)", 4, "pcs", 0.0, "Harga handle belum ada")
    u.hardware("I-00003", "Nylon leveler glides M8", 5, "pcs", LEVELER, "4 sudut + 1 tengah")
    std_notes(u, drawing); u.dump()

doors_unit("D21", "BUFFET 4 DOORS", "Dining", 800, 765, 705, 671, "LV433.D21 - Buffet 4 Drs Model (1).pdf")
doors_unit("L31", "TV UNIT 4 DOORS", "Living", 550, 515, 455, 421, "LV433.L31 - TV Unit 4 Drs. Model (1).pdf")


# ----------------------------------------------------------------------------------------------- COFFEE + CONSOLE (meja terbuka)
def open_table(code, name, room, W, D, H, drawing, box_d):
    u = Item(code, name, room, W, D, H, drawing)
    top_and_legs(u, W, D, H - TOP_T)
    wi, di = W - 2 * LEG, D - 2 * LEG
    u.panel("Bottom shelf plywood 18", "LND-PLY-E0-18-MSF", wi, di, 18, 1, 1, f"308 | RULES ply 18 1 muka (rak terbuka); {W:g}-2x{LEG} x {D:g}-2x{LEG} DERIVED")
    u.panel("Drawer divider plywood 18", PLY18, 155, di - BACK_T, 18, 1, 0, "307 | sekat antar 2 laci, tinggi 155 = muka laci; polos (ASSUMED)")
    drawers_std(u, 2, 535, 155, box_d)
    u.hardware("HNDL / TBD", "Handle (sesuai sampel)", 2, "pcs", 0.0, "Harga handle belum ada")
    u.hardware("I-00003", "Nylon leveler glides M8", 4, "pcs", LEVELER, "Leveler kaki")
    std_notes(u, drawing); u.dump()

open_table("L01", "COFFEE TABLE 2 DRWS & SHELF", "Living", 1300, 600, 480, "LV433.L01 - Coffee Table 2 Drws, 1 shelf Model (1).pdf", 450)
open_table("L21", "CONSOLE TABLE 2 DRWS & SHELF", "Living", 1300, 380, 760, "LV433.L21 - Console Table 2 Drws & Shelf Model (1).pdf", 300)

# ----------------------------------------------------------------------------------------------- DINING TABLE
dt = Item("D02", "DINING TABLE 180x100", "Dining", 1800, 1000, 770, "LV433.D02 - Dining Table 180 x 100 Model (1).pdf", flatpack="Y")
dt.solid("Table top solid glued", 1800, 1000, 35, 1, tier="A", note="Top kayu solid ghep 35 mm (GHEP), R30")
dt.solid("Leg 80x80", 735, 80, 80, 4, tier="B", note="Kaki 80x80, tinggi 735 di bawah top")
dt.solid("Apron long", 1640, 60, 30, 2, tier="A", note="Apron 60 tinggi, tebal 30 diasumsikan")
dt.solid("Apron short", 840, 60, 30, 2, tier="B", note="Apron samping")
dt.hardware("KD-FITTING", "KD fitting kaki ke apron (hybrid bolt + insert nut)", 8, "set", 0.0, "Gambar: KD point, harga belum ada")
dt.hardware("I-00003", "Nylon leveler glides M8", 4, "pcs", LEVELER, "Leveler kaki")
dt.h["notes"] = "Dari gambar LV433.D02. Tebal apron diasumsikan 30; packing flatpack belum dirinci."
dt.dump()

# ----------------------------------------------------------------------------------------------- MIRROR
m = Item("B71", "MIRROR", "Bedroom", 1000, 30, 1000, "LV433.B71 - Mirror Model (1).pdf")
m.solid("Frame horizontal", 1000, 60, 30, 2, tier="B", note="Frame 60x30, miter 45")
m.solid("Frame vertical", 1000, 60, 30, 2, tier="B", note="Frame 60x30, miter 45")
m.solid("Mounting support", 730, 40, 25, 2, exposed="N", tier="C", note="Do do khung guong 730x40x25")
m.panel("Backing MDF veneer 3", "LND-MDF-E0-3", 930, 930, 3, 1, 0, "Gambar: MDFV 4 mm, papan 3 mm terdekat")
m.hardware("I-00007", "Mirror 5 mm, beveled (930 x 930 mm)", 0.865, "m2", 180000.0, "Kaca 5 mm mai vat")
m.hardware("INSERT-NUT", "Insert nut 6x15", 8, "pcs", 0.0, "Harga belum ada")
m.h["notes"] = "Dari gambar LV433.B71. Backing 4 mm dihitung dengan papan 3 mm."
m.dump()

# ----------------------------------------------------------------------------------------------- BEDS
def bed(code, name, W, drawing, notes):
    """W = overall bed width (2120 queen / 2420 king). Headboard posts 60 => inner = W - 120."""
    inner = W - 120
    foot_w = W - 520  # 1600 queen, 1900 king (footboard overall)
    foot_in = foot_w - 120
    u = Item(code, name, "Bedroom", 2130, W, 1200, drawing)
    u.solid("Headboard post", 1200, 60, 40, 2, tier="A", note="Tiang headboard 60x40")
    u.solid("Headboard top rail", inner, 40, 35, 1, tier="A", note="Rel atas 40x35")
    u.solid("Headboard bottom rail", inner, 40, 30, 1, tier="A", note="Rel bawah 40x30")
    u.solid("Footboard post", 450, 60, 40, 2, tier="B", note="Tiang footboard")
    u.solid("Footboard top rail", foot_in, 40, 35, 1, tier="A", note="Rel atas footboard")
    u.solid("Footboard bottom rail", foot_in, 40, 30, 1, tier="A", note="Rel bawah footboard")
    u.solid("Side rail", 2050, 150, 40, 2, tier="A", note="Rel samping 2050x150x40")
    u.solid("Centre leg", 255, 40, 40, 4, exposed="N", tier="C", note="Kaki tengah 255 tinggi")
    u.solid("Slat", 1845 if code == "B02" else 1545, 60, 30, 14, exposed="N", tier="C", note="14 slat (jarak 70)")
    u.solid("Hollow steel 30x60", 2070, 60, 30, 2, mat="METAL", exposed="N", tier="B", note="Hollow steel 30x60x2070, tebal 1.5")
    u.panel("Headboard panel MDF 12 (upholstery)", "LND-MDF-E0-12", 1100, inner - 30, 12, 1, 0, "Panel upholstery headboard")
    u.panel("Footboard panel MDF veneer 12", "LND-MDF-E0-12-MSF", 165, foot_in, 12, 1, 1, "Panel footboard 165 tinggi")
    u.hardware("FABRIC-UPH", "Upholstery fabric", 3.5 if code == "B01" else 4.0, "m lari", 85000.0, "Kain headboard (harga dari koleksi Sienna)")
    u.hardware("FOAM-HIGH", "High density foam 40 mm", 1, "pcs", 45000.0, "Busa headboard")
    u.hardware("BED-BRACKET", "Heavy duty KD bed rail bracket", 4, "pcs", 18500.0, "Hardware ke kaki/bahu")
    u.hardware("I-00003", "Nylon glides / plastic nail 25 mm", 8, "pcs", 3500.0, "Paku plastik dasar kaki")
    u.h["notes"] = notes
    u.dump()

bed("B01", "QUEEN BED WITH UPHOLSTERY", 2120, "LV433.B01 - Queen Bed with Upholstery Model (1).pdf",
    "Dari gambar LV433.B01. Jumlah hollow steel (2), tinggi panel upholstery, jumlah kain dan busa diasumsikan.")
bed("B02", "KING BED WITH UPHOLSTERY", 2420, "LV433.B02 - King Bed with Upholstery.pdf",
    "Dari gambar LV433.B02 (judul gambar tertulis Queen, ukuran W2420 = King). Asumsi sama dengan B01.")

order = ["B01", "B02", "B41", "B51", "B61", "B71", "D02", "D21", "L01", "L21", "L31"]
json.dump([f"LV433-{c}" for c in order], open(os.path.join(OUT, "_order.json"), "w"))
print("wrote", len(order), "specs")
