import os
import json
import re
from datetime import datetime, timedelta
from dateutil import parser
from pymongo import MongoClient
from openai import OpenAI
import sys
sys.path.append('..')
from backend.db_connection import db


def build_macros_query(data, user_id):
    start_date = data.get("start_date", None)
    end_date=data.get("end_date",None)
    if ((start_date and end_date) and (start_date!=end_date)) or (not start_date and not end_date):
        intent="full_details"
    else:
        intent="day"
    if start_date is None:
        start_date=end_date
    base_query = {"collection": "macro_plans"}

    if intent == "day":
        try:
            pipeline = [
                {"$match": {"user_id": user_id}},
                {"$project": {
                    "user_id": 1,
                    "Weekly_Plan": {
                        "$filter": {
                            "input": "$Weekly_Plan",
                            "as": "week",
                            "cond": {
                                "$and": [
                                    {"$lte": ["$$week.start_date", start_date]},
                                    {"$gte": ["$$week.end_date", start_date]}
                                ]
                            }
                        }
                    }
                }},
                {"$project": {
                    "user_id": 1,
                    "expected_macros": {"$arrayElemAt": ["$Weekly_Plan.expected_macros", 0]},
                    "_id": 0
                }}
            ]

            base_query["pipeline"] = pipeline

        except Exception as e:
            print(f"⚠️ Date parse error: {e}")
            pipeline = [
                {"$match": {"user_id": user_id}},
                {"$project": {
                    "user_id": 1,
                    "Weekly_Plan": {
                        "$filter": {
                            "input": "$Weekly_Plan",
                            "as": "week",
                            "cond": {"$eq": ["$$week.start_date", start_date]}
                        }
                    }
                }},
                {"$project": {
                    "user_id": 1,
                    "expected_macros": {"$arrayElemAt": ["$Weekly_Plan.expected_macros", 0]},
                    "_id": 0
                }}
            ]
            base_query["pipeline"] = pipeline

    else:
        base_query["filter"] = {"user_id": user_id}
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


def format_macros_response(query_data):
    if not query_data:
        return "No metabolic data found."

    try:
        data = json.loads(json.dumps(query_data, default=str))
        entry = data[0]

        lines = []
        lines.append("Metabolism & Goal Summary:\n")

        user_id = entry.get("user_id")
        if user_id:
            lines.append(f"User ID: {user_id}\n")

        goal_type = entry.get("goal_type")
        start_weight = entry.get("start_weight_kg")
        target_weight = entry.get("target_weight_kg")

        if goal_type or start_weight or target_weight:
            if goal_type:
                lines.append(f"Goal Type: {goal_type}")
            if start_weight:
                lines.append(f"Starting Weight: {start_weight} kg")
            if target_weight:
                lines.append(f"Target Weight: {target_weight} kg")
            lines.append("")

        bmr = entry.get("BMR")
        tdee = entry.get("TDEE")
        goal_cal = entry.get("Goal_Calories")

        if bmr or tdee or goal_cal:
            if bmr:
                lines.append(f"BMR: {bmr}")
            if tdee:
                lines.append(f"TDEE: {tdee}")
            if goal_cal:
                lines.append(f"Goal Calories per Day: {goal_cal}")
            lines.append("")

        macros = entry.get("Macros") or entry.get("expected_macros")
        if macros:
            lines.append("Base Macro Targets:")
            lines.append(f"- Protein: {macros.get('Protein_g', 'N/A')} g")
            lines.append(f"- Fats: {macros.get('Fats_g', 'N/A')} g")
            lines.append(f"- Carbs: {macros.get('Carbs_g', 'N/A')} g")
            lines.append(f"- Fiber: {macros.get('Fiber_g', 'N/A')} g")
            lines.append("")

        weekly_plan = entry.get("Weekly_Plan", [])
        if weekly_plan:
            lines.append(f"{len(weekly_plan)}-Week Progressive Plan:\n")

            for week in weekly_plan:
                lines.append(
                    f"Week {week.get('week_number')}: "
                    f"{week.get('start_date')} to {week.get('end_date')}"
                )
                lines.append(f"- Expected Weight: {week.get('expected_weight_kg', 'N/A')} kg")
                lines.append(f"- Expected Daily Calories: {week.get('expected_calories', 'N/A')} kcal")

                exp_macros = week.get("expected_macros", {})
                lines.append(
                    f"- Expected Macros: Protein {exp_macros.get('Protein_g','N/A')}g | "
                    f"Fats {exp_macros.get('Fats_g','N/A')}g | "
                    f"Carbs {exp_macros.get('Carbs_g','N/A')}g | "
                    f"Fiber {exp_macros.get('Fiber_g','N/A')}g"
                )

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
    user_id = "u002"
    query = build_macros_query({'intent': 'macros', 'subquery': 'show macros for 2025-10-21', 'start_date': '2025-11-24', 'end_date': '2025-11-25'}, user_id)
    print("Generated Query:", query)
    results = execute_macros_query(query)
    print("Result:", results)
    print(to_toon_compact(results))
