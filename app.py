import streamlit as st
import os
import requests
from datetime import datetime
import dateparser
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

st.title("Notion & ChatGPT Task APP")

# Task input
user_input = st.text_input("Describe your task (e.g., 'Eat dinner today at 9pm'):")

# Function to extract date and time
def extract_datetime(text):
    parsed = dateparser.parse(text)
    if parsed:
        date_str = parsed.date().isoformat()
        time_str = parsed.strftime("%H:%M") if parsed.time() != datetime.min.time() else ""
        return date_str, time_str
    return None, None

# Generate suggestions from OpenAI
def get_suggestions(prompt):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that rewrites task titles and GTD-style context labels. Respond only in JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    try:
        raw_output = response.choices[0].message.content
        data = eval(raw_output.strip())  # expected to be a dict with 'titles' and 'contexts'
        return data.get("titles", []), data.get("contexts", [])
    except Exception as e:
        st.error("Failed to parse GPT response")
        return [], []

# Process input
if user_input:
    prompt = f"Generate 6 suggested task titles and 6 GTD-style context tags (like Home, Computer, Errands, Calls) for: '{user_input}'. Return JSON like: {{ \"titles\": [...], \"contexts\": [...] }}"
    titles, contexts = get_suggestions(prompt)

    if titles:
        selected_title = st.selectbox("Select a Task Title:", titles)
    else:
        selected_title = st.text_input("Manually enter task title:")

    if contexts:
        selected_contexts = st.multiselect("Select one or more GTD Contexts:", contexts)
    else:
        selected_contexts = st.multiselect("Manually enter GTD Contexts:", [])

    # Date & Time Handling
    default_date, default_time = extract_datetime(user_input)

    due_date = st.date_input("Due Date:", value=datetime.strptime(default_date, "%Y-%m-%d") if default_date else None)
    due_time = st.time_input("Time (optional):", value=datetime.strptime(default_time, "%H:%M").time() if default_time else datetime.now().time()) if default_time else None

    # Submit to Notion
    if st.button("Add Task to Notion"):
        headers = {
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }

        # Build the payload
        properties = {
            "Name": {
                "title": [{"text": {"content": selected_title}}]
            },
            "Context": {
                "multi_select": [{"name": c} for c in selected_contexts]
            },
            "Due": {
                "date": {
                    "start": f"{due_date}T{due_time.strftime('%H:%M:%S')}" if due_time else f"{due_date}"
                }
            }
        }

        payload = {
            "parent": {"database_id": NOTION_DATABASE_ID},
            "properties": properties
        }

        response = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload)

        if response.status_code == 200:
            st.success("Task added to Notion successfully!")
        else:
            st.error(f"Failed to add task: {response.text}")
