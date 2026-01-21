import json
import os
import time

import pandas as pd
import streamlit as st

from ui.utils import get_clean_filename


def render_history_tab():
    st.subheader("📄 Daily Results")

    today_str = time.strftime("%Y-%m-%d")
    csv_path = os.path.join("scraped_jobs", f"jobs_found_{today_str}.csv")
    output_dir = os.path.join("output", today_str)

    drive_map = {}
    if os.path.exists("history.json"):
        try:
            with open("history.json", "r") as f:
                hist_data = json.load(f)
                for h in hist_data:
                    if h.get("drive_link"):
                        drive_map[h["url"]] = h["drive_link"]
        except Exception:
            pass

    if os.path.exists(csv_path) and os.path.exists(output_dir):
        df = pd.read_csv(csv_path)

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

                source_icon = "🌐"
                if "Source" in row and row["Source"] == "Email":
                    source_icon = "📧"

                my_drive_link = drive_map.get(row["URL"])

                if os.path.exists(full_pdf_path):
                    found_pdfs += 1
                    with st.expander(
                        f"{source_icon} ✅ {row['Company']} - {row['Title']}",
                        expanded=True,
                    ):
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
                                    key=f"pdf_download_{index}",
                                )

                        with c3:
                            if my_drive_link:
                                st.link_button(
                                    "☁️ Drive",
                                    my_drive_link,
                                    width="stretch",
                                    help="Open this PDF in Google Drive",
                                )
                            else:
                                st.button(
                                    "☁️ Local Only",
                                    disabled=True,
                                    width="stretch",
                                    key=f"drive_na_{index}",
                                    help="Drive Upload was disabled when this resume was generated.",
                                )
                        with c4:
                            st.link_button("🔗 Apply", row["URL"], width="stretch")

            if found_pdfs == 0:
                st.warning("Jobs were found, but no Resumes were generated yet.")
            else:
                st.success(f"Showing {found_pdfs} generated resumes for today.")
    else:
        st.info(f"No activity found for today ({today_str}).")
