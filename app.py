import json
from openai import OpenAIError

def parse_task_details(user_input):
    system_prompt = (
        "You're an intelligent task parser. Extract the following fields from the user's task input:\n"
        "- title (a short task title)\n"
        "- contexts (a list of GTD-style contexts like phone, computer, errands — no @ symbol)\n"
        "- date (if provided, e.g., today, June 9, etc.)\n"
        "- time (if specified, e.g., 9pm, 14:00)\n\n"
        "Return your result strictly as a JSON object with these keys: title, contexts, date, time.\n"
        "Do NOT return anything else outside the JSON."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0
        )

        raw_output = response.choices[0].message.content.strip()

        # Try parsing the JSON output
        parsed = json.loads(raw_output)
        return parsed

    except json.JSONDecodeError:
        st.error("Failed to parse GPT response. Make sure the format is correct.")
        return None
    except OpenAIError as e:
        st.error(f"OpenAI Error: {e}")
        return None
