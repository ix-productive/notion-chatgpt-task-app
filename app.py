import os
import json
import streamlit as st
import dateparser
from openai import OpenAI
from notion_client import Client as NotionClient
from datetime import datetime

# Load environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")
notion_token = os.getenv("NOTION_TOKEN")
notion_database_id = os.getenv("NOTION_DATABASE_ID")

client = OpenAI(api_key=openai_api_key)
notion = NotionClient(auth=notion_token)

st.set_page_config(page_title="Task Entry Assistant", layout="centered")

st.title("Task Entry Assistant")

# --- Task input ---
user_input = st.text_input("Describe your task in natural language:")

if user_input:
    with st.spinner("Generating task suggestions..."):
        prompt = f"""
You are a task assistant helping extract task metadata from natural language input.

Given the input: "{user_input}"

Return ONLY a valid JSON with the following fields:
- "title": A short, clear task title
- "contexts": A list of relevant GTD contexts (like @Computer, @Errands, @Work, etc)
- "goal": The purpose/desired outcome (optional, can be null)
- "status": One of ["Backlog", "Next", "In Progress", "Waiting", "Done"]
- "project": Project name if any (optional, can be null)
- "due_date": Full ISO 8601 date string if any (e.g., "2025-06-08T21:00:00") or null

Respond ONLY with the JSON object. Example:

{{
  "title": "Eat dinner",
  "contexts": ["@Home", "@Evening"],
  "goal": null,
  "status": "Next",
  "project": null,
  "due_date": "2025-06-08T21:00:00"
}}
"""
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            raw = response.choices[0].message.content.strip()
            data = json.loads(raw)

            st.success("Suggestions loaded. You can edit before saving:")

            task_title = st.text_input("Task Title", value=data["title"])
            contexts = st.multiselect("GTD Contexts", options=[
                "@Computer", "@Phone", "@Errands", "@Home", "@Work", "@Evening", "@Weekend", "@Waiting"
            ], default=data.get("contexts", []))
            goal = st.text_input("Goal (optional)", value=data.get("goal") or "")
            status = st.selectbox("Status", ["Backlog", "Next", "In Progress", "Waiting", "Done"], index=["Backlog", "Next", "In Progress", "Waiting", "Done"].index(data["status"]))
            project = st.text_input("Project (optional)", value=data.get("project") or "")

            due_date_str = data.get("due_date")
            if due_date_str:
                due_date = datetime.fromisoformat(due_date_str)
            else:
                due_date = None
            due_date_input = st.date_input("Due Date", value=due_date.date() if due_date else None)
            time_input = st.time_input("Due Time", value=due_date.time() if due_date else datetime.now().time())

            if st.button("Save to Notion"):
                full_dt = datetime.combine(due_date_input, time_input)

                notion.pages.create(
                    parent={"database_id": notion_database_id},
                    properties={
                        "Name": {"title": [{"text": {"content": task_title}}]},
                        "Contexts": {"multi_select": [{"name": ctx} for ctx in contexts]},
                        "Goal": {"rich_text": [{"text": {"content": goal}}]} if goal else {},
                        "Status": {"select": {"name": status}},
                        "Project": {"rich_text": [{"text": {"content": project}}]} if project else {},
                        "Due": {"date": {"start": full_dt.isoformat()}}
                    }
                )
                st.success("Task saved to Notion.")

        except json.JSONDecodeError:
            st.error("Failed to parse GPT response. Please try again.")
        except Exception as e:
            st.error(f"Unexpected error: {e}")
