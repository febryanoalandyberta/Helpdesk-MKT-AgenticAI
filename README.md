# Helpdesk MKT Agentic AI Automation

> Sistem Helpdesk Otomatis berbasis AI untuk PT Megakreasi Tech (MKT)  
> Mengelola 18 site bioskop Sam's Studio's · 72 POS Devices

---

## 🏗️ Arsitektur

```
Zammad Ticketing → CrewAI Multi-Agent → PostgreSQL / ChromaDB
                        ├── Tier 0 Agent (Triage & SOP Search)
                        ├── Tier 1 Agent (Technical Diagnostic)
                        ├── Knowledge Agent
                        ├── Escalation Agent → Telegram Bot
                        └── Monitoring Agent
                                ↓
                    Dashboard Monitoring (Web UI)
```

---

## 🚀 Quick Start

### 1. Setup Environment

```bash
cd backend
copy .env.example .env
# Edit .env dan isi: OPENAI_API_KEY, ZAMMAD_TOKEN, TELEGRAM_BOT_TOKEN
```

### 2. Jalankan dengan Docker (Recommended)

```bash
docker-compose up -d
```

Akses:
- **Dashboard**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **ChromaDB**: localhost:8001

### 3. Jalankan Manual (tanpa Docker)

```bash
# Start PostgreSQL & Redis terlebih dahulu

cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

---

## 📁 Struktur Folder

```
Helpdesk MKT Agentic AI Automation/
├── backend/
│   ├── main.py               # FastAPI entry point
│   ├── config.py             # Settings & env vars
│   ├── database.py           # SQLAlchemy async engine
│   ├── models/               # Database models
│   │   ├── site.py           # 18 cinema sites
│   │   ├── device.py         # 72 POS devices
│   │   ├── ticket.py         # Helpdesk tickets
│   │   ├── incident.py       # AI incident memory
│   │   ├── user.py           # RBAC users
│   │   └── audit_log.py      # Audit trail
│   ├── agents/               # CrewAI Agents
│   │   ├── tier0_agent.py    # Triage AI (Confidence scoring)
│   │   ├── tier1_agent.py    # Technical Diagnostic AI
│   │   ├── knowledge_agent.py
│   │   ├── escalation_agent.py
│   │   └── monitoring_agent.py
│   ├── tools/                # CrewAI Tools
│   │   ├── zammad_tools.py   # Zammad API
│   │   ├── telegram_tools.py # Telegram Bot
│   │   ├── diagnostic_tools.py # SSH, Ping, Port Check
│   │   └── knowledge_tools.py  # ChromaDB Vector Search
│   ├── crew/
│   │   └── orchestrator.py   # Multi-agent workflow engine
│   ├── api/                  # FastAPI Routers
│   │   ├── tickets.py
│   │   ├── sites.py
│   │   ├── devices.py
│   │   ├── dashboard.py
│   │   ├── incidents.py
│   │   └── auth.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── index.html            # Dashboard SPA
│   ├── css/style.css         # Premium dark theme
│   └── js/app.js             # Dashboard logic
├── docker-compose.yml
└── README.md
```

---

## 🤖 Workflow AI

| Confidence Score | Action |
|---|---|
| ≥ 85% | Auto-resolve (Tier 0) |
| 60–84% | Request more info |
| < 60% | Escalate to Tier 1 |
| Severity CRITICAL | Direct escalation to Tier 1 |

---

## 🔐 Security

- JWT Authentication (Role-Based: ADMIN, HELPDESK_L1, HELPDESK_L2, MANAGER, VIEWER)
- Read-Only SSH diagnostics — no destructive commands
- Encrypted credential references
- Full audit logging semua aksi agent

---

## 📊 Dashboard Features

- **KPI Cards**: Open tickets, SLA breached, Auto-resolution rate, MTTR, Device availability
- **AI Confidence Trend**: 7-day chart
- **Site Health Grid**: 18 sites real-time health
- **Ticket Management**: Filter by severity/status, AI trigger
- **Device Monitoring**: Ping check langsung dari UI
- **Incident Memory**: Long-term AI learning database
- **Audit Log**: Full activity trail

---

## 📋 API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/login` | Login JWT |
| GET | `/api/tickets/` | List tiket |
| POST | `/api/tickets/` | Buat tiket + trigger AI |
| POST | `/api/tickets/{id}/process` | Trigger AI manual |
| GET | `/api/sites/` | List 18 sites |
| GET | `/api/devices/` | List 72 devices |
| POST | `/api/devices/{id}/ping` | Ping device |
| GET | `/api/dashboard/overview` | KPI metrics |
| GET | `/api/dashboard/site-health` | Per-site health |
| GET | `/api/dashboard/confidence-trend` | AI trend 7 hari |

---

## ⚙️ Environment Variables Utama

```env
OPENAI_API_KEY=sk-...          # Wajib untuk CrewAI
ZAMMAD_URL=https://...         # URL Zammad instance
ZAMMAD_TOKEN=...               # API Token Zammad
TELEGRAM_BOT_TOKEN=...         # Token Telegram Bot
DATABASE_URL=postgresql+asyncpg://...
```

---

*Built by Anti Gravity · PT Megakreasi Tech (MKT) · Sam's Studio's Cinema Network*
