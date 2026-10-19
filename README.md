# BOM-APP — Factory Furniture Costing & BOM Engine

Engine perhitungan Bill of Materials (BOM) & HPP otomatis untuk manufaktur mebel ekspor (Standar Tala Living / Living Ikon / PLV). 
Mendukung ekstraksi otomatis dari gambar kerja PDF (CAD/Vision) hingga menghasilkan workbook Excel berstandar **Golden Master** yang terekonsiliasi penuh.

---

## 1. Aturan Konstruksi Baku (Factory Rules v2.3)

### A. Rumus Kotak Laci Paten (Mandat Terbaru Oktober 2026)
Dihitung otomatis dari ukuran muka laci (**$W_{\text{front}} \times H_{\text{front}}$**) dan kedalaman kabinet ($D$):
* **Tinggi Kotak Laci (Seragam Keliling):** $\mathbf{H_{\text{front}} - 30\text{ mm}}$
  * Celah atas bebas: 20 mm
  * Celah bawah mekanisme rel DTC: 10 mm
  * Berlaku seragam untuk: **Sisi Laci (5/B-12-0X)**, **Muka Dalam (11/B-12-0X)**, dan **Belakang Laci (11/B-12-0X)**.
* **Lebar Kotak Laci:** $\mathbf{W_{\text{front}} - 64\text{ mm}}$
  * Celah samping kanan: 20 mm
  * Celah samping kiri: 20 mm
  * Tebal 2x dinding samping triplek 12 mm: 24 mm
* **Dasar Laci (12/B-6-0X):** $\mathbf{(W_{\text{front}} - 54\text{ mm}) \times (D - 7\text{ mm})}$
  * Masuk alur dado 5 mm tiap sisi: $+10\text{ mm}$ dari lebar dalam
  * Toleransi kaitan rel DTC: $-7\text{ mm}$ dari kedalaman laci $D$
* **Penggabungan Sub-front & Belakang:** Otomatis digabung pada baris `11 / B-12-0X Drawer box front/back` ($\text{Qty} = 2 \times \text{laci}$).

### B. Deduksi Sambungan Kaki Sudut (Joint Deduction)
* **Rel Horizontal Carcass:** Panjang Bersih = Bentang Luar $- (2 \times \text{tebal kaki sudut})$.
  * Contoh Buffet: $1650 - (2 \times 45) = 1560\text{ mm}$.
  * Contoh Tallboy: $950 - (2 \times 40) = 870\text{ mm}$.
  * Contoh Nakas: $470 - (2 \times 40) = 390\text{ mm}$.

### C. Anatomi Tempat Tidur (Bed Anatomy)
* **Side Rail (21/A):** Wajib menembus tiang luar ke luar ($2140\text{ mm}$), bukan ukuran matras ($2040\text{ mm}$).
* **Stretcher Headboard/Footboard:** Panjang Bersih = Lebar Luar $- (2 \times \text{lebar tiang})$ ($1530\text{ mm}$ Queen, $1830\text{ mm}$ King).
* **Strict 1:1 Callouts:** Dilarang merangkum rel bed ke nama generic; rel atas, tengah, bawah, dan pembagi $190\text{ mm}$ wajib terpisah 1:1.

### D. Konstruksi Casegoods, Buffet & Credenza (v2.3)
* **Kaki Tinggi ($> 200\text{ mm}$):** Dasar bawah bodi menggunakan **rangka rel kayu solid (apron rails)** $40 \times 25\text{ mm}$ dan rel tengah $45 \times 36\text{ mm}$, **bukan** panel triplek utuh.
* **Tinggi Pintu Bersih:** Tinggi bukaan kabinet dikurangi celah lis 25 mm ($525 - 25 = 500\text{ mm}$).
* **Anti Duplikasi Pintu:** Jumlah daun pintu dikunci mengikuti spesifikasi item (contoh "2 Doors" = 2 pcs).
* **Partisi & Ambalan:** Partisi vertikal masuk menjangkau bibir rebate ($410\text{ mm}$). Ambalan diberi lis kayu solid depan ($520 \times 30 \times 20\text{ mm}$).
* **Panel Belakang Bersekat:** Jika ada tiang vertikal belakang, panel belakang dipotong per kompartemen (bay).

### E. Frame Cermin Miter 45°
* Batang horizontal dan vertikal dipotong panjang luar penuh ($1000\text{ mm}$ untuk cermin $1000 \times 1000$).

---

### F. Material Panel: Plywood vs MDF (dikunci 19 Okt 2026)
* **Kode gambar** `<Grup>-<Tebal>-<n>X`: grup **B = Plywood**, grup **C = MDF board**.
* **n** = jumlah muka veneer: `0X` RAW, `1X` single face, `2X` double face.
* **Grade board DIKUNCI E0** untuk semua plywood dan MDF (landed Kudus, `RATES!PANEL_GRADE`, `config.PANEL_GRADE`). Keputusan meeting 19 Okt 2026, menggantikan kunci E2 sebelumnya. E2 / CARB tidak boleh dipakai; generator memberi peringatan bila ada.
* Rate code: plywood `LND-PLY-E0-<T>` (raw) dan `LND-PLY-E0-<T>-MSF|MDF`; MDF `LND-MDF-E0-<T>` dan `LND-MDF-E0-<T>-MSF|MDF`. Kode lama (`PLY-18-MSF`) dan kode E2 otomatis diubah ke E0 oleh `to_e0()`.
* **Awas nama sama:** pada `PLY-18-MDF`, "MDF" = *Mindi Double Face* (plywood), **bukan** papan MDF. Papan MDF selalu berawalan `LND-MDF-`.
* Pengecekan otomatis: `core/panel_rules.py` memberi peringatan `[PANEL RULE WARNING]` bila tebal tidak cocok dengan rate code, atau label tidak cocok dengan rate code.

---

### G. Prioritas sumber angka saat membaca gambar (dikunci 19 Okt 2026)
* **Ketebalan panel dan ukuran kotak laci mengikuti RULES** (Part Master v3 dan Factory Rules v2.3), **bukan** angka tebal yang tertulis di gambar. Contoh: top dan samping `C18 1X`, belakang `B9 1X`, muka laci MDF 18, kotak laci plywood 12 (H-30, W-64), dasar laci 6 (W-54, D-7).
* **Gambar menentukan tata letak:** ukuran luar, lebar bukaan, tinggi muka laci, penampang kaki dan rangka.
* Selisih antara gambar dan rule dicatat di kolom note tiap baris, supaya bisa ditinjau manusia.

---

### H. Sudut Membulat vs Kayu Lengkung (dikunci 19 Okt 2026, direvisi)
* **R30 / R38 / R40 di gambar = profil router** pada papan lurus. **Tidak mengubah tier, ukuran, atau biaya.** Hanya dicatat di note baris (`[PROFIL]`).
* **Kayu yang memang dilengkungkan** (`curved = "Y"`, mis. rel lengkung kepala bed): tier **A-CURVED**, blank = ukuran jadi + busur + `RATES!CURVE_ALLOW`. `CURVE_ALLOW` masih kosong (oranye).
* Aturan idempoten: `core/curves.py`.

---

### I. Veneer (dikunci 19 Okt 2026)
* Harga veneer dihitung dari harga log, yield slicing, dan ongkos vendor, bukan satu angka tetap.
* **Rumus:** harga kayu per m2 = harga log x tebal / yield efektif; yield efektif = yield slicing x lebar trim / lebar flitch (30% x 150/160 = 28,125%). Ditambah ongkos slicing Rp 12.000 per m2 veneer jadi.
* **Tiga ketebalan:** 0,6 / 1,0 / 1,2 mm = Rp 18.827 / 23.378 / 25.653 per m2 (cocok dengan pasar 0,6 mm 18-20 ribu).
* **Per muka papan** (lembar 2440x1220) = (veneer per m2 + lem/lakban Rp 10.424) x luas lembar + tenaga press Rp 57.143: 0,6 mm Rp 144.216; 1,0 mm Rp 157.764; 1,2 mm Rp 164.538.
* **Standar = 0,6 mm.** Kode `-MSF` / `-MDF` memakai 0,6 mm. Tambah `-V10` atau `-V12` di belakang kode untuk 1,0 atau 1,2 mm (contoh `LND-PLY-E2-18-MSF-V10`).
* Blok VENEER di sheet RATES (sel biru bisa diedit) dan `config.VENEER` memakai rumus yang sama; `tests/test_veneer.py` memastikan keduanya cocok lewat hitung ulang LibreOffice.
* Belum pasti (CONFIRM): harga log Rp 3,2 jt (card lama 3 jt), ongkos slicing dihitung per m2 jadi, susut log ke flitch, susut pressing, veneer penyeimbang di papan 1X. Teak belum diubah (masih model lama).
* Kode panel yang tidak ada di tabel harga sekarang menimbulkan error, tidak lagi diam-diam memakai Rp 215.000.

---

## 2. Format Baku BOM Koleksi (Multi-Item Workbook)

Untuk setiap batch gambar atau koleksi, format output dikunci:
1. **1 File Multi-Item per Koleksi:** Seluruh item dalam koleksi dirangkum ke dalam satu file `.xlsx`.
2. **Tab `ITEMS` (Roll-up Utama):** Format padat 1 baris per produk, menampilkan foto, kode, nama, dimensi, status `costed` (checks = 0), breakdown unsur biaya, dan Unit Cost (HPP).
3. **Tab Per-Item Padat & Bersih:** Tanpa baris kosong berlebih (*dense table*), menampilkan rincian kayu solid, panel, hardware, dan rekap HPP terhubung ke formula rate card.
4. **Tab `RATES` Terpusat:** Rate card terpusat untuk perubahan harga bahan baku otomatis.
5. **Penamaan File Baku:** `[Nama Koleksi / Drawing] [YYYYMMDD-HHMMSS].xlsx`.

---

## 3. Panduan Penggunaan CLI

```bash
# Menampilkan status engine dan rate card aktif
python cli.py info

# Menampilkan rangkuman aturan konstruksi aktif
python cli.py rules

# Menghitung otomatis part kotak laci dari ukuran front W x H dan depth D
python cli.py derive-drawer -w 870 -H 180 -d 350

# Menghitung otomatis BOM dari gambar kerja PDF
python cli.py auto "path/ke/drawing.pdf"

# Membuat single BOM dari file JSON spesifikasi
python cli.py create "data/item_spec.json" -o "output.xlsx"

# Menggabungkan beberapa JSON spec menjadi 1 workbook koleksi multi-item
python cli.py collection "data/item1.json" "data/item2.json" -t "SIENNA COLLECTION"

# Memvalidasi formula dan open input checks pada file BOM Excel
python cli.py verify "path/ke/bom.xlsx"
```


### J. Catatan meeting 19 Okt 2026
* **E0 untuk semua plywood dan MDF** (6, 9, 12 mm dan seterusnya). Menggantikan kunci E2.
* **Material:** MDF dan plywood furniture grade (bukan marine).
* **Plywood E0:** kotak laci (sisi, depan/belakang, dasar, support), panel belakang, sekat/divider.
* **MDF veneer E0:** panel samping 1 muka (MSF), pintu 2 muka (MDF), muka laci 1 muka (MSF). Atas, rak, headboard dan lainnya tetap seperti spec.
* Diterapkan otomatis oleh `apply_meeting_rule()` di `core/panel_rules.py` (idempoten, ketebalan tidak diubah, tebal di luar tabel papan hanya diberi tanda). `derive_drawer_box` kini memberi muka laci MDF 18 satu muka.
* **Harga veneer** memakai perhitungan bagian I.
* "Select cheapest price" (pilih harga termurah) belum dijelaskan maksudnya; lihat Pertanyaan Terbuka di vault.


### K. METAL = besi hollow (dikunci 19 Okt 2026)
* Komponen bermaterial **METAL** = **besi hollow hitam**. Biaya = panjang (m) x jumlah x harga per meter dari daftar `HOLLOW-<a>x<b>x<tebal dinding>` di sheet RATES (harga batang 6 m / 6). Sisi dipasangkan dari lebar dan tebal komponen, urutan bebas (30x60 = 60x30).
* **Tebal dinding tidak ada di gambar.** Satu pengaturan untuk semua: `RATES!HOLLOW_WALL`, saat ini **1,2 mm (CONFIRM)**. Ubah angka ini, semua biaya metal mengikuti.
* Penampang yang tidak ada di daftar dihitung Rp 0 dan barisnya berwarna oranye.
* Sumber harga: `data/prices/besi_hollow_hitam_2026-10-19.json` (297 ukuran, smsperkasa.com). Baris `METAL_A..D` dan `metal_brass/steel` tidak dipakai lagi.
* Brass (`MT BRASS`, mis. TV unit L31) saat ini ikut dihitung sebagai besi hollow; harga brass sungguhan belum ada.
