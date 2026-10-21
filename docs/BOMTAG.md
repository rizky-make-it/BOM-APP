# BOMTAG - melabel komponen di AutoCAD (panduan drafter)

Tiga perintah AutoCAD yang membuat label (tag nomor berkotak) dan data BOM sekaligus. Ukuran dan nomor part tidak perlu diketik ulang ke tabel di mana pun.

## Pasang (sekali per PC)
1. Salin `tools/lisp/bomtag.lsp` ke folder mana pun, misalnya `C:\Tala\bomtag.lsp`.
2. Di AutoCAD ketik `APPLOAD`, pilih file itu, klik Load. Agar otomatis termuat tiap AutoCAD dibuka, masukkan ke Startup Suite (tombol Contents).
3. Bila Part Master berubah, bangun ulang filenya: `python tools/build_bomtag.py`.

## Pakai
**BOMTAG** - ulangi untuk tiap komponen:
1. Klik di dalam komponen (di tampak apa pun, bidang gambar apa pun). Panjang x lebar terukur otomatis dari bidang yang diklik.
2. Ketik nomor part (3 digit, Part Master v3). Ketik `?` untuk melihat daftar 126 part.
3. Ketik kode bahan (A, A1, B-18-1X, C-18-1X, MT-20x20 ...). Enter = pakai yang terakhir.
4. Panjang, lebar, tebal: Enter bila angka terukur sudah benar; ketik bila berbeda (mis. tebal, atau bagian yang tidak berbentuk kotak).
5. Jumlah total part itu di seluruh produk (bukan per tampak).
6. Klik tempat kotak nomor. Selesai; lanjut komponen berikutnya. Enter kosong = berhenti.

Komponen yang sama (spesifikasi sama) otomatis memakai NOMOR yang sama: beri tag di setiap tampak, jumlahnya cukup diisi sekali.

**BOMCHECK** - jalankan sebelum menyerahkan gambar. Melaporkan nomor part yang tidak ada di Part Master, kode bahan tidak dikenal, ukuran kosong, dan satu nomor dipakai untuk dua spesifikasi berbeda.

**BOMEXPORT** - menulis `<nama gambar>_bomtag.json` di folder gambar. File ini diserahkan ke BOM-APP.

## Yang terjadi sesudahnya (IT/BOM-APP)
```
python tools/bomtag_import.py X_bomtag.json --item KODE --name NAMA --out DIR
python tools/dwg2d_to_spec.py DIR/KODE_components.json --collection KOLEKSI --overall PxLxT --out DIR
```
Tebal panel, rumus kotak laci, dan finishing tetap mengikuti RULES di BOM-APP, bukan angka tag. Tag yang berstatus CHECK (nomor/bahan tidak valid, ukuran kosong) tetap CHECK di BOM.

## Batas yang jujur (v1)
- Bagian interaktif (klik, daftar, `BOUNDARY`) BELUM diuji oleh siapa pun di AutoCAD yang terbuka. Yang sudah diuji otomatis: pembuatan tag, penulisan data, BOMCHECK, BOMEXPORT, pada bidang XY (Skyline) dan XZ (L11), dibaca ulang oleh pembaca independen. Uji pertama oleh satu drafter di PC-nya diperlukan.
- Pengukuran otomatis hanya andal untuk bidang tertutup berbentuk kotak; selain itu ketik ukuran sendiri.
- Tag memakai layer `BOM-NO`; data tersimpan di XDATA aplikasi `TALA_BOM` pada angka tag.
- Tidak ada fitur hapus/ubah otomatis atas gambar drafter: BOMTAG hanya MENAMBAH objek di layer `BOM-NO`.
