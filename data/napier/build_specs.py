"""NAPIER (LV433) spec generator. Dimensions are read from the working drawings in data/napier/src.
Run from repo root:  python data/napier/build_specs.py   -> writes data/napier/lv433_*_spec.json + _order.json
Construction (Napier standard seen on every casegood drawing): 60x60 corner legs, 35 mm top frame (50 wide) around a
15 mm MDF-veneer panel, 12 mm MDF-veneer side panels, 20 mm rails, DTC 3-fold L300 slides, leveler feet.
All panels use explicit E0 codes (LND-PLY-E0-* / LND-MDF-E0-*). Items that the drawings do not state are marked in notes.
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


def casegood(it, W, D, H, leg_h, top_t=35):
    """Legs + 35 mm top frame + 15 mm MDF top panel (common to every Napier casegood)."""
    it.solid("Leg 60x60", leg_h, 60, 60, 4, tier="B", note="Kaki 60x60, tinggi di bawah top 35")
    it.solid("Top frame long", W, 50, top_t, 2, note="Frame top 50 x 35 keliling")
    it.solid("Top frame short", D - 100, 50, top_t, 2, note="Frame top sisi pendek")
    it.panel("Top panel MDF veneer 15", "LND-MDF-E0-15-MSF", W - 100, D - 100, 15, 1, 1, "Panel top 15 mm dalam frame")


def drawers_box(it, n, box_w, box_d, box_h, face_w, face_h, label_slide="HW-RAIL-DTC"):
    it.panel("Drawer face MDF veneer 15", "LND-MDF-E0-15-MSF", face_w, face_h, 15, n, 1, "Muka laci 15 mm")
    it.panel("Drawer box side", "LND-PLY-E0-12", box_d, box_h, 12, 2 * n, 0, "Sisi kotak laci 12 mm")
    it.panel("Drawer box front/back", "LND-PLY-E0-12", box_w - 24, box_h, 12, 2 * n, 0, "Depan/belakang kotak laci (lebar - 2x12)")
    it.panel("Drawer bottom", "LND-PLY-E0-6", box_w - 12, box_d - 10, 6, n, 0, "Dasar laci 6 mm (tebal 5 di gambar, papan 6 terdekat)")
    it.hardware(label_slide, 'Rel laci DTC 3 tingkat L300 (lebar 42 mm)', n, "pair", RAIL_PAIR, "Gambar: ray trượt bi 3 tầng L300")


# ----------------------------------------------------------------------------------------------- BEDSIDE
b = Item("B41", "BEDSIDE 2 DRWS", "Bedroom", 550, 450, 550, "LV433.B41 - Bedside 2 Drws (1) Model (1).pdf")
casegood(b, 550, 450, 550, 515)
b.panel("Side panel MDF veneer 12", "LND-MDF-E0-12-MSF", 455, 330, 12, 2, 1, "Panel samping 330 x 455")
b.panel("Back panel MDF 12", "LND-MDF-E0-12", 455, 430, 12, 1, 0, "Panel belakang 430 x 455 (tebal tidak tertulis, 12 diasumsikan)")
b.solid("Frame rail front/back", 430, 30, 20, 6, exposed="N", note="Rel 30x20 atas/tengah/bawah depan-belakang")
b.solid("Frame rail side", 330, 30, 20, 4, exposed="N", note="Rel samping atas/bawah")
drawers_box(b, 2, 404, 360, 160, 426, 209)
b.hardware("HNDL / TBD", "Handle (sesuai sampel)", 2, "pcs", 0.0, "Harga handle belum ada")
b.hardware("I-00003", "Nylon leveler glides M8", 4, "pcs", LEVELER, "Leveler kaki")
b.h["notes"] = "Dari gambar LV433.B41. Rel 30x20 dan tebal panel belakang diasumsikan (tidak tertulis)."
b.dump()

# ----------------------------------------------------------------------------------------------- TALLBOY
t = Item("B51", "TALLBOY 4 DRWS", "Bedroom", 950, 450, 1100, "LV433.B51 - Tallboy 4 Drws Model (1).pdf")
casegood(t, 950, 450, 1100, 1065)
t.panel("Side panel MDF veneer 12", "LND-MDF-E0-12-MSF", 1005, 330, 12, 2, 1, "Panel samping 330 x 1005")
t.panel("Back panel MDF 12", "LND-MDF-E0-12", 1005, 830, 12, 1, 0, "Panel belakang 830 x 1005 (tebal diasumsikan)")
t.solid("Frame rail front/back", 830, 30, 20, 6, exposed="N", note="Rel 30x20 atas, tengah, bawah")
t.solid("Frame rail side", 330, 30, 20, 6, exposed="N", note="Rel samping")
drawers_box(t, 4, 804, 350, 180, 826, 241)
t.hardware("HNDL / TBD", "Handle (sesuai sampel)", 8, "pcs", 0.0, "2 handle per laci, harga belum ada")
t.hardware("I-00003", "Nylon leveler glides M8", 4, "pcs", LEVELER, "Leveler kaki")
t.h["notes"] = "Dari gambar LV433.B51. Rel 30x20 dan tebal panel belakang diasumsikan."
t.dump()

# ----------------------------------------------------------------------------------------------- DRESSER
d = Item("B61", "DRESSER 6 DRWS", "Bedroom", 1500, 450, 800, "LV433.B61 - Dresser 6 Drws Model (1).pdf")
casegood(d, 1500, 450, 800, 765)
d.panel("Side panel MDF veneer 12", "LND-MDF-E0-12-MSF", 705, 330, 12, 2, 1, "Panel samping 330 x 705")
d.panel("Back panel MDF 12", "LND-MDF-E0-12", 705, 1460, 12, 1, 0, "Panel belakang 1460 x 705 (tebal diasumsikan)")
d.solid("Frame rail front/back", 1460, 30, 20, 8, exposed="N", note="Rel 30x20 atas, tengah x2, bawah, depan-belakang")
d.solid("Frame rail side", 330, 30, 20, 4, exposed="N", note="Rel samping")
d.solid("Centre divider", 705, 30, 20, 1, exposed="N", note="Sekat tengah 30 mm antar 2 kolom laci")
drawers_box(d, 6, 649, 350, 180, 675, 222)
d.hardware("HNDL / TBD", "Handle (sesuai sampel)", 6, "pcs", 0.0, "Harga handle belum ada")
d.hardware("I-00003", "Nylon leveler glides M8", 5, "pcs", LEVELER, "4 sudut + 1 tengah")
d.h["notes"] = "Dari gambar LV433.B61. Layout 2 kolom x 3 baris. Rel dan sekat diasumsikan."
d.dump()

# ----------------------------------------------------------------------------------------------- BUFFET + TV
def doors_unit(code, name, room, H, leg_h, body_h, door_h, drawing):
    u = Item(code, name, room, 1800, 450, H, drawing)
    casegood(u, 1800, 450, H, leg_h)
    u.panel("Side panel MDF veneer 12", "LND-MDF-E0-12-MSF", body_h, 330, 12, 2, 1, f"Panel samping 330 x {body_h}")
    u.panel("Back panel MDF 12", "LND-MDF-E0-12", body_h, 1760, 12, 1, 0, "Panel belakang 1760 (tebal diasumsikan)")
    u.panel("Centre partition MDF veneer 18", "LND-MDF-E0-18-MSF", body_h, 405, 18, 1, 2, "Sekat tengah")
    u.panel("Adjustable shelf MDF veneer 18", "LND-MDF-E0-18-MSF", 866, 340, 18, 2, 1, "Adj. shelf 866 (kedalaman 340 diasumsikan)")
    u.panel("Door MDF veneer 18", "LND-MDF-E0-18-MDF", door_h, 409, 18, 4, 2, "4 pintu, 409 lebar")
    u.solid("Frame rail front/back", 1680, 30, 20, 4, exposed="N", note="Rel 30x20 atas dan bawah depan-belakang")
    u.solid("Frame rail side", 330, 30, 20, 4, exposed="N", note="Rel samping")
    u.hardware("HW-HINGE-DTC", "Engsel bật soft close DTC, cup 35 mm 165 derajat", 8, "pcs", HINGE, "2 engsel per pintu")
    u.hardware("HNDL / TBD", "Handle (sesuai sampel)", 4, "pcs", 0.0, "Harga handle belum ada")
    u.hardware("I-00003", "Nylon leveler glides M8", 5, "pcs", LEVELER, "4 sudut + 1 tengah")
    u.h["notes"] = f"Dari gambar {drawing[:9]}. Kedalaman shelf, rel, dan tebal back diasumsikan."
    u.dump()

doors_unit("D21", "BUFFET 4 DOORS", "Dining", 800, 765, 705, 671, "LV433.D21 - Buffet 4 Drs Model (1).pdf")
doors_unit("L31", "TV UNIT 4 DOORS", "Living", 550, 515, 455, 421, "LV433.L31 - TV Unit 4 Drs. Model (1).pdf")

# ----------------------------------------------------------------------------------------------- COFFEE + CONSOLE
def open_table(code, name, room, W, D, H, drawing, box_d):
    u = Item(code, name, room, W, D, H, drawing)
    casegood(u, W, D, H, H - 35)
    u.solid("Frame rail long", W - 120, 30, 20, 4, exposed="N", note="Rel 30x20 atas dan bawah (rangka rak)")
    u.solid("Frame rail short", D - 120, 30, 20, 4, exposed="N", note="Rel samping")
    u.solid("Drawer divider post", 155, 30, 20, 1, exposed="N", note="Sekat tengah antar 2 laci (30 mm)")
    u.panel("Bottom shelf MDF veneer 15", "LND-MDF-E0-15-MSF", W - 120, D - 120, 15, 1, 1, "Rak bawah terbuka")
    drawers_box(u, 2, 549, box_d, 105, 535, 155)
    u.hardware("HNDL / TBD", "Handle (sesuai sampel)", 2, "pcs", 0.0, "Harga handle belum ada")
    u.hardware("I-00003", "Nylon leveler glides M8", 4, "pcs", LEVELER, "Leveler kaki")
    u.h["notes"] = f"Dari gambar {drawing[:9]}. Rel 30x20 dan sekat diasumsikan."
    u.dump()

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
