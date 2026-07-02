"""
Telegram Notification Tools — CrewAI-compatible tools for Telegram alerts
"""
import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import os
from loguru import logger


class TelegramNotifyInput(BaseModel):
    chat_id: str = Field(..., description="Telegram chat/group ID to send the message to")
    message: str = Field(..., description="Message text to send (supports HTML or Markdown)")
    parse_mode: Optional[str] = Field("HTML", description="Parse mode: HTML or Markdown")


class TelegramNotify(BaseTool):
    name: str = "telegram_notify"
    description: str = (
        "Send a notification message to a Telegram chat or group. "
        "Use this for incident alerts, escalation notices, and status updates. "
        "Use HTML formatting for better readability."
    )
    args_schema: type = TelegramNotifyInput

    def _run(self, chat_id: str, message: str, parse_mode: str = "HTML") -> Dict[str, Any]:
        target_id = chat_id
        if not target_id:
            target_id = os.getenv("TELEGRAM_DEFAULT_GROUP_ID")
        
        try:
            url = f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN', '')}/sendMessage"
            payload = {
                "chat_id": target_id,
                "text": message,
                "parse_mode": parse_mode,
            }
            with httpx.Client(timeout=15) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                logger.info(f"[TelegramTool] Sent message to chat {chat_id}")
                return {
                    "success": True,
                    "message_id": data.get("result", {}).get("message_id"),
                    "chat_id": chat_id,
                }
        except Exception as e:
            logger.error(f"[TelegramTool] Error sending message to {chat_id}: {e}")
            return {"success": False, "error": str(e)}


def build_incident_alert(
    ticket_id: str,
    site_name: str,
    device_name: str,
    severity: str,
    issue_summary: str,
    root_cause: str,
    recommendation: str,
    pic_name: str,
    confidence_score: float = 0.0,
) -> str:
    """Build structured Telegram incident alert message (HTML format)."""

    severity_emoji = {
        "CRITICAL": "🔴",
        "HIGH": "🟠",
        "MEDIUM": "🟡",
        "LOW": "🟢",
    }.get(severity.upper(), "⚪")

    return f"""🚨 <b>Incident Alert — MKT Helpdesk</b>

{severity_emoji} <b>Severity:</b> {severity}
🎫 <b>Ticket ID:</b> <code>{ticket_id}</code>
📍 <b>Site:</b> {site_name}
🖥️ <b>Device:</b> {device_name}

📋 <b>Issue:</b>
{issue_summary}

🔍 <b>Root Cause:</b>
{root_cause or "Sedang dianalisis..."}

✅ <b>Recommendation:</b>
{recommendation}

🤖 <b>AI Confidence:</b> {confidence_score:.0f}%
👤 <b>PIC:</b> {pic_name}

<i>Powered by MKT Agentic AI System</i>"""


class TelegramTools:
    @staticmethod
    def get_all() -> list:
        return [TelegramNotify()]
