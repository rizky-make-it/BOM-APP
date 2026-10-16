# PLAN: Part Master & Sistem Penomoran 3-Digit (v3.0) — BOM-APP

## 1. Keputusan Arsitektur (Approved via Grill)
* **Format Label:** `[PART_NO] [MAT_CODE]`, contoh: `401 A-20-0X`, `402 B-12-0X`, `901 DTC-14` (tanpa slash, dipisah spasi).
* **Kompatibilitas:** Simpan engine lama (`core/rules_v2.py`), buat engine dan katalog baru (`core/part_catalog_v3.py` & `core/rules_v3.py`). Sediakan mapper konversi dari format lama (1-25 dan ①-⑰) ke 3 digit.
* **Cakupan Part:** Seluruh 126 part dari 9 famili (100–900) diaktifkan penuh.
* **Aturan Konstruksi:** Rumus paten v2.3 (kotak laci H-30, W-64, D-7, bed rail 2140mm, dll.) tetap terkunci, komponen dan label otomatis mengikuti kode 3 digit.

## 2. 9 Famili Part Master (126 Part)
1. **101–199: Legs & base** (10 part) — Kaki, stretcher bawah, plinth, pedestal, leg block.
2. **201–299: Frame rails & supports** (16 part) — Top rail, bottom rail, mid rail, drawer runner, face frame, cleat.
3. **301–399: Case panels** (17 part) — Sisi, belakang, sekat, ambalan, lis solid, cermin.
4. **401–499: Drawers** (12 part) — Muka laci, kotak laci (sisi, muka dalam, belakang, dasar), tray, trim.
5. **501–599: Doors** (10 part) — Daun pintu slab/frame, kaca/rotan center, sliding door, flap.
6. **601–699: Tops & surfaces** (9 part) — Top bodi, daun meja, edging, insert, countertop.
7. **701–799: Seating & upholstery** (22 part) — Rangka dudukan, sandaran, tangan, webbing/springs, busa, cover fabric/kulit.
8. **801–899: Beds** (14 part) — Headboard, footboard, side rail, center spine, slat, bed base metal.
9. **901–999: Hardware & bought-in** (16 part) — Rel laci, engsel, handle, glide, leveler, KD fitting, kunci, lampu.

## 3. Struktur File Baru & Perubahan
* `data/part_master_v3.json`: Ekstraksi 126 part dari workbook Excel (metadata lengkap, famili, alias, default material, rule).
* `core/part_catalog_v3.py`: Modul katalog Python:
  - `PART_CATALOG_V3`: Dictionary 126 part.
  - `FAMILIES_V3`: Definisi 9 famili part.
  - `format_part_label(part_no, mat_code)`: Utility format `[PART_NO] [MAT_CODE]`.
  - `map_legacy_to_v3(old_code)`: Mapper dari kode lama (1–25 / ①–⑰) ke 3 digit.
  - Helper fungsi pencarian by name / alias.
* `core/rules_v3.py`: Engine konstruksi v3:
  - Implementasi `derive_drawer_box` memakai `401`, `402`, `403`, `404`, `405`, `901`.
  - Implementasi `derive_door` memakai `501`, `902`.
  - Implementasi `derive_bed_anatomy` memakai `806`, `808`, `809`, `811`, `812`, `904`, `907`.
  - Implementasi `derive_buffet_casegoods` memakai `101`, `201`, `206`, `301`, `302`, `307`, `601`.
* `tests/test_part_master_v3.py`: Regression & verification unit test.

## 4. Definisi Selesai (Definition of Done)
- [x] Workbook master diparsing 100% tanpa ada part tercecer (126/126).
- [x] File data `part_master_v3.json` tervalidasi skema.
- [x] `part_catalog_v3.py` menyediakan lookup O(1) dan mapper legacy.
- [x] `rules_v3.py` menghasilkan label dengan format `[PART_NO] [MAT_CODE]`.
- [x] Test suite lulus 100% dengan eksekusi nyata.
