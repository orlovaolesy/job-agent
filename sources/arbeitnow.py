import requests

def fetch_arbeitnow(keyword):
    try:
        resp = requests.get("https://arbeitnow.com/api/job-board-api", timeout=15)
        resp.raise_for_status()  
        data = resp.json().get("data", [])
    except Exception as e:
        print(f"[Arbeitnow] Error: {e}")
        return []

    return [
        {
            "title": j.get("title"),
            "company": j.get("company_name"),
            "description": j.get("description"),
            "link": j.get("url"),
            "source": "Arbeitnow"
        }
        for j in data if keyword.lower() in (j.get("description") or "").lower()
    ]
