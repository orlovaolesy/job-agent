# Job Agent: Automatic Job Collector

🔍 A Python agent that collects job postings from popular websites based on keywords, removes duplicates, and sends a clean digest to your email 📬

---

## ✨ Features
- Multiple job sources supported (Reed, Remotive, Arbeitnow, etc.)
- Keyword search only in job descriptions
- Duplicate removal by title + company + link
- Weekly digest automatically sent by email
- Easy configuration with `.env` and API keys
- CSV export of results for history tracking

---

## 🚀 Quickstart

1. **Clone & enter**
    ```bash
   git clone https://github.com/<your-user>/job-agent.git
   cd job-agent
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
 

3. **Configure environment**
   Copy .env.example → .env
   Add your credentials (see below)

4. **Run the agent**
   ```bash
   python main.py

✅ Results will be saved and also sent to your email.

## ⚙️ Configuration
```bash
.env
env

Gmail SMTP
GMAIL_USER=your@gmail.com
GMAIL_APP_PASSWORD=your_app_password

API Keys
REED_API_KEY=your_reed_key

Recipient
TO_EMAIL=receiver@gmail.com

---

### Notes
mail requires an App Password (enable 2FA → create app password).
Reed API key can be requested via their developer portal.
For other boards (e.g. Remotive, Arbeitnow), no API key is needed.

