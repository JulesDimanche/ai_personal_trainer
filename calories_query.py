import os
import json
import ast
import re
from datetime import datetime, timedelta
from dateutil import parser
from pymongo import MongoClient
from openai import OpenAI
from db_connection import db, diet_col
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

def extract_query_entities(user_input):
    prompt = f"""
You are a precise information extractor for a nutrition tracking assistant.
Extract the following from the user input:

1. intent — choose from ["daily_food", "weekly_summary", "food_details", "other"]
2. start_date — in ISO format (YYYY-MM-DD) if mentioned and this is the start date, else null
3. end_date — in ISO format (YYYY-MM-DD) if mentioned and this is the end date, else null
4. food — if any specific food item is mentioned, else null

User input: "{user_input}"

Respond ONLY in JSON like this:
{{
  "intent": "daily_food",
  "start_date": "2025-10-13",
  "end_date": "2025-10-21",
  "food": "banana"
}}
"""

    try:
        response = client_deepseek.chat.completions.create(
            model=MODEL_NAME,  
            messages=[{"role": "system", "content": "You extract structured data from text."},
                      {"role": "user", "content": prompt}],
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
        return {"intent": "daily_food", "start_date": None,"end_date":None, "food": None}


QUERY_TEMPLATES = {
    "daily_food": lambda date, user_id: {
        "collection": "diet_logs",
        "filter": {"user_id": user_id, "date": date},
        "projection": {
            "plan_data.meal_type": 1,
            "plan_data.items.food": 1,
            "plan_data.items.quantity": 1,
            "plan_data.items.weight": 1,
            "plan_data.items.calories": 1,
            "plan_data.items.proteins": 1,
            "plan_data.items.fats": 1,
            "plan_data.items.carbs": 1,
            "_id": 0
        }
    },
    "weekly_summary": lambda start_date, end_date, user_id: {
        "collection": "diet_logs",
        "filter": {"user_id": user_id, "date": {"$gte": start_date, "$lte": end_date}},
        "projection": {"plan_data.items.food": 1,
            "plan_data.items.weight": 1,
            "plan_data.items.calories": 1, "date": 1, "_id": 0}
    },
    "food_details": lambda food_name, user_id: {
        "collection": "diet_logs",
        "filter": {
            "user_id": user_id,
            "plan_data.items.food": {"$regex": food_name, "$options": "i"}
        },
        "projection": {
            "date": 1,
            "plan_data.meal_type": 1,
            "plan_data.items.$": 1, 
            "_id": 0
        }
    },
}
    
def get_week_range_from_date(date_str):
    dt = datetime.fromisoformat(date_str)
    start = dt - timedelta(days=dt.weekday())     
    end = start + timedelta(days=6)               
    return start.isoformat(), end.isoformat()

def build_query(user_input, user_id):

    entities = extract_query_entities(user_input)
    intent = entities.get("intent", "daily_food")
    start_date = entities.get("start_date")
    end_date = entities.get("end_date")
    food_name = entities.get("food")

    if intent == "daily_food":
        date = start_date or datetime.now().date().isoformat()
        return QUERY_TEMPLATES[intent](date, user_id)

    elif intent == "weekly_summary":
        if start_date and end_date:
            pass
        elif not start_date and not end_date:
            end_date = end_date or datetime.now().date().isoformat()
            start_date = start_date or (datetime.now().date()-timedelta(days=30)).isoformat()
        else:
            start_date, end_date = get_week_range_from_date(start_date)
        return QUERY_TEMPLATES[intent](start_date, end_date, user_id)

    elif intent == "food_details":
        if not food_name:
            print("⚠️ No food detected, defaulting to all food items.")
            food_name = ""
        return QUERY_TEMPLATES[intent](food_name, user_id)

    else:
        date = start_date or datetime.now().date().isoformat()
        return QUERY_TEMPLATES["daily_food"](date, user_id)

def execute_query(query_json):
    try:
        if isinstance(query_json, str):
            query_json = json.loads(query_json)

        collection_name = query_json.get("collection", "diet_logs")
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

def format_response(user_input, query_data):
    if not query_data:
        return "No food intake records found for that date."
    try:
        safe_data=json.loads(json.dumps(query_data,default=str))
        prompt=f"""You are a helpful nutrition assistant.
        The user asked: "{user_input}"

        Here is the retrieved data from MongoDB:
        {json.dumps(safe_data, indent=2)}

        Format the data into a clear, human-readable summary relevant to the user's question.
        Use bullet points appropriate.
        Be concise but complete. Mention food, quantities, calories, and any patterns or insights.
"""
        messages = [
            {"role": "system", "content":"You are a helpful and precise nutrition assistant." },
            {"role":"user","content":prompt}]
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
    

if __name__ == "__main__":
    user_id='u001'
    user_input = "what foods i intake most often?"
    query = build_query(user_input,user_id)
    print("Generated Query:", query)
    results = execute_query(query)
    print('the result is: ',results)
    print(format_response(user_input, results))