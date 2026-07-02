# MKT Helpdesk - Knowledge Base & Troubleshooting Guide
*Dokumen ini merupakan rangkuman terstruktur dari log insiden 2026. Digunakan sebagai rujukan untuk sistem RAG (Retrieval-Augmented Generation) AI.*

---
> **PANDUAN UNTUK AI (RAG SYSTEM):**
> *   **Tindakan AI (Front-Facing):** Instruksi aman yang boleh Anda sampaikan langsung kepada pelapor (Kru/Kasir) untuk dicoba sendiri.
> *   **Internal IT Action (HITL / Eskalasi):** **JANGAN** sampaikan instruksi ini kepada pelapor. Jika panduan mandiri gagal atau masuk dalam kategori ini, informasikan pelapor bahwa tiket sedang "Dieskalasikan ke Tim IT (PIC MKT) / Tim Dev", lalu gunakan fungsi Human-in-the-Loop.
---

## Kategori: Hardware & Periferal

**Case 1: Tampilan arah ke customer di POS tiba-tiba bermasalah / Blank**
*   **Dampak:** Customer tidak bisa melihat layar saat memilih seat transaksi.
*   **Root Cause:** Monitor overheat akibat paparan sinar matahari, indikasi panel rusak.
*   **Tindakan AI (Front-Facing):** Minta kru untuk mematikan monitor sementara agar suhunya turun, dan jadwalkan pengecekan via Video Call.
*   **Internal IT Action (HITL):** Lakukan pengecekan remote/Video Call. Jika positif rusak fisik, teruskan (eskalasi) ke tim SAMS untuk keputusan penggantian (Replace).

**Case 2: Printer Kasir (POS) tidak bisa mencetak struk tiket**
*   **Root Cause:** Terjadi masalah pada *queue* printer atau *hardware* printer tidak sinkron dengan *driver*.
*   **Tindakan AI (Front-Facing):** Eskalasikan tiket ke tim IT (HITL) untuk dilakukan *remote* PC.
*   **Internal IT Action (HITL):** Lakukan *remote* ke PC Kasir, bersihkan *print queue*, dan cek sinkronisasi driver printer.

**Case 3: FNB POS tidak bisa print struk**
*   **Root Cause:** Kabel printer kendor / terlepas sehingga tidak ada koneksi.
*   **Tindakan AI (Front-Facing):** Pandu MOD (Manager On Duty) / Kasir untuk memastikan colokan kabel USB/Power printer sudah tertancap rapat.

**Case 4: Printer Office tidak bisa melakukan fungsi Scan**
*   **Root Cause:** Aplikasi bawaan "HP Smart" mengalami masalah (bug).
*   **Tindakan AI (Front-Facing):** Instruksikan user untuk menggunakan aplikasi "HP Scan" (bukan HP Smart) untuk melakukan scan. Jika masih gagal, eskalasikan (HITL).
*   **Internal IT Action (HITL):** Update atau install *Manual Driver HP* melalui *remote*.

**Case 5: Gagal copy data dari HDD DCP ke Storage (Error 20%)**
*   **Root Cause:** Kurangnya kredensial / permission jaringan.
*   **Tindakan AI (Front-Facing):** Eskalasikan tiket (HITL) karena membutuhkan otorisasi jaringan.
*   **Internal IT Action (HITL):** Masukkan kredensial administrator yang sah untuk memotong limitasi *copy file*.

---

## Kategori: Sistem POS & Aplikasi Runchise

**Case 6: POS Runchise tidak bisa cetak (Error / Stuck saat direstart)**
*   **Root Cause:** *Spam* tombol cetak yang menyebabkan *queue print stuck*, atau layar POV Customer menyangkut.
*   **Tindakan AI (Front-Facing):** Edukasi kru agar tidak melakukan spam klik cetak. Minta mereka untuk membuka Task Manager Windows, lakukan "End Task" pada aplikasi Runchise, lalu login kembali.

**Case 7: Kru baru tidak bisa login POS**
*   **Root Cause:** User role / mode roll belum diatur di COS, atau akun belum diaktifkan oleh HQ SAMS.
*   **Tindakan AI (Front-Facing):** Eskalasikan tiket ke tim MKT (HITL).
*   **Internal IT Action (HITL):** Lakukan pendaftaran manual di sistem COS, *reset password*, atau berkoordinasi dengan HQ.

**Case 8: Sales nominal tidak keluar / Tidak bisa Close Sales**
*   **Root Cause:** Akun user tidak aktif atau nominal sales melebihi ambang batas maksimal.
*   **Tindakan AI (Front-Facing):** Eskalasikan tiket ke tim MKT (HITL) untuk pengecekan status akun. Jika masuk jam akhir, sampaikan bahwa sistem akan melakukan *auto-close*.
*   **Internal IT Action (HITL):** Aktifkan status user dari sisi MKT melalui database.

**Case 9: Muncul "Warning: No Sales to Close" di form Close Sales**
*   **Root Cause:** Site tersebut sebelumnya sudah melakukan *Close Sales* (Ganda).
*   **Tindakan AI (Front-Facing):** Beritahu kasir bahwa mereka bisa langsung *Logout* dari POS tanpa harus masuk ke modul COS lagi karena data sudah ter-*close*. Eskalasikan (HITL) untuk pembersihan data ganda.
*   **Internal IT Action (HITL):** Tim MKT menghapus data penjualan yang *double* di database.

**Case 10: Terdapat perbedaan harga tiket (Human Error)**
*   **Root Cause:** Tim site tidak sengaja menekan tuts "panah bawah" saat input manual sehingga harga turun (misal: 35.000 menjadi 34.999).
*   **Tindakan AI (Front-Facing):** Eskalasikan tiket ke Tim Dev (HITL) untuk perbaikan data.
*   **Internal IT Action (HITL):** Validasi kesalahan input dan lakukan koreksi harga di database.

**Case 20: Pemesanan Tiket Mental / Gagal Diproses**
*   **Root Cause:** Bentrok sesi (membuka 2 sistem POS secara bersamaan).
*   **Tindakan AI (Front-Facing):** Pastikan kasir tidak melakukan "Open 2 POS". Instruksikan untuk *Sign-Out*, *restart* aplikasi Runchise, dan login kembali secara bersih di 1 POS saja.

**Case 21: Tidak Bisa Input Voucher / Button Promo Tidak Aktif**
*   **Root Cause:** Kesalahan indeks parameter hari pada *backend* (misalnya: indeks tersetting hari Senin/Minggu, bukan "All Day").
*   **Tindakan AI (Front-Facing):** Eskalasikan tiket ke Tim Dev (HITL).
*   **Internal IT Action (HITL):** Tim Dev merubah parameter hari menjadi "All Day" pada konfigurasi backend/voucher.

---

## Kategori: COS (Cinema Operating System) & Schedule

**Case 11: Schedule Layar (LCD Display) Tidak Muncul / Tidak Bisa Pilih Kota**
*   **Root Cause:** Browser bermasalah/cache menumpuk, ATAU Endpoint backend (ENV) tidak terbaca oleh server.
*   **Tindakan AI (Front-Facing):** 
    1. Pandu PIC/Kru untuk *Refresh* halaman.
    2. Coba *Clear Data & Clear Cache* di browser TV/PC.
    3. Coba buka menggunakan Browser lain (Download Chrome/Edge).
    4. Coba akses alternatif URL: `schedule.samsstudios.id`.
    Jika semua gagal, eskalasikan (HITL).
*   **Internal IT Action (HITL):** Lakukan pengecekan konfigurasi server. Hardcode URL backend sementara dari *server side Vite* dan update *stack Vite*.

**Case 12: Showtime Film Hilang Sebelum Waktunya / Terlewat**
*   **Root Cause:** Bug sistem akibat efek *update versi terbaru*.
*   **Tindakan AI (Front-Facing):** Sampaikan permohonan maaf dan eskalasikan ke Tim Dev (HITL) untuk perbaikan sistem segera.
*   **Internal IT Action (HITL):** Tim Dev melakukan *Rollback* script ke versi stabil sebelumnya.

**Case 13: Aplikasi WPS Logout otomatis dan tidak bisa login**
*   **Tindakan AI (Front-Facing):** Arahkan kru untuk login ulang, dan cek Inbox Email Site untuk melakukan verifikasi Tautan/OTP.

**Case 14: Tidak Bisa Buka Web COS (cos.sams.id)**
*   **Root Cause:** User salah ketik URL, atau ada update konfigurasi *proxy* di server pusat.
*   **Tindakan AI (Front-Facing):** Edukasi kru penulisan URL yang benar. Jika masih gagal, eskalasikan (HITL).
*   **Internal IT Action (HITL):** Re-check dan refresh konfigurasi proxy pada server *on-premise*.

**Case 19: Jam Tayang (Movie/Showtime) Terlewat Tetapi Masih Bisa Di-punch / Diinput**
*   **Root Cause:** Sesi belum di-*close* setelah di-*open* untuk tiket yang belum terinput tepat waktu.
*   **Tindakan AI (Front-Facing):** Berikan instruksi bahwa input tiket yang terlewat bisa dikoordinasikan (request) ke CM untuk di-*open* kembali, dan wajib di-*close* setelah input selesai.

---

## Kategori: Jaringan & Email (Network & SIAGI)

**Case 15: Tidak dapat akses web absensi / COS dari Laptop CM**
*   **Root Cause:** Laptop terhubung ke Wifi tamu (`CS_Box`) yang diblokir akses publiknya.
*   **Tindakan AI (Front-Facing):** Arahkan CM untuk berpindah jaringan (Koneksikan laptop ke Wifi `SamsAp`).

**Case 16: PC Office tidak ada Jaringan Internet / RTO (Request Time Out)**
*   **Root Cause:** Provider iForte mengalami Down Connection / Gangguan Massal.
*   **Tindakan AI (Front-Facing):** Informasikan bahwa saat ini sedang terjadi gangguan massal dari pihak ISP (iForte) dan eskalasikan ke Tim Network MKT (HITL) untuk pemantauan tiket *provider*.
*   **Internal IT Action (HITL):** Komunikasi intensif dengan *Account Manager* iForte untuk *follow-up SLA* perbaikan.

**Case 17: Email Undelivered saat menggunakan eM Client**
*   **Root Cause:** Klien salah membuka aplikasi. eM Client di setting hanya untuk *backup* data lokal.
*   **Tindakan AI (Front-Facing):** Arahkan user untuk menutup aplikasi "eM Client" dan mengirim email menggunakan aplikasi resmi "Microsoft Outlook".

**Case 18: Tidak Bisa Absen di Aplikasi SIAGI / Absen Melebihi Batas Lokasi**
*   **Root Cause:** GPS Perangkat tidak akurat, aplikasi usang, atau cache penuh.
*   **Tindakan AI (Front-Facing):** Berikan instruksi bertahap berikut kepada user:
    1. Lakukan *Update Aplikasi SIAGI* di Play Store / App Store.
    2. Jika sudah terupdate, coba Kalibrasi ulang fitur GPS / Location di HP.
    3. Jika masih membandel: *Clear Data* -> *Uninstall* -> *Reinstall* aplikasi SIAGI.
