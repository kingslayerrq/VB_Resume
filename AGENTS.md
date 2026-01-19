# 🤖 Agent Architecture & Service Layer

**Context for AI Coding Assistants:**
This project follows a **Service-Oriented Architecture** where the UI (`app.py` or `nicegui_app.py`) delegates all business logic to stateless functions located in the `services/` directory.

## 📂 Directory Map
* **`services/`**: Contains all business logic (Scraping, AI, PDF generation, Cloud ops).
* **`utils/`**: Shared helpers (File I/O, String cleaning).
* **`config_manager.py`**: Handles loading/saving/sanitizing user settings.

---

## 1. Job Discovery Service
**Files:** `services/scraper_agent.py`, `services/gmail_job_agent.py`
**Libraries:** `JobSpy`, `google-api-python-client`

### A. Web Scraper (`scraper_agent.py`)
* **Function:** `scrape_jobs(scrape_config: dict) -> list[dict]`
* **Responsibility:** Interacts with `JobSpy` to fetch jobs from LinkedIn, Indeed, Glassdoor, etc.
* **Key Logic:**
    * Applies filters: `hours_old`, `is_remote`, `distance`.
    * **Blacklist Filter:** Must remove jobs containing keywords defined in `config['blacklist']`.
* **Output Schema (Job Object):**
    ```python
    {
        "title": str,
        "company": str,
        "description": str, # Full HTML/Markdown description
        "url": str,         # Direct apply link
        "Source": "Web"     # Metadata tag
    }
    ```

### B. Gmail Scraper (`gmail_job_agent.py`)
* **Function:** `fetch_job_urls_from_gmail(creds, limit=10) -> list[dict]`
* **Responsibility:** Scans user's Gmail for "Job Alert" emails, extracts tracking links, and resolves them to final URLs.
* **Dependencies:** Requires `credentials.json` (Google OAuth).
* **Output:** Same `Job Object` schema as above, but with `"Source": "Email"`.

---

## 2. AI Tailoring Service
**Files:** `agents/tailor_agent.py`, `services/llm_client.py`, `services/model_registry.py`, `services/model_providers.json`
**Libraries:** `openai`, `requests`

### Core Function: `tailor_resume(master_resume: dict, job_description: str, llm_settings: dict | None) -> dict`
* **Input:**
    * `master_resume`: The raw JSON data of the user's full history.
    * `job_description`: The raw text of the target job listing.
    * `llm_settings`: Provider settings (`provider`, `model`, optional `api_key`).
* **Responsibility:**
    * Uses the selected model provider (OpenAI or local Ollama) to rewrite bullet points.
    * **Constraint:** Must maintain the strict JSON schema of the master resume.
    * **Optimization:** Injects keywords from the JD into the "Skills" and "Summary" sections.
* **Output:** A new JSON dictionary (structure matches `master_resume`) containing *only* the relevant experience for this specific job.

**Related LLM Consumers:** `agents/filter_agent.py`, `agents/proofread_agent.py`, `agents/resume_parser_agent.py` also use `services/llm_client.py`.
**Provider Registry:** `services/model_providers.json` is the single source of truth for provider options, models, and model availability checks.

---

## 3. Rendering Service (PDF)
**File:** `services/pdf_agent.py`
**Libraries:** `jinja2`, `playwright`

### Core Function: `generate_pdf(resume_json: dict, output_path: str) -> str`
* **Input:** The tailored JSON from the AI Agent.
* **Responsibility:**
    1.  **Hydration:** Injects JSON data into an HTML template (`assets/template.html`) using Jinja2.
    2.  **Rendering:** Launches a headless Chromium browser via Playwright.
    3.  **Printing:** Saves the rendered page as a PDF to `output_path`.
* **Return:** Absolute path to the generated PDF.

---

## 4. Cloud Service (Google Drive)
**File:** `services/drive_agent.py`
**Libraries:** `google-api-python-client`, `google-auth`

### Core Function: `upload_resume_to_drive(file_path: str) -> str | None`
* **Logic:**
    * Checks for existence of a folder named `"Resumes"`. Creates it if missing.
    * Uploads the file.
    * **Permissions:** Sets file to `reader` for `anyone` (or specific user) to generate a viewable link.
* **Return:** The `webViewLink` (URL) to the file on Google Drive, or `None` if upload failed/disabled.

---

## 5. Notification Service
**File:** `services/notification_agent.py`
**Libraries:** `requests`

### Core Function: `send_discord_alert(summary: dict, webhook_url: str)`
* **Input:** `summary` dict containing counts (Found, Generated, Failed) and a list of success details.
* **Responsibility:** Formats a rich embed message for Discord.
* **Payload:** Includes links to the **Drive PDF** and the **Apply URL** for every generated resume.

---

## 6. Config & State Management
**File:** `config_manager.py`

### Key Functions:
* `load_config(path) -> dict`: Reads raw JSON from disk. Handles missing file creation.
* `get_effective_config(path) -> dict`: **CRITICAL.** Reads config from disk *AND* sanitizes it based on environment.
    * *Rule:* If `credentials.json` is missing, force `enable_google`, `enable_drive`, and `use_email` to `False`.
* `save_config(data, path)`: Writes to disk.

**Model Settings (Config Keys):**
* `model_provider`: `"ollama"` (default) or `"openai"`.
* `model_name`: Model string for the selected provider (e.g., `llama3.1:8b`, `gpt-4o`).
* `model_api_keys`: Map of provider → API key (e.g., `{"openai": "...", "ollama": ""}`).
* `agent_models`: Optional per-agent overrides `{tailor, proofread, filter, parser}` with `provider`/`model`.

**Provider Availability:**
* Model checks use `services/model_providers.json` `model_check` definitions (e.g., Ollama `/api/show`, OpenAI `/v1/models`).

---

## 🔄 Workflow Orchestration (The Runner)
**File:** `main.py` (or `services/workflow.py` in refactor)

The `run_daily_workflow` function ties these agents together sequentially:
1.  **Load:** Get Config & Master Resume.
2.  **Hunt:** Call `scraper_agent` + `gmail_job_agent` (if enabled) → `job_batch`.
3.  **Loop:** For each job in `job_batch`:
    * Call `ai_agent.tailor_resume` → `tailored_json`.
    * Call `pdf_agent.generate_pdf` → `local_pdf_path`.
    * Call `drive_agent.upload_resume_to_drive` (if enabled) → `drive_link`.
    * Update `history.json`.
4.  **Notify:** Call `notification_agent` with results.

---

## 7. 🛠️ Maintenance Protocol (The Loop)
**Rule for AI Agents & Developers:**
Any time you modify the codebase, add a new feature, or change a function signature, you **MUST** update this `agents.md` file to reflect those changes immediately.

**Checklist for Updates:**
1.  **New Service?** Add a new section (e.g., "7. LinkedIn Easy Apply Agent").
2.  **Schema Change?** Update the JSON input/output examples above.
3.  **New Library?** Update the "Libraries" line in the relevant section.
4.  **Logic Change?** If an agent's responsibility changes (e.g., Scraper now hunts on WeWorkRemotely), update the "Key Logic" bullet points.

**Goal:** This file must always remain the "Single Source of Truth" for the system architecture.
