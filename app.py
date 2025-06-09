import os
import streamlit as st
from openai import OpenAI
from notion_client import Client as NotionClient
import dateparser
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
notion_token = os.getenv("NOTION_TOKEN")
notion_database_id = os.getenv("NOTION_DATABASE_ID")

# Initialize clients
client = OpenAI(api_key=openai_api_key)
notion = NotionClient(auth=notion_token)

st.title("Notion & ChatGPT Task App")

user_input = st.text_input("Describe your task")

if user_input:
    prompt = f"""You are helping someone break down their task entry into Notion. 
    Given this input: "{user_input}", return exactly:
    1. 6 title suggestions for the task.
    2. 6 GTD context suggestions, like Computer, Home, Phone, etc. (no @ symbols).
    3. If any due date or time is mentioned, extract it clearly in natural language (like 'today at 9pm', 'in two days', etc.).

    Format:
    {{
        "titles": ["..."],
        "contexts": ["..."],
        "due": "..."
    }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        reply = response.choices[0].message.content
        parsed = eval(reply)  # assuming GPT returns safe Python-like JSON
        titles = parsed.get("titles", [])
        contexts = parsed.get("contexts", [])
        due_natural = parsed.get("due", "")

        selected_title = st.selectbox("Choose a task title", titles)
        selected_contexts = st.multiselect("Select GTD contexts", contexts)

        # Date parsing
        due_datetime = None
        if due_natural:
            due_datetime = dateparser.parse(due_natural)
        if due_datetime:
            selected_date = st.date_input("Due Date", value=due_datetime.date())
            selected_time = st.time_input("Due Time", value=due_datetime.time())
        else:
            selected_date = st.date_input("Due Date")
            selected_time = st.time_input("Due Time")

        if st.button("Create Task in Notion"):
            notion.pages.create(
                parent={"database_id": notion_database_id},
                properties={
                    "Name": {"title": [{"text": {"content": selected_title}}]},
                    "GTD Context": {"multi_select": [{"name": ctx} for ctx in selected_contexts]},
                    "Due": {
                        "date": {
                            "start": f"{selected_date}T{selected_time}"
                        }
                    },
                }
            )
            st.success("Task added to Notion!")
    except Exception as e:
        st.error("Failed to parse GPT response. Please try again.")
        st.text(str(e))
