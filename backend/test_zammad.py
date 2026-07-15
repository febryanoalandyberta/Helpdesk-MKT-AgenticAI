import httpx
from config import settings
r = httpx.get("http://localhost:8080/api/v1/tickets/search", headers={"Authorization": f"Token token={settings.ZAMMAD_TOKEN}"}, params={"query": "created_at:>2024-01-01", "limit": 20, "sort_by": "created_at", "order_by": "desc"})
if r.status_code == 200:
    data = r.json()
    if isinstance(data, list):
        print("Tickets (list):", [t if isinstance(t, int) else t.get("id") for t in data])
    elif "assets" in data and "Ticket" in data["assets"]:
        print("Tickets (assets):", list(data["assets"]["Ticket"].keys()))
else:
    print("Error:", r.status_code, r.text)
