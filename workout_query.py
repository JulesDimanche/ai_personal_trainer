import os
import json
import re
from datetime import datetime, timedelta
from dateutil import parser
from pymongo import MongoClient
from db_connection import db, workout_col



# ----------- QUERY TEMPLATES -----------

WORKOUT_QUERY_TEMPLATES = {
    "workout": lambda date, user_id: {
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

def get_week_range_from_date(date_str):
    dt = datetime.fromisoformat(date_str)
    start = dt - timedelta(days=dt.weekday())
    end = start + timedelta(days=6)
    return start.isoformat(), end.isoformat()

def build_workout_query(data, user_id):
    entities=data
    intent = entities.get("intent", "workout")
    start_date = entities.get("start_date")
    end_date = entities.get("end_date")
    exercise = entities.get("exercise")

    date = start_date or end_date
    return WORKOUT_QUERY_TEMPLATES[intent](date, user_id)

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

def format_workout_response(query_data):
    if not query_data:
        return "No workout records found."

    try:
        safe_data = json.loads(json.dumps(query_data, default=str))

        lines = []
        lines.append("Workout Summary:\n")

        for entry in safe_data:
            workout_list = entry.get("workout_data", [])
            summary = entry.get("summary", {})

            for w in workout_list:
                exercise = w.get("exercise_name", "Unknown exercise")
                muscle = w.get("muscle_group", "Unknown muscle")
                sets = w.get("sets", "N/A")
                reps = w.get("reps", [])
                weight = w.get("weight", "N/A")
                duration = w.get("duration_minutes", "N/A")
                calories = w.get("calories_burned", "N/A")

                rep_str = ", ".join(str(r) for r in reps) if reps else "N/A"

                lines.append(f"Exercise: {exercise}")
                lines.append(f"- Muscle Group: {muscle}")
                lines.append(f"- Sets: {sets} | Reps: {rep_str} | Weight: {weight} kg")
                lines.append(f"- Duration: {duration} min | Calories Burned: {calories}")
                lines.append("")

            if summary:
                lines.append("Overall Summary:")
                lines.append(f"- Total Exercises: {summary.get('total_exercises', 'N/A')}")
                lines.append(f"- Total Sets: {summary.get('total_sets', 'N/A')}")
                lines.append(f"- Total Reps: {summary.get('total_reps', 'N/A')}")
                lines.append(f"- Total Duration: {summary.get('total_duration_minutes', 'N/A')} minutes")
                lines.append(f"- Total Calories Burned: {summary.get('total_calories_burned', 'N/A')}")
                lines.append("")

        return "\n".join(lines)

    except Exception as e:
        print(f"Formatting error: {str(e)}")
        return "Formatting error."

if __name__ == "__main__":
    user_id = "u001"
    query = build_workout_query({'intent': 'workout', 'start_date': None, 'end_date': '2025-10-24', 'exercise': "bench press"}, user_id)
    print("Generated Query:", query)
    results = execute_workout_query(query)
    print("Result:", results)
    print(format_workout_response(results))
