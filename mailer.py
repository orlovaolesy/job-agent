import yagmail
import os

def send_jobs_email(jobs, to_email, subject="Job Digest"):
    body = "<h2>Новые вакансии</h2><ul>"
    for j in jobs:
        body += f"<li><strong>{j['title']}</strong> — {j['company']} [{j['source']}]<br>"
        body += f"<a href='{j['link']}' target='_blank'>Открыть</a></li>"
    body += "</ul>" if jobs else "<p>Новых вакансий не найдено.</p>"

    # ⬇️ вот тут самое главное
    yag = yagmail.SMTP(
        user=os.getenv("GMAIL_USER"),
        password=os.getenv("GMAIL_APP_PASSWORD")
    )

    yag.send(to_email, subject, contents=[body])

