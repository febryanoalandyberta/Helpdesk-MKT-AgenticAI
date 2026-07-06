from fastapi import FastAPI
import uvicorn
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import json

load_dotenv()

# We need to import the crew
from src.mkt_helpdesk_ai.crew import MktHelpdeskCrew

app = FastAPI(title="MKT Helpdesk CrewAI API")

class TicketPayload(BaseModel):
    ticket_id: str
    title: str
    description: str
    reporter_name: str
    site_name: str
    severity: str

@app.post("/api/analyze")
def analyze_ticket(payload: TicketPayload):
    inputs = {
        "ticket_id": payload.ticket_id,
        "title": payload.title,
        "description": payload.description,
        "reporter_name": payload.reporter_name,
        "site_name": payload.site_name,
        "severity": payload.severity,
        # Default placeholder values for the other required inputs for now
        "category": "GENERAL",
        "symptom": payload.description[:50],
        "device_type": "UNKNOWN",
        "device_name": payload.site_name,
        "ip_address": "0.0.0.0",
        "issue_description": payload.description,
        "issue_summary": payload.title,
        "root_cause": "Pending",
        "recommendation": "Pending",
        "pic_name": payload.reporter_name,
        "telegram_group_id": os.getenv("TELEGRAM_DEFAULT_GROUP_ID", ""),
        "device_statuses": "UNKNOWN",
        "resolved_ticket_id": payload.ticket_id,
    }
    
    try:
        crew_instance = MktHelpdeskCrew().crew()
        result = crew_instance.kickoff(inputs=inputs)
        
        # Result might be a string or object.
        output = str(result)
        
        # We need to extract the final output. If the agent returns JSON, we return it.
        # Otherwise we'll wrap it.
        return {"status": "success", "result": output}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
