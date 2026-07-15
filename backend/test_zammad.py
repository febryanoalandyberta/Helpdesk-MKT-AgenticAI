import httpx
from config import settings
r = httpx.get("http://localhost:8080/api/v1/tickets/search", headers={"Authorization": f"Token token={settings.ZAMMAD_TOKEN}"}, params={"query": "created_at:>2020-01-01", "limit": 2, "sort_by": "created_at", "order_by": "desc", "expand": "true"})
print("Status:", r.status_code)
data = r.json()
print("Type:", type(data))
if isinstance(data, list) and len(data) > 0:
    print("First item type:", type(data[0]))
elif isinstance(data, dict):
    print("Keys:", data.keys())
