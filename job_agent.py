import os
import re
import time
import html
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from dateutil import parser as dateparser
import yagmail

# =========================
# CONFIG
# =========================
KEYWORDS = ["data analyst", "data entry", "Python", "Excel", "Power BI", "SQL", "junior data analyst", "junior data science", "data science trainee"]
LOCATIONS = ["London", "Remote"]  # Hint for labeling
LOOKBACK_HOURS = 72

TO_EMAIL = os.getenv("TO_EMAIL", "olesiaodyntsova.job@gmail.com")
GMAIL_USER = os.getenv("GMAIL_USER")          # set in GitHub Secrets
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")  # set in GitHub Secrets
DRY_RUN = os.getenv("DRY_RUN", "0") == "1"    # <<< NEW: enable with DRY_RUN="1"

NOW_UTC = datetime.now(timezone.utc)
SINCE_UTC = NOW_UTC - timedelta(hours=LOOKBACK_HOURS)
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Referer": "https://uk.indeed.com/",
}
# =========================
# UTILITIES
# =========================
def norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def contains_keyword(text: str) -> bool:
    t = (text or "").lower()
    return any(k.lower() in t for k in KEYWORDS)

def within_last_24h(dt: datetime) -> bool:
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt >= SINCE_UTC

def safe_get(url, params=None, headers=None, max_retries=3):
    last_err = None
    for i in range(max_retries):
        try:
            time.sleep(0.8 + i * 0.5)  # gentle backoff
            resp = requests.get(url, params=params, headers=headers or UA, timeout=30)
            # some sites 403 on first try then succeed on retry; treat 403 specially
            if resp.status_code == 403:
                last_err = requests.HTTPError(f"403 Forbidden: {resp.url}")
                continue
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            last_err = e
    # give up after retries
    raise last_err
    
def dedupe(jobs):
    seen = set()
    out = []
    for j in jobs:
        key = (j["title"].lower(), j["company"].lower(), j["link"])
        if key not in seen:
            seen.add(key)
            out.append(j)
    return out

def fmt_job(j):
    when = j.get("posted_at_iso", "")
    src = j.get("source", "")
    loc = j.get("location", "")
    return f"{j['title']} — {j['company']} ({loc}) [{src}]\n{j['link']}\nPosted: {when}"

# =========================
# SCRAPERS
# =========================

def scrape_weworkremotely():
    """
    WeWorkRemotely:
    - Use RSS for Data category (reliable timestamps)
    - Plus HTML keyword search to broaden results
    - Match keywords in title OR description/snippet
    """
    jobs = []

    # ---------- 1) RSS: Remote Data category ----------
    try:
        url = "https://weworkremotely.com/categories/remote-data-jobs.rss"
        r = safe_get(url)
        soup = BeautifulSoup(r.text, "xml")
        for item in soup.find_all("item"):
            title = norm_space(item.title.text if item.title else "")
            link = norm_space(item.link.text if item.link else "")
            desc = html.unescape(item.description.text if item.description else "")
            company = ""
            m = re.split(r"\s+–\s+|\s+-\s+", title)
            if len(m) >= 2:
                company, title = m[0], " - ".join(m[1:])
            pub = item.pubDate.text if item.pubDate else ""
            try:
                dt = dateparser.parse(pub)
            except Exception:
                dt = NOW_UTC - timedelta(days=999)

            if contains_keyword(title) or contains_keyword(desc):
                if within_last_24h(dt):
                    jobs.append({
                        "title": title,
                        "company": company or "N/A",
                        "location": "Remote",
                        "link": link,
                        "posted_at_iso": dt.isoformat(),
                        "source": "WeWorkRemotely"
                    })
    except Exception as e:
        print(f"[WARN] WWR RSS failed: {e}")

    # ---------- 2) HTML search: broaden coverage ----------
    # Search terms from your KEYWORDS list; adjust pages if you want more depth.
    for term in KEYWORDS:
        for page in range(1, 3):  # first 2 pages
            search_url = (
                "https://weworkremotely.com/remote-jobs/search"
                f"?term={requests.utils.quote(term)}&page={page}"
            )
            try:
                r = safe_get(search_url)
            except Exception as e:
                print(f"[WARN] WWR search failed for term '{term}' page {page}: {e}")
                continue

            soup = BeautifulSoup(r.text, "html.parser")
            # Typical listing links look like: /remote-jobs/<slug>
            for a in soup.select("section.jobs li a[href*='/remote-jobs/']"):
                link = "https://weworkremotely.com" + (a.get("href") or "")
                title_el = a.select_one("span.title")
                company_el = a.select_one("span.company")
                # WWR search pages don't expose timestamps; we'll treat as "now"
                dt = NOW_UTC

                title = norm_space(title_el.get_text() if title_el else "")
                company = norm_space(company_el.get_text() if company_el else "N/A")

                # We don't have a full description here, but title match is often enough.
                # (Optional: follow each link and scrape the job detail page for a real description.)
                if contains_keyword(title):
                    if within_last_24h(dt):
                        jobs.append({
                            "title": title,
                            "company": company,
                            "location": "Remote",
                            "link": link,
                            "posted_at_iso": dt.isoformat(),
                            "source": "WeWorkRemotely"
                        })

    return jobs

def scrape_reed():
    """
    Reed UK:
    - Locations: London, UK-wide, Remote (work from home)
    - Sort: newest first (DisplayDate)
    - Match keywords in title OR description/snippet
    - Final time filter enforced by within_last_24h(dt)
    """
    base = "https://www.reed.co.uk/jobs"
    queries = [
        ("data-analyst-jobs-in-london", "London"),
        ("data-entry-jobs-in-london", "London"),
        ("data-analyst-jobs", "UK"),
        ("data-entry-jobs", "UK"),
        ("data-analyst-jobs?fromHome=True", "Remote (UK)"),
        ("data-entry-jobs?fromHome=True", "Remote (UK)"),
    ]

    def extract_text(el):
        return norm_space(el.get_text(" ", strip=True)) if el else ""

    jobs = []
    for path, loc in queries:
        for page in range(1, 6):  # first 5 pages
            # Build URL (handle existing query string)
            url = (
                f"{base}/{path}&pageno={page}&sortby=DisplayDate"
                if "?" in path
                else f"{base}/{path}?pageno={page}&sortby=DisplayDate"
            )

            try:
                r = safe_get(url)
            except Exception as e:
                print(f"[WARN] Reed fetch failed for {url}: {e}")
                continue

            soup = BeautifulSoup(r.text, "html.parser")
            cards = soup.select("article.job-result-card") or soup.select("article.job-result")

            for c in cards:
                title_el = c.select_one("h2.title a")
                comp_el  = c.select_one(".gtmJobListingPostedBy a, .job-result-heading__posted-by")
                date_el  = c.select_one("div.metadata div.posted-by, .job-metadata__item--time")

                # Try several possible description/snippet containers Reed uses
                desc_el = (
                    c.select_one(".job-description")
                    or c.select_one(".description")
                    or c.select_one(".job-result-description")
                    or c.select_one(".job-card_job-description")
                )

                link = title_el["href"] if title_el and title_el.has_attr("href") else None
                if link and not link.startswith("http"):
                    link = "https://www.reed.co.uk" + link

                title   = extract_text(title_el)
                company = extract_text(comp_el)
                date_tx = extract_text(date_el)
                desc    = extract_text(desc_el)

                # Rough posted time parsing (final 72h filter applied below)
                dt = NOW_UTC - timedelta(days=999)
                low = date_tx.lower()
                if "today" in low or "hour" in low:
                    dt = NOW_UTC
                else:
                    m = re.search(r"(\d+)\s+day", low)
                    if m:
                        dt = NOW_UTC - timedelta(days=int(m.group(1)))

                # <<< Match keywords in title OR description/snippet >>>
                if (title and contains_keyword(title)) or contains_keyword(desc):
                    if within_last_24h(dt):
                        jobs.append({
                            "title": title,
                            "company": company or "N/A",
                            "location": loc,
                            "link": link or "",
                            "posted_at_iso": dt.isoformat(),
                            "source": "Reed"
                        })

    return jobs
    
def scrape_indeed_uk():
    """
    Indeed UK: use 'fromage=3' (last 72h) + sort=date; London + Remote filters.
    Matches keywords in title OR snippet. Handles 403 blocks gracefully.
    """
    jobs = []

    def fetch(query, location=None, remote=False):
        base = "https://uk.indeed.com/jobs"
        params = {
            "q": query,
            "sort": "date",
            "fromage": "3",   # last 3 days
            "limit": "50",
        }
        if location:
            params["l"] = location
        if remote:
            params["remotejob"] = "1"

        try:
            r = safe_get(base, params=params)
        except Exception as e:
            print(f"[WARN] Indeed blocked or failed for query '{query}' (loc={location}, remote={remote}): {e}")
            return

        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select("div.job_seen_beacon") or soup.select("a.tapItem")

        for card in cards:
            title_el   = card.select_one("h2.jobTitle span") or card.select_one("h2.jobTitle")
            comp_el    = card.select_one("span.companyName")
            loc_el     = card.select_one("div.companyLocation")
            snippet_el = card.select_one("div.job-snippet")
            link_el    = card.select_one("a.jcs-JobTitle") or (card if card.name == "a" else None)

            title   = norm_space(title_el.get_text() if title_el else "")
            company = norm_space(comp_el.get_text() if comp_el else "")
            loc_txt = norm_space(loc_el.get_text() if loc_el else (location or ("Remote" if remote else "")))
            snippet = norm_space(snippet_el.get_text() if snippet_el else "")

            link = ""
            if link_el and link_el.has_attr("href"):
                href = link_el["href"]
                link = "https://uk.indeed.com" + href if href.startswith("/") else href

            # Match keywords in title OR snippet
            if contains_keyword(title) or contains_keyword(snippet):
                jobs.append({
                    "title": title,
                    "company": company or "N/A",
                    "location": loc_txt,
                    "link": link,
                    "posted_at_iso": NOW_UTC.isoformat(),  # we rely on fromage=3 for recency
                    "source": "Indeed"
                })

    # Run the 4 searches
    fetch("data analyst", location="London")
    fetch("data entry",  location="London")
    fetch("data analyst", remote=True)
    fetch("data entry",  remote=True)

    return jobs

# Stubs (optional future upgrade with Playwright/login or APIs)
def scrape_hays_stub():
    return []

def scrape_linkedin_stub():
    return []

# =========================
# MAIN
# =========================
def collect_all_jobs():
    all_jobs = []

    for name, fn in [
        ("WeWorkRemotely", scrape_weworkremotely),
        ("Reed", scrape_reed),
        ("Indeed", scrape_indeed_uk),
        ("Hays", scrape_hays_stub),
        ("LinkedIn", scrape_linkedin_stub),
    ]:
        try:
            batch = fn() or []
            print(f"[INFO] {name}: {len(batch)} jobs")
            all_jobs += batch
        except Exception as e:
            print(f"[WARN] {name} scraper failed: {e}")

    out = []
    for j in all_jobs:
        if j.get("posted_at_iso"):
            try:
                dt = dateparser.parse(j["posted_at_iso"])
            except Exception:
                dt = NOW_UTC - timedelta(days=999)
            if within_last_24h(dt):
                out.append(j)
        else:
            out.append(j)

    out = dedupe(out)
    out.sort(key=lambda x: x.get("posted_at_iso", ""), reverse=True)
    return out

def send_email(jobs):
    # --- DRY RUN: skip email sending ---
    if DRY_RUN:
        print("[INFO] DRY_RUN=1 → skipping email send")
        return

    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        raise RuntimeError("Missing GMAIL_USER or GMAIL_APP_PASSWORD env vars.")
    yag = yagmail.SMTP(GMAIL_USER, GMAIL_APP_PASSWORD)
    subject = "💼 Weekly Job Digest — Data Analyst / Data Entry (last 24h)"
    if jobs:
        lines = [fmt_job(j) for j in jobs]
        body = "Here are the freshest roles from the last 72 hours:\n\n" + "\n\n".join(lines)
    else:
        body = "No roles matched in the last 72 hours this week."
    yag.send(TO_EMAIL, subject, body)

def main():
    jobs = collect_all_jobs()
    print(f"Found {len(jobs)} jobs")
    summary = {
        "generated_at": NOW_UTC.isoformat(),
        "count": len(jobs),
        "jobs": jobs
    }
    with open("latest_jobs.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    send_email(jobs)
    print(f"JSON saved. Email {'skipped (DRY_RUN)' if DRY_RUN else 'sent'} to {TO_EMAIL}")

if __name__ == "__main__":
    main()

