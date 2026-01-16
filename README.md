# 🏭 AI Resume Factory

**The "Set It and Forget It" Job Hunt Automation System.**

This application automates the entire job application lifecycle. It scrapes job boards (LinkedIn, Indeed, etc.) for roles matching your criteria, uses GPT-4o to tailor your resume specifically for each job description, generates a perfectly formatted PDF, and notifies you via Discord.

## ✨ Features

* **🕵️ Automated Scraping:** Hunts for jobs on LinkedIn, Indeed, Glassdoor, and ZipRecruiter using `JobSpy`.
* **🧠 AI Tailoring:** Uses OpenAI (GPT-4o) to rewrite your resume bullet points for every single job application, ensuring high ATS scores.
* **🎨 Dynamic PDF Generation:** Converts JSON data into professional HTML/CSS resumes and renders them as PDFs using `Playwright`.
* **⚡ Daily Automation:** Built-in Task Scheduler integration to run "headless" in the background every morning.
* **👤 Multi-Profile Support:** Manage separate identities (e.g., "Software Engineer" vs. "Game Developer") with unique settings.
* **🔔 Discord Notifications:** Get a summary of all generated resumes sent directly to your phone.

## 🚀 Quick Start (Windows)

1.  **Download & Unzip** the project folder.
2.  Double-click **`start_app.bat`**.
    * *Note: The first run will take a few minutes to install Python dependencies and the browser engine.*
3.  The **Dashboard** will open automatically in your browser.

## ⚙️ Configuration

1.  **Master Resume:** Go to the "📝 Master Resume" tab. Upload your current PDF resume to auto-convert it into the Master JSON format.
2.  **API Keys:** Open the Sidebar > **API Keys**. Enter your OpenAI API Key.
    * *(Optional)* Add a Discord Webhook URL for notifications.
3.  **Job Settings:** Set your target Role (e.g., "Python Developer") and Location.

## 🤖 Automating Your Hunt

You don't need to keep the app open!
1.  Go to the **"⚡ Automation"** tab.
2.  Click **"Generate Runner Script"** to create a custom batch file.
3.  Click **"Schedule Task"** to register it with Windows Task Scheduler.
4.  Your computer will now wake up automatically to hunt for jobs.

## 📂 Project Structure

* `profiles/` - Stores your settings for different job personas.
* `output/` - Contains your generated resumes, organized by date.
* `scraped_jobs/` - CSV logs of all jobs found.
* `agents/` - The AI logic for Searching, Tailoring, and Proofreading.

## 🛠️ Tech Stack

* **UI:** Streamlit
* **AI:** OpenAI GPT-4o / GPT-4o-mini
* **Scraping:** Python-JobSpy
* **Rendering:** Jinja2 + Playwright

---
*Created by [Kingslayerrq]*