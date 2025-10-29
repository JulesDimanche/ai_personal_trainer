# weekly_progress_query.py
import os
import json
import re
from datetime import datetime, timedelta
from pymongo import MongoClient
from openai import OpenAI
from db_connection import db
from dotenv import load_dotenv

load_dotenv()

# --------------------------------------------------------------------
# MODEL SETUP
# --------------------------------------------------------------------
client_deepseek = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

MODEL_NAME = "deepseek/deepseek-chat-v3.1:free"

EXTRA_HEADERS = {
    "HTTP-Referer": os.environ.get("SITE_URL", "http://localhost"),
    "X-Title": os.environ.get("SITE_NAME", "Weekly Progress Query System")
}

weekly_col = db["weekly_progress"]

# --------------------------------------------------------------------
# ENTITY EXTRACTION (LLM)
# --------------------------------------------------------------------
def extract_query_entities(user_input):
    prompt = f"""
You are an intelligent query extractor for a fitness tracking assistant.

From the user's question, extract the following fields in JSON format:
1. intent — choose from ["weekly_summary", "trend", "targets", "adjustments", "weight_change", "other"]
2. start_date — ISO date (YYYY-MM-DD) if mentioned, else null
3. end_date — ISO date (YYYY-MM-DD) if mentioned, else null
4. week_number — integer if mentioned, else null

Example output:
{{
  "intent": "weekly_summary",
  "start_date": "2025-10-06",
  "end_date": "2025-10-12",
  "week_number": 2
}}

User input: "{user_input}"
"""

    try:
        response = client_deepseek.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You extract structured fields from user fitness queries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            extra_headers=EXTRA_HEADERS
        )

        text = response.choices[0].message.content.strip()
        json_match = re.search(r'\{[\s\S]*\}', text)
        if not json_match:
            raise ValueError("No JSON object found in model output.")
        data = json.loads(json_match.group(0))
        return data

    except Exception as e:
        print(f"❌ Extraction error: {e}")
        return {"intent": "weekly_summary", "start_date": None, "end_date": None, "week_number": None}

# --------------------------------------------------------------------
# QUERY TEMPLATES
# --------------------------------------------------------------------
QUERY_TEMPLATES = {
    "weekly_summary": lambda start_date, end_date, user_id: {
        "collection": "weekly_progress",
        "filter": {
            "user_id": user_id,
            **({"start_date": {"$gte": start_date}} if start_date else {}),
            **({"end_date": {"$lte": end_date}} if end_date else {})
        },
        "projection": {
            "start_date": 1,
            "end_date": 1,
            "week_number": 1,
            "average_achieved": 1,
            "adjusted_targets": 1,
            "adjustment_reason": 1,
            "_id": 0
        }
    },

    "targets": lambda user_id: {
        "collection": "weekly_progress",
        "filter": {"user_id": user_id},
        "projection": {
            "week_number": 1,
            "adjusted_targets": 1,
            "_id": 0
        }
    },

    "weight_change": lambda user_id: {
        "collection": "weekly_progress",
        "filter": {"user_id": user_id},
        "projection": {
            "week_number": 1,
            "average_achieved.first_week_weight_kg": 1,
            "average_achieved.last_week_weight_kg": 1,
            "average_achieved.weight_change_kg": 1,
            "_id": 0
        }
    },

    "adjustments": lambda user_id: {
        "collection": "weekly_progress",
        "filter": {"user_id": user_id},
        "projection": {
            "week_number": 1,
            "adjustment_reason": 1,
            "_id": 0
        }
    },

    "trend": lambda user_id: {
        "collection": "weekly_progress",
        "filter": {"user_id": user_id},
        "projection": {
            "week_number": 1,
            "average_achieved.calories": 1,
            "average_achieved.protein_g": 1,
            "average_achieved.carbs_g": 1,
            "average_achieved.fats_g": 1,
            "average_achieved.workout_intensity": 1,
            "_id": 0
        }
    },
}

# --------------------------------------------------------------------
# MAIN QUERY BUILDER
# --------------------------------------------------------------------
def build_query(user_input, user_id):
    entities = extract_query_entities(user_input)
    intent = entities.get("intent", "weekly_summary")
    start_date = entities.get("start_date")
    end_date = entities.get("end_date")
    week_number = entities.get("week_number")

    if intent == "weekly_summary":
        return QUERY_TEMPLATES["weekly_summary"](start_date, end_date, user_id)

    elif intent in QUERY_TEMPLATES:
        return QUERY_TEMPLATES[intent](user_id)

    else:
        return QUERY_TEMPLATES["weekly_summary"](start_date, end_date, user_id)

# --------------------------------------------------------------------
# EXECUTION
# --------------------------------------------------------------------
def execute_query(query_json):
    try:
        if isinstance(query_json, str):
            query_json = json.loads(query_json)

        collection_name = query_json.get("collection", "weekly_progress")
        collection = db[collection_name]

        if "pipeline" in query_json:
            pipeline = query_json["pipeline"]
            results = list(collection.aggregate(pipeline))
            return results

        elif "filter" in query_json:
            mongo_filter = query_json.get("filter", {})
            projection = query_json.get("projection", None)
            results = list(collection.find(mongo_filter, projection))
            return results

        else:
            print("⚠️ Unsupported query format.")
            return []

    except Exception as e:
        print(f"❌ Query execution error: {str(e)}")
        return []

# --------------------------------------------------------------------
# RESPONSE FORMATTING
# --------------------------------------------------------------------
def format_response(user_input, query_data):
    if not query_data:
        return "No weekly progress data found for the requested period."

    try:
        safe_data = json.loads(json.dumps(query_data, default=str))
        prompt = f"""
You are a fitness progress summarizer.
The user asked: "{user_input}"

Here is the weekly progress data from MongoDB:
{json.dumps(safe_data, indent=2)}

Summarize clearly:
- Mention the week range and number.
- Report average calories, macros, and workout intensity.
- Mention any adjustment reasons or weight changes.
Be concise and readable.
"""
        response = client_deepseek.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful fitness assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            extra_headers=EXTRA_HEADERS,
        )
        formatted = response.choices[0].message.content.strip()
        return formatted
    except Exception as e:
        print(f"❌ Formatting error: {str(e)}")
        return "An error occurred while formatting the response."

# --------------------------------------------------------------------
# TEST
# --------------------------------------------------------------------
if __name__ == "__main__":
    user_id = "u001"
    user_input = "show me my weekly summary for the last weeks"
    query = build_query(user_input, user_id)
    print("Generated Query:", query)
    results = execute_query(query)
    print("Results:", results)
    print(format_response(user_input, results))
