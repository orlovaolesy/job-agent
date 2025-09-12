import requests
from config import REED_API_KEY

def fetch_reed(keyword, location="UK", per_page=25):
    url = "https://www.reed.co.uk/api/1.0/jobs"
    params = {"keywords": keyword, "location": location, "pageSize": per_page}
    headers = {"x-api-key": REED_API_KEY}
    resp = requests.get(url, params=params, headers=headers)
    data = resp.json().get("results", [])
    return [
        {
            "title": j["jobTitle"],
            "company": j.get("employerName"),
            "description": j.get("description"),
            "link": j.get("jobUrl"),
            "source": "Reed"
        }
        for j in data if keyword.lower() in (j.get("description") or "").lower()
    ]
