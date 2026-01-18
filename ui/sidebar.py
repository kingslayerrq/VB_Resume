import os
import time

import streamlit as st

from config_manager import load_config, save_config, get_effective_config
from ui.state import SidebarInputs, SidebarState


def _build_updated_config(config, inputs):
    updated_config = config.copy()
    updated_config.update(
        {
            "openai_key": inputs.new_openai,
            "discord_webhook": inputs.new_discord,
            "enable_discord": inputs.enable_discord,
            "role": inputs.new_role,
            "location": inputs.new_location,
            "job_type": inputs.job_type,
            "scrape_sites": inputs.selected_sites,
            "is_remote": inputs.is_remote,
            "distance": inputs.distance,
            "hours_old": inputs.hours_old,
            "fetch_full_desc": inputs.fetch_full_desc,
            "target": inputs.new_target,
            "safety_limit": inputs.new_limit,
            "blacklist": inputs.blacklist_list,
            "enable_google": inputs.enable_google,
            "enable_drive": inputs.enable_drive,
            "use_email": inputs.use_email,
            "email_max_results": inputs.email_limit,
        }
    )
    return updated_config


def render_sidebar():
    config = load_config()

    with st.sidebar:
        st.title("🏭 Resume Factory")
        st.caption("Manage Search Profiles")

        if not os.path.exists("profiles"):
            os.makedirs("profiles")

        profile_files = [f for f in os.listdir("profiles") if f.endswith(".json")]
        if not profile_files:
            save_config(load_config(), "profiles/default.json")
            profile_files = ["default.json"]

        col_p1, col_p2 = st.columns([5, 1])
        with col_p1:
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
                label_visibility="collapsed",
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

        current_profile_path = os.path.join("profiles", selected_profile)
        config = get_effective_config(current_profile_path)

        st.markdown("---")

        st.subheader("🎯 Job Search")
        new_role = st.text_input(
            "Job Role", value=config["role"], placeholder="e.g. Software Engineer"
        )
        new_location = st.text_input(
            "Location", value=config["location"], placeholder="e.g. New York or Remote"
        )

        with st.expander("🛠️ Filters & Scraper", expanded=True):
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

            available_sites = ["linkedin", "indeed", "glassdoor", "zip_recruiter"]
            selected_sites = st.multiselect(
                "Job Boards",
                available_sites,
                default=config.get("scrape_sites", ["linkedin"]),
            )

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
            use_email = config.get("use_email", False)
            email_limit = config.get("email_max_results", 10)
            enable_drive = config.get("enable_drive", False)
            enable_google = config.get("enable_google", False)

            has_google_creds = os.path.exists("credentials.json")

            enable_google = st.checkbox(
                "Enable Google Cloud (Gmail/Drive)",
                value=config.get("enable_google", has_google_creds),
                disabled=not has_google_creds,
                help="Requires 'credentials.json' in the root folder.",
            )

            if not enable_google:
                use_email = False
                enable_drive = False

            if not has_google_creds:
                st.info(
                    "⚠️ Google features are disabled. Add `credentials.json` to enable Gmail scanning and Drive uploads."
                )
            elif enable_google:
                with st.expander("☁️ Google Integrations (Gmail & Drive)", expanded=enable_google):
                    st.markdown("**📧 Gmail Scraper**")
                    st.caption("Scan your Gmail for Job Boards emails to find links.")

                    c1, c2 = st.columns([1, 2])
                    with c1:
                        use_email = st.toggle(
                            "Enable Gmail Scraper",
                            value=config.get("use_email", False) and enable_google,
                            disabled=not enable_google,
                        )
                    with c2:
                        email_limit = st.number_input(
                            "Max Emails to Scan",
                            min_value=1,
                            max_value=50,
                            value=config.get("email_max_results", 10),
                            disabled=not use_email,
                            help="Marks scanned emails as read to prevent duplicates.",
                        )

                    st.divider()

                    st.markdown("**💾 Cloud Storage**")
                    enable_drive = st.checkbox(
                        "Upload Resumes to Google Drive",
                        value=config.get("enable_drive", False) and enable_google,
                        key="enable_drive_checkbox",
                        disabled=not enable_google,
                        help="Automatically uploads the generated PDF to a 'Resumes' folder.",
                    )

                    if not enable_google:
                        st.caption(
                            "⚠️ *Add `credentials.json` to root folder to enable these features.*"
                        )

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

        st.markdown("---")
        if st.button("💾 Save Settings", type="primary", width="stretch"):
            inputs = SidebarInputs(
                new_openai=new_openai,
                new_discord=new_discord,
                enable_discord=enable_discord,
                new_role=new_role,
                new_location=new_location,
                job_type=job_type,
                selected_sites=selected_sites,
                is_remote=is_remote,
                distance=distance,
                hours_old=hours_old,
                fetch_full_desc=fetch_full_desc,
                new_target=new_target,
                new_limit=new_limit,
                blacklist_list=blacklist_list,
                enable_google=enable_google,
                enable_drive=enable_drive,
                use_email=use_email,
                email_limit=email_limit,
            )
            updated_config = _build_updated_config(config, inputs)
            save_config(updated_config, current_profile_path)
            st.toast(f"Settings saved to {selected_profile}!", icon="✅")

    inputs = SidebarInputs(
        new_openai=new_openai,
        new_discord=new_discord,
        enable_discord=enable_discord,
        new_role=new_role,
        new_location=new_location,
        job_type=job_type,
        selected_sites=selected_sites,
        is_remote=is_remote,
        distance=distance,
        hours_old=hours_old,
        fetch_full_desc=fetch_full_desc,
        new_target=new_target,
        new_limit=new_limit,
        blacklist_list=blacklist_list,
        enable_google=enable_google,
        enable_drive=enable_drive,
        use_email=use_email,
        email_limit=email_limit,
    )

    return SidebarState(
        config=config,
        selected_profile=selected_profile,
        current_profile_path=current_profile_path,
        inputs=inputs,
    )
