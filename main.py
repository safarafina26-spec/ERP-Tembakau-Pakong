from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
import sqlite3
from datetime import datetime

from database import get_db, hash_password, init_db

app = FastAPI(
    title="Sistem Informasi Harga & Transaksi Tembakau Pakong - ERP Module",
    description="Modul ERP Tembakau Madura Berbasis Web Kecamatan Pakong",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inisialisasi DB saat start jika belum ada
init_db()

# Schema Pydantic
class LoginRequest(BaseModel):
    nomor_telepon: str
    kata_sandi: str

class RegisterRequest(BaseModel):
    nama: str
    peran: str
    nomor_telepon: str
    desa_id: int
    kata_sandi: str

class HargaInputRequest(BaseModel):
    tanggal: str
    desa_id: int
    tipe_lahan_id: int
    grade_id: int
    harga_per_kg: float
    sumber: str
    pelapor_id: int
    catatan: Optional[str] = None

class VerifikasiHargaRequest(BaseModel):
    harga_id: int
    pengurus_id: int
    status: str # 'disetujui' atau 'ditolak'
    catatan: Optional[str] = None

class PenawaranRequest(BaseModel):
    pemosting_id: int
    desa_id: int
    tipe_lahan_id: int
    grade_id: int
    berat_kg: float
    harga_diminta: float
    keterangan: Optional[str] = None
    tanggal: Optional[str] = None

class TanggapanRequest(BaseModel):
    penawaran_id: int
    penanggap_id: int
    harga_tawar: float
    pesan: Optional[str] = None

class TransaksiRequest(BaseModel):
    tanggal: str
    penjual_id: int
    pembeli_id: int
    desa_id: int
    tipe_lahan_id: int
    grade_id: int
    berat_kg: float
    harga_per_kg: float
    catatan: Optional[str] = None
    penawaran_id: Optional[int] = None

# --- API ENDPOINTS ---

# 1. Referensi Data
@app.get("/api/referensi")
def get_referensi():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, nama_desa, kecamatan FROM desa ORDER BY nama_desa")
    desa = [dict(row) for row in c.fetchall()]
    
    c.execute("SELECT id, nama, keterangan FROM tipe_lahan")
    tipe_lahan = [dict(row) for row in c.fetchall()]
    
    c.execute("SELECT id, nama_grade, keterangan, harga_patokan_bawah, harga_patokan_atas FROM grade")
    grade = [dict(row) for row in c.fetchall()]
    
    conn.close()
    return {"desa": desa, "tipe_lahan": tipe_lahan, "grade": grade}

# 2. Autentikasi Pengguna & Profil
@app.post("/api/auth/login")
def login(req: LoginRequest):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
    SELECT p.id, p.nama, p.peran, p.nomor_telepon, p.desa_id, p.kata_sandi, p.status_verifikasi, d.nama_desa 
    FROM pengguna p
    LEFT JOIN desa d ON p.desa_id = d.id
    WHERE p.nomor_telepon = ?
    """, (req.nomor_telepon,))
    user = c.fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=400, detail="Nomor telepon tidak terdaftar.")
    
    if user["kata_sandi"] != hash_password(req.kata_sandi):
        raise HTTPException(status_code=400, detail="Kata sandi keliru.")
    
    return {
        "status": "success",
        "user": {
            "id": user["id"],
            "nama": user["nama"],
            "peran": user["peran"],
            "nomor_telepon": user["nomor_telepon"],
            "desa_id": user["desa_id"],
            "desa_nama": user["nama_desa"],
            "status_verifikasi": user["status_verifikasi"]
        }
    }

@app.post("/api/auth/register")
def register(req: RegisterRequest):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM pengguna WHERE nomor_telepon = ?", (req.nomor_telepon,))
    if c.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Nomor telepon sudah terdaftar.")
    
    pwd_hash = hash_password(req.kata_sandi)
    c.execute("""
    INSERT INTO pengguna (nama, peran, nomor_telepon, desa_id, kata_sandi, status_verifikasi)
    VALUES (?, ?, ?, ?, ?, 'terverifikasi')
    """, (req.nama, req.peran, req.nomor_telepon, req.desa_id, pwd_hash))
    user_id = c.lastrowid
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Pendaftaran berhasil", "user_id": user_id}

@app.get("/api/pengguna")
def list_pengguna(peran: Optional[str] = None):
    conn = get_db()
    c = conn.cursor()
    query = """
    SELECT p.id, p.nama, p.peran, p.nomor_telepon, p.desa_id, d.nama_desa, p.status_verifikasi, p.dibuat_pada
    FROM pengguna p
    LEFT JOIN desa d ON p.desa_id = d.id
    """
    params = []
    if peran:
        query += " WHERE p.peran = ?"
        params.append(peran)
    query += " ORDER BY p.id ASC"
    c.execute(query, params)
    data = [dict(row) for row in c.fetchall()]
    conn.close()
    return data

# 3. Modul Informasi Harga Lapangan
@app.get("/api/harga/terbaru")
def get_harga_terbaru(desa_id: Optional[int] = None, grade_id: Optional[int] = None, tipe_lahan_id: Optional[int] = None):
    conn = get_db()
    c = conn.cursor()
    query = """
    SELECT h.id, h.tanggal, h.harga_per_kg, h.sumber, h.status_verifikasi, h.catatan,
           d.nama_desa, tl.nama as nama_lahan, g.nama_grade,
           p.nama as nama_pelapor, p.peran as peran_pelapor,
           v.nama as nama_verifikator
    FROM harga h
    JOIN desa d ON h.desa_id = d.id
    JOIN tipe_lahan tl ON h.tipe_lahan_id = tl.id
    JOIN grade g ON h.grade_id = g.id
    JOIN pengguna p ON h.pelapor_id = p.id
    LEFT JOIN pengguna v ON h.diverifikasi_oleh = v.id
    WHERE h.status_verifikasi = 'disetujui'
    """
    params = []
    if desa_id:
        query += " AND h.desa_id = ?"
        params.append(desa_id)
    if grade_id:
        query += " AND h.grade_id = ?"
        params.append(grade_id)
    if tipe_lahan_id:
        query += " AND h.tipe_lahan_id = ?"
        params.append(tipe_lahan_id)
        
    query += " ORDER BY h.tanggal DESC, h.id DESC"
    c.execute(query, params)
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return rows

@app.get("/api/harga/menunggu-verifikasi")
def get_harga_menunggu():
    conn = get_db()
    c = conn.cursor()
    query = """
    SELECT h.id, h.tanggal, h.harga_per_kg, h.sumber, h.status_verifikasi, h.catatan,
           d.nama_desa, tl.nama as nama_lahan, g.nama_grade,
           p.nama as nama_pelapor, p.peran as peran_pelapor
    FROM harga h
    JOIN desa d ON h.desa_id = d.id
    JOIN tipe_lahan tl ON h.tipe_lahan_id = tl.id
    JOIN grade g ON h.grade_id = g.id
    JOIN pengguna p ON h.pelapor_id = p.id
    WHERE h.status_verifikasi = 'menunggu'
    ORDER BY h.id DESC
    """
    c.execute(query)
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return rows

@app.post("/api/harga/input")
def input_harga(req: HargaInputRequest):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
    INSERT INTO harga (tanggal, desa_id, tipe_lahan_id, grade_id, harga_per_kg, sumber, status_verifikasi, pelapor_id, catatan)
    VALUES (?, ?, ?, ?, ?, ?, 'menunggu', ?, ?)
    """, (req.tanggal, req.desa_id, req.tipe_lahan_id, req.grade_id, req.harga_per_kg, req.sumber, req.pelapor_id, req.catatan))
    harga_id = c.lastrowid

    # Buat notifikasi ke pengurus poktan
    c.execute("""
    INSERT INTO notifikasi (jenis, judul, isi)
    VALUES ('verifikasi', 'Laporan Harga Baru Masuk', ?)
    """, (f"Laporan harga Rp{req.harga_per_kg:,.0f}/kg baru saja diinput dan memerlukan verifikasi.",))

    conn.commit()
    conn.close()
    return {"status": "success", "message": "Laporan harga tersimpan dan menunggu verifikasi pengurus poktan.", "harga_id": harga_id}

@app.post("/api/harga/verifikasi")
def verifikasi_harga(req: VerifikasiHargaRequest):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
    UPDATE harga 
    SET status_verifikasi = ?, diverifikasi_oleh = ?, catatan = COALESCE(?, catatan)
    WHERE id = ?
    """, (req.status, req.pengurus_id, req.catatan, req.harga_id))
    
    # Ambil detail harga untuk notifikasi jika disetujui
    if req.status == 'disetujui':
        c.execute("""
        SELECT h.harga_per_kg, d.nama_desa, g.nama_grade, tl.nama as nama_lahan
        FROM harga h
        JOIN desa d ON h.desa_id = d.id
        JOIN grade g ON h.grade_id = g.id
        JOIN tipe_lahan tl ON h.tipe_lahan_id = tl.id
        WHERE h.id = ?
        """, (req.harga_id,))
        h_info = c.fetchone()
        if h_info:
            c.execute("""
            INSERT INTO notifikasi (jenis, judul, isi)
            VALUES ('perubahan_harga', 'Harga Baru Diterbitkan', ?)
            """, (f"Harga terverifikasi: {h_info['nama_grade']} ({h_info['nama_lahan']}) di {h_info['nama_desa']} resmi tercatat Rp{h_info['harga_per_kg']:,.0f}/kg.",))

    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Harga berhasil diperbarui menjadi {req.status}."}

# 4. Modul Pembanding Harga (Lokal vs Acuan Industri Pabrikan)
@app.get("/api/harga/pembanding")
def get_pembanding():
    conn = get_db()
    c = conn.cursor()
    # Dapatkan harga acuan industri
    c.execute("""
    SELECT ha.id, ha.harga_per_kg as harga_acuan, ha.sumber, ha.berlaku_sejak,
           g.id as grade_id, g.nama_grade, tl.id as tipe_lahan_id, tl.nama as nama_lahan
    FROM harga_acuan ha
    JOIN grade g ON ha.grade_id = g.id
    JOIN tipe_lahan tl ON ha.tipe_lahan_id = tl.id
    """)
    acuan_list = [dict(row) for row in c.fetchall()]

    result = []
    for ac in acuan_list:
        # Cari rata-rata harga lokal terkini (status disetujui) untuk grade & tipe lahan yang sama
        c.execute("""
        SELECT AVG(harga_per_kg) as rata_lokal, MIN(harga_per_kg) as min_lokal, MAX(harga_per_kg) as max_lokal, COUNT(*) as jml_transaksi
        FROM harga
        WHERE grade_id = ? AND tipe_lahan_id = ? AND status_verifikasi = 'disetujui'
        """, (ac["grade_id"], ac["tipe_lahan_id"]))
        stat = c.fetchone()
        
        rata_lokal = round(stat["rata_lokal"], 2) if stat["rata_lokal"] else None
        selisih = round(rata_lokal - ac["harga_acuan"], 2) if rata_lokal else None
        persentase = round((selisih / ac["harga_acuan"]) * 100, 2) if selisih else None

        result.append({
            "grade_id": ac["grade_id"],
            "nama_grade": ac["nama_grade"],
            "tipe_lahan_id": ac["tipe_lahan_id"],
            "nama_lahan": ac["nama_lahan"],
            "harga_acuan": ac["harga_acuan"],
            "sumber_acuan": ac["sumber"],
            "rata_lokal": rata_lokal,
            "min_lokal": stat["min_lokal"],
            "max_lokal": stat["max_lokal"],
            "jml_laporan": stat["jml_transaksi"],
            "selisih": selisih,
            "persentase": persentase
        })

    conn.close()
    return result

# 5. Modul Penawaran Petani & Tanggapan Pengepul
@app.get("/api/penawaran")
def list_penawaran(status: Optional[str] = None):
    conn = get_db()
    c = conn.cursor()
    query = """
    SELECT p.id, p.tanggal, p.berat_kg, p.harga_diminta, p.keterangan, p.status,
           u.nama as pemosting_nama, u.nomor_telepon as pemosting_telp,
           d.nama_desa, tl.nama as nama_lahan, g.nama_grade,
           (SELECT COUNT(*) FROM tanggapan_penawaran tp WHERE tp.penawaran_id = p.id) as total_tanggapan
    FROM penawaran p
    JOIN pengguna u ON p.pemosting_id = u.id
    JOIN desa d ON p.desa_id = d.id
    JOIN tipe_lahan tl ON p.tipe_lahan_id = tl.id
    JOIN grade g ON p.grade_id = g.id
    """
    params = []
    if status:
        query += " WHERE p.status = ?"
        params.append(status)
    query += " ORDER BY p.id DESC"
    c.execute(query, params)
    data = [dict(row) for row in c.fetchall()]
    conn.close()
    return data

@app.post("/api/penawaran/buat")
def buat_penawaran(req: PenawaranRequest):
    conn = get_db()
    c = conn.cursor()
    tgl = req.tanggal or datetime.now().strftime("%Y-%m-%d")
    c.execute("""
    INSERT INTO penawaran (pemosting_id, desa_id, tipe_lahan_id, grade_id, berat_kg, harga_diminta, keterangan, status, tanggal)
    VALUES (?, ?, ?, ?, ?, ?, ?, 'terbuka', ?)
    """, (req.pemosting_id, req.desa_id, req.tipe_lahan_id, req.grade_id, req.berat_kg, req.harga_diminta, req.keterangan, tgl))
    pen_id = c.lastrowid

    # Notifikasi penawaran baru
    c.execute("""
    INSERT INTO notifikasi (jenis, judul, isi)
    VALUES ('penawaran_baru', 'Penawaran Tembakau Baru Terbit', ?)
    """, (f"Petani memposting penawaran baru: {req.berat_kg} kg tembakau harga diminta Rp{req.harga_diminta:,.0f}/kg.",))

    conn.commit()
    conn.close()
    return {"status": "success", "message": "Penawaran berhasil diposting", "penawaran_id": pen_id}

@app.post("/api/penawaran/tanggapi")
def tanggapi_penawaran(req: TanggapanRequest):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
    INSERT INTO tanggapan_penawaran (penawaran_id, penanggap_id, harga_tawar, pesan)
    VALUES (?, ?, ?, ?)
    """, (req.penawaran_id, req.penanggap_id, req.harga_tawar, req.pesan))
    
    # Update status penawaran jadi 'ditawar'
    c.execute("UPDATE penawaran SET status = 'ditawar' WHERE id = ?", (req.penawaran_id,))
    
    # Kirim notifikasi ke pemosting
    c.execute("SELECT pemosting_id FROM penawaran WHERE id = ?", (req.penawaran_id,))
    pemosting = c.fetchone()
    if pemosting:
        c.execute("""
        INSERT INTO notifikasi (pengguna_id, jenis, judul, isi)
        VALUES (?, 'penawaran_baru', 'Tawaran Harga Masuk', ?)
        """, (pemosting["pemosting_id"], f"Pengepul telah mengajukan penawaran beli senilai Rp{req.harga_tawar:,.0f}/kg untuk tembakau Anda."))

    conn.commit()
    conn.close()
    return {"status": "success", "message": "Tanggapan penawaran berhasil diajukan"}

@app.get("/api/penawaran/{penawaran_id}/tanggapan")
def list_tanggapan(penawaran_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
    SELECT tp.id, tp.harga_tawar, tp.pesan, tp.status, tp.waktu,
           u.nama as penanggap_nama, u.peran as penanggap_peran, u.nomor_telepon as penanggap_telp
    FROM tanggapan_penawaran tp
    JOIN pengguna u ON tp.penanggap_id = u.id
    WHERE tp.penawaran_id = ?
    ORDER BY tp.id DESC
    """, (penawaran_id,))
    data = [dict(row) for row in c.fetchall()]
    conn.close()
    return data

# 6. Modul Transaksi Jual Beli
@app.get("/api/transaksi")
def list_transaksi(user_id: Optional[int] = None, desa_id: Optional[int] = None):
    conn = get_db()
    c = conn.cursor()
    query = """
    SELECT t.id, t.tanggal, t.berat_kg, t.harga_per_kg, t.total, t.catatan,
           pj.id as penjual_id, pj.nama as penjual_nama, pj.nomor_telepon as penjual_telp,
           pb.id as pembeli_id, pb.nama as pembeli_nama, pb.nomor_telepon as pembeli_telp,
           d.nama_desa, tl.nama as nama_lahan, g.nama_grade
    FROM transaksi t
    JOIN pengguna pj ON t.penjual_id = pj.id
    JOIN pengguna pb ON t.pembeli_id = pb.id
    JOIN desa d ON t.desa_id = d.id
    JOIN tipe_lahan tl ON t.tipe_lahan_id = tl.id
    JOIN grade g ON t.grade_id = g.id
    """
    params = []
    conditions = []
    if user_id:
        conditions.append("(t.penjual_id = ? OR t.pembeli_id = ?)")
        params.extend([user_id, user_id])
    if desa_id:
        conditions.append("t.desa_id = ?")
        params.append(desa_id)
        
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
        
    query += " ORDER BY t.tanggal DESC, t.id DESC"
    c.execute(query, params)
    data = [dict(row) for row in c.fetchall()]
    conn.close()
    return data

@app.post("/api/transaksi/catat")
def catat_transaksi(req: TransaksiRequest):
    conn = get_db()
    c = conn.cursor()
    total = round(req.berat_kg * req.harga_per_kg, 2)
    c.execute("""
    INSERT INTO transaksi (tanggal, penjual_id, pembeli_id, desa_id, tipe_lahan_id, grade_id, berat_kg, harga_per_kg, total, catatan, penawaran_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (req.tanggal, req.penjual_id, req.pembeli_id, req.desa_id, req.tipe_lahan_id, req.grade_id, req.berat_kg, req.harga_per_kg, total, req.catatan, req.penawaran_id))
    trx_id = c.lastrowid

    # Jika transaksi berasal dari penawaran, set status selesai
    if req.penawaran_id:
        c.execute("UPDATE penawaran SET status = 'selesai' WHERE id = ?", (req.penawaran_id,))

    # Kirim notifikasi ke penjual dan pembeli
    c.execute("""
    INSERT INTO notifikasi (pengguna_id, jenis, judul, isi)
    VALUES (?, 'transaksi', 'Transaksi Tembakau Tercatat', ?)
    """, (req.penjual_id, f"Transaksi penjualan {req.berat_kg} kg tembakau senilai Rp{total:,.0f} telah berhasil dicatat."))
    
    c.execute("""
    INSERT INTO notifikasi (pengguna_id, jenis, judul, isi)
    VALUES (?, 'transaksi', 'Transaksi Pembelian Tercatat', ?)
    """, (req.pembeli_id, f"Transaksi pembelian {req.berat_kg} kg tembakau senilai Rp{total:,.0f} telah berhasil dicatat."))

    conn.commit()
    conn.close()
    return {"status": "success", "message": "Transaksi berhasil disimpan", "transaksi_id": trx_id, "total": total}

# 7. Modul Rekap & Laporan ERP
@app.get("/api/laporan/ringkasan")
def get_laporan_ringkasan():
    conn = get_db()
    c = conn.cursor()
    
    # Total volume & omzet transaksi
    c.execute("SELECT COUNT(*) as total_trx, SUM(berat_kg) as total_kg, SUM(total) as total_omzet, AVG(harga_per_kg) as rata_harga FROM transaksi")
    trx_stat = dict(c.fetchone())
    
    # Rata-rata per desa
    c.execute("""
    SELECT d.nama_desa, COUNT(t.id) as jml_trx, SUM(t.berat_kg) as total_kg, SUM(t.total) as total_nilai, AVG(t.harga_per_kg) as rata_harga
    FROM desa d
    LEFT JOIN transaksi t ON d.id = t.desa_id
    GROUP BY d.id
    ORDER BY total_nilai DESC
    """)
    desa_stat = [dict(row) for row in c.fetchall()]

    # Rata-rata per grade
    c.execute("""
    SELECT g.nama_grade, COUNT(t.id) as jml_trx, SUM(t.berat_kg) as total_kg, AVG(t.harga_per_kg) as rata_harga
    FROM grade g
    LEFT JOIN transaksi t ON g.id = t.grade_id
    GROUP BY g.id
    ORDER BY g.id ASC
    """)
    grade_stat = [dict(row) for row in c.fetchall()]

    conn.close()
    return {
        "transaksi_umum": trx_stat,
        "per_desa": desa_stat,
        "per_grade": grade_stat
    }

# 8. Modul Notifikasi
@app.get("/api/notifikasi")
def get_notifikasi(user_id: Optional[int] = None):
    conn = get_db()
    c = conn.cursor()
    query = """
    SELECT id, pengguna_id, jenis, judul, isi, status_dibaca, waktu
    FROM notifikasi
    WHERE pengguna_id IS NULL
    """
    params = []
    if user_id:
        query += " OR pengguna_id = ?"
        params.append(user_id)
    query += " ORDER BY id DESC LIMIT 20"
    c.execute(query, params)
    data = [dict(row) for row in c.fetchall()]
    conn.close()
    return data

# Serve static files (logo, etc)
@app.get("/logo_etp.jpg")
def get_logo():
    logo_path = os.path.join(os.path.dirname(__file__), "logo_etp.jpg")
    if os.path.exists(logo_path):
        return FileResponse(logo_path, media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="Logo not found")

# Serve static HTML UI
FRONTEND_FILE = os.path.join(os.path.dirname(__file__), "index.html")

@app.get("/", response_class=HTMLResponse)
def index_page():
    if os.path.exists(FRONTEND_FILE):
        with open(FRONTEND_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Sistem ERP Tembakau Pakong Aktif. File index.html sedang dimuat...</h1>"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
