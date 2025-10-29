import os
import json
import re
from datetime import datetime, timedelta
from dateutil import parser
from pymongo import MongoClient
from openai import OpenAI
from db_connection import db, workout_col
from dotenv import load_dotenv

load_dotenv()

client_deepseek = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

MODEL_NAME = "deepseek/deepseek-chat-v3.1:free"

EXTRA_HEADERS = {
    "HTTP-Referer": os.environ.get("SITE_URL", "http://localhost"),
    "X-Title": os.environ.get("SITE_NAME", "MongoDB Workout Query System")
}


# ----------- ENTITY EXTRACTION -----------

def extract_workout_query_entities(user_input):
    prompt = f"""
You are a precise information extractor for a fitness tracking assistant.
Extract the following from the user input:

1. intent — choose from ["daily_workout", "weekly_summary", "exercise_details", "other"]
2. start_date — in ISO format (YYYY-MM-DD) if mentioned and this is the start date, else null
3. end_date — in ISO format (YYYY-MM-DD) if mentioned and this is the end date, else null
4. exercise — if any specific exercise is mentioned, else null

User input: "{user_input}"

Respond ONLY in JSON like this:
{{
  "intent": "daily_workout",
  "start_date": "2025-10-13",
  "end_date": "2025-10-21",
  "exercise": "bench press"
}}
"""
    try:
        response = client_deepseek.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You extract structured data from text."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )

        text = response.choices[0].message.content.strip()
        json_match = re.search(r'\{[\s\S]*\}', text)
        if not json_match:
            raise ValueError("No JSON object found in model output.")

        clean_text = json_match.group(0)
        data = json.loads(clean_text)
        return data

    except Exception as e:
        print(f"❌ Extraction error: {e}")
        return {"intent": "daily_workout", "start_date": None, "end_date": None, "exercise": None}


# ----------- QUERY TEMPLATES -----------

WORKOUT_QUERY_TEMPLATES = {
    "daily_workout": lambda date, user_id: {
        "collection": "workouts_logs",
        "filter": {"user_id": user_id, "date": date},
        "projection": {
            "workout_data.exercise_name": 1,
            "workout_data.muscle_group": 1,
            "workout_data.sets": 1,
            "workout_data.reps": 1,
            "workout_data.weight": 1,
            "workout_data.duration_minutes": 1,
            "workout_data.calories_burned": 1,
            "summary": 1,
            "_id": 0
        }
    },

    "weekly_summary": lambda start_date, end_date, user_id: {
        "collection": "workouts_logs",
        "filter": {"user_id": user_id, "date": {"$gte": start_date, "$lte": end_date}},
        "projection": {"date": 1, "summary": 1, "_id": 0}
    },

    "exercise_details": lambda exercise_name, user_id: {
        "collection": "workouts_logs",
        "filter": {
            "user_id": user_id,
            "workout_data.exercise_name": {"$regex": exercise_name, "$options": "i"}
        },
        "projection": {
            "date": 1,
            "workout_data.$": 1,
            "summary.total_calories_burned": 1,
            "_id": 0
        }
    },
}


# ----------- DATE UTIL -----------

def get_week_range_from_date(date_str):
    dt = datetime.fromisoformat(date_str)
    start = dt - timedelta(days=dt.weekday())
    end = start + timedelta(days=6)
    return start.isoformat(), end.isoformat()


# ----------- QUERY BUILDER -----------

def build_workout_query(user_input, user_id):
    entities = extract_workout_query_entities(user_input)
    intent = entities.get("intent", "daily_workout")
    start_date = entities.get("start_date")
    end_date = entities.get("end_date")
    exercise = entities.get("exercise")

    if intent == "daily_workout":
        date = start_date or datetime.now().date().isoformat()
        return WORKOUT_QUERY_TEMPLATES[intent](date, user_id)

    elif intent == "weekly_summary":
        if not start_date or not end_date:
            end_date = datetime.now().date().isoformat()
            start_date = (datetime.now().date() - timedelta(days=6)).isoformat()
        return WORKOUT_QUERY_TEMPLATES[intent](start_date, end_date, user_id)

    elif intent == "exercise_details":
        if not exercise:
            print("⚠️ No exercise detected, defaulting to all exercises.")
            exercise = ""
        return WORKOUT_QUERY_TEMPLATES[intent](exercise, user_id)

    else:
        date = start_date or datetime.now().date().isoformat()
        return WORKOUT_QUERY_TEMPLATES["daily_workout"](date, user_id)


# ----------- QUERY EXECUTION -----------

def execute_workout_query(query_json):
    try:
        if isinstance(query_json, str):
            query_json = json.loads(query_json)

        collection_name = query_json.get("collection", "workout_logs")
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

        elif isinstance(query_json, dict):
            results = list(collection.find(query_json))
            return results

        else:
            print("⚠️ Unsupported query format, returning empty result.")
            return []

    except Exception as e:
        print(f"❌ Query execution error: {str(e)}")
        return []


# ----------- RESPONSE FORMATTING -----------

def format_workout_response(user_input, query_data):
    if not query_data:
        return "No workout records found for that date."

    try:
        safe_data = json.loads(json.dumps(query_data, default=str))
        prompt = f"""
You are a helpful fitness assistant.
The user asked: "{user_input}"

Here is the retrieved data from MongoDB:
{json.dumps(safe_data, indent=2)}

Format this into a clear, readable workout summary for the user.
- List exercises, sets, reps, weights, calories burned, and any daily or weekly totals.
- Highlight workout volume and intensity.
- Be concise but informative.
"""
        messages = [
            {"role": "system", "content": "You are a helpful and precise fitness assistant."},
            {"role": "user", "content": prompt}
        ]

        response = client_deepseek.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.2,
            extra_headers=EXTRA_HEADERS
        )

        formatted_response = response.choices[0].message.content.strip() if response and response.choices else "No response generated."
        return formatted_response

    except Exception as e:
        print(f"❌ Formatting error: {str(e)}")
        return "An error occurred while formatting the response."


# ----------- MAIN TEST -----------

if __name__ == "__main__":
    user_id = "u001"
    user_input = "show my chest workouts today"
    query = build_workout_query(user_input, user_id)
    print("Generated Query:", query)
    results = execute_workout_query(query)
    print("Result:", results)
    print(format_workout_response(user_input, results))
