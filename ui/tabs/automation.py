import os
import subprocess
from datetime import datetime

import streamlit as st


def render_automation_tab(resume_exists, selected_profile, current_profile_path, config):
    if not resume_exists:
        st.error(
            "⚠️ **CRITICAL:** You need a Master Resume to run the Automation! Please go to the '📝 Master Resume' tab and save one."
        )
        return

    st.header(f"⚡ Automate: {selected_profile}")
    st.markdown(f"Generate a task specifically for the **{config['role']}** profile.")

    col_auto_1, col_auto_2 = st.columns(2)

    profile_name = selected_profile.replace(".json", "")
    batch_filename = f"run_{profile_name}.bat"

    script_path = os.path.abspath("run_headless.py")
    config_abs_path = os.path.abspath(current_profile_path)
    work_dir = os.getcwd()

    with col_auto_1:
        st.subheader("Step 1: Create Runner Script")

        if st.button(f"🛠️ Generate '{batch_filename}'"):
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

    with col_auto_2:
        st.subheader("Step 2: Schedule Task")
        run_time = st.time_input(
            "Run this profile at:", value=datetime.strptime("09:00", "%H:%M").time()
        )

        if st.button(f"📅 Schedule '{profile_name}'"):
            bat_path = os.path.abspath(batch_filename)

            if not os.path.exists(bat_path):
                st.error(f"Please generate '{batch_filename}' first!")
            else:
                time_str = run_time.strftime("%H:%M")
                task_name = f"ResumeAI_{profile_name}"

                cmd = (
                    f"schtasks /Create /SC DAILY /TN \"{task_name}\" /TR \"{bat_path}\" /ST {time_str} /F"
                )

                try:
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    if "SUCCESS" in result.stdout:
                        st.success(f"✅ Task '{task_name}' scheduled for {time_str}.")
                    else:
                        st.error(result.stderr)
                except Exception as e:
                    st.error(f"Error: {e}")

    st.markdown("---")
    with st.expander("📝 Manual Instructions (If Auto Fails)"):
        st.markdown(
            f"""
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
            """
        )
