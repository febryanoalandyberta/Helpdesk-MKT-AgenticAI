# instruksi.md

# Prompt Instruksi untuk Anti Gravity

Gunakan instruksi ini sebagai **master prompt** untuk membangun sistem lengkap bernama:

# Helpdesk MKT Agentic AI Automation

---

## 1. Tujuan Sistem

Bangun sebuah sistem helpdesk otomatis untuk Operational Team IT Helpdesk PT Megakreasi Tech (MKT).

PT Megakreasi Tech (MKT) adalah perusahaan IT support yang menangani operasional bioskop Sam's Studio's.

Sam's Studio's memiliki:
- 18 site bioskop.
- 18 kota berbeda.
- Setiap site memiliki 4 perangkat POS:
  - POS Ticketing 01
  - POS Ticketing 02
  - POS FNB 01
  - POS FNB 02

Total perangkat yang dikelola minimal:
- 72 POS.

Sistem ini harus membantu tim IT Helpdesk MKT untuk:
- Menerima tiket dari Zammad.
- Melakukan analisis otomatis.
- Mencari solusi dari knowledge base.
- Melakukan diagnosis teknis.
- Mengirim notifikasi ke Telegram.
- Menyediakan dashboard monitoring.
- Menyimpan memory insiden.

---

## 2. Arsitektur Konseptual

```text
Site / Customer
      ↓
Zammad Ticketing System
      ↓
CrewAI Multi-Agent System
      ├── Agentic AI Tier 0
      ├── Agentic AI Tier 1
      ├── Knowledge Agent
      ├── Escalation Agent
      └── Monitoring Agent
      ↓
Integrations
      ├── Telegram Bot
      ├── Knowledge Base
      ├── POS Systems
      └── Monitoring Database
      ↓
Dashboard Monitoring
```

**Catatan Penting:**
- Anti Gravity digunakan untuk membangun seluruh sistem ini.
- Anti Gravity bukan bagian dari workflow bisnis.
- CrewAI adalah engine Agentic AI yang menjalankan seluruh agent.

---

## 3. Technology Stack

Gunakan teknologi berikut:

- Application Builder: Anti Gravity
- Agentic AI Engine: CrewAI
- Ticketing System: Zammad
- Database: PostgreSQL
- Cache: Redis
- Notification: Telegram Bot API
- Knowledge Base: Vector Database atau PostgreSQL
- Monitoring: Grafana atau dashboard internal
- Remote Diagnostic Tools: SSH, Ping, Port Check

---

## 4. Modul yang Harus Dibangun

Bangun modul berikut:

1. Zammad Integration Module
2. CrewAI Orchestrator Module
3. Agentic AI Tier 0 Module
4. Agentic AI Tier 1 Module
5. Knowledge Base Module
6. Telegram Notification Module
7. Dashboard Monitoring Module
8. Incident Memory Module
9. Audit Logging Module
10. Site & Device Inventory Module
11. User Authentication & Authorization Module

---

## 5. Workflow Logic

### Step 1
Customer atau Site membuat tiket melalui Zammad.

### Step 2
Sistem mengambil tiket baru dari Zammad.

### Step 3
CrewAI menjalankan Agentic AI Tier 0.

### Step 4
Tier 0 melakukan:
- Analisis issue.
- Klasifikasi kategori.
- Penentuan severity.
- Pencarian SOP.
- Penentuan confidence score.

### Step 5
Jika confidence tinggi, Tier 0 memberikan solusi otomatis.

### Step 6
Jika confidence rendah atau issue kompleks, Tier 0 meneruskan ke Agentic AI Tier 1.

### Step 7
Tier 1 melakukan diagnosis teknis ke perangkat POS.

### Step 8
Escalation Agent mengirim notifikasi ke Telegram.

### Step 9
Sistem memperbarui tiket di Zammad.

### Step 10
Sistem menyimpan hasil ke Incident Memory.

### Step 11
Dashboard Monitoring diperbarui.

---

# 6. Agentic AI Tier 0

## Role

Tier 0 Helpdesk Triage Agent.

Bertugas sebagai first-line AI support untuk:
- Membaca tiket.
- Memahami masalah.
- Mengklasifikasikan issue.
- Menentukan severity.
- Mencari solusi dari knowledge base.
- Memberikan respon otomatis.
- Menentukan apakah perlu eskalasi.

---

## Tasks

1. Retrieve ticket details.
2. Analyze issue description.
3. Detect site dan device.
4. Classify issue category.
5. Determine severity.
6. Search SOP dan incident history.
7. Generate recommendation.
8. Calculate confidence score.
9. Decide next action.

---

## Tools

- zammad_get_ticket
- zammad_update_ticket
- knowledge_search
- incident_memory_search
- site_lookup
- device_lookup
- telegram_notify

---

## Cooperation

Tier 0 dapat bekerja sama dengan:
- Knowledge Agent
- Escalation Agent
- Agentic AI Tier 1

Rules:
- Confidence ≥ 85% → Auto response.
- Confidence 60–84% → Request more information.
- Confidence < 60% → Escalate to Tier 1.
- Severity Critical → Direct escalation.

---

## Guardrails

Tier 0 tidak boleh:
- Menjalankan command pada server.
- Mengubah konfigurasi.
- Restart service.
- Menutup tiket tanpa bukti.

Tier 0 wajib:
- Menyertakan confidence score.
- Menyertakan referensi SOP.
- Menjelaskan alasan keputusan.

---

## Memory

### Short-Term Memory
- Ticket context.
- Conversation history.

### Long-Term Memory
- SOP.
- Historical incidents.
- Known resolutions.

### Entity Memory
- Site.
- Device.
- PIC.

---

# 7. Agentic AI Tier 1

## Role

Tier 1 Technical Diagnostic Agent.

Bertugas melakukan diagnosis teknis mendalam pada perangkat POS dan infrastruktur pendukung.

---

## Tasks

1. Receive escalation from Tier 0.
2. Identify target device.
3. Ping host.
4. Check open ports.
5. Collect logs.
6. Check service status.
7. Analyze root cause.
8. Generate corrective recommendations.
9. Update ticket.
10. Send escalation summary.

---

## Tools

- ping_host
- check_port
- ssh_execute_readonly
- get_system_logs
- get_service_status
- get_disk_usage
- get_cpu_memory_usage
- telegram_notify
- zammad_update_ticket
- incident_memory_write

---

## Cooperation

Tier 1 bekerja sama dengan:
- Tier 0
- Monitoring Agent
- Escalation Agent

Rules:
- Mengembalikan root cause dan rekomendasi.
- Jika tidak ditemukan root cause, eskalasi ke PIC manusia.

---

## Guardrails

Tier 1 hanya boleh:
- Menjalankan command read-only.
- Mengumpulkan data diagnostik.

Tier 1 tidak boleh:
- Restart service.
- Menghapus file.
- Mengubah konfigurasi.
- Menjalankan command destruktif.

Semua aktivitas harus dicatat pada audit log.

---

## Memory

### Diagnostic Memory
- Previous diagnostics.
- Root cause patterns.

### Infrastructure Memory
- Site inventory.
- Device inventory.
- Credentials reference.

### Resolution Memory
- Successful solutions.

---

# 8. Knowledge Agent

## Role
Mengambil informasi dari:
- SOP.
- Technical documentation.
- FAQ.
- Historical incidents.

---

# 9. Escalation Agent

## Role
Menentukan PIC dan membuat notifikasi terstruktur.

---

# 10. Monitoring Agent

## Role
Mengumpulkan metrik operasional.

Metrics:
- Open tickets.
- SLA breaches.
- Auto resolution rate.
- MTTR.
- Device health.

---

# 11. Data Entities

## Site
- site_id
- site_name
- city
- timezone
- telegram_group_id
- pic_primary
- pic_secondary

## Device
- device_id
- site_id
- device_name
- device_type
- ip_address
- operating_system
- credentials_reference

## Ticket
- ticket_id
- zammad_ticket_id
- category
- severity
- confidence_score
- status

## Incident Memory
- incident_id
- summary
- root_cause
- resolution
- tags
- embedding

---

# 12. Telegram Notification Template

```text
🚨 Incident Alert
Ticket ID: {{ticket_id}}
Site: {{site_name}}
Device: {{device_name}}
Severity: {{severity}}
Issue: {{issue_summary}}
Root Cause: {{root_cause}}
Recommendation: {{recommendation}}
PIC: {{pic_name}}
```

---

# 13. Dashboard Monitoring

Dashboard harus menampilkan:
- Open Tickets
- Tickets by Severity
- SLA Status
- Auto Resolution Rate
- MTTR
- Device Health per Site
- Escalation Statistics
- AI Confidence Trends

---

# 14. Security Requirements

- Role-Based Access Control.
- Secret Management.
- Audit Logging.
- Encrypted Credentials.
- Read-Only Diagnostics by Default.

---

# 15. Design Principles

- Modular Architecture.
- Human-in-the-Loop.
- Explainable AI.
- Secure by Default.
- Production Ready.
- Scalable.

---

# 16. Deliverables

Bangun sistem lengkap dengan:

1. Frontend Dashboard.
2. Backend API.
3. CrewAI Multi-Agent Orchestrator.
4. Zammad Integration.
5. Telegram Integration.
6. Knowledge Base.
7. Incident Memory.
8. Monitoring Dashboard.
9. Audit Logs.
10. Authentication System.

---

# 17. Final Goal

Hasil akhir harus berupa aplikasi enterprise yang mampu:
- Menerima tiket dari Zammad.
- Menjalankan Agentic AI Tier 0 dan Tier 1 berbasis CrewAI.
- Melakukan diagnosis otomatis.
- Mengirim notifikasi Telegram.
- Menyimpan memory insiden.
- Menyajikan dashboard monitoring.
- Mendukung tim Operational IT Helpdesk MKT untuk 18 site bioskop Sam's Studio's.

