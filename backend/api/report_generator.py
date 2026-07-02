import os
import logging
from datetime import datetime, timedelta
from fpdf import FPDF
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.ticket import Ticket, TicketStatus

logger = logging.getLogger(__name__)

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'MKT Helpdesk AI - Laporan Mingguan', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

async def generate_weekly_pdf_report(db: AsyncSession, filepath: str):
    """Membuat laporan PDF kinerja helpdesk selama 7 hari terakhir."""
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    
    q = await db.execute(select(Ticket).where(Ticket.created_at >= one_week_ago))
    tickets = q.scalars().all()
    
    total_tickets = len(tickets)
    closed_tickets = sum(1 for t in tickets if t.status == TicketStatus.CLOSED or t.status == TicketStatus.RESOLVED)
    escalated_tickets = sum(1 for t in tickets if getattr(t, 'escalated', False))
    auto_resolved = sum(1 for t in tickets if t.resolved_by == "MKT Agentic AI")
    
    # Calculate MTTR
    resolved_times = [
        (t.resolved_at - t.created_at).total_seconds() / 60
        for t in tickets if t.resolved_at and t.created_at
    ]
    mttr_minutes = sum(resolved_times) / len(resolved_times) if resolved_times else 0
    mttr_str = f"{mttr_minutes:.1f} Menit"
    if mttr_minutes > 60:
        mttr_str = f"{mttr_minutes / 60:.1f} Jam"
        
    ai_success_rate = (auto_resolved / total_tickets * 100) if total_tickets > 0 else 0
    
    pdf = PDFReport()
    pdf.add_page()
    
    # Tanggal
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 10, f"Periode: {one_week_ago.strftime('%d %b %Y')} - {datetime.utcnow().strftime('%d %b %Y')}", 0, 1)
    pdf.ln(5)
    
    # Ringkasan Statistik
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Ringkasan Eksekutif:', 0, 1)
    pdf.set_font('Arial', '', 11)
    
    stats = [
        f"1. Total Tiket Masuk: {total_tickets} tiket",
        f"2. Tiket Berhasil Diselesaikan: {closed_tickets} tiket",
        f"3. Diselesaikan Otomatis oleh AI: {auto_resolved} tiket ({ai_success_rate:.1f}%)",
        f"4. Tiket Dieskalasi ke Manusia: {escalated_tickets} tiket",
        f"5. Rata-rata Waktu Penyelesaian (MTTR): {mttr_str}"
    ]
    for stat in stats:
        pdf.cell(0, 8, stat, 0, 1)
        
    pdf.ln(10)
    
    # Narasi AI (Template)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Kesimpulan AI:', 0, 1)
    pdf.set_font('Arial', '', 11)
    
    if ai_success_rate > 30:
        narasi = "Kinerja AI minggu ini sangat baik. Sebagian besar masalah berhasil diselesaikan secara otomatis tanpa intervensi manusia, mengurangi beban kerja tim IT secara signifikan."
    elif total_tickets == 0:
        narasi = "Tidak ada tiket yang masuk dalam 7 hari terakhir. Operasional berjalan sangat lancar."
    else:
        narasi = "Minggu ini banyak tiket yang membutuhkan penanganan khusus dari tim teknis. AI mendeteksi beberapa isu kompleks yang harus segera diaudit oleh supervisor."
        
    pdf.multi_cell(0, 8, narasi)
    
    # Simpan
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    pdf.output(filepath)
    return filepath
