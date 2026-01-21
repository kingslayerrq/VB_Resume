import asyncio
import os
import time

import streamlit as st

from config_manager import save_config, get_effective_config
from main import run_daily_workflow


def _apply_inputs_to_config(config, inputs):
    model_api_keys = config.get("model_api_keys", {}).copy()
    model_api_keys[inputs.model_provider] = inputs.model_api_key
    updated_config = config.copy()
    updated_config.update(
        {
            "model_api_keys": model_api_keys,
            "model_provider": inputs.model_provider,
            "model_name": inputs.model_name,
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
            "agent_models": inputs.agent_models,
            "enable_notion": inputs.enable_notion,
            "notion_api_key": inputs.notion_api_key,
            "notion_database_id": inputs.notion_database_id,
        }
    )
    return updated_config


def render_runner_tab(resume_exists, config, inputs, current_profile_path):
    if not resume_exists:
        st.error(
            "⛔ You cannot run the workflow until you save a Master Resume. Go to the '📝 Master Resume' tab and save one."
        )
        return

    col1, col2 = st.columns([1, 3])
    with col1:
        start_btn = st.button("▶️ START WORKFLOW", type="primary", width="stretch")

    st.subheader("🖥️ Live Execution Log")
    log_window = st.empty()

    if start_btn:
        raw_user_config = _apply_inputs_to_config(config, inputs)
        save_config(raw_user_config, current_profile_path)

        config = get_effective_config(current_profile_path)

        st.toast("Settings auto-saved & verified!", icon="🛡️")

        provider = config.get("model_provider", "ollama")
        model_name = config.get("model_name", "llama3.1:8b")
        api_key = config.get("model_api_keys", {}).get(provider)
        if provider == "openai" and not api_key:
            st.error("❌ OpenAI API Key is missing!")
            return

        if provider == "openai" and api_key:
            os.environ["OPENAI_API_KEY"] = api_key
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
                    "enable_google": config.get("enable_google", False),
                    "enable_drive": config.get("enable_drive", False),
                    "use_email": config.get("use_email", False),
                    "email_max_results": config.get("email_max_results", 10),
                }

                llm_settings = {
                    "provider": provider,
                    "model": model_name,
                    "api_key": api_key,
                    "model_api_keys": config.get("model_api_keys", {}),
                    "agent_models": config.get("agent_models", {}),
                }
                notion_config = {
                    "enable": config.get("enable_notion", False),
                    "api_key": config.get("notion_api_key", ""),
                    "database_id": config.get("notion_database_id", ""),
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
                        llm_settings=llm_settings,
                        notion_config=notion_config,
                    )
                )
                st.success("✅ Done!")
            except Exception as e:
                st.error(f"❌ Error: {e}")
