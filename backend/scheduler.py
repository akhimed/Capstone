import openai
import os
import json
from datetime import datetime, timedelta

openai.api_key = os.getenv("OPENAI_API_KEY")

def default_serializer(obj):
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def get_next_two_weeks_dates():
    today = datetime.today()
    # Start from this week's Monday
    start_of_week = today - timedelta(days=today.weekday())
    # Generate 14 days (2 weeks) starting from this week's Monday
    return [(start_of_week + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(14)]

def generate_ai_schedule(availabilities):
    date_range = get_next_two_weeks_dates()
    formatted_dates = ", ".join(date_range)

    prompt = (
        "You are an AI scheduling assistant. You will receive a list of employee availabilities. "
        "Your task is to generate an optimized work schedule for ONLY the current and next week (14 total days). "
        f"The only valid dates for scheduling are:\n{formatted_dates}.\n"
        "The schedule MUST contain at least one shift for each of the 14 dates listed.\n"
        "❗Do not generate shifts for any dates outside this list.\n"
        "Distribute shifts fairly, but do not invent additional days or employee names.\n\n"
        "Return the output ONLY in the following strict JSON format:\n"
        "{\n"
        "  \"schedule\": [\n"
        "    {\n"
        "      \"name\": \"John Doe\",\n"
        "      \"availability\": \"9 AM - 5 PM\",\n"
        "      \"date\": \"2025-04-03\"\n"
        "    },\n"
        "    ...\n"
        "  ]\n"
        "}\n\n"
        "Here is the employee availability data:\n"
        f"{json.dumps(availabilities, default=default_serializer)}\n\n"
        "Return ONLY the JSON response. Do NOT include any additional text, explanation, or markdown."
    )


    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that outputs weekly employee schedules in JSON."},
            {"role": "user", "content": prompt}
        ]
    )

    content = response["choices"][0]["message"]["content"]

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        print("AI returned invalid JSON:")
        print(content)
        return {"error": "Invalid AI output"}
