"""
main.py — Entry point CrewAI MKT Helpdesk AI
Jalankan dengan: crewai run (dari folder crewai_agents/)
Atau langsung: python src/mkt_helpdesk_ai/main.py
"""
from dotenv import load_dotenv
load_dotenv()  # Load .env dari folder crewai_agents/

from mkt_helpdesk_ai.crew import MktHelpdeskCrew


def run():
    """
    Entry point utama — jalankan crew dengan contoh tiket.
    Di production, inputs akan datang dari Zammad webhook.
    """
    # Contoh tiket untuk demo/test
    inputs = {
        "ticket_id": "1",
        "title": "POS Ticketing 01 tidak bisa cetak tiket",
        "description": (
            "POS di Sam Studio Bandung tiba-tiba tidak bisa mencetak tiket. "
            "Sudah coba restart printer tapi masih error. "
            "Antrian penonton menumpuk. Printer model Epson TM-T82X."
        ),
        "reporter_name": "Budi Santoso",
        "site_name": "Sam's Studio's Bandung",
        "severity": "HIGH",
        # Untuk knowledge_search_task
        "category": "PRINTING",
        "symptom": "Printer tidak bisa cetak tiket setelah restart",
        "device_type": "POS_TICKETING",
        # Untuk technical_diagnosis_task
        "device_name": "POS Ticketing 01 - Bandung",
        "ip_address": "192.168.6.10",
        "issue_description": "Printer tidak merespons, status offline di sistem",
        # Untuk escalation_notification_task
        "issue_summary": "POS Ticketing tidak bisa cetak tiket",
        "root_cause": "Belum diidentifikasi — perlu diagnosis Tier 1",
        "recommendation": "Cek koneksi USB printer, restart spooler service",
        "pic_name": "Budi Santoso",
        "telegram_group_id": "-100123456789",
        # Untuk monitoring_update_task
        "device_statuses": "POS Ticketing 01: OFFLINE, POS Ticketing 02: ONLINE",
        "resolved_ticket_id": "TKT-10001",
    }

    print("=" * 60)
    print("[AI] MKT Helpdesk AI -- CrewAI Multi-Agent System")
    print("     PT Megakreasi Tech | Sam's Studio's Cinema Network")
    print("     18 Sites | 72 POS Devices")
    print("=" * 60)
    print(f"\n[TIKET] Memproses Tiket: {inputs['ticket_id']}")
    print(f"   Site   : {inputs['site_name']}")
    print(f"   Issue  : {inputs['title']}")
    print(f"   Pelapor: {inputs['reporter_name']}")
    print(f"   Severity: {inputs['severity']}")
    print("\n" + "=" * 60)

    result = MktHelpdeskCrew().crew().kickoff(inputs=inputs)

    print("\n" + "=" * 60)
    print("[DONE] HASIL ANALISIS CREW AI:")
    print("=" * 60)
    print(result)
    return result


def kickoff():
    """Called by crewai run command."""
    run()


if __name__ == "__main__":
    run()
