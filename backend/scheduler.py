import openai
import os
import json
from datetime import datetime

openai.api_key = os.getenv("OPENAI_API_KEY")

def default_serializer(obj):
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def generate_ai_schedule(availabilities):
    prompt = (
        "You are an AI scheduling assistant. Given a list of employee availabilities, "
        "generate an optimal schedule that distributes shifts fairly across the week.\n\n"
        "Return the result in this exact JSON format:\n"
        "{\n"
        "  \"schedule\": [\n"
        "    {\n"
        "      \"name\": \"John Doe\",\n"
        "      \"availability\": \"9 AM - 5 PM\",\n"
        "      \"date\": \"2025-03-25\"\n"
        "    },\n"
        "    ...\n"
        "  ]\n"
        "}\n\n"
        "Here is the employee availability data:\n"
        f"{json.dumps(availabilities, default=default_serializer)}\n\n"
        "Return ONLY the JSON. Do not include explanations or markdown formatting."
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
