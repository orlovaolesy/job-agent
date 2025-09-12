import yagmail
import os

def send_jobs_email(jobs, to_email, subject="Job Digest"):
    body = "<h2>New jobs</h2><ul>"
    for j in jobs:
        body += f"<li><strong>{j['title']}</strong> — {j['company']} [{j['source']}]<br>"
        body += f"<a href='{j['link']}' target='_blank'>Open</a></li>"
    body += "</ul>" if jobs else "<p>No new vacancies found.</p>"

    # ⬇️
    yag = yagmail.SMTP(
        user=os.getenv("GMAIL_USER"),
        password=os.getenv("GMAIL_APP_PASSWORD")
    )

    yag.send(to_email, subject, contents=[body])

