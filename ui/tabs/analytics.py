import json
import os

import pandas as pd
import streamlit as st


def render_analytics_tab():
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

            if "source" not in hist_df.columns:
                hist_df["source"] = "Web"

            hist_df["source"] = hist_df["source"].fillna("Web")
            hist_df["company"] = hist_df["company"].fillna("Unknown")
            hist_df["title"] = hist_df["title"].fillna("Unknown")

            def get_status_icon(status):
                if status == "GENERATED":
                    return "✅"
                if status == "FAILED_CONTENT":
                    return "❌"
                if status == "FILTERED_OUT":
                    return "⚠️"
                if "Duplicate" in str(status):
                    return "🔄"
                return "❓"

            def get_source_icon(source):
                if source == "Email":
                    return "📧"
                return "🌐"

            if "status" in hist_df.columns:
                hist_df["icon"] = hist_df["status"].apply(get_status_icon)
                hist_df["source_icon"] = hist_df["source"].apply(get_source_icon)

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

                filtered_df = hist_df.copy()

                if search_term:
                    filtered_df = filtered_df[
                        filtered_df["company"].str.contains(search_term, case=False)
                        | filtered_df["title"].str.contains(search_term, case=False)
                    ]

                if filter_status:
                    filtered_df = filtered_df[filtered_df["status"].isin(filter_status)]
                if filter_source:
                    filtered_df = filtered_df[filtered_df["source"].isin(filter_source)]

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
