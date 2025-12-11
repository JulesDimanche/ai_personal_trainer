import os
import json
import ast
from pymongo import MongoClient
import sys
sys.path.append('..')
from backend.db_connection import db

QUERY_TEMPLATES = {
    "calories": lambda date, user_id: {
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
}
    

def build_query(data, user_id):
    entities=data
    intent = entities.get("intent", "calories")
    start_date = entities.get("start_date")
    end_date = entities.get("end_date")
    food_name = entities.get("food")

    date = start_date or end_date
    return QUERY_TEMPLATES[intent](date, user_id)

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

def format_response(query_data):
    if not query_data:
        return "No food intake records found."

    try:
        safe_data = json.loads(json.dumps(query_data, default=str))

        lines = []
        lines.append("Food Intake Summary:\n")

        for entry in safe_data:
            plan_data = entry.get("plan_data", [])

            for meal in plan_data:
                meal_type = meal.get("meal_type", "Unknown meal")
                items = meal.get("items", [])

                lines.append(f"Meal: {meal_type}")

                for item in items:
                    food = item.get("food", "Unknown")
                    qty = item.get("quantity", "N/A")
                    weight = item.get("weight", "N/A")
                    calories = item.get("calories", "N/A")
                    protein = item.get("proteins", "N/A")
                    fats = item.get("fats", "N/A")
                    carbs = item.get("carbs", "N/A")

                    lines.append(f"- Food: {food} | Qty: {qty} | Weight: {weight}g")
                    lines.append(f"  Calories: {calories} | Protein: {protein}g | Fat: {fats}g | Carbs: {carbs}g")

                lines.append("")
        return "\n".join(lines)

    except Exception as e:
        print(f"Formatting error: {str(e)}")
        return "Formatting error."
def to_toon_compact(data):
    if isinstance(data, dict):
        items = []
        for k, v in data.items():
            items.append(f"{k}:{to_toon_compact(v)}")
        return "(" + ",".join(items) + ")"

    elif isinstance(data, list):
        items = [to_toon_compact(i) for i in data]
        return "[" + ",".join(items) + "]"

    elif isinstance(data, str):
        return f"\"{data}\""

    else:
        return str(data)


if __name__ == "__main__":
    user_id='u001'
    data={'intent': 'calories', 'backend': 'mongo', 'query_text': 'show macros on 2025-10-21', 'start_date': '2025-10-21', 'end_date': '2025-10-21', 'data': None, 'summary': None}
    query = build_query(data,user_id)
    print("Generated Query:", query)
    results = execute_query(query)
    print('the result is: ',results)
    print(to_toon_compact(results))