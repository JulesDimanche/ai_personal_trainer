import os
import json
import re
from datetime import datetime, timedelta
from dateutil import parser
from pymongo import MongoClient
from openai import OpenAI
from db_connection import db
from dotenv import load_dotenv

load_dotenv()

client_deepseek = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

MODEL_NAME = "deepseek/deepseek-chat-v3.1:free"

EXTRA_HEADERS = {
    "HTTP-Referer": os.environ.get("SITE_URL", "http://localhost"),
    "X-Title": os.environ.get("SITE_NAME", "MongoDB Query System")
}


def extract_macros_query_entities(user_input):
    prompt = f"""
You are a precise information extractor for a fitness tracking assistant.
Extract the following details from the user input related to macros or nutrition:

1. intent — choose from:
   - "day" → if the user asks for a specific date or week (e.g., "show macros for 2025-11-17" or "this week macros")
   - "full_details" → if the user asks for overall or complete macros data (e.g., "show my macros plan", "full macro details")

2. start_date — in ISO format (YYYY-MM-DD) if a date or start date is mentioned in the user input; otherwise null.

User input: "{user_input}"

Respond ONLY in valid JSON like this:
{{
  "intent": "day",
  "start_date": "2025-11-10"
}}
"""

    try:
        response = client_deepseek.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You extract structured data from text precisely and output valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
        )

        text = response.choices[0].message.content.strip()
        json_match = re.search(r'\{[\s\S]*\}', text)
        if not json_match:
            raise ValueError("No JSON object found in model output.")

        clean_text = json_match.group(0)
        data = json.loads(clean_text)

        # Normalize fields
        intent = data.get("intent", "full_details")
        start_date = data.get("start_date")

        return {"intent": intent, "start_date": start_date}

    except Exception as e:
        print(f"❌ Extraction error: {e}")
        return {"intent": "full_details", "start_date": None}


def build_macros_query(user_input, user_id):
    entities = extract_macros_query_entities(user_input)
    start_date = entities.get("start_date")

    base_query = {"collection": "macro_plans", "filter": {"user_id": user_id}}

    if start_date:
        base_query["filter"]["Weekly_Plan"] = {"$elemMatch": {"start_date": start_date}}
        base_query["projection"] = {
            "Weekly_Plan.$": 1,  
            "user_id": 1,
            "_id": 0
    }
    else:
        base_query["projection"] = {
            "user_id": 1,
            "BMR": 1,
            "TDEE": 1,
            "Goal_Calories": 1,
            "goal_type": 1,
            "start_weight_kg": 1,
            "target_weight_kg": 1,
            "Macros": 1,
            "Weekly_Plan": 1,
            "_id": 0
        }

    return base_query


def execute_macros_query(query_json):
    try:
        if isinstance(query_json, str):
            query_json = json.loads(query_json)

        collection_name = query_json.get("collection", "macro_plans")
        collection = db[collection_name]

        mongo_filter = query_json.get("filter", {})
        projection = query_json.get("projection", None)
        results = list(collection.find(mongo_filter, projection))
        return results

    except Exception as e:
        print(f"❌ Query execution error: {str(e)}")
        return []



def format_macros_response(user_input, query_data):
    if not query_data:
        return "No macros details found for that date."

    try:
        data = json.loads(json.dumps(query_data, default=str))
        prompt = f"""
The user asked: "{user_input}"

Here is the data from MongoDB:
{json.dumps(data, indent=2)}

Generate a clear, human-readable summary of the macros information.
- If it's a specific week, show expected calories, protein, carbs, fats, and fiber.
- If it's the full plan, summarize BMR, TDEE, goal calories, target weights, and weekly breakdown.
Keep it concise and readable.
"""
        response = client_deepseek.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful nutrition assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            extra_headers=EXTRA_HEADERS
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"❌ Formatting error: {str(e)}")
        return "An error occurred while formatting the macros response."

if __name__ == "__main__":
    user_id = "u002"
    user_input = "give me my macros"
    query = build_macros_query(user_input, user_id)
    print("Generated Query:", query)
    results = execute_macros_query(query)
    print("Result:", results)
    print(format_macros_response(user_input, results))
