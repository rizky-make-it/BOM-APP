# Uji pembaca DWG: AutoCAD (accoreconsole) vs CADCraft (MCP) - 21 Okt 2026
Skrip: `tools/reader_bench.py --sections A,B,C,D` (bisa diulang). Hasil mentah: `%LOCALAPPDATA%/hermes/cache/scratch/bench/bench_*.json`.

## A. Kunci jawaban sintetis (koordinat dunia diketahui pasti, 6 bidang x 4 polyline + 12 garis 3D)
| | AutoCAD | CADCraft (asumsi bidang XZ) | CADCraft (asumsi bidang XY) |
|---|---|---|---|
| XZ (0,-1,0) | 4/4 | 4/4 | 0/4 |
| XY (0,0,1) | 4/4 | 0/4 | 4/4 |
| YZ, XZ-belakang, YZ-belakang, miring | 4/4 tiap bidang | 0/4 | 0/4 |
| garis 3D | 12/12 | 12/12 | 12/12 |
- AutoCAD benar di semua bidang (24/24). CADCraft tidak mengeluarkan normal bidang polyline dan TIDAK memberi peringatan: hasil benar hanya bila bidang ditebak benar (satu asumsi = 4 dari 24). Ini bukan masalah ketelitian angka, tetapi informasi yang hilang.

## B. Stabilitas (10-12 kali baca file sama)
- Semua pembaca 100% berhasil dan keluarannya identik tiap kali (deterministik). Kecepatan: AutoCAD 1,1-1,9 s, CADCraft 0,1-0,4 s. File 20 MB (PL 016): AutoCAD 2,4 s, CADCraft 15,5 s.
- KOREKSI: catatan lama "AutoCAD gagal membuka satu file (ErrorStatus=76)" SALAH. Itu kesalahan skrip saya (argumen --out dianggap nama DWG; file lexi 3 di cache sudah dipindah). Tidak ada kegagalan pembaca AutoCAD yang terbukti.

## C. Korpus nyata: 44 DWG unik di PC ini, perbandingan 3D penuh
- Gagal baca: AutoCAD 0, CADCraft 0.
- Garis identik sampai 0,01 mm (urutan ujung diabaikan): 100% pada semua file kecuali BED-VIEW (227 segmen mikro 0,015 mm dari 3.690, belum diselidiki). Teks+ujung leader 602/602 (100%). Dimensi 2480/2483 (99,9%; 3 beda di Skyline). Polyline 3371/3413 (98,8%): sisanya polyline bukan-XZ yang tidak bisa dipetakan CADCraft (lihat A).
- Catatan metode: selisih semu 96% sempat muncul karena cara mencocokkan garis (ujung terbalik pada garis vertikal); sudah diperbaiki.

## D. CADCraft menyimpan DWG, AutoCAD membaca hasilnya (L11, B01, Skyline)
- Garis dan leader utuh 100%; jumlah layout, viewport, dan objek 3DSOLID tetap.
- RUSAK: polyline bidang XZ tergeser (L11: asli (-6421,0,1105) menjadi (-6206,1171,0); 0/151 sama) karena normal bidang hilang; nilai ukur DIMENSI berubah (L11 28/73 sama, B01 32/67). Hasil simpan CADCraft TIDAK boleh dijadikan DWG keluaran untuk gambar Sienna/Lexi.

## Kesimpulan
- Sebagai PEMBACA geometri 2D dasar (garis, dimensi, leader): setara, CADCraft 3-5x lebih cepat (kecuali file >10 MB).
- AutoCAD wajib untuk: polyline di bidang mana pun, menulis DWG keluaran, cetak lembar drafter (viewport), solid 3D.
- Untuk mesin BOM berakurasi tinggi: AutoCAD = pembaca utama; CADCraft = pembaca kedua untuk silang-cek (dua pembaca setuju = lanjut, beda = tandai CHECK). Bukan migrasi penuh.
