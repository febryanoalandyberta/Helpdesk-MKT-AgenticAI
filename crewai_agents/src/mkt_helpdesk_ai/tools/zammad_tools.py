"""
Zammad Integration Tools — CrewAI-compatible tools for ticket operations
"""
import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import os
from loguru import logger


class ZammadGetTicketInput(BaseModel):
    ticket_id: str = Field(..., description="Zammad ticket ID to retrieve")


class ZammadUpdateTicketInput(BaseModel):
    ticket_id: str = Field(..., description="Zammad ticket ID to update")
    note: str = Field(..., description="Note/comment to add to the ticket")
    state: Optional[str] = Field(None, description="New ticket state: open, closed, pending")
    tags: Optional[list] = Field(None, description="Tags to add to the ticket")


class ZammadGetTicket(BaseTool):
    name: str = "zammad_get_ticket"
    description: str = (
        "Retrieve full ticket details from Zammad by ticket ID. "
        "Returns ticket title, description, reporter info, and metadata."
    )
    args_schema: type = ZammadGetTicketInput

    def _run(self, ticket_id: str) -> Dict[str, Any]:
        try:
            headers = {
                "Authorization": f"Token token={os.getenv('ZAMMAD_TOKEN', '')}",
                "Content-Type": "application/json",
            }
            url = f"{os.getenv('ZAMMAD_URL', '')}/api/v1/tickets/{ticket_id}"
            with httpx.Client(timeout=30) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                logger.info(f"[ZammadTool] Retrieved ticket #{ticket_id}")
                return {
                    "success": True,
                    "ticket_id": data.get("id"),
                    "title": data.get("title"),
                    "state": data.get("state"),
                    "priority": data.get("priority"),
                    "group": data.get("group"),
                    "customer": data.get("customer"),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "tags": data.get("tags", []),
                    "raw": data,
                }
        except Exception as e:
            logger.error(f"[ZammadTool] Error getting ticket #{ticket_id}: {e}")
            return {"success": False, "error": str(e)}


class ZammadUpdateTicket(BaseTool):
    name: str = "zammad_update_ticket"
    description: str = (
        "Add a note to a Zammad ticket and optionally update its state. "
        "Use this to record AI analysis results, recommendations, and status changes."
    )
    args_schema: type = ZammadUpdateTicketInput

    def _run(self, ticket_id: str, note: str, state: Optional[str] = None, tags: Optional[list] = None) -> Dict[str, Any]:
        try:
            headers = {
                "Authorization": f"Token token={os.getenv('ZAMMAD_TOKEN', '')}",
                "Content-Type": "application/json",
            }
            # Add article (note)
            article_payload = {
                "ticket_id": ticket_id,
                "body": note,
                "type": "note",
                "internal": True,
            }
            url = f"{os.getenv('ZAMMAD_URL', '')}/api/v1/ticket_articles"
            with httpx.Client(timeout=30) as client:
                resp = client.post(url, json=article_payload, headers=headers)
                resp.raise_for_status()

                # Update state if provided
                if state:
                    ticket_url = f"{os.getenv('ZAMMAD_URL', '')}/api/v1/tickets/{ticket_id}"
                    client.put(ticket_url, json={"state": state}, headers=headers)

                logger.info(f"[ZammadTool] Updated ticket #{ticket_id}")
                return {"success": True, "ticket_id": ticket_id, "note_added": True}
        except Exception as e:
            logger.error(f"[ZammadTool] Error updating ticket #{ticket_id}: {e}")
            return {"success": False, "error": str(e)}


class ZammadTools:
    """Collection of all Zammad tools for CrewAI agents."""

    @staticmethod
    def get_all() -> list:
        return [ZammadGetTicket(), ZammadUpdateTicket()]
