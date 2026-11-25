# Panduan Menjalankan Aplikasi Web Modul Informasi Harga & Transaksi Tembakau Pakong

Aplikasi ini dibangun berdasarkan rancangan sistem informasi web dan modul awal ERP komoditas tembakau Madura di Kecamatan Pakong, Kabupaten Pamekasan (mengacu pada studi integrasi pasar vertikal Ningsih & Sustiyana, 2026).

---

## 1. Arsitektur & Teknologi
- **Backend**: Python 3.13 + FastAPI + Uvicorn
- **Database**: SQLite3 (`tembakau_pakong.db`) dengan skema relasional lengkap (Desa, Tipe Lahan, Grade, Pengguna, Harga Acuan, Harga Lapangan, Penawaran, Transaksi, Notifikasi)
- **Frontend**: HTML5, Tailwind CSS, Chart.js (Grafik fluktuasi harga harian per desa Cen Lecen, Lebbek, Bicorong)
- **Desain UI**: Mobile-first & responsif untuk kemudahan pengoperasian oleh petani lewat ponsel genggam

---

## 2. Cara Menjalankan Aplikasi Web

Buka terminal PowerShell di folder proyek ini (`c:\Users\LENOVO\Documents\Project ERP`), lalu jalankan:

```powershell
python main.py
```
atau
```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Setelah server aktif, buka browser di ponsel atau komputer pada alamat:
👉 **http://localhost:8000** (atau **http://127.0.0.1:8000**)

---

## 3. Akun Demo Berdasarkan Aktor Sistem (Bab 2.1)

Anda dapat berganti peran secara langsung melalui tombol **"Ganti Akun / Masuk"** di bagian kanan atas aplikasi:

| Peran Aktor | Nama Akun | No. Telepon | Kata Sandi | Lokasi Desa |
|---|---|---|---|---|
| **Petani** | Pak Slamet | `08123456701` | `petani123` | Cen Lecen |
| **Petani** | Pak Mat Rais | `08123456702` | `petani123` | Lebbek |
| **Pengepul** | Haji Munawir | `08123456703` | `pengepul123` | Pakong |
| **Pengepul / Tengkulak** | Haji Syamsul | `08123456704` | `pengepul123` | Bicorong |
| **Pengurus Poktan** | Pak Budi Santoso | `08123456705` | `poktan123` | Cen Lecen |
| **Pengurus Poktan** | Ustadz Mahmud | `08123456706` | `poktan123` | Lebbek |
| **Admin Sistem** | Administrator Sistem | `08123456700` | `admin123` | Pakong |
| **Pihak Gudang / Pabrik** | Perwakilan Pabrikan | `08123456709` | `gudang123` | Pamekasan |

---

## 4. Modul yang Telah Berfungsi Penuh

1. **Informasi Harga**: Menampilkan harga tembakau terverifikasi per desa di Pakong, tipe lahan (Gunung, Tegal, Sawah), dan grade mutu (Super A, A, B, C, D) lengkap dengan grafik tren harga.
2. **Pembanding Acuan**: Menghitung selisih margin harga pasar lokal vs patokan acuan pabrikan (Gudang Garam, Djarum, Disbun Pamekasan) untuk memperkuat posisi tawar petani.
3. **Penawaran & Pasar Mini**: Petani dapat memasang penawaran jual panen mereka, dan pengepul/pembeli dapat mengajukan tawaran harga beli secara transparan.
4. **Pencatatan Transaksi**: Pembuatan nota transaksi digital terstruktur lengkap dengan kalkulasi otomatis timbangan berat x harga per kg.
5. **Verifikasi Poktan**: Alur kontrol validitas data di mana laporan harga berstatus *menunggu* sebelum disetujui oleh pengurus kelompok tani.
6. **Rekap & Laporan ERP**: Ringkasan perputaran uang (omzet), volume total terjual (Kg), dan rekapitulasi data per desa dan per grade yang siap dicetak/diekspor.
7. **Notifikasi**: Siaran info harga terkini dan update transaksi otomatis kepada petani dan pengurus.
