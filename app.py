import streamlit as st
from openai import OpenAI
import os
import requests
from datetime import datetime

st.set_page_config(page_title="Analytics Copilot Demo")

st.title("📊 Analytics Copilot — Demo")
st.caption("Paste a dashboard link and ask a question. Now with optional real Mixpanel data for ONE saved report.")

# ----------------- Sidebar: Mixpanel (optional) -----------------
st.sidebar.header("Optional: Mixpanel setup (one saved report)")

st.sidebar.markdown("""
If you want REAL numbers:
1. In Mixpanel, create or open an **Insights** report you like.
2. Note the **Project ID** and **bookmark_id**.
3. Add Mixpanel secrets in Streamlit (same place as OPENAI_API_KEY).
4. Paste the **bookmark_id** below.
""")

mixpanel_report_id = st.sidebar.text_input(
    "Mixpanel saved Insights report bookmark_id",
    placeholder="e.g. 1234567"
)

st.sidebar.caption("If empty, the app will NOT call Mixpanel and will use GPT only.")

# ----------------- Main inputs -----------------
dashboard_link = st.text_input(
    "Dashboard link",
    placeholder="Paste your Mixpanel (or any) dashboard link here..."
)

question = st.text_area(
    "Your question",
    placeholder="Example: What was signup conversion last week in Bangalore?"
)

# OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Helper: call Mixpanel Insights Query API for one saved report
def call_mixpanel_insights():
    """
    Uses Mixpanel Query API 'Query Saved Report' for Insights.
    It fetches the same formatted results as the Mixpanel UI for that report.
    Docs: https://developer.mixpanel.com/reference/insights-query
    """
    project_id = st.secrets.get("MIXPANEL_PROJECT_ID")
    mp_user = st.secrets.get("MIXPANEL_USERNAME")
    mp_secret = st.secrets.get("MIXPANEL_SECRET")

    if not (project_id and mp_user and mp_secret and mixpanel_report_id):
        return None, "Mixpanel not fully configured."

    try:
        # Basic auth with service account username + secret
        # Endpoint for Query Saved Report (Insights)
        url = "https://mixpanel.com/api/query/insights"
        params = {
            "project_id": project_id,
            "bookmark_id": mixpanel_report_id,
        }
        resp = requests.get(url, params=params, auth=(mp_user, mp_secret))
        if resp.status_code != 200:
            return None, f"Mixpanel API error: {resp.status_code} {resp.text[:200]}"

        data = resp.json()

        # We expect 'series' to contain metric names and time series values.
        # Example structure (simplified):
        # {
        #   "computed_at": "...",
        #   "date_range": {"from_date": "2025-11-01", "to_date": "2025-11-07"},
        #   "series": {
        #       "Total signups": {
        #           "2025-11-01T00:00:00-07:00": 100,
        #           "2025-11-02T00:00:00-07:00": 120,
        #           ...
        #       }
        #   }
        # }
        # We'll extract the latest value and previous value for the first metric.
        series = data.get("series") or {}
        if not series:
            return None, "Mixpanel API returned no series data."

        metric_name = list(series.keys())[0]
        timeseries = series[metric_name]

        # Sort by date key
        # Keys are ISO timestamps, we'll sort lexicographically
        sorted_points = sorted(timeseries.items(), key=lambda x: x[0])
        latest_date_str, latest_value = sorted_points[-1]
        prev_date_str, prev_value = (sorted_points[-2] if len(sorted_points) > 1 else (None, None))

        # Simplify date to YYYY-MM-DD for display
        def simplify_date(ts):
            try:
                return ts.split("T")[0]
            except Exception:
                return ts

        latest_date = simplify_date(latest_date_str)
        prev_date = simplify_date(prev_date_str) if prev_date_str else None

        summary_text = f"The metric **{metric_name}** from your saved Mixpanel report is **{latest_value}** on **{latest_date}**."
        if prev_value is not None:
            diff = latest_value - prev_value
            direction = "increased" if diff > 0 else "decreased" if diff < 0 else "stayed flat"
            summary_text += f" It has {direction} compared to **{prev_value}** on **{prev_date}**."

        return {
            "metric_name": metric_name,
            "latest_value": latest_value,
            "latest_date": latest_date,
            "prev_value": prev_value,
            "prev_date": prev_date,
            "plain_summary": summary_text,
        }, None

    except Exception as e:
        return None, f"Error calling Mixpanel: {e}"

if st.button("Ask Copilot"):
    if not question:
        st.warning("Please enter a question.")
    else:
        with st.spinner("Thinking..."):

            # 1) Try Mixpanel (if configured)
            mixpanel_info = None
            mixpanel_error = None

            if mixpanel_report_id:
                mixpanel_info, mixpanel_error = call_mixpanel_insights()

            # 2) Build prompt for GPT
            if mixpanel_info:
                # Use REAL data in the prompt
                real_data_snippet = mixpanel_info["plain_summary"]
            else:
                real_data_snippet = "No live Mixpanel numbers are available. Answer based on general analytics reasoning."

            prompt = f"""
            You are an analytics copilot for dashboards.

            The user shared this dashboard link:
            {dashboard_link}

            The question is:
            {question}

            Live data from Mixpanel (if any):
            {real_data_snippet}

            INSTRUCTIONS:
            - Answer in 1–3 short sentences.
            - If Mixpanel numbers are present above, use them directly and clearly.
            - If not, give a helpful, high-level analytical insight and tell the user to check the dashboard for exact numbers.
            - Always reference the dashboard link as the source.
            - Avoid any personal data or PII.
            """

            # 3) Call GPT
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
            )

            answer = response.choices[0].message.content
            st.success(answer)

            # Show raw Mixpanel info for debugging/demo (optional)
            if mixpanel_error:
                st.info(f"Mixpanel note: {mixpanel_error}")
            elif mixpanel_info:
                with st.expander("Show raw Mixpanel summary"):
                    st.write(mixpanel_info)

