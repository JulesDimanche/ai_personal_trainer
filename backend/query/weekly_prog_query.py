# weekly_progress_query.py
import os
import json
import re
from pymongo import MongoClient
from backend.db_connection import db

QUERY_TEMPLATES = {
    "weekly_progress": lambda start_date, end_date, user_id: {
        "collection": "weekly_progress",
        "filter": {
            "user_id": user_id,
            **(
            {
                "start_date": {"$lte": end_date},
                "end_date": {"$gte": start_date}
            } if start_date and end_date else
            {
                "end_date": {"$gte": start_date}
            } if start_date else
            {
                "start_date": {"$lte": end_date}
            } if end_date else
            {})
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

def build_query(user_input, user_id):
    entities=user_input
    start_date = entities.get("start_date")
    end_date = entities.get("end_date")
    week_number = entities.get("week_number")

    return QUERY_TEMPLATES["weekly_progress"](start_date, end_date, user_id)

    
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
    
def format_response(query_data):
    if not query_data:
        return "No weekly adjustment data found."

    try:
        data = json.loads(json.dumps(query_data, default=str))
        lines = []
        lines.append("Weekly Adjustment Summary:\n")

        for week in data:
            week_num = week.get("week_number", "N/A")
            start = week.get("start_date", "N/A")
            end = week.get("end_date", "N/A")

            lines.append(f"Week {week_num}: {start} to {end}\n")

            adj = week.get("adjusted_targets", {})
            macros = adj.get("daily_macros", {})

            lines.append("Adjusted Targets:")
            lines.append(f"- Daily Calories: {adj.get('daily_calories', 'N/A')}")
            lines.append(
                f"- Macros: Protein {macros.get('protein_g','N/A')}g | "
                f"Carbs {macros.get('carbs_g','N/A')}g | "
                f"Fats {macros.get('fats_g','N/A')}g"
            )
            lines.append(f"- Workout Intensity: {adj.get('workout_intensity', 'N/A')}")
            lines.append(f"- Target Weight: {adj.get('target_weight_kg', 'N/A')} kg\n")

            achieved = week.get("average_achieved", {})

            lines.append("Average Achieved:")
            lines.append(f"- Calories: {achieved.get('calories', 'N/A')}")
            lines.append(f"- Protein: {achieved.get('protein_g', 'N/A')} g")
            lines.append(f"- Carbs: {achieved.get('carbs_g', 'N/A')} g")
            lines.append(f"- Fats: {achieved.get('fats_g', 'N/A')} g")
            lines.append(f"- Workout Intensity: {achieved.get('workout_intensity', 'N/A')}")
            lines.append(f"- Recent Avg Weight: {achieved.get('recent_avg_weight_kg', 'N/A')} kg")
            lines.append(f"- First Week Weight: {achieved.get('first_week_weight_kg', 'N/A')} kg")
            lines.append(f"- Last Week Weight: {achieved.get('last_week_weight_kg', 'N/A')} kg")
            lines.append(f"- Weight Change: {achieved.get('weight_change_kg', 'N/A')} kg")

            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        print("Formatting error:", e)
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
    user_id = "u001"
    user_input = "show me my weekly summary for the last weeks"
    data={"intent":"weekly_summary","start_date":"2025-10-14","end_date":"2025-10-22","week_number":None}
    query = build_query(data, user_id)
    print("Generated Query:", query)
    results = execute_query(query)
    print("Results:", results)
    print(to_toon_compact(results))

