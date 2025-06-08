import os
import json
import re
import streamlit as st
import dateparser
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.title("Notion & ChatGPT Task App")
st.write("Describe your task in natural language. GPT will suggest task titles and GTD contexts.")

# --- Task input and auto-trigger on input change ---
if "user_input" not in st.session_state:
    st.session_state.user_input = ""

new_input = st.text_input("What task do you want to add?", value=st.session_state.user_input, key="task_input")

if new_input.strip() and new_input != st.session_state.user_input:
    st.session_state.user_input = new_input
    for key in [
        "titles", "contexts", "due_date",
        "selected_title", "selected_context",
        "final_title", "final_context", "options_generated"
    ]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

# --- Generate GPT options ---
if st.session_state.user_input and "options_generated" not in st.session_state:
    prompt = f"""
You are a task assistant using the GTD method. Based on this input:

\"{st.session_state.user_input}\"

Respond only with a JSON object like this:

{{
  "titles": ["title 1", "title 2", "title 3", "title 4", "title 5", "title 6"],
  "contexts": ["context 1", "context 2", "context 3", "context 4", "context 5", "context 6"],
  "due_date": "next Friday"
}}

- Titles should be short and distinct
- Contexts must be GTD-style categories (like Computer, Phone, Errands — no @ symbols)
- Return exactly 6 distinct suggestions for both titles and contexts
- Leave due_date empty if none mentioned
- Respond with valid JSON only
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.choices[0].message.content.strip()
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found.")

        data = json.loads(match.group(0))
        st.session_state.titles = data.get("titles", [])
        st.session_state.contexts = data.get("contexts", [])
        st.session_state.due_date = data.get("due_date", "")
        st.session_state.options_generated = True

    except Exception as e:
        st.error("GPT response error.")
        st.text(str(e))

# --- UI for selecting/editing task properties ---
if st.session_state.get("options_generated", False):
    st.subheader("Choose and Customize")

    title_choice = st.selectbox("Choose a task title", st.session_state.titles, key="title_select")
    if st.button("Confirm this title"):
        st.session_state.selected_title = title_choice

    editable_title = st.text_input(
        "Edit task title",
        value=st.session_state.get("selected_title", st.session_state.titles[0]),
        key="final_title"
    )

    context_choice = st.selectbox("Choose a GTD context", st.session_state.contexts, key="context_select")
    if st.button("Confirm this context"):
        st.session_state.selected_context = context_choice

    editable_context = st.text_input(
        "Edit GTD context",
        value=st.session_state.get("selected_context", st.session_state.contexts[0]),
        key="final_context"
    )

    # --- Due date parsing ---
    due_input = st.text_input("Due date (e.g., 'tomorrow at 5pm')", value=st.session_state.get("due_date", ""), key="final_due")
    parsed_due = dateparser.parse(due_input)

    if parsed_due:
        input_lower = due_input.lower()
        has_time = any(x in input_lower for x in ["am", "pm", ":", "morning", "evening", "noon", "night"])
        if has_time:
            formatted_due = parsed_due.strftime("%Y-%m-%d %H:%M")
        else:
            formatted_due = parsed_due.strftime("%Y-%m-%d")
    else:
        formatted_due = due_input

    st.markdown("### Final Task Preview")
    st.write(f"**Title:** {editable_title}")
    st.write(f"**Context:** {editable_context}")
    st.write(f"**Due Date:** {formatted_due}")
