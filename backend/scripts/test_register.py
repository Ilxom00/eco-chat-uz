import urllib.request
import json

url = "http://127.0.0.1:8000/internal/bot/bot/register"
headers = {
    "X-Internal-Secret": "eco-internal-secret-2024-prod",
    "Content-Type": "application/json"
}
req = urllib.request.Request(url, data=json.dumps({}).encode(), headers=headers)
try:
    with urllib.request.urlopen(req) as r:
        print("STATUS:", r.status)
        print("BODY:", r.read().decode())
except Exception as e:
    print("ERROR:", e)
    if hasattr(e, "read"):
        print("BODY:", e.read().decode())
