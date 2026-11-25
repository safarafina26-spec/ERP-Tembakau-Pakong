import asyncio
from main import (
    get_referensi, login, LoginRequest, get_harga_terbaru,
    get_pembanding, input_harga, HargaInputRequest,
    verifikasi_harga, VerifikasiHargaRequest, buat_penawaran,
    PenawaranRequest, tanggapi_penawaran, TanggapanRequest,
    catat_transaksi, TransaksiRequest, get_laporan_ringkasan,
    get_notifikasi, index_page
)

def run_direct_module_tests():
    print("=== PENGUJIAN LOGIKA FUNGSI & MODUL APLIKASI (BLACK-BOX) ===")

    # 1. Uji Tampilan Web
    html = index_page()
    assert "ERP Tembakau Pakong" in html
    assert "Cen Lecen" in html
    print("[1/9 PASS] Frontend Web: index.html berhasil dirender.")

    # 2. Uji Referensi Master Data
    ref = get_referensi()
    assert len(ref["desa"]) >= 12
    assert len(ref["tipe_lahan"]) == 3
    assert len(ref["grade"]) >= 5
    print(f"[2/9 PASS] Master Data: {len(ref['desa'])} Desa, {len(ref['tipe_lahan'])} Tipe Lahan, {len(ref['grade'])} Grade.")

    # 3. Uji Autentikasi Pengguna
    auth = login(LoginRequest(nomor_telepon="08123456701", kata_sandi="petani123"))
    assert auth["status"] == "success"
    assert auth["user"]["peran"] == "petani"
    print(f"[3/9 PASS] Login Pengguna: Berhasil autentikasi {auth['user']['nama']}.")

    # 4. Uji Modul Informasi Harga Lapangan
    harga_list = get_harga_terbaru()
    assert len(harga_list) > 0
    print(f"[4/9 PASS] Modul Harga: {len(harga_list)} catatan harga terverifikasi aktif.")

    # 5. Uji Modul Pembanding Acuan
    pembanding = get_pembanding()
    assert len(pembanding) > 0
    print(f"[5/9 PASS] Modul Pembanding: {len(pembanding)} data perbandingan harga riil vs pabrikan terhitung.")

    # 6. Uji Input & Verifikasi Alur Poktan
    h_input = input_harga(HargaInputRequest(
        tanggal="2026-08-25",
        desa_id=1,
        tipe_lahan_id=1,
        grade_id=1,
        harga_per_kg=74000,
        sumber="Timbangan Lapangan Kelompok Tani Cen Lecen",
        pelapor_id=1
    ))
    assert h_input["status"] == "success"
    harga_id = h_input["harga_id"]

    h_verif = verifikasi_harga(VerifikasiHargaRequest(
        harga_id=harga_id,
        pengurus_id=5,
        status="disetujui",
        catatan="Valid sesuai panen pagi"
    ))
    assert h_verif["status"] == "success"
    print(f"[6/9 PASS] Siklus Verifikasi Poktan: Input ID #{harga_id} -> Verifikasi Disetujui -> Diterbitkan Publik.")

    # 7. Uji Pasar Penawaran & Tanggapan Nego
    pen = buat_penawaran(PenawaranRequest(
        pemosting_id=1,
        desa_id=1,
        tipe_lahan_id=1,
        grade_id=1,
        berat_kg=300,
        harga_diminta=73500,
        keterangan="Rajangan daun atas kering sempurna"
    ))
    assert pen["status"] == "success"
    pen_id = pen["penawaran_id"]

    tanggapan = tanggapi_penawaran(TanggapanRequest(
        penawaran_id=pen_id,
        penanggap_id=3,
        harga_tawar=72000,
        pesan="Siap timbang di rumah sore ini"
    ))
    assert tanggapan["status"] == "success"
    print(f"[7/9 PASS] Modul Penawaran & Tanggapan: Penawaran #{pen_id} berhasil diajukan dan ditawar.")

    # 8. Uji Pencatatan Transaksi Jual Beli
    trx = catat_transaksi(TransaksiRequest(
        tanggal="2026-08-25",
        penjual_id=1,
        pembeli_id=3,
        desa_id=1,
        tipe_lahan_id=1,
        grade_id=1,
        berat_kg=300,
        harga_per_kg=72000,
        catatan="Deal kesepakatan penawaran",
        penawaran_id=pen_id
    ))
    assert trx["status"] == "success"
    assert trx["total"] == 300 * 72000
    print(f"[8/9 PASS] Modul Transaksi: Nota transaksi berhasil dibukukan dengan total Rp{trx['total']:,.0f}.")

    # 9. Uji Laporan Rekapitulasi ERP & Notifikasi
    lap = get_laporan_ringkasan()
    notifs = get_notifikasi()
    assert lap["transaksi_umum"]["total_trx"] > 0
    assert len(notifs) > 0
    print(f"[9/9 PASS] Modul Rekap ERP & Notifikasi: Total Omzet Rp{lap['transaksi_umum']['total_omzet']:,.0f}, Notifikasi aktif: {len(notifs)}.")

    print("\n=======================================================")
    print(" SELURUH MODUL APLIKASI WEB BERFUNGSI 100% SESUAI RANCANGAN")
    print("=======================================================")

if __name__ == "__main__":
    run_direct_module_tests()
