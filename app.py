import streamlit as st
import asyncio
import subprocess
from datetime import datetime
import os
import sys
import json
import pandas as pd
import time
from config_manager import load_config, save_config
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
            prev_index = profile_files.index(st.session_state.get("last_profile", profile_files[0]))
        except ValueError:
            prev_index = 0
            
        selected_profile = st.selectbox(
            "Active Profile", 
            profile_files, 
            index=prev_index, 
            key="active_profile_box", 
            label_visibility="collapsed" # Hide label to save space
        )
        st.session_state["last_profile"] = selected_profile

    with col_p2:
        with st.popover("➕", help="Create New Profile"):
            st.markdown("**New Profile**")
            new_profile_name = st.text_input("Name", placeholder="e.g. GameDev")
            if st.button("Create", type="primary"):
                if new_profile_name.strip():
                    safe_name = "".join(c for c in new_profile_name if c.isalnum() or c in (' ', '_', '-')).strip()
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
    config = load_config(current_profile_path)
    
    st.markdown("---")

    # --- 2. MAIN SETTINGS (Grouped) ---
    
    # GROUP A: JOB SEARCH (The most important inputs)
    st.subheader("🎯 Job Search")
    new_role = st.text_input("Job Role", value=config['role'], placeholder="e.g. Software Engineer")
    new_location = st.text_input("Location", value=config['location'], placeholder="e.g. New York or Remote")

    # GROUP B: FILTERS (Collapsible)
    with st.expander("🛠️ Filters & Scraper", expanded=True):
        # Row 1: Types & Remote
        current_job_type = config.get('job_type', ["fulltime"])
        if isinstance(current_job_type, str): current_job_type = [current_job_type]
        
        job_type = st.multiselect("Job Type", ["fulltime", "internship", "contract", "parttime"], default=current_job_type)
        is_remote = st.checkbox("Remote Only", value=config.get('is_remote', False))
        
        st.markdown("---")
        
        # Row 2: Boards
        available_sites = ["linkedin", "indeed", "glassdoor", "zip_recruiter"]
        selected_sites = st.multiselect("Job Boards", available_sites, default=config.get('scrape_sites', ["linkedin"]))

        # Row 3: Sliders side-by-side
        c1, c2 = st.columns(2)
        with c1:
            hours_old = st.number_input("Max Age (Hours)", 24, 336, value=config.get('hours_old', 72))
        with c2:
            distance = st.number_input("Distance (Miles)", 5, 200, value=config.get('distance', 50))

        fetch_full_desc = st.checkbox("Deep Fetch LinkedIn", value=config.get('fetch_full_desc', True))

    # GROUP C: ADVANCED (Hidden by default)
    with st.expander("⚙️ Advanced & Limits", expanded=False):
        new_target = st.number_input("Success Target", 1, 50, value=config['target'], help="Number of successful resumes to generate before stopping.")
        new_limit = st.number_input("Safety Check Limit", 10, 500, value=config['safety_limit'], help="Maximum jobs to process in one run before stopping.")
        
        default_blacklist = ", ".join(config.get('blacklist', ["Manager", "Senior", "Director"]))
        blacklist_input = st.text_area("Blacklist Keywords", value=default_blacklist, height=68, help="Comma-separated keywords to filter out jobs (e.g. 'Senior, Manager').")
        blacklist_list = [x.strip() for x in blacklist_input.split(",") if x.strip()]
        
        st.markdown("### API Keys")
        new_openai = st.text_input("OpenAI Key", value=config['openai_key'], type="password")
        new_discord = st.text_input("Discord Webhook", value=config['discord_webhook'])
        enable_discord = st.checkbox("Enable Notifications", value=config.get('enable_discord', False))

    # --- 3. SAVE ACTION ---
    st.markdown("---")
    if st.button("💾 Save Settings", type="primary", use_container_width=True):
        updated_config = config.copy()
        updated_config.update({
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
            "blacklist": blacklist_list
        })
        save_config(updated_config, current_profile_path)
        st.toast(f"Settings saved to {selected_profile}!", icon="✅")

# --- MAIN UI ---
st.title("🏭 AI Resume Factory")

# Alert if Resume is missing
if not resume_exists:
    st.error(
        "⚠️ **CRITICAL:** No Master Resume found! Please go to the '📝 Master Resume' tab and save one."
    )

# TABS
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["🚀 Runner", "📝 Master Resume", "⚡ Automation", "📂 History", "📊 Analytics"]
)

# --- TAB 1: RUNNER ---
with tab1:
    if not resume_exists:
        st.warning("⛔ You cannot run the workflow until you save a Master Resume.")
    else:
        col1, col2 = st.columns([1, 3])
        with col1:
            start_btn = st.button("▶️ START WORKFLOW", type="primary", width="stretch")

        # Live Log Console
        st.subheader("🖥️ Live Execution Log")
        log_window = st.empty()

        if start_btn:
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
                        scrape_conf = {
                            "hours_old": config.get("hours_old", 72),
                            "sites": config.get("scrape_sites", ["linkedin"]),
                            "is_remote": config.get("is_remote", False),
                            "job_type": config.get("job_type", ["fulltime"]),
                            "distance": config.get("distance", 50),
                            "fetch_full_desc": config.get("fetch_full_desc", True),
                            "blacklist": config.get("blacklist", []),
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

with tab3:
    st.header(f"⚡ Automate: {selected_profile}")
    st.markdown(f"Generate a task specifically for the **{config['role']}** profile.")

    col_auto_1, col_auto_2 = st.columns(2)

    # --- STEP 1: CREATE BATCH FILE ---
    with col_auto_1:
        st.subheader("Step 1: Create Runner Script")

        # Unique Name for this batch file
        profile_name = selected_profile.replace(".json", "")
        batch_filename = f"run_{profile_name}.bat"

        if st.button(f"🛠️ Generate '{batch_filename}'"):
            python_path = sys.executable
            script_path = os.path.abspath("run_headless.py")
            config_abs_path = os.path.abspath(
                current_profile_path
            )  # Absolute path to profile
            work_dir = os.getcwd()

            # PASS THE CONFIG PATH IN THE BATCH COMMAND
            bat_content = f"""@echo off
cd /d "{work_dir}"
"{python_path}" "{script_path}" --config "{config_abs_path}"
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
            time_str = run_time.strftime("%H:%M")
            task_name = f"ResumeAI_{profile_name}"  # Unique Task Name

            cmd = f'schtasks /Create /SC DAILY /TN "{task_name}" /TR "{bat_path}" /ST {time_str} /F'

            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if "SUCCESS" in result.stdout:
                    st.success(f"✅ Task '{task_name}' scheduled for {time_str}.")
                else:
                    st.error(result.stderr)
            except Exception as e:
                st.error(f"Error: {e}")

    # --- MANUAL INSTRUCTIONS ---
    st.markdown("---")
    with st.expander("📝 Manual Instructions (If Auto Fails)"):
        st.markdown(f"""
        1. Press **Windows Key** and search for **Task Scheduler**.
        2. Click **Create Basic Task** on the right.
        3. **Name:** `Resume Factory Daily`
        4. **Trigger:** Daily at your preferred time.
        5. **Action:** Start a program.
        6. **Program/Script:** Browse and select:  
           `{os.path.abspath("run_daily.bat")}`
        7. **Start in (Optional):** Paste this folder path:  
           `{os.getcwd()}`
        8. **Finish**.
        
        **To wake up computer:** Right-click the new task > Properties > Conditions > Check "Wake the computer to run this task".
        """)

# --- TAB 4: HISTORY ---
with tab4:
    st.subheader("📄 Daily Results")

    today_str = time.strftime("%Y-%m-%d")
    csv_path = os.path.join("scraped_jobs", f"jobs_found_{today_str}.csv")
    output_dir = os.path.join("output", today_str)

    if os.path.exists(csv_path) and os.path.exists(output_dir):
        df = pd.read_csv(csv_path)

        results_container = st.container()

        with results_container:
            found_pdfs = 0
            for index, row in df.iterrows():
                # Reconstruct the expected filename using the Helper Function
                pdf_name = get_clean_filename(row["Company"], row["Title"])
                full_pdf_path = os.path.join(output_dir, pdf_name)

                if os.path.exists(full_pdf_path):
                    found_pdfs += 1
                    with st.expander(
                        f"✅ {row['Company']} - {row['Title']}", expanded=True
                    ):
                        c1, c2, c3 = st.columns([2, 1, 1])
                        with c1:
                            st.caption("Job Source URL")
                            st.write(f"{row['URL']}")
                        with c2:
                            with open(full_pdf_path, "rb") as f:
                                st.download_button(
                                    label="⬇️ Download PDF",
                                    data=f,
                                    file_name=pdf_name,
                                    mime="application/pdf",
                                    type="primary",
                                    width="stretch",
                                )
                        with c3:
                            st.link_button("🔗 Apply Now", row["URL"], width="stretch")

            if found_pdfs == 0:
                st.warning(
                    "Jobs were found, but no Resumes were generated yet (Checks failed or in progress)."
                )
            else:
                st.success(f"Showing {found_pdfs} generated resumes for today.")

    else:
        st.info(
            f"No activity found for today ({today_str}). Run the workflow to see results here."
        )

# --- TAB 5: LOGS ---
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
            hist_df = pd.DataFrame(history)

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

            if "status" in hist_df.columns:
                hist_df["icon"] = hist_df["status"].apply(get_status_icon)
                cols = ["icon", "date", "company", "title", "status", "url"]
                existing_cols = [c for c in cols if c in hist_df.columns]
                hist_df = hist_df[existing_cols]

                st.dataframe(
                    hist_df.sort_values(by="date", ascending=False),
                    column_config={
                        "icon": st.column_config.TextColumn("State", width="small"),
                        "url": st.column_config.LinkColumn("Job Link"),
                        "status": st.column_config.TextColumn("Detail"),
                        "date": st.column_config.DateColumn(
                            "Date", format="YYYY-MM-DD"
                        ),
                    },
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.dataframe(hist_df)
        else:
            st.info("History is empty.")
    else:
        st.info("No history.json found yet.")
