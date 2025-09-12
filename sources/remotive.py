import requests

def fetch_remotive(keyword):
    resp = requests.get("https://remotive.com/api/remote-jobs")
    jobs = resp.json().get("jobs", [])
    return [
        {
            "title": j["title"],
            "company": j["company_name"],
            "description": j["description"],
            "link": j["url"],
            "source": "Remotive"
        }
        for j in jobs if keyword.lower() in (j["description"] or "").lower()
    ]

 