# STANDAR GAMBAR KERJA UNTUK BOM — TALA LIVING
Versi 1.0 · 20 Oktober 2026 · berlaku untuk semua DWG yang akan dibaca BOM-APP

Prinsip: gambar dibaca seperti gambar arsitek. **Di gambar hanya tag kode (keynote)**; semua data komponen ada di **lembar keynote / schedule** yang dibuat otomatis oleh BOM-APP. Drafter cukup melabeli tiap komponen dengan benar satu kali.

## 1. Lembar
- Kertas A3, satuan **mm**, skala tertulis di tiap tampak.
- Nomor lembar: `<KODE ITEM>-01` tampak luar (depan, samping, atas, perspektif), `-02` potongan (A, B, C) dan detail laci/pintu, `-03` keynote & schedule (dibuat BOM-APP).
- Kop: nama item, kode item, koleksi, dimensi keseluruhan W × D × H, drafter, tanggal, revisi.

## 2. Tampak wajib
1. Depan, samping, atas: dimensi keseluruhan dan posisi tiap komponen.
2. Potongan tegak (depan dan samping) dan potongan denah: memperlihatkan tebal panel, rangka, kotak laci.
3. Detail laci / pintu: bukaan, kotak laci, rel, handle.
Setiap komponen harus terlihat **utuh (dua ukuran)** minimal di satu tampak, bukan hanya dari tepi.

## 3. Label komponen (keynote) — INTI STANDAR
Satu MULTILEADER per komponen per tampak, teks dalam satu baris dengan format tetap:

```
NAMA KOMPONEN | L x W x T | KODE BAHAN
SIDE DRAWER | 450 x 170 x 12 | B-12-0X
LEG | 450 x 20 x 20 | MT-20x20x0.8
TOP PANEL | 550 x 550 x 18 | B-18-1X
```

- **NAMA** diambil dari PART LIST pabrik (1–20): Bottom stretcher F/B, Bottom stretcher L/R, Leg, Shelfing, Divider, Front drawer, Inner drawer, Side drawer, Back drawer, Bottom drawer, Door panel, Back panel, Side panel, Front rail, Side rail, Back rail, Vertical support, Horizontal support, Top stretcher, Top panel. Komponen di luar daftar: tulis nama jelas + tanda `*`.
- **L x W x T** = ukuran jadi, mm; L sisi terpanjang. Untuk hollow: panjang x sisi x sisi.
- **KODE BAHAN** dari tabel pabrik: `A` solid, `A1` solid laminated, `B-<tebal>-<0X/1X/2X>` plywood, `C-<tebal>-<0X/1X/2X>` MDF (0X/1X/2X = muka veneer), `MT-<a>x<b>x<dinding>` hollow besi, `D1` engsel soft close, `D2` rel laci, `HW-<nama>` hardware lain.
- Komponen yang sama (ukuran & bahan sama) diberi label **sekali per tampak**; jumlah dihitung BOM-APP dari geometri dan potongan, bukan dari jumlah label.
- Label ditempatkan di layer `BOM-KEYNOTE`, panah menyentuh komponennya. Tidak ada teks komponen di luar MULTILEADER.

## 4. Dilarang
- Label bahan saja (`PLY 12MM`) tanpa nama komponen.
- Satu label untuk beberapa komponen berbeda; label pada ruang kosong.
- Ukuran berbeda antara tampak untuk komponen yang sama.
- Blok/xref berisi teks komponen (tidak terbaca).

## 5. Yang dibuat BOM-APP dari gambar yang sesuai standar
1. Setiap label diganti **tag keynote** `[n]` (kotak) di tempat yang sama, panah drafter tetap.
2. Lembar `-03` keynote & schedule: KEYNOTE | NO PART LIST | NAMA | L x W x T | QTY | BAHAN | STATUS | CATATAN, plus kop.
3. JSON untuk aplikasi BOM, lalu spec BOM-APP → HPP.
Status: `STATED` (tertulis di gambar), `DERIVED` (dihitung dari geometri), `CHECK` (perlu konfirmasi drafter). Target gambar sesuai standar: 100% STATED, 0 CHECK, < 10 detik per DWG.

## 6. Checklist drafter sebelum serah
- [ ] Tiap komponen punya label `NAMA | L x W x T | KODE` dan terlihat utuh di satu tampak.
- [ ] Dimensi keseluruhan W × D × H ada di kop dan di tampak.
- [ ] Potongan memperlihatkan semua tebal panel dan kotak laci.
- [ ] Nama komponen sesuai PART LIST; kode bahan sesuai tabel pabrik.
- [ ] Tidak ada label bahan saja.
