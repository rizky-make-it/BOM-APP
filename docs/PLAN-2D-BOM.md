# PLAN (ditunda 20 Okt 2026): gambar kerja 2D drafter -> BOM Lexi
Status: **DITUNDA atas permintaan Rizky** ("simpan plan ini dulu dan dilanjut nanti, kita ada hal yang perlu di fix di bom app"). Lanjutkan dari sini, jangan mulai dari nol.

## Keputusan yang mengikat (sudah dicatat di Keputusan-Owner)
- BOM mengandalkan gambar 2D drafter (tampak + potongan + label bahan + dimensi). Model 3D di file hanya pelengkap; di lexi 3 model 3D tidak mewakili produk.
- Semua AutoCAD berjalan headless (`tools/acad_core.py`, uji 100/100). PC ini = server BOM-App.

## Yang sudah jadi (commit terakhir 8cae97b)
- `tools/dwg2d_labels.py`: bidang dari garis lepas (polygonize) + label MULTILEADER -> `%LOCALAPPDATA%/Temp/tallboy_2d_labels.json` (50 label, kolom x 25645-26600).
- `tools/dwg2d_statement.py`: 22 baris STATED (label, ukuran, jumlah) + peran DERIVED -> `tallboy_2d_statement.json`.
- `tools/dwg2d_sheet.py`: balon (2 rel kiri/kanan, tanpa tumpuk) + tabel pada SALINAN gambar drafter, cetak A3 portrait. Hasil: `C:\Users\Admin\Documents\Hasil-DWG\2d\Tallboy-2D-BOM.pdf` (+ .dwg). Rizky sudah melihat; keluhan terpotong & balon menumpuk sudah dibereskan.
- Catatan jalur 3D (v1/v2 `acad_fill_sheet*.py`, `templates/TALA_A3.dwt`) tetap ada untuk item yang modelnya benar dan berbentuk kotak.

## Langkah berikutnya, urut
1. **STATED -> spec BOM-APP** untuk tallboy 4 laci: 22 baris jadi SolidPart/PanelPart (format data/sienna/*.json). Tebal ikut RULES (bukan 20/9 dari gambar), kotak laci dari `derive_drawer_box` dengan bukaan 870 x 350 (x4) dan kedalaman dari potongan (415/421), hardware D2 rel laci. Tandai STATED/DERIVED/ASSUMED per nilai.
2. Jalankan engine (`to_e0`, `apply_meeting_rule`, `check_panel`, `calculate_bom_costing`) -> HPP tallboy; bandingkan ukuran dengan dimensi drafter (350x4, 870, 415, 745, 450, 950, 1100). Laporkan selisih, jangan dipaksa.
3. Peran part: kirim tabel 22 baris ke drafter/Evin untuk koreksi (3 baris "?", baris curiga "PLYWOOD 6MM 816x109"). Setelah dikoreksi, jadikan tabel aturan label+ukuran -> peran (file data, bukan if-else).
4. Generalisasi ke item lain di lexi 3 (bedside 1 laci, dresser 6 laci, kursi, bed): parameter kolom x/z per item (sekarang hard-coded untuk tallboy di `dwg2d_labels.py` X0/X1 dan `dwg2d_sheet.py` COL_X0/COL_X1/window). Deteksi kolom otomatis sudah ada (cluster bidang), tinggal dipakai.
5. Lembar: pendekkan garis penunjuk (tambat di tepi bidang terdekat ke rel, bukan pusat); balon pada semua salinan part kembar; opsi cetak lembar layout drafter asli + tabel (`acad_plot_layout.py`).
6. Jadikan satu perintah: `python tools/dwg2d_pipeline.py <dwg> --item <nama/kolom> --out DIR` -> labels, statement, sheet PDF, spec JSON, HPP.
7. Setelah stabil: tulis skill `tala-shop-drawing-2d` (prosedur + pitfalls) dan uji ketahanan 50 pekerjaan 2D.

## Pitfalls yang sudah dibayar mahal (jangan ulang)
- Console: ZOOM window 3D tidak dipatuhi; PLAN memandang dari bawah. Pakai `VPOINT 0,-1,0` + `UCS V` + `-PLOT Window x1,z1 x2,z2 Fit Center`. Model space tidak bertanya "scale lineweights".
- Entmake di bidang XZ: 210=(0,-1,0), koordinat OCS (x, z). LINE boleh 3D dunia langsung.
- Jendela cetak harus dari extent SEMUA geometri drafter (dimensi ada di luar bidang berlabel), berhenti sebelum gambar tetangga (dresser mulai x 27700).
- Balon offset tetap = menumpuk pada bagian tipis sejajar; pakai rel + jarak minimum 2.4 R.
- Nama layout berspasi: `(setvar "CTAB" "...")`. Nitro Pro mengunci PDF lama: tulis nama baru.

## File kerja (Temp, bisa hilang; regenerasi dengan alat di atas)
`%LOCALAPPDATA%/Temp/lexi3.dwg`, `lexi3_solids.json`, `lexi3_groups.json`, `tallboy_2d_labels.json`, `tallboy_2d_statement.json`, `lexi_k{1,2,3}_numbering.json`.
Sumber asli: `C:\Users\Admin\AppData\Local\hermes\cache\documents\doc_279be0992feb_lexi 3.dwg`.
