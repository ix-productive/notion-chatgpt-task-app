import streamlit as st
import os
import json
from openai import OpenAI
from notion_client import Client as NotionClient
import dateparser

# Load environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")
notion_token = os.getenv("NOTION_TOKEN")
database_id = os.getenv("NOTION_DATABASE_ID")

client = OpenAI(api_key=openai_api_key)
notion = NotionClient(auth=notion_token)

st.set_page_config(page_title="Notion Task Creator", layout="centered")
st.title("Create Task from Natural Language")

user_input = st.text_area("Describe your task:")

def parse_task_details(text):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a task assistant. Extract a clear task title, "
                    "up to 3 GTD context tags (no @ symbols), and any date/time from natural language input. "
                    "Respond ONLY in valid JSON format with keys: title, contexts (list), date (optional), time (optional)."
                )
            },
            {"role": "user", "content": text}
        ],
        response_format="json"
    )
    try:
        parsed = json.loads(response.choices[0].message.content)
        return parsed
    except Exception:
        return None

if user_input:
    parsed = parse_task_details(user_input)
    if parsed:
        title = st.text_input("Task Title", parsed.get("title", ""))
        contexts = st.multiselect(
            "GTD Contexts",
            options=[
                "Home", "Work", "Phone", "Computer", "Errands",
                "Agenda", "Waiting", "Someday", "Anywhere"
            ],
            default=parsed.get("contexts", [])
        )

        date_str = parsed.get("date", "")
        time_str = parsed.get("time", "")

        if date_str:
            due_date = dateparser.parse(date_str)
            date_input = st.date_input("Due Date", due_date.date() if due_date else None)
        else:
            date_input = st.date_input("Due Date")

        if time_str:
            due_time = dateparser.parse(time_str)
            time_input = st.time_input("Due Time", due_time.time() if due_time else None)
        else:
            time_input = st.time_input("Due Time")

        status = st.selectbox("Status", ["Backlog", "Next", "In Progress", "Waiting", "Done"])
        project = st.text_input("Project")

        if st.button("Add to Notion"):
            try:
                properties = {
                    "Name": {"title": [{"text": {"content": title}}]},
                    "Context": {"multi_select": [{"name": ctx} for ctx in contexts]},
                    "Status": {"select": {"name": status}},
                    "Project": {"rich_text": [{"text": {"content": project}}]}
                }

                if date_input:
                    date_str = date_input.isoformat()
                    if time_input:
                        date_str += f"T{time_input.strftime('%H:%M:%S')}"
                    properties["Due"] = {"date": {"start": date_str}}

                notion.pages.create(parent={"database_id": database_id}, properties=properties)
                st.success("Task added to Notion.")
            except Exception as e:
                st.error(f"Failed to add task: {str(e)}")
    else:
        st.error("Failed to parse GPT response. Please try again.")
