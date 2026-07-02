# MKT Helpdesk Agentic AI Automation
## Technical Architecture & Operational Guide
**Dokumen Resmi Presentasi Head Dept - Confidential**

---

## 1. Arsitektur Sistem (System Architecture)
MKT Helpdesk Agentic AI adalah sistem tiket dan pemantauan mandiri berbasi AI yang mengkombinasikan arsitektur *Microservices* modern. Sistem ini di-hosting di dalam ekosistem **Docker Container** untuk menjamin stabilitas dan isolasi *environment*.

### Komponen Utama:
1. **Frontend (Vanilla HTML/CSS/JS + Vite):** Antarmuka pengguna *real-time* dengan fitur Auto-Polling (Refresh otomatis setiap 10 detik). Bertugas merender Dashboard KPI, Incident Memory, dan Zammad Ticketing.
2. **Backend (Python 3.11 + FastAPI):** Mesin utama yang menghubungkan UI, Database, dan AI. Berisi endpoint REST API, *scheduler* otomatis (Polling Zammad tiap 15 detik), dan sistem *Webhook* penerima insiden dari agen PC Kasir.
3. **Database (PostgreSQL 16 + Redis 7):**
   - **PostgreSQL:** Menyimpan data terstruktur jangka panjang (*Incident Memory*, Data Tiket, Audit Log).
   - **Redis:** *In-Memory Caching* dan *Message Broker* untuk pengiriman data temporal (Ping Status, CrewAI Workflow stream).
4. **AI Engine (CrewAI + ChromaDB):** Agen AI multi-peran (Tier 0 & Tier 1) yang diotaki oleh Gemini 2.0 Flash. Dilengkapi dengan **ChromaDB** sebagai sistem RAG (*Retrieval-Augmented Generation*) untuk mencari *troubleshoot* dari kasus masa lalu.
5. **Zammad (Ticketing System):** Platform Helpdesk pihak ketiga yang menerima laporan dari User/Telegram dan di-sinkronisasikan oleh Backend kita secara proaktif.

---

## 2. Cara Menggunakan Sistem (Operational Guide)

### A. Cara Menyalakan Sistem (Start-Up)
1. Buka aplikasi **Docker Desktop** pada Windows Server/PC Anda. Pastikan statusnya hijau (*Engine Running*).
2. Buka folder `D:\Helpdesk MKT Agentic AI Automation`.
3. Jalankan file `start_all.bat`.
4. Script akan menyalakan secara berurutan: Zammad -> PostgreSQL & Redis -> MKT Backend -> CrewAI Engine.
5. Akses antarmuka di Browser melalui: `http://localhost:8000` (atau IP PC terkait).

### B. Cara Menggunakan Frontend (Dashboard)
- **Dashboard:** Menampilkan agregasi data KPI harian (Tiket Open, MTTR, SLA). Data ini diperbarui setiap 10 detik secara *background*.
- **Incident Memory:** Melihat rekaman peringatan kerusakan (*Hardware Alert*) yang dikirim langsung dari agen PowerShell di PC Kasir. Angka notifikasi merah menunjukkan *New Unread Alert*. Angka akan menghilang otomatis saat menu dibuka.
- **Zammad Tickets:** AI akan memfilter tiket yang masuk dan melakukan analisis mandiri. Jika AI berhasil memecahkan masalah (Tier 0), status akan menjadi "Resolved by AI".

### C. Alur Kerja Hardware Monitor (Agen PC Kasir)
1. PC Kasir di site menjalankan `hardware_monitor.ps1` secara *invisible background*.
2. Script memonitor *WMI Event* (Windows Management Instrumentation) untuk mencatat aktivitas pelepasan kabel USB dan LAN.
3. Saat kabel tercabut, script menembak *Webhook API* `POST /api/devices/{device_id}/hardware-alert` ke MKT Backend.
4. Backend meneruskan alert ke Database PostgreSQL dan *Frontend* menampilkan notifikasi merah secara instan.

---

## 3. Cara Menangani Bug & Troubleshoot (Developer Guide)

Sebagai Programmer/Admin, Anda harus mengetahui lokasi spesifik jika terjadi kendala sistem:

### Isu 1: Tiket Zammad Telat Masuk / Tidak Sinkron
- **Penyebab:** *Rate Limit* dari server Zammad atau *Backend Service* terhenti.
- **Troubleshoot:**
  1. Buka file konfigurasi di `backend/config.py`.
  2. Pastikan `ZAMMAD_POLL_INTERVAL` di setel ke angka wajar (rekomendasi: 15 detik).
  3. Restart Backend container: Buka terminal (CMD) dan jalankan `docker restart mkt_backend`.
  4. Cek log via `docker logs mkt_backend --tail 50`.

### Isu 2: Frontend Tidak Auto-Refresh
- **Penyebab:** Browser meng-cache file Javascript versi lama (`app.js`).
- **Troubleshoot:** 
  1. Instruksikan pengguna untuk menekan **Ctrl + F5** di browser (Hard Refresh).
  2. Verifikasi di file `frontend/js/app.js` pada fungsi `initClock()` bahwa perintah `setInterval(refreshActivePage, 10000)` sudah ter-eksekusi.

### Isu 3: Jawaban AI (CrewAI) Halu / Tidak Sesuai SOP
- **Penyebab:** Knowledge Base (RAG) di ChromaDB belum terupdate dengan dokumen terbaru.
- **Troubleshoot:**
  1. Buka file `IT_Helpdesk_Knowledge_Base.md`. Masukkan SOP atau kasus terbaru di file tersebut.
  2. Buka terminal (CMD/Powershell), jalankan skrip *Ingest*:
     `docker exec mkt_crewai python ingest_rag.py`
  3. AI akan me-refresh memorinya berdasarkan dokumen Markdown terbaru secara instan.

### Isu 4: Database Error / Container Mati
- **Penyebab:** Memori Docker penuh atau *corrupt container*.
- **Troubleshoot:**
  1. Cek status database: `docker ps | findstr postgres`
  2. Jika statusnya *Exited*, periksa error-nya: `docker logs mkt_postgres`
  3. Lakukan restart penuh: `docker-compose restart postgres redis backend crewai`

---

## 4. Keunggulan Sistem Ini (Elevator Pitch)
1. **Otomasi Proaktif:** Tidak lagi menunggu kasir melapor hardware rusak. AI memantau USB & LAN secara proaktif detik itu juga via WMI *Sensors*.
2. **Auto-Pilot Operations:** Frontend modern dengan *Auto-Polling*, menghilangkan keharusan *Admin* untuk me-refresh halaman berulang-ulang.
3. **Pemisahan Penanganan (Tier 0 & HITL):** AI dibekali logika pintar untuk mendeteksi mana masalah yang bisa ia pandu langsung (Tier 0), dan mana masalah rahasia server yang harus segera dieskalasikan ke Human-in-The-Loop (HITL).
4. **Data Aman 100%:** PostgreSQL & Redis di-isolasi sepenuhnya di *On-Premise Server* menggunakan arsitektur Volume Docker tahan banting.

*(Disusun oleh MKT Agentic AI - 2026)*
