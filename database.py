import sqlite3
import hashlib
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "tembakau_pakong.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Tabel Desa
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS desa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama_desa TEXT NOT NULL UNIQUE,
        kecamatan TEXT NOT NULL DEFAULT 'Pakong'
    )
    """)

    # 2. Tabel Tipe Lahan
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tipe_lahan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama TEXT NOT NULL UNIQUE,
        keterangan TEXT
    )
    """)

    # 3. Tabel Grade Tembakau
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS grade (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama_grade TEXT NOT NULL UNIQUE,
        keterangan TEXT,
        harga_patokan_bawah REAL,
        harga_patokan_atas REAL
    )
    """)

    # 4. Tabel Pengguna (Roles: petani, pengepul, pengurus_poktan, admin, pihak_gudang)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pengguna (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama TEXT NOT NULL,
        peran TEXT NOT NULL,
        nomor_telepon TEXT UNIQUE NOT NULL,
        desa_id INTEGER,
        kata_sandi TEXT NOT NULL,
        status_verifikasi TEXT DEFAULT 'terverifikasi',
        dibuat_pada TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (desa_id) REFERENCES desa(id)
    )
    """)

    # 5. Tabel Harga Acuan / Referensi Pasar
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS harga_acuan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grade_id INTEGER NOT NULL,
        tipe_lahan_id INTEGER NOT NULL,
        harga_per_kg REAL NOT NULL,
        sumber TEXT NOT NULL, -- misal: Pabrik Gudang Garam, Djarum, Disbun Pamekasan
        berlaku_sejak TEXT NOT NULL,
        FOREIGN KEY (grade_id) REFERENCES grade(id),
        FOREIGN KEY (tipe_lahan_id) REFERENCES tipe_lahan(id)
    )
    """)

    # 6. Tabel Harga Harian Lapangan
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS harga (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tanggal TEXT NOT NULL,
        desa_id INTEGER NOT NULL,
        tipe_lahan_id INTEGER NOT NULL,
        grade_id INTEGER NOT NULL,
        harga_per_kg REAL NOT NULL,
        sumber TEXT NOT NULL,
        status_verifikasi TEXT DEFAULT 'menunggu', -- menunggu, disetujui, ditolak
        pelapor_id INTEGER NOT NULL,
        diverifikasi_oleh INTEGER,
        catatan TEXT,
        dibuat_pada TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (desa_id) REFERENCES desa(id),
        FOREIGN KEY (tipe_lahan_id) REFERENCES tipe_lahan(id),
        FOREIGN KEY (grade_id) REFERENCES grade(id),
        FOREIGN KEY (pelapor_id) REFERENCES pengguna(id),
        FOREIGN KEY (diverifikasi_oleh) REFERENCES pengguna(id)
    )
    """)

    # 7. Tabel Penawaran (Marketplace Mini Petani - Pengepul)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS penawaran (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pemosting_id INTEGER NOT NULL,
        desa_id INTEGER NOT NULL,
        tipe_lahan_id INTEGER NOT NULL,
        grade_id INTEGER NOT NULL,
        berat_kg REAL NOT NULL,
        harga_diminta REAL NOT NULL,
        keterangan TEXT,
        status TEXT DEFAULT 'terbuka', -- terbuka, ditawar, selesai, dibatalkan
        tanggal TEXT NOT NULL,
        FOREIGN KEY (pemosting_id) REFERENCES pengguna(id),
        FOREIGN KEY (desa_id) REFERENCES desa(id),
        FOREIGN KEY (tipe_lahan_id) REFERENCES tipe_lahan(id),
        FOREIGN KEY (grade_id) REFERENCES grade(id)
    )
    """)

    # 8. Tabel Tanggapan Penawaran
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tanggapan_penawaran (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        penawaran_id INTEGER NOT NULL,
        penanggap_id INTEGER NOT NULL,
        harga_tawar REAL NOT NULL,
        pesan TEXT,
        status TEXT DEFAULT 'diajukan', -- diajukan, diterima, ditolak
        waktu TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (penawaran_id) REFERENCES penawaran(id),
        FOREIGN KEY (penanggap_id) REFERENCES pengguna(id)
    )
    """)

    # 9. Tabel Transaksi
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transaksi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tanggal TEXT NOT NULL,
        penjual_id INTEGER NOT NULL,
        pembeli_id INTEGER NOT NULL,
        desa_id INTEGER NOT NULL,
        tipe_lahan_id INTEGER NOT NULL,
        grade_id INTEGER NOT NULL,
        berat_kg REAL NOT NULL,
        harga_per_kg REAL NOT NULL,
        total REAL NOT NULL,
        catatan TEXT,
        penawaran_id INTEGER,
        dibuat_pada TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (penjual_id) REFERENCES pengguna(id),
        FOREIGN KEY (pembeli_id) REFERENCES pengguna(id),
        FOREIGN KEY (desa_id) REFERENCES desa(id),
        FOREIGN KEY (tipe_lahan_id) REFERENCES tipe_lahan(id),
        FOREIGN KEY (grade_id) REFERENCES grade(id),
        FOREIGN KEY (penawaran_id) REFERENCES penawaran(id)
    )
    """)

    # 10. Tabel Notifikasi
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifikasi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pengguna_id INTEGER, -- NULL jika broadcast untuk semua
        jenis TEXT NOT NULL, -- 'perubahan_harga', 'penawaran_baru', 'verifikasi'
        judul TEXT NOT NULL,
        isi TEXT NOT NULL,
        status_dibaca INTEGER DEFAULT 0,
        waktu TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (pengguna_id) REFERENCES pengguna(id)
    )
    """)

    conn.commit()

    # Seed data awal jika belum ada
    seed_initial_data(cursor, conn)
    conn.close()

def seed_initial_data(cursor, conn):
    # Cek apakah sudah di-seed
    cursor.execute("SELECT COUNT(*) FROM desa")
    if cursor.fetchone()[0] > 0:
        return

    # Seed Desa di Kecamatan Pakong (termasuk 3 desa riset paper: Cen Lecen, Lebbek, Bicorong + desa sekitarnya)
    desa_list = [
        "Cen Lecen", "Lebbek", "Bicorong", "Pakong", "Bandungan", 
        "Bajang", "Klampis", "Seddur", "Somalang", "Palalang", "Bangkau", "Dahat"
    ]
    for d in desa_list:
        cursor.execute("INSERT INTO desa (nama_desa, kecamatan) VALUES (?, 'Pakong')", (d,))

    # Seed Tipe Lahan (Gunung, Tegal, Sawah sesuai paper & dokumen rancangan)
    tipe_lahan = [
        ("Gunung", "Lahan lereng perbukitan, karakter tembakau beraroma kuat dan nikotin tinggi"),
        ("Tegal", "Lahan kering tegalan, aroma seimbang dan warna cerah keemasan"),
        ("Sawah", "Lahan sawah pasca padi, rajangan halus daun tebal warna agak gelap")
    ]
    for nama, ket in tipe_lahan:
        cursor.execute("INSERT INTO tipe_lahan (nama, keterangan) VALUES (?, ?)", (nama, ket))

    # Seed Grade Tembakau Madura
    grades = [
        ("Grade Super A", "Warna kuning emas terang, aroma wangi gurih, rajangan rapi", 65000, 85000),
        ("Grade A", "Kuning kecoklatan bersih, rajangan baik, aroma harum khas", 55000, 68000),
        ("Grade B", "Coklat kemerahan, aroma cukup tajam, kadar getah sedang", 45000, 56000),
        ("Grade C", "Coklat tua / agak gelap, rajangan daun bawah/tengah", 35000, 46000),
        ("Grade D (Lokal)", "Daun asalan / campuran, rajangan sedang", 25000, 36000)
    ]
    for g, k, b, a in grades:
        cursor.execute("INSERT INTO grade (nama_grade, keterangan, harga_patokan_bawah, harga_patokan_atas) VALUES (?, ?, ?, ?)", (g, k, b, a))

    # Seed Pengguna (Akun demo berbagai peran)
    users = [
        ("Pak Slamet (Petani Cen Lecen)", "petani", "08123456701", 1, hash_password("petani123")),
        ("Pak Mat Rais (Petani Lebbek)", "petani", "08123456702", 2, hash_password("petani123")),
        ("Haji Munawir (Pengepul Pakong)", "pengepul", "08123456703", 4, hash_password("pengepul123")),
        ("Haji Syamsul (Tengkulak Bicorong)", "pengepul", "08123456704", 3, hash_password("pengepul123")),
        ("Pak Budi Santoso (Ketua Poktan Cen Lecen)", "pengurus_poktan", "08123456705", 1, hash_password("poktan123")),
        ("Ustadz Mahmud (Ketua Poktan Lebbek)", "pengurus_poktan", "08123456706", 2, hash_password("poktan123")),
        ("Administrator Sistem", "admin", "08123456700", 4, hash_password("admin123")),
        ("Perwakilan Gudang Pabrikan Pamekasan", "pihak_gudang", "08123456709", 4, hash_password("gudang123"))
    ]
    for nama, peran, telp, d_id, pwd in users:
        cursor.execute("""
        INSERT INTO pengguna (nama, peran, nomor_telepon, desa_id, kata_sandi, status_verifikasi) 
        VALUES (?, ?, ?, ?, ?, 'terverifikasi')
        """, (nama, peran, telp, d_id, pwd))

    # Seed Harga Acuan Industri / Pabrikan
    # Gunung
    cursor.execute("INSERT INTO harga_acuan (grade_id, tipe_lahan_id, harga_per_kg, sumber, berlaku_sejak) VALUES (1, 1, 72000, 'Pabrikan PT Gudang Garam Pamekasan', '2026-08-01')")
    cursor.execute("INSERT INTO harga_acuan (grade_id, tipe_lahan_id, harga_per_kg, sumber, berlaku_sejak) VALUES (2, 1, 62000, 'Pabrikan PT Gudang Garam Pamekasan', '2026-08-01')")
    cursor.execute("INSERT INTO harga_acuan (grade_id, tipe_lahan_id, harga_per_kg, sumber, berlaku_sejak) VALUES (3, 1, 50000, 'Pabrikan PT Djarum Gudang Larangan', '2026-08-01')")
    # Tegal
    cursor.execute("INSERT INTO harga_acuan (grade_id, tipe_lahan_id, harga_per_kg, sumber, berlaku_sejak) VALUES (1, 2, 68000, 'Disbun Pamekasan & Pabrikan', '2026-08-01')")
    cursor.execute("INSERT INTO harga_acuan (grade_id, tipe_lahan_id, harga_per_kg, sumber, berlaku_sejak) VALUES (2, 2, 58000, 'Disbun Pamekasan & Pabrikan', '2026-08-01')")
    cursor.execute("INSERT INTO harga_acuan (grade_id, tipe_lahan_id, harga_per_kg, sumber, berlaku_sejak) VALUES (3, 2, 48000, 'Disbun Pamekasan & Pabrikan', '2026-08-01')")
    # Sawah
    cursor.execute("INSERT INTO harga_acuan (grade_id, tipe_lahan_id, harga_per_kg, sumber, berlaku_sejak) VALUES (2, 3, 52000, 'Pasar Tembakau Keppo', '2026-08-01')")
    cursor.execute("INSERT INTO harga_acuan (grade_id, tipe_lahan_id, harga_per_kg, sumber, berlaku_sejak) VALUES (3, 3, 44000, 'Pasar Tembakau Keppo', '2026-08-01')")

    # Seed Histori Harga Harian (untuk tren dan transmisi harga di Cen Lecen, Lebbek, Bicorong)
    sample_prices = [
        # Cen Lecen (Transmisi tinggi ~1.120 di paper)
        ("2026-08-10", 1, 1, 1, 68000, "Transaksi Pasar Cen Lecen", "disetujui", 3, 5),
        ("2026-08-15", 1, 1, 1, 70000, "Survei Pengepul Munawir", "disetujui", 3, 5),
        ("2026-08-20", 1, 1, 1, 71500, "Pasar Desa Cen Lecen", "disetujui", 1, 5),
        ("2026-08-22", 1, 1, 2, 61000, "Pembelian Pengepul", "disetujui", 3, 5),
        ("2026-08-24", 1, 1, 1, 72500, "Timbangan Poktan", "disetujui", 5, 5),
        
        # Lebbek (Transmisi sedang ~0.405)
        ("2026-08-10", 2, 2, 1, 64000, "Laporan Petani Lebbek", "disetujui", 2, 6),
        ("2026-08-15", 2, 2, 1, 65000, "Pengepul Syamsul", "disetujui", 4, 6),
        ("2026-08-20", 2, 2, 1, 66000, "Laporan Poktan Lebbek", "disetujui", 6, 6),
        ("2026-08-24", 2, 2, 2, 57000, "Pengepul Syamsul", "disetujui", 4, 6),

        # Bicorong (Transmisi rendah ~0.135)
        ("2026-08-10", 3, 2, 1, 58000, "Tengkulak Lokal", "disetujui", 4, 5),
        ("2026-08-15", 3, 2, 1, 59000, "Laporan Tengkulak", "disetujui", 4, 5),
        ("2026-08-20", 3, 2, 1, 59500, "Survei Lapangan", "disetujui", 4, 5),
        ("2026-08-23", 3, 3, 3, 41000, "Laporan Petani", "disetujui", 2, 5),

        # Menunggu verifikasi (untuk dicoba disetujui pengurus poktan)
        ("2026-08-25", 1, 1, 1, 74000, "Input Tengkulak Baru", "menunggu", 3, None),
        ("2026-08-25", 2, 2, 2, 59000, "Input Petani Mat Rais", "menunggu", 2, None)
    ]
    for tgl, des, lah, grd, hrg, smb, stt, pel, ver in sample_prices:
        cursor.execute("""
        INSERT INTO harga (tanggal, desa_id, tipe_lahan_id, grade_id, harga_per_kg, sumber, status_verifikasi, pelapor_id, diverifikasi_oleh)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (tgl, des, lah, grd, hrg, smb, stt, pel, ver))

    # Seed Penawaran Awal
    cursor.execute("""
    INSERT INTO penawaran (pemosting_id, desa_id, tipe_lahan_id, grade_id, berat_kg, harga_diminta, keterangan, status, tanggal)
    VALUES (1, 1, 1, 1, 250, 72000, 'Tembakau gunung Cen Lecen rajangan kering siap angkut di gudang petani', 'terbuka', '2026-08-24')
    """)
    cursor.execute("""
    INSERT INTO penawaran (pemosting_id, desa_id, tipe_lahan_id, grade_id, berat_kg, harga_diminta, keterangan, status, tanggal)
    VALUES (2, 2, 2, 2, 400, 58000, 'Tembakau tegal Lebbek wangi khas daun tengah 8 keranjang', 'ditawar', '2026-08-23')
    """)

    # Seed Tanggapan Penawaran
    cursor.execute("""
    INSERT INTO tanggapan_penawaran (penawaran_id, penanggap_id, harga_tawar, pesan, status)
    VALUES (2, 3, 56500, 'Saya angkut besok pagi jam 8, siap timbang di tempat', 'diajukan')
    """)

    # Seed Transaksi Riil
    sample_trx = [
        ("2026-08-21", 1, 3, 1, 1, 1, 300, 71000, 21300000, "Pembayaran tunai di rumah petani Pak Slamet"),
        ("2026-08-22", 2, 4, 2, 2, 2, 250, 56000, 14000000, "Diangkut pikap Haji Syamsul di Lebbek"),
        ("2026-08-23", 1, 3, 1, 1, 2, 180, 60000, 10800000, "Grade A rajangan sore")
    ]
    for tgl, pen, pem, des, lah, grd, brt, hrg, tot, cat in sample_trx:
        cursor.execute("""
        INSERT INTO transaksi (tanggal, penjual_id, pembeli_id, desa_id, tipe_lahan_id, grade_id, berat_kg, harga_per_kg, total, catatan)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (tgl, pen, pem, des, lah, grd, brt, hrg, tot, cat))

    # Seed Notifikasi
    cursor.execute("""
    INSERT INTO notifikasi (pengguna_id, jenis, judul, isi)
    VALUES (NULL, 'perubahan_harga', 'Pembaruan Harga Tembakau Pakong', 'Harga Grade Super A lahan Gunung di Cen Lecen menyentuh Rp72.500/kg (naik Rp1.500).')
    """)
    cursor.execute("""
    INSERT INTO notifikasi (pengguna_id, jenis, judul, isi)
    VALUES (1, 'penawaran_baru', 'Penawaran Anda Ditanggapi', 'Pengepul Haji Munawir telah melihat penawaran 250 kg Grade Super A Anda.')
    """)
    cursor.execute("""
    INSERT INTO notifikasi (pengguna_id, jenis, judul, isi)
    VALUES (5, 'verifikasi', 'Menunggu Verifikasi Data Harga', 'Ada 2 laporan harga baru dari tengkulak & petani yang menunggu validasi Pengurus Poktan.')
    """)

    conn.commit()

if __name__ == "__main__":
    init_db()
    print("Database SQLite berhasil diinisialisasi dan diisi dengan data referensi Kecamatan Pakong.")
