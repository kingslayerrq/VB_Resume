# 🏭 AI Resume Factory

[![CI Tests](https://github.com/kingslayerrq/VB_Resume/actions/workflows/tests.yml/badge.svg)](https://github.com/kingslayerrq/VB_Resume/actions)
[![Code Quality](https://github.com/kingslayerrq/VB_Resume/actions/workflows/lint.yml/badge.svg)](https://github.com/kingslayerrq/VB_Resume/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**The "Set It and Forget It" Job Hunt Automation System.**

This application automates the entire job application lifecycle. It works in parallel: scraping job boards (LinkedIn, Indeed, etc.) AND scanning your Gmail for job alerts. It uses **GPT-4o** to tailor your resume specifically for each job description, generates a perfectly formatted PDF, uploads it to **Google Drive**, and notifies you via Discord.

## ✨ Features

### 🧠 Core Intelligence
* **🕵️ Dual-Engine Scraping:** Hunts for jobs on Web Boards (LinkedIn, Indeed, Glassdoor, ZipRecruiter) AND scans your **Gmail** for "Job Alert" emails simultaneously.
* **🤖 AI Tailoring:** Uses OpenAI (GPT-4o) to rewrite your resume bullet points for every single application, optimizing for ATS keywords and relevance.
* **🔍 Deep Enrichment:** Automatically visits job links found in emails to scrape the *real* job title and company name, fixing generic "LinkedIn Import" errors.

### ⚙️ Automation & Cloud
* **☁️ Cloud Sync:** Automatically uploads every generated resume to a specific folder in your **Google Drive** for easy access on mobile.
* **⚡ Daily Automation:** Built-in Task Scheduler integration to run "headless" in the background every morning.
* **🔔 Discord Notifications:** Get a summary of all generated resumes (with Drive links) sent directly to your phone.

### 📊 Dashboard
* **🎨 Dynamic PDF Generation:** Converts JSON data into professional HTML/CSS resumes using `Playwright`.
* **📈 Interactive Analytics:** Filter your history by Date, Source (Email vs Web), Company, or Status.
* **👤 Multi-Profile Support:** Manage separate identities (e.g., "Software Engineer" vs. "Game Developer") with unique settings.

---

## 🚀 Quick Start (Windows)

### 1. Prerequisites (Crucial!)
To use the Gmail and Drive features, you must bring your own Google API Key.
1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Create a project and enable **Gmail API** and **Google Drive API**.
3.  Go to **Credentials** → **Create Credentials** → **OAuth Client ID** → **Desktop App**.
4.  Download the JSON file, rename it to `credentials.json`, and place it in this folder.

### 2. Installation
1.  **Download & Unzip** the project folder.
2.  Double-click **`start_app.bat`**.
    * *Note: The first run will take a few minutes to install Python dependencies and the browser engine.*
    * *It will ask you to log in to Google once to generate a `token.json` file.*
3.  The **Dashboard** will open automatically in your browser.

---

## ⚙️ Configuration

1.  **Master Resume:** Go to the "📝 Master Resume" tab. Upload your current PDF resume to auto-convert it into the Master JSON format.
2.  **API Keys:** Open the Sidebar > **API Keys**. Enter your **OpenAI API Key**.
    * *(Optional)* Add a Discord Webhook URL for notifications.
3.  **Job Settings:** Set your target Role (e.g., "Python Developer") and Location.
4.  **Email Integration:** In "Settings", toggle **Gmail Scraper** on to process your daily job alert emails.

## 🤖 Automating Your Hunt

You don't need to keep the app open!
1.  Go to the **"⚡ Automation"** tab.
2.  Click **"Generate Runner Script"** to create a custom batch file for your specific profile.
3.  Click **"Schedule Task"** to register it with Windows Task Scheduler.
4.  Your computer will now wake up automatically at your chosen time to hunt for jobs.

## 📂 Project Structure

* `profiles/` - Stores your settings for different job personas.
* `output/` - Contains your generated resumes, organized by date.
* `scraped_jobs/` - CSV logs of all jobs found.
* `agents/` - The logic for Searching, Gmail Parsing, AI Tailoring, and Drive Uploads.
* `tests/` - Unit and Integration tests (run via `pytest`).

## 🛠️ Tech Stack

* **UI:** Streamlit
* **AI:** OpenAI GPT-4o / GPT-4o-mini
* **Scraping:** JobSpy + Playwright + Gmail API
* **Rendering:** Jinja2 + HTML/CSS

---

## 🤝 Connect & Support

Vibreated by **Kingslayerrq** with ❤️. If you found this tool helpful in your job search:

* [![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/C0C81SHMX1)
* ⭐ **[Star this repo on GitHub!](https://github.com/kingslayerrq/VB_Resume)**
* 🐛 **Report Issues:** Found a bug? Open an issue in the Issues tab.
* 💬 **Join the Conversation:**
    * [**Join the Discord Server**](https://discord.com/invite/TcdP9peVsc)
    * [**Follow on GitHub**](https://github.com/kingslayerrq)

*Happy Hunting! 🎯*