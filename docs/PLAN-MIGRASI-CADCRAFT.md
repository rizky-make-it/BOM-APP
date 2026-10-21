# PLAN migrasi AutoCAD -> CADCraft (21 Okt 2026) - status: DIREKOMENDASIKAN BERTAHAP, belum dieksekusi
Permintaan Rizky: "migrasi menggunakan CADCraft sepenuhnya di proyek kita".

## Fakta terukur (cadcraft-cli 0.8.0 portable, C:/Users/Admin/tools/cadcraft/cadcraft-0.8.0-windows-x64-portable)
- Skyline.dwg: LINE 425/425 identik dengan AutoCAD; DIMENSION 140, MTEXT 9, LEADER 13 sama. 3 record DWG (tipe 535) tidak terbaca (peringatan).
- B01 / L11 / lexi 3: terbaca, skipped=0. MULTILEADER terbaca lengkap (tip, landing, dogleg, teks) = cukup untuk jalur 2D.
- **3DSOLID TIDAK terbaca**: lexi 3 punya 174 objek "Proxy" dengan dxf_type 3DSOLID berisi tag mentah, tanpa geometri/ACIS. Jadi `tools/acad_solids.py` (MASSPROP, ukuran solid) TIDAK bisa dipindah. Penyimpanan DWG oleh CADCraft juga membuang objek yang tidak dikenal.
- CADCraft menulis DWG hanya R2000. Peringatan sendiri: "saving over the original loses them".
- Belum diuji: cetak layout drafter ke PDF (convert PNG/SVG/PDF selalu model space), ubah teks MULTILEADER (pengganti entmod 304), entmake setara lewat command_line/script, hasil kerja pada gambar bergaya paper-space leader (ALT-LD-031A).

## Yang bergantung pada AutoCAD (13 file di tools/)
acad_core (jalankan/plot), acad_read (dump entget), dwg2d_read, dwg2d_components, dwg2d_label_sheet, dwg2d_number_labels, dwg2d_sheet, acad_fill_sheet(+v1), acad_template, acad_plot_layout, acad_stress, acad_solids.

## Langkah (urut, berhenti bila gagal)
1. Pembaca: `tools/cc_read.py` (MCP stdio) menghasilkan JSON yang sama bentuknya dengan acad_read (lines, polylines, leaders, dims, layouts). Uji: bandingkan dengan acad_read pada Skyline, L11, B01, B02, lexi 3, STANDARD.zip (10 DWG); target hasil `dwg2bom` identik (L11 HPP 706.960, B01/B02 sama).
2. Uji tulis di salinan: tag keynote (LWPOLYLINE+TEXT), kosongkan teks MULTILEADER, layout BOM-TABLE, PLOT layout ke PDF. Bila salah satu tidak bisa -> bagian itu tetap AutoCAD.
3. Pindahkan `dwg2d_components` ke pembaca baru; jalankan tes + bandingkan PDF.
4. Pensiunkan acad_* hanya setelah 1-3 lulus. `acad_solids` dan jalur 3D tetap AutoCAD (atau diganti ekspor STEP) - TIDAK ikut migrasi.
5. Daftarkan CADCraft sebagai MCP Hermes (opsional).

## Risiko / keputusan Rizky
- "Sepenuhnya" belum mungkin selama ada DWG yang hanya punya solid 3D (lexi 3 versi 3D, tapi kita sudah memutuskan BOM mengandalkan 2D drafter).
- DWG keluaran CADCraft R2000: periksa dibuka di AutoCAD drafter sebelum dipakai tim.
- Lisensi AutoCAD sudah ada; migrasi menghemat lisensi hanya bila drafter juga pindah. Tidak ada keuntungan akurasi yang terbukti.

## HASIL PENGUKURAN (21 Okt 2026, tools/cc_read.py + tools/cc_compare.py, 18 DWG: Skyline, Sienna x5, lexi 2/3, STANDARD x10)
- LINE 4389/4389 identik (100%); DIMENSION 1306/1309 (99,8%; 3 beda di Skyline); MULTILEADER teks 341/341 dan ujung panah 341/341 (100%, Sienna+Lexi).
- Kecepatan: CADCraft 4,4 detik total vs AutoCAD 21,7 detik (sekitar 5x lebih cepat); tanpa lisensi, tanpa proses accoreconsole yang bisa macet (ErrorStatus=76 terjadi pada AutoCAD saat DWG dibuka bersama file yang sedang terbuka).
- KEKURANGAN CADCraft: (1) LWPOLYLINE keluar dalam koordinat OCS tanpa normal ekstrusi -> polyline pada bidang XZ (gaya Sienna/Lexi) tidak bisa diubah ke WCS: cocok 99/1831 saja; (2) 3DSOLID jadi Proxy tanpa geometri; (3) 3-4 record DWG tidak terbaca (tipe 535/519); (4) tulis DWG R2000.
- KEKURANGAN cc_read (belum selesai, bukan CADCraft): entitas LEADER + MTEXT gaya STANDARD belum dipasangkan (data ada: CAB-01 6 Leader + 31 MText).
- Kesimpulan: untuk membaca garis/dimensi/label, CADCraft MCP setara dan lebih cepat; untuk bidang XZ (polyline) dan solid, AutoCAD masih unggul. Migrasi penuh BELUM bisa.

## KOREKSI (21 Okt 2026, setelah Rizky: "kamu tidak memberi kesempatan untuk CADCraft")
- Klaim "polyline XZ tidak bisa" TERLALU KERAS. `query_entities` memang tanpa normal, tetapi bila diasumsikan normal (0,-1,0) (bidang XZ gaya Sienna/Lexi, sama dengan entmake kita), 126 dari 151 polyline L11 cocok persis dengan AutoCAD (83%). 25 sisanya tidak cocok (bidang lain / elevasi; belum diselidiki). Jalur lewat `convert -> DXF` tetap kehilangan normal (selalu 0,0,1).
- BELUM DIUJI sama sekali (jangan dianggap gagal): jalur tulis `command_line/script/execute` (tag, kosongkan teks leader), layout + plot PDF, ekspor STEP/solid, pasangan LEADER+MTEXT gaya STANDARD.

## UJI JALUR TULIS CADCraft (21 Okt 2026, Skyline) - MCP terdaftar di Hermes (`hermes mcp add cadcraft`, 12 tool, aktif di sesi baru)
- TULIS: `execute` line / rectang / text (justify MC) menaruh 15 tag (garis + kotak + angka) = 45 perintah, 0 error, ~0 detik; `save` ke DWG baru jalan; kotak dan angka terbaca jelas di render PNG (`cadcraft-cli convert --window`). Penempatan koordinat tag masih kasar (tag 2 menembus pintu, 5/6 menempel dimensi): masalah posisi saya, bukan alat.
- PLOT layout: `execute plot {layout, paper, fit}` menghasilkan PDF A3 per layout (2 lembar, 96-130 KB). TETAPI isi lembar CABINET (2) TIDAK sama dengan plot AutoCAD: potongan terpotong di tepi kanan dan blok DETAIL tumpang tindih, sedangkan AutoCAD mencetak lembar depan+perspektif utuh. Belum diselidiki (kemungkinan viewport/clip layout tidak dihormati CADCraft). Jadi untuk cetak lembar drafter AutoCAD masih lebih benar.
- BELUM: kosongkan teks MULTILEADER drafter (`mleaderedit`), solid via STEP, leader+MText gaya STANDARD.

## PENYEBAB plot layout CADCraft tidak setara (21 Okt 2026, dibandingkan berdampingan dengan AutoCAD, layout CABINET dan CABINET (2) milik Skyline)
- AutoCAD: tiap viewport paper space menampilkan model space pada skala dan jendelanya sendiri (lembar depan: tampak depan + perspektif; lembar potongan: 3 potongan + DETAIL A/B/C + elevasi pintu), semua utuh dalam bingkai drafter.
- CADCraft (`execute plot {layout, paper, fit}`): isi viewport TIDAK dipotong dan skalanya salah: satu potongan tampil raksasa, DETAIL A/B/C tumpang tindih, tampak lain terpotong di tepi. Cetak viewport (pusat tampilan, skala, clip) tidak dihormati untuk DWG ini. Parameter `fit`, `lineweights`, `scale` tidak mengubahnya.
- Akibat: plot lembar drafter TETAP AutoCAD. Sisa pekerjaan CADCraft (baca, tulis tag, render PNG per jendela model space) tidak terpengaruh. Lembar schedule baru yang kita gambar sendiri (tanpa viewport drafter) kemungkinan bisa dicetak CADCraft: belum diuji.
- Pilihan bila tetap ingin 100% CADCraft: laporkan ke pengembang (storytold/cadcraft) bersama Skyline.dwg, atau cetak lewat render PNG jendela model space per tampak lalu susun sendiri (kehilangan skala drafter).
