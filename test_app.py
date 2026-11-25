import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def run_tests():
    print("=== PENGUJIAN OTOMATIS MODUL ERP TEMBAKAU PAKONG ===")
    
    # 1. Test Referensi Data
    res = requests.get(f"{BASE_URL}/api/referensi")
    assert res.status_code == 200, f"Error: {res.text}"
    ref = res.json()
    print(f"[OK] Referensi dimuat: {len(ref['desa'])} Desa, {len(ref['tipe_lahan'])} Tipe Lahan, {len(ref['grade'])} Grade.")

    # 2. Test Autentikasi Pengguna
    login_payload = {"nomor_telepon": "08123456701", "kata_sandi": "petani123"}
    res = requests.post(f"{BASE_URL}/api/auth/login", json=login_payload)
    assert res.status_code == 200, f"Login gagal: {res.text}"
    user = res.json()["user"]
    print(f"[OK] Login Berhasil: {user['nama']} (Peran: {user['peran']})")

    # 3. Test Ambil Informasi Harga Terverifikasi
    res = requests.get(f"{BASE_URL}/api/harga/terbaru")
    assert res.status_code == 200
    harga_list = res.json()
    print(f"[OK] Data harga terverifikasi: {len(harga_list)} entri tersedia.")

    # 4. Test Pembanding Harga (Lokal vs Acuan Pabrikan)
    res = requests.get(f"{BASE_URL}/api/harga/pembanding")
    assert res.status_code == 200
    pembanding = res.json()
    print(f"[OK] Pembanding harga: {len(pembanding)} kombinasi grade/lahan teranalisis.")

    # 5. Test Input Laporan Harga Baru (Menunggu Verifikasi)
    input_payload = {
        "tanggal": "2026-08-25",
        "desa_id": 1,
        "tipe_lahan_id": 1,
        "grade_id": 1,
        "harga_per_kg": 73000,
        "sumber": "Uji Sistem Otomatis",
        "pelapor_id": 1,
        "catatan": "Pengujian automated test"
    }
    res = requests.post(f"{BASE_URL}/api/harga/input", json=input_payload)
    assert res.status_code == 200
    harga_id = res.json()["harga_id"]
    print(f"[OK] Input harga baru berhasil: ID #{harga_id} berstatus 'menunggu'.")

    # 6. Test Verifikasi oleh Pengurus Poktan
    verif_payload = {
        "harga_id": harga_id,
        "pengurus_id": 5, # Pak Budi Santoso (Ketua Poktan Cen Lecen)
        "status": "disetujui",
        "catatan": "Disetujui lewat verifikasi otomatis"
    }
    res = requests.post(f"{BASE_URL}/api/harga/verifikasi", json=verif_payload)
    assert res.status_code == 200
    print(f"[OK] Verifikasi harga berhasil disetujui oleh pengurus Poktan.")

    # 7. Test Penawaran Petani
    penawaran_payload = {
        "pemosting_id": 1,
        "desa_id": 1,
        "tipe_lahan_id": 1,
        "grade_id": 1,
        "berat_kg": 200,
        "harga_diminta": 72500,
        "keterangan": "Test penawaran tembakau panen baru"
    }
    res = requests.post(f"{BASE_URL}/api/penawaran/buat", json=penawaran_payload)
    assert res.status_code == 200
    pen_id = res.json()["penawaran_id"]
    print(f"[OK] Penawaran baru diposting: ID #{pen_id}")

    # 8. Test Tanggapan Pengepul
    nego_payload = {
        "penawaran_id": pen_id,
        "penanggap_id": 3, # Haji Munawir
        "harga_tawar": 71000,
        "pesan": "Tawaran test: siap angkut"
    }
    res = requests.post(f"{BASE_URL}/api/penawaran/tanggapi", json=nego_payload)
    assert res.status_code == 200
    print(f"[OK] Tanggapan tawaran beli berhasil diajukan oleh Pengepul.")

    # 9. Test Catat Transaksi Jual Beli
    trx_payload = {
        "tanggal": "2026-08-25",
        "penjual_id": 1,
        "pembeli_id": 3,
        "desa_id": 1,
        "tipe_lahan_id": 1,
        "grade_id": 1,
        "berat_kg": 200,
        "harga_per_kg": 71000,
        "catatan": "Transaksi deal dari penawaran",
        "penawaran_id": pen_id
    }
    res = requests.post(f"{BASE_URL}/api/transaksi/catat", json=trx_payload)
    assert res.status_code == 200
    trx_res = res.json()
    print(f"[OK] Transaksi berhasil dicatat: Total Rp{trx_res['total']:,.0f}")

    # 10. Test Rekap & Laporan ERP
    res = requests.get(f"{BASE_URL}/api/laporan/ringkasan")
    assert res.status_code == 200
    laporan = res.json()
    print(f"[OK] Laporan rekap ERP: Total Omzet Rp{laporan['transaksi_umum']['total_omzet']:,.0f} dengan {laporan['transaksi_umum']['total_trx']} transaksi.")

    print("\n>>> SEMUA 10 SKENARIO PENGUJIAN FITUR SISTEM SUKSES (100% PASS) <<<")

if __name__ == "__main__":
    run_tests()
