import requests
from config import JOOBLE_API_KEY

def fetch_jooble(keyword, location="UK"):
    if not JOOBLE_API_KEY:
        return []
    payload = {"keywords": keyword, "location": location, "apiKey": JOOBLE_API_KEY}
    resp = requests.post("https://jooble.org/api", json=payload)
    jobs = resp.json().get("jobs", [])
    return [
        {
            "title": j.get("title"),
            "company": j.get("company"),
            "description": j.get("snippet") or "",
            "link": j.get("link"),
            "source": "Jooble"
        }
        for j in jobs if keyword.lower() in (j.get("snippet") or "").lower()
    ]
