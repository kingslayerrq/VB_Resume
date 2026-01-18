import streamlit as st
import asyncio
import os
import sys

from agents.resume_parser_agent import parse_resume_to_json
from resume_schema import DEFAULT_RESUME
from ui.sidebar import render_sidebar
from ui.tabs.analytics import render_analytics_tab
from ui.tabs.automation import render_automation_tab
from ui.tabs.guide import render_guide_tab
from ui.tabs.history import render_history_tab
from ui.tabs.master_resume import render_master_resume_tab
from ui.tabs.runner import render_runner_tab


# --- CRITICAL FIX FOR WINDOWS ---
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

st.set_page_config(page_title="Resume Factory AI", page_icon="🏭", layout="wide")

RESUME_FILE = "master_resume.json"

# Check if resume exists
resume_exists = os.path.exists(RESUME_FILE)

sidebar_state = render_sidebar()
config = sidebar_state.config

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
    render_runner_tab(
        resume_exists=resume_exists,
        config=config,
        inputs=sidebar_state.inputs,
        current_profile_path=sidebar_state.current_profile_path,
    )

# --- TAB 2: MASTER RESUME EDITOR ---
with tab2:
    render_master_resume_tab(
        resume_exists=resume_exists,
        resume_file=RESUME_FILE,
        config=config,
        default_resume=DEFAULT_RESUME,
        parse_resume_to_json=parse_resume_to_json,
    )

# --- TAB 3: AUTOMATION ---
with tab3:
    render_automation_tab(
        resume_exists=resume_exists,
        selected_profile=sidebar_state.selected_profile,
        current_profile_path=sidebar_state.current_profile_path,
        config=config,
    )

# --- TAB 4: DAILY RESULTS ---
with tab4:
    render_history_tab()

# --- TAB 5: ANALYTICS & LOGS ---
with tab5:
    render_analytics_tab()

# --- TAB GUIDE ---
with tab_guide:
    render_guide_tab()
