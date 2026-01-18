import streamlit as st
import asyncio
import subprocess
from datetime import datetime
import os
import sys
import json
import pandas as pd
import time
from config_manager import load_config, save_config, get_effective_config
from main import run_daily_workflow
from resume_schema import DEFAULT_RESUME
from agents.resume_parser_agent import parse_resume_to_json


# --- HELPER FUNCTION ---
def get_clean_filename(company, title):
    company_clean = "".join(c for c in str(company) if c.isalnum())
    role_clean = "".join(c for c in str(title) if c.isalnum())[:15]
    return f"Resume_{company_clean}_{role_clean}.pdf"


# --- CRITICAL FIX FOR WINDOWS ---
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

st.set_page_config(page_title="Resume Factory AI", page_icon="🏭", layout="wide")

# --- LOAD STATE ---
config = load_config()
RESUME_FILE = "master_resume.json"

# Check if resume exists
resume_exists = os.path.exists(RESUME_FILE)

# --- SIDEBAR: PROFILE MANAGER ---
with st.sidebar:
    st.title("🏭 Resume Factory")

    # --- 1. PROFILE SECTION (Top Priority) ---
    st.caption("Manage Search Profiles")

    if not os.path.exists("profiles"):
        os.makedirs("profiles")

    profile_files = [f for f in os.listdir("profiles") if f.endswith(".json")]
    if not profile_files:
        save_config(load_config(), "profiles/default.json")
        profile_files = ["default.json"]

    col_p1, col_p2 = st.columns([5, 1])
    with col_p1:
        # Keep profile selection stable
        try:
            prev_index = profile_files.index(
                st.session_state.get("last_profile", profile_files[0])
            )
        except ValueError:
            prev_index = 0

        selected_profile = st.selectbox(
            "Active Profile",
            profile_files,
            index=prev_index,
            key="active_profile_box",
            label_visibility="collapsed",  # Hide label to save space
        )
        st.session_state["last_profile"] = selected_profile

    with col_p2:
        with st.popover("➕", help="Create New Profile"):
            st.markdown("**New Profile**")
            new_profile_name = st.text_input("Name", placeholder="e.g. GameDev")
            if st.button("Create", type="primary"):
                if new_profile_name.strip():
                    safe_name = "".join(
                        c
                        for c in new_profile_name
                        if c.isalnum() or c in (" ", "_", "-")
                    ).strip()
                    # replace spaces with underscores
                    safe_name = safe_name.replace(" ", "_")
                    filename = f"{safe_name}.json"
                    new_path = os.path.join("profiles", filename)
                    if os.path.exists(new_path):
                        st.error("Name already in use!")
                    else:
                        base_config = load_config("profiles/default.json")
                        base_config["role"] = safe_name
                        save_config(base_config, new_path)
                        st.session_state["last_profile"] = filename
                        time.sleep(0.5)
                        st.rerun()

    # Load Config
    current_profile_path = os.path.join("profiles", selected_profile)
    config = get_effective_config(current_profile_path)

    st.markdown("---")

    # --- 2. MAIN SETTINGS (Grouped) ---

    # GROUP A: JOB SEARCH (The most important inputs)
    st.subheader("🎯 Job Search")
    new_role = st.text_input(
        "Job Role", value=config["role"], placeholder="e.g. Software Engineer"
    )
    new_location = st.text_input(
        "Location", value=config["location"], placeholder="e.g. New York or Remote"
    )

    # GROUP B: FILTERS (Collapsible)
    with st.expander("🛠️ Filters & Scraper", expanded=True):
        # Row 1: Types & Remote
        current_job_type = config.get("job_type", ["fulltime"])
        if isinstance(current_job_type, str):
            current_job_type = [current_job_type]

        job_type = st.multiselect(
            "Job Type",
            ["fulltime", "internship", "contract", "parttime"],
            default=current_job_type,
        )
        is_remote = st.checkbox("Remote Only", value=config.get("is_remote", False))

        st.markdown("---")

        # Row 2: Boards
        available_sites = ["linkedin", "indeed", "glassdoor", "zip_recruiter"]
        selected_sites = st.multiselect(
            "Job Boards",
            available_sites,
            default=config.get("scrape_sites", ["linkedin"]),
        )

        # Row 3: Sliders side-by-side
        c1, c2 = st.columns(2)
        with c1:
            hours_old = st.number_input(
                "Max Age (Hours)", 24, 336, value=config.get("hours_old", 72)
            )
        with c2:
            distance = st.number_input(
                "Distance (Miles)", 5, 200, value=config.get("distance", 50)
            )

        fetch_full_desc = st.checkbox(
            "Deep Fetch LinkedIn", value=config.get("fetch_full_desc", True)
        )


    # GROUP C: ADVANCED (Hidden by default)
    with st.expander("⚙️ Advanced & Limits", expanded=False):
        new_target = st.number_input(
            "Success Target",
            1,
            50,
            value=config["target"],
            help="Number of successful resumes to generate before stopping.",
        )
        new_limit = st.number_input(
            "Safety Check Limit",
            10,
            500,
            value=config["safety_limit"],
            help="Maximum jobs to process in one run before stopping.",
        )

        default_blacklist = ", ".join(
            config.get("blacklist", ["Manager", "Senior", "Director"])
        )
        blacklist_input = st.text_area(
            "Blacklist Keywords",
            value=default_blacklist,
            height=68,
            help="Comma-separated keywords to filter out jobs (e.g. 'Senior, Manager').",
        )
        blacklist_list = [x.strip() for x in blacklist_input.split(",") if x.strip()]

        st.header("🔌 Integrations")
        # Initialize variables
        use_email = config.get("use_email", False)
        email_limit = config.get("email_max_results", 10)
        enable_drive = config.get("enable_drive", False)
        enable_google = config.get("enable_google", False)

        # Check if Google Credentials exist
        has_google_creds = os.path.exists("credentials.json")
        
        # 1. GOOGLE INTEGRATION TOGGLE
        enable_google = st.checkbox(
            "Enable Google Cloud (Gmail/Drive)", 
            value=config.get("enable_google", has_google_creds), # Default to ON if keys exist, OFF if they don't
            disabled=not has_google_creds,
            help="Requires 'credentials.json' in the root folder."
        )

        # !!! If the master switch is OFF, force the child settings to OFF.
        # !!! This ensures they save as False even if their widgets are hidden.
        if not enable_google:
            use_email = False
            enable_drive = False
        
        if not has_google_creds:
            st.info("⚠️ Google features are disabled. Add `credentials.json` to enable Gmail scanning and Drive uploads.")
        elif enable_google:
            # Gmail Settings
            with st.expander("☁️ Google Integrations (Gmail & Drive)", expanded=enable_google):
            
                # 1. GMAIL SECTION
                st.markdown("**📧 Gmail Scraper**")
                st.caption("Scan your Gmail for Job Boards emails to find links.")
                
                c1, c2 = st.columns([1, 2])
                with c1:
                    use_email = st.toggle(
                        "Enable Gmail Scraper", 
                        value=config.get("use_email", False) and enable_google,
                        disabled=not enable_google  # Lock if no creds
                    )
                with c2:
                    email_limit = st.number_input(
                        "Max Emails to Scan",
                        min_value=1,
                        max_value=50,
                        value=config.get("email_max_results", 10),
                        disabled=not use_email,  # Lock if scraper is OFF
                        help="Marks scanned emails as read to prevent duplicates."
                    )

                st.divider()  # Visual separation
                
                # 2. DRIVE SECTION
                st.markdown("**💾 Cloud Storage**")
                enable_drive = st.checkbox(
                    "Upload Resumes to Google Drive",
                    value=config.get("enable_drive", False) and enable_google,
                    key="enable_drive_checkbox",
                    disabled=not enable_google, # Lock if no creds
                    help="Automatically uploads the generated PDF to a 'Resumes' folder."
                )
                
                if not enable_google:
                    st.caption("⚠️ *Add `credentials.json` to root folder to enable these features.*")

        st.markdown("### API Keys")
        new_openai = st.text_input(
            "OpenAI Key", value=config["openai_key"], type="password"
        )
        new_discord = st.text_input("Discord Webhook", value=config["discord_webhook"])
        enable_discord = st.checkbox(
            "Enable Notifications",
            value=config.get("enable_discord", False),
            help="Toggle Discord notifications on or off.",
        )

    # --- 3. SAVE ACTION ---
    st.markdown("---")
    if st.button("💾 Save Settings", type="primary", width="stretch"):
        updated_config = config.copy()
        updated_config.update(
            {
                "openai_key": new_openai,
                "discord_webhook": new_discord,
                "enable_discord": enable_discord,
                "role": new_role,
                "location": new_location,
                "job_type": job_type,
                "scrape_sites": selected_sites,
                "is_remote": is_remote,
                "distance": distance,
                "hours_old": hours_old,
                "fetch_full_desc": fetch_full_desc,
                "target": new_target,
                "safety_limit": new_limit,
                "blacklist": blacklist_list,
                # Google Settings
                "enable_google": enable_google,
                "enable_drive": enable_drive,
                "use_email": use_email,
                "email_max_results": email_limit,
            }
        )
        save_config(updated_config, current_profile_path)
        st.toast(f"Settings saved to {selected_profile}!", icon="✅")

# --- MAIN UI ---
st.title("🏭 AI Resume Factory")


# TABS
tab_guide, tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "📖 Guide",
        "🚀 Runner",
        "📝 Master Resume",
        "⚡ Automation",
        "📂 History",
        "📊 Analytics",
    ]
)

# --- TAB 1: RUNNER ---
with tab1:
    if not resume_exists:
        st.error(
            "⛔ You cannot run the workflow until you save a Master Resume. Go to the '📝 Master Resume' tab and save one."
        )
    else:
        col1, col2 = st.columns([1, 3])
        with col1:
            start_btn = st.button("▶️ START WORKFLOW", type="primary", width="stretch")

        # Live Log Console
        st.subheader("🖥️ Live Execution Log")
        log_window = st.empty()

        if start_btn:
            # --- [NEW] AUTO-SAVE & SANITIZE ---
            # 1. Capture user intent from UI
            raw_user_config = config.copy()
            raw_user_config.update({
                "openai_key": new_openai,
                "discord_webhook": new_discord,
                "enable_discord": enable_discord,
                "role": new_role,
                "location": new_location,
                "job_type": job_type,
                "scrape_sites": selected_sites,
                "is_remote": is_remote,
                "distance": distance,
                "hours_old": hours_old,
                "fetch_full_desc": fetch_full_desc,
                "target": new_target,
                "safety_limit": new_limit,
                "blacklist": blacklist_list,
                # Google Settings
                "enable_google": enable_google,
                "enable_drive": enable_drive,
                "use_email": use_email,
                "email_max_results": email_limit,
            })
            
            # 2. Save raw intent to disk
            save_config(raw_user_config, current_profile_path)
            
            # 3. Reload the "Effective" config (The Safer Way)
            config = get_effective_config(current_profile_path)
            
            st.toast("Settings auto-saved & verified!", icon="🛡️")
            # ---------------------------------------

            if not config["openai_key"]:
                st.error("❌ OpenAI API Key is missing!")
            else:
                os.environ["OPENAI_API_KEY"] = config["openai_key"]
                session_logs = []

                def ui_logger(msg):
                    timestamp = time.strftime("%H:%M:%S")
                    session_logs.append(f"[{timestamp}] {msg}")
                    log_window.code("\n".join(session_logs), language="bash")

                with st.spinner("🤖 Agents working..."):
                    try:
                        # Construct scrape_conf using the FRESH 'config' variable
                        scrape_conf = {
                            "hours_old": config.get("hours_old", 72),
                            "sites": config.get("scrape_sites", ["linkedin"]),
                            "is_remote": config.get("is_remote", False),
                            "job_type": config.get("job_type", ["fulltime"]),
                            "distance": config.get("distance", 50),
                            "fetch_full_desc": config.get("fetch_full_desc", True),
                            "blacklist": config.get("blacklist", []),
                            "enable_google": config.get("enable_google", False),
                            "enable_drive": config.get("enable_drive", False),
                            "use_email": config.get("use_email", False),
                            "email_max_results": config.get("email_max_results", 10),
                        }

                        asyncio.run(
                            run_daily_workflow(
                                role=config["role"],
                                location=config["location"],
                                target_successes=config["target"],
                                safety_limit=config["safety_limit"],
                                enable_discord=config.get("enable_discord", True),
                                scrape_config=scrape_conf,
                                status_callback=ui_logger,
                            )
                        )
                        st.success("✅ Done!")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")

# --- TAB 2: MASTER RESUME EDITOR ---
with tab2:
    st.header("📝 Edit Master Resume")

    # 1. Initialize State (Runs once)
    if "resume_json" not in st.session_state:
        if resume_exists:
            with open(RESUME_FILE, "r") as f:
                st.session_state["resume_json"] = json.dumps(json.load(f), indent=4)
        else:
            st.session_state["resume_json"] = json.dumps(DEFAULT_RESUME, indent=4)

    # Ensure the widget key exists so we can modify it programmatically
    if "json_editor" not in st.session_state:
        st.session_state["json_editor"] = st.session_state["resume_json"]

    col_a, col_b = st.columns([1, 1])

    # --- ONBOARDING: PARSE PDF ---
    with col_a:
        st.info(
            "🆕 **New here?** Upload your existing PDF resume to auto-fill the JSON."
        )
        uploaded_resume = st.file_uploader("Upload PDF Resume", type=["pdf"])

        if uploaded_resume:
            if st.button("✨ Auto-Convert to JSON", type="primary"):
                if not config["openai_key"]:
                    st.error("❌ Please set your OpenAI API Key in the Sidebar first!")
                else:
                    with st.spinner("🧠 AI is reading your resume..."):
                        try:
                            # 1. Run the Agent
                            parsed_data = parse_resume_to_json(
                                uploaded_resume, config["openai_key"]
                            )
                            new_json_str = json.dumps(parsed_data, indent=4)

                            # 2. CRITICAL FIX: Update the widget's specific key directly
                            st.session_state["json_editor"] = new_json_str
                            st.session_state["resume_json"] = new_json_str

                            st.success("✅ Conversion Complete!")
                            time.sleep(0.5)
                            st.rerun()  # Force refresh to display new text
                        except Exception as e:
                            st.error(f"❌ Error parsing resume: {e}")

    # --- JSON EDITOR ---
    st.markdown("---")
    st.subheader("Master Resume JSON")

    # Text Area linked to "json_editor" key
    # We remove 'value=' because the key handles the state now
    resume_json_str = st.text_area(
        "Edit your details here:", height=600, key="json_editor"
    )

    # Save Button
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("💾 Save Master Resume"):
            try:
                # Read directly from the widget's state
                current_text = st.session_state["json_editor"]
                new_data = json.loads(current_text)

                # Save to file
                with open(RESUME_FILE, "w") as f:
                    json.dump(new_data, f, indent=4)

                # Sync backup state
                st.session_state["resume_json"] = current_text

                st.success("✅ Saved to disk!")
                time.sleep(1)
                st.rerun()
            except json.JSONDecodeError as e:
                st.error(f"❌ Invalid JSON: {e}")

# --- TAB 3: AUTOMATION ---
with tab3:
    # Alert if Resume is missing
    if not resume_exists:
        st.error(
            "⚠️ **CRITICAL:** You need a Master Resume to run the Automation! Please go to the '📝 Master Resume' tab and save one."
        )
    else:
        st.header(f"⚡ Automate: {selected_profile}")
        st.markdown(
            f"Generate a task specifically for the **{config['role']}** profile."
        )

        col_auto_1, col_auto_2 = st.columns(2)

        # Unique Name for this batch file
        profile_name = selected_profile.replace(".json", "")
        batch_filename = f"run_{profile_name}.bat"

        # Calculate paths
        script_path = os.path.abspath("run_headless.py")
        config_abs_path = os.path.abspath(current_profile_path)
        work_dir = os.getcwd()

        # --- STEP 1: CREATE BATCH FILE ---
        with col_auto_1:
            st.subheader("Step 1: Create Runner Script")

            if st.button(f"🛠️ Generate '{batch_filename}'"):
                # IMPROVEMENT: Use 'call venv/scripts/activate' instead of direct python path.
                # This ensures Playwright browsers are found correctly.
                bat_content = f"""@echo off
    cd /d "{work_dir}"
    call venv\\Scripts\\activate
    python "{script_path}" --config "{config_abs_path}"
    timeout /t 10
    """
                with open(batch_filename, "w") as f:
                    f.write(bat_content)

                st.success(f"✅ Created {batch_filename}")
                st.code(bat_content, language="batch")

        # --- STEP 2: SCHEDULE TASK ---
        with col_auto_2:
            st.subheader("Step 2: Schedule Task")
            run_time = st.time_input(
                "Run this profile at:", value=datetime.strptime("09:00", "%H:%M").time()
            )

            if st.button(f"📅 Schedule '{profile_name}'"):
                bat_path = os.path.abspath(batch_filename)

                # Check if file exists first
                if not os.path.exists(bat_path):
                    st.error(f"Please generate '{batch_filename}' first!")
                else:
                    time_str = run_time.strftime("%H:%M")
                    task_name = f"ResumeAI_{profile_name}"

                    cmd = f'schtasks /Create /SC DAILY /TN "{task_name}" /TR "{bat_path}" /ST {time_str} /F'

                    try:
                        result = subprocess.run(
                            cmd, shell=True, capture_output=True, text=True
                        )
                        if "SUCCESS" in result.stdout:
                            st.success(
                                f"✅ Task '{task_name}' scheduled for {time_str}."
                            )
                        else:
                            st.error(result.stderr)
                    except Exception as e:
                        st.error(f"Error: {e}")

        # --- MANUAL INSTRUCTIONS ---
        st.markdown("---")
        with st.expander("📝 Manual Instructions (If Auto Fails)"):
            st.markdown(f"""
                1. Press  **Windows Key** and search for **Task Scheduler**.
                2. Click **Create Basic Task** on the right.
                3. **Name:** `ResumeAI - {profile_name}`
                4. **Trigger:** Daily at your preferred time.
                5. **Action:** Start a program.
                6. **Program/Script:** Browse and select:  
                `{os.path.join(work_dir, batch_filename)}`
                7. **Start in (Important):** Paste this folder path:  
                `{work_dir}`
                8. **Finish**.
                
                **To wake up computer:** Right-click the new task > Properties > Conditions > Check "Wake the computer to run this task".
                """)
# --- TAB 4: DAILY RESULTS ---
with tab4:
    st.subheader("📄 Daily Results")

    today_str = time.strftime("%Y-%m-%d")
    csv_path = os.path.join("scraped_jobs", f"jobs_found_{today_str}.csv")
    output_dir = os.path.join("output", today_str)

    # 1. LOAD HISTORY (To lookup Drive Links)
    drive_map = {}
    if os.path.exists("history.json"):
        try:
            with open("history.json", "r") as f:
                hist_data = json.load(f)
                # Create a dictionary: { Job_URL : Drive_Link }
                for h in hist_data:
                    if h.get("drive_link"):
                        drive_map[h["url"]] = h["drive_link"]
        except Exception:
            pass  # Ignore errors if file is busy/corrupt

    if os.path.exists(csv_path) and os.path.exists(output_dir):
        df = pd.read_csv(csv_path)

        # Quick Stats
        if "Source" in df.columns:
            c1, c2 = st.columns(2)
            c1.metric("📧 From Emails", len(df[df["Source"] == "Email"]))
            c2.metric("🌐 From Web Scraper", len(df[df["Source"] == "Web"]))
            st.divider()

        results_container = st.container()

        with results_container:
            found_pdfs = 0
            for index, row in df.iterrows():
                pdf_name = get_clean_filename(row["Company"], row["Title"])
                full_pdf_path = os.path.join(output_dir, pdf_name)

                # Determine Icon
                source_icon = "🌐"
                if "Source" in row and row["Source"] == "Email":
                    source_icon = "📧"

                # Lookup Drive Link
                my_drive_link = drive_map.get(row["URL"])

                if os.path.exists(full_pdf_path):
                    found_pdfs += 1
                    with st.expander(
                        f"{source_icon} ✅ {row['Company']} - {row['Title']}",
                        expanded=True,
                    ):
                        # UPDATED COLUMNS: Added a 4th column for Drive Button
                        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])

                        with c1:
                            st.caption("Job Source URL")
                            st.write(f"{row['URL']}")
                            if "Source" in row:
                                st.caption(f"Detected via: {row['Source']}")

                        with c2:
                            with open(full_pdf_path, "rb") as f:
                                st.download_button(
                                    label="⬇️ PDF",
                                    data=f,
                                    file_name=pdf_name,
                                    mime="application/pdf",
                                    type="primary",
                                    width="stretch",
                                )

                        with c3:
                            # GOOGLE DRIVE BUTTON
                            if my_drive_link:
                                st.link_button(
                                    "☁️ Drive", 
                                    my_drive_link, 
                                    width="stretch",
                                    help="Open this PDF in Google Drive"
                                )
                            else:
                                # Disabled State
                                st.button(
                                    "☁️ Local Only",  # Changed text to be clearer
                                    disabled=True,
                                    width="stretch",
                                    key=f"drive_na_{index}",
                                    help="Drive Upload was disabled when this resume was generated."
                                )
                        with c4:
                            st.link_button("🔗 Apply", row["URL"], width="stretch")

            if found_pdfs == 0:
                st.warning("Jobs were found, but no Resumes were generated yet.")
            else:
                st.success(f"Showing {found_pdfs} generated resumes for today.")

    else:
        st.info(f"No activity found for today ({today_str}).")

# --- TAB 5: ANALYTICS & LOGS ---
with tab5:
    st.subheader("📊 Activity Log")

    if os.path.exists("history.json"):
        try:
            with open("history.json", "r") as f:
                content = f.read().strip()
                if content:
                    history = json.loads(content)
                else:
                    history = []
        except json.JSONDecodeError:
            st.error("⚠️ history.json is corrupted. You may need to delete it.")
            history = []

        if history:
            # 1. Create DataFrame
            hist_df = pd.DataFrame(history)

            # 2. Handle Missing Columns (Backwards Compatibility)
            if "source" not in hist_df.columns:
                hist_df["source"] = "Web"  # Default for old entries

            # Fill N/A values to prevent errors
            hist_df["source"] = hist_df["source"].fillna("Web")
            hist_df["company"] = hist_df["company"].fillna("Unknown")
            hist_df["title"] = hist_df["title"].fillna("Unknown")

            # 3. Add Visual Helpers
            def get_status_icon(status):
                if status == "GENERATED":
                    return "✅"
                elif status == "FAILED_CONTENT":
                    return "❌"
                elif status == "FILTERED_OUT":
                    return "⚠️"
                elif "Duplicate" in str(status):
                    return "🔄"
                else:
                    return "❓"

            def get_source_icon(source):
                if source == "Email":
                    return "📧"
                return "🌐"

            if "status" in hist_df.columns:
                hist_df["icon"] = hist_df["status"].apply(get_status_icon)
                hist_df["source_icon"] = hist_df["source"].apply(get_source_icon)

                # --- 4. FILTERS UI ---
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    search_term = st.text_input(
                        "🔍 Search Log", placeholder="Company or Title..."
                    )
                with c2:
                    filter_status = st.multiselect(
                        "Status", hist_df["status"].unique(), default=[]
                    )
                with c3:
                    filter_source = st.multiselect(
                        "Source", hist_df["source"].unique(), default=[]
                    )

                # --- 5. APPLY FILTERS ---
                filtered_df = hist_df.copy()

                # Text Search
                if search_term:
                    filtered_df = filtered_df[
                        filtered_df["company"].str.contains(search_term, case=False)
                        | filtered_df["title"].str.contains(search_term, case=False)
                    ]

                # Dropdown Filters
                if filter_status:
                    filtered_df = filtered_df[filtered_df["status"].isin(filter_status)]
                if filter_source:
                    filtered_df = filtered_df[filtered_df["source"].isin(filter_source)]

                # --- 6. DISPLAY TABLE ---
                # Select and reorder columns
                cols_to_show = [
                    "icon",
                    "source_icon",
                    "date",
                    "company",
                    "title",
                    "status",
                    "source",
                    "url",
                ]
                # Only grab columns that actually exist (safety)
                final_cols = [c for c in cols_to_show if c in filtered_df.columns]

                display_df = filtered_df[final_cols]

                st.dataframe(
                    display_df.sort_values(by="date", ascending=False),
                    column_config={
                        "icon": st.column_config.TextColumn(
                            "St", width="small", help="Status"
                        ),
                        "source_icon": st.column_config.TextColumn(
                            "Src", width="small", help="Source Type"
                        ),
                        "url": st.column_config.LinkColumn("Job Link"),
                        "status": st.column_config.TextColumn("Detail"),
                        "source": st.column_config.TextColumn("Source Type"),
                        "date": st.column_config.DateColumn(
                            "Date", format="YYYY-MM-DD"
                        ),
                    },
                    width="stretch",
                    hide_index=True,
                )

                st.caption(f"Showing {len(display_df)} of {len(hist_df)} records.")
            else:
                st.dataframe(hist_df)
        else:
            st.info("History is empty.")
    else:
        st.info("No history.json found yet.")

# --- TAB GUIDE ---
with tab_guide:
    readme_path = "README.md"

    if os.path.exists(readme_path):
        try:
            with open(readme_path, "r", encoding="utf-8") as f:
                    readme_lines = f.readlines()

            # FILTER: Remove the first line if it's the main title (starts with # )
            # We iterate and keep everything EXCEPT the top-level H1
            filtered_content = []
            for line in readme_lines:
                if line.strip().startswith("# 🏭 AI Resume Factory"):
                        continue  # Skip the specific duplicate title
                filtered_content.append(line)

            # Join it back into a single string
            final_markdown = "".join(filtered_content)

            # Render
            st.markdown(final_markdown, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error loading README: {e}")
    else:
        st.warning("README.md not found.")
