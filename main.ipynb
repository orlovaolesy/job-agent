from dotenv import load_dotenv
import os
import json
from sources.arbeitnow import fetch_arbeitnow
from sources.remotive import fetch_remotive
load_dotenv()

from filter_jobs import dedupe_and_sort
from mailer import send_jobs_email

def load_keywords(path="keywords.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def collect_jobs():
    keywords = load_keywords()
    all_jobs = []
    for kw in keywords:
        print("Search by:", kw)
        all_jobs.extend(fetch_arbeitnow(kw))
        all_jobs.extend(fetch_remotive(kw))

    return dedupe_and_sort(all_jobs)

if __name__ == "__main__":
    jobs = collect_jobs()
    print("Total found:", len(jobs))
    send_jobs_email(jobs, os.getenv("TO_EMAIL"))
