import os

import streamlit as st


def render_guide_tab():
    readme_path = "README.md"

    if os.path.exists(readme_path):
        try:
            with open(readme_path, "r", encoding="utf-8") as f:
                readme_lines = f.readlines()

            filtered_content = []
            for line in readme_lines:
                if line.strip().startswith("# 🏭 AI Resume Factory"):
                    continue
                filtered_content.append(line)

            final_markdown = "".join(filtered_content)

            st.markdown(final_markdown, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error loading README: {e}")
    else:
        st.warning("README.md not found.")
