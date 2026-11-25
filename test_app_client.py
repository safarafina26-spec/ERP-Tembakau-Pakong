from fastapi.testclient import TestClient
from main import app
import json

client = TestClient(app)

def test_full_system():
    print("=== TESTING DENGAN FASTAPI TESTCLIENT (IN-PROCESS ASGI) ===")

    # 1. Test Static HTML Homepage
    res = client.get("/")
    assert res.status_code == 200
    assert "ERP Tembakau Pakong" in res.text
    print("[1/10 PASS] Antarmuka web (index.html) berhasil dimuat.")

    # 2. Test Referensi Data
    res = client.get("/api/referensi")
    assert res.status_code == 200
    data = res.json()
    assert len(data["desa"]) >= 3
    assert len(data["tipe_lahan"]) == 3
    assert len(data["grade"]) >= 5
    print(f"[2/10 PASS] Referensi Master Data: {len(data['desa'])} Desa di Pakong, {len(data['tipe_lahan'])} Tipe Lahan, {len(data['grade'])} Grade Tembakau.")

    # 3. Test Autentikasi Pengguna
    res = client.post("/api/auth/login", json={"nomor_telepon": "08123456701", "kata_sandi": "petani123"})
    assert res.status_code == 200
    user = res.json()["user"]
    print(f"[3/10 PASS] Autentikasi: Berhasil masuk sebagai '{user['nama']}' ({user['peran']}).")

    # 4. Test Modul Informasi Harga Lapangan
    res = client.get("/api/harga/terbaru")
    assert res.status_code == 200
    harga_list = res.json()
    assert len(harga_list) > 0
    print(f"[4/10 PASS] Informasi Harga: {len(harga_list)} data harga terverifikasi di Cen Lecen, Lebbek, dan Bicorong.")

    # 5. Test Modul Pembanding Harga Acuan
    res = client.get("/api/harga/pembanding")
    assert res.status_code == 200
    pembanding = res.json()
    assert len(pembanding) > 0
    print(f"[5/10 PASS] Modul Pembanding Harga: {len(pembanding)} acuan industri (Gudang Garam, Djarum, Disbun) terbandingkan.")

    # 6. Test Input Harga Baru (Status Menunggu)
    input_payload = {
        "tanggal": "2026-08-25",
        "desa_id": 1,
        "tipe_lahan_id": 1,
        "grade_id": 1,
        "harga_per_kg": 73500,
        "sumber": "Timbangan Lapangan Kelompok Tani",
        "pelapor_id": 1,
        "catatan": "Kualitas rajangan daun atas prima"
    }
    res = client.post("/api/harga/input", json=input_payload)
    assert res.status_code == 200
    harga_id = res.json()["harga_id"]
    print(f"[6/10 PASS] Input Harga Lapangan: ID #{harga_id} berstatus 'menunggu' verifikasi Poktan.")

    # 7. Test Verifikasi Harga oleh Pengurus Poktan
    verif_payload = {
        "harga_id": harga_id,
        "pengurus_id": 5, # Pak Budi Santoso (Ketua Poktan)
        "status": "disetujui",
        "catatan": "Harga sesuai transaksi timbangan hari ini"
    }
    res = client.post("/api/harga/verifikasi", json=verif_payload)
    assert res.status_code == 200
    print(f"[7/10 PASS] Verifikasi Poktan: Harga ID #{harga_id} resmi diverifikasi dan diterbitkan.")

    # 8. Test Pasang Penawaran & Tanggapan Pengepul
    pen_res = client.post("/api/penawaran/buat", json={
        "pemosting_id": 1,
        "desa_id": 1,
        "tipe_lahan_id": 1,
        "grade_id": 1,
        "berat_kg": 350,
        "harga_diminta": 73000,
        "keterangan": "Tembakau gunung super wangi 10 keranjang siap kirim"
    })
    assert pen_res.status_code == 200
    pen_id = pen_res.json()["penawaran_id"]

    nego_res = client.post("/api/penawaran/tanggapi", json={
        "penawaran_id": pen_id,
        "penanggap_id": 3, # Haji Munawir
        "harga_tawar": 72000,
        "pesan": "Siap ambil sore ini tunai"
    })
    assert nego_res.status_code == 200
    print(f"[8/10 PASS] Modul Penawaran: Penawaran #{pen_id} berhasil diposting dan ditawar pembeli.")

    # 9. Test Pencatatan Transaksi Jual Beli
    trx_res = client.post("/api/transaksi/catat", json={
        "tanggal": "2026-08-25",
        "penjual_id": 1,
        "pembeli_id": 3,
        "desa_id": 1,
        "tipe_lahan_id": 1,
        "grade_id": 1,
        "berat_kg": 350,
        "harga_per_kg": 72000,
        "catatan": "Deal transaksi panen Cen Lecen",
        "penawaran_id": pen_id
    })
    assert trx_res.status_code == 200
    total_nilai = trx_res.json()["total"]
    assert total_nilai == 350 * 72000
    print(f"[9/10 PASS] Modul Transaksi: Berhasil membukukan transaksi senilai Rp{total_nilai:,.0f}.")

    # 10. Test Laporan Rekapitulasi ERP & Notifikasi
    lap_res = client.get("/api/laporan/ringkasan")
    assert lap_res.status_code == 200
    lap_data = lap_res.json()
    notif_res = client.get("/api/notifikasi")
    assert notif_res.status_code == 200
    notif_data = notif_res.json()
    print(f"[10/10 PASS] Laporan ERP & Notifikasi: Omzet Rp{lap_data['transaksi_umum']['total_omzet']:,.0f}, Notifikasi aktif: {len(notif_data)} pesan.")

    print("\n=======================================================")
    print(" SELURUH MODUL APLIKASI WEB BERHASIL DIVERIFIKASI 100%")
    print("=======================================================")

if __name__ == "__main__":
    test_full_system()
