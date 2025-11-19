import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="Analytics Copilot Demo")

st.title("📊 Analytics Copilot — Demo")
st.caption("Paste a dashboard link and ask a question. This is a simple text-only demo.")

# Inputs from user
dashboard_link = st.text_input(
    "Dashboard link",
    placeholder="Paste your Mixpanel (or any) dashboard link here..."
)

question = st.text_area(
    "Your question",
    placeholder="Example: What was signup conversion last week in Bangalore?"
)

# Create OpenAI client using secret (we'll set it in Streamlit Cloud)
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

if st.button("Ask Copilot"):
    if not question:
        st.warning("Please enter a question.")
    else:
        with st.spinner("Thinking..."):
            prompt = f"""
            You are an analytics copilot.

            The user is asking about this dashboard:
            {dashboard_link}

            QUESTION:
            {question}

            INSTRUCTIONS:
            - Answer in 1–2 short sentences.
            - If you don't know exact numbers, give a helpful, high-level analytical insight.
            - Always reference the dashboard link as the source.
            - Do not invent very specific numbers unless they are obvious from the question.
            - Avoid any personal data or PII.
            """

            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
            )

            answer = response.choices[0].message.content
            st.success(answer)
