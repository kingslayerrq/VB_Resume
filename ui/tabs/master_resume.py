import json
import time

import streamlit as st


def render_master_resume_tab(
    resume_exists,
    resume_file,
    config,
    default_resume,
    parse_resume_to_json,
):
    st.header("📝 Edit Master Resume")

    if "resume_json" not in st.session_state:
        if resume_exists:
            with open(resume_file, "r") as f:
                st.session_state["resume_json"] = json.dumps(json.load(f), indent=4)
        else:
            st.session_state["resume_json"] = json.dumps(default_resume, indent=4)

    if "json_editor" not in st.session_state:
        st.session_state["json_editor"] = st.session_state["resume_json"]

    col_a, col_b = st.columns([1, 1])

    with col_a:
        st.info("🆕 **New here?** Upload your existing PDF resume to auto-fill the JSON.")
        uploaded_resume = st.file_uploader("Upload PDF Resume", type=["pdf"])

        if uploaded_resume:
            if st.button("✨ Auto-Convert to JSON", type="primary"):
                provider = config.get("model_provider", "ollama")
                model_name = config.get("model_name", "llama3.1:8b")
                api_key = config.get("model_api_keys", {}).get(provider)
                if provider == "openai" and not api_key:
                    st.error("❌ Please set your OpenAI API Key in the Sidebar first!")
                else:
                    with st.spinner("🧠 AI is reading your resume..."):
                        try:
                            llm_settings = {
                                "provider": provider,
                                "model": model_name,
                                "api_key": api_key,
                            }
                            parsed_data = parse_resume_to_json(
                                uploaded_resume, llm_settings
                            )
                            new_json_str = json.dumps(parsed_data, indent=4)

                            st.session_state["json_editor"] = new_json_str
                            st.session_state["resume_json"] = new_json_str

                            st.success("✅ Conversion Complete!")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error parsing resume: {e}")

    st.markdown("---")
    st.subheader("Master Resume JSON")

    st.text_area("Edit your details here:", height=600, key="json_editor")

    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("💾 Save Master Resume"):
            try:
                current_text = st.session_state["json_editor"]
                new_data = json.loads(current_text)

                with open(resume_file, "w") as f:
                    json.dump(new_data, f, indent=4)

                st.session_state["resume_json"] = current_text

                st.success("✅ Saved to disk!")
                time.sleep(1)
                st.rerun()
            except json.JSONDecodeError as e:
                st.error(f"❌ Invalid JSON: {e}")
