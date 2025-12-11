import os
from datetime import datetime,date
from typing import Dict, Any
from backend.macro_generator import generate_macro
from backend.tracker.progress_tracker import generate_initial_week
macro_collection = None

try:
    from backend.db_connection import db as _db
    macro_collection = _db['macro_plans']
    print("Using macro_collection from db_connection module")
except Exception:
    macro_collection = None

if macro_collection is None:
    try:
        from pymongo import MongoClient
        MONGO_URI = os.getenv("MONGO_URI")
        if MONGO_URI:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            db_from_uri = client.get_default_database() or client["mydb"]
            macro_collection = db_from_uri["macros"]
            print("Using macro_collection from direct MongoDB connection")
    except Exception:
        macro_collection = None

def generate_and_upsert_macro(user_payload: Dict[str, Any]) -> Dict[str, Any]:

    if "user_id" not in user_payload:
        raise ValueError("user_payload must include 'user_id'")

    plan = generate_macro(user_payload)

    now_iso = datetime.utcnow().isoformat()
    plan_doc = dict(plan)
    plan_doc["updated_at"] = now_iso
    plan_doc.pop("created_at", None)

    if macro_collection is None:
        raise RuntimeError(
            "No MongoDB collection available as 'macro_collection'.\n"
            "Provide one of the following in your environment:\n"
            " - a module `db_connection` exposing `db` (pymongo.Database),\n"
            " - a module `db` exposing a `db` (pymongo.Database),\n"
            " - set MONGO_URI environment variable so the service can connect directly.\n"
            "Or adapt `api/services/macro_service.py` to your project's DB loader."
        )

    filter_q = {"user_id": plan_doc["user_id"]}
    update_q = {
        "$set": plan_doc,
        "$setOnInsert": {"created_at": now_iso}
    }

    result = macro_collection.update_one(filter_q, update_q, upsert=True)

    stored_doc = macro_collection.find_one(filter_q, {"_id": 0})
    try:
        generate_initial_week(plan["user_id"], date.today())
    except Exception as e:
        print(f"generate_initial_week failed for {plan_doc['user_id']}: {e}")
    return stored_doc or plan_doc
def view_macros(user_id: str,date:str) -> Dict[str, Any]:
    if not user_id:
        raise ValueError("user_id must be provided")

    if macro_collection is None:
        raise RuntimeError("macro_collection not initialized")

    user_data = macro_collection.find_one({"user_id": user_id}, {"_id": 0})

    if not user_data:
        return { "Goal_Calories": 0,
                "Protein_g":0,
                "Fats_g": 0,
                "Carbs_g": 0,
                "Fiber_g": 0,
                "week_number": 0 }
    date_obj = datetime.strptime(date, "%Y-%m-%d").date()

    for week in user_data["Weekly_Plan"]:
        start = datetime.strptime(week["start_date"], "%Y-%m-%d").date()
        end = datetime.strptime(week["end_date"], "%Y-%m-%d").date()

        if start <= date_obj <= end:
            return {
                "Goal_Calories": week["expected_calories"],
                "Protein_g": week["expected_macros"]["Protein_g"],
                "Fats_g": week["expected_macros"]["Fats_g"],
                "Carbs_g": week["expected_macros"]["Carbs_g"],
                "Fiber_g": week["expected_macros"]["Fiber_g"],
                "week_number": week["week_number"]
            }

    raise ValueError(f"Date {date} does not fall into any macro plan range")
def view_macros_full(user_id: str) -> Dict[str, Any]:
    if not user_id:
        raise ValueError("user_id must be provided")

    if macro_collection is None:
        raise RuntimeError("macro_collection not initialized")

    user_data = macro_collection.find_one({"user_id": user_id}, {"_id": 0})

    if not user_data:
        return {
          "BMR": 0,
          "TDEE": 0,
          "goal_type": 'None',
          "total_weeks": 0,
          "start_weight_kg": 0,
          "target_weight_kg": 0,
          "Target_Change": 0,
          "Weekly_Plan": 0,
          "created_at": 0,
          "updated_at": 0,
        }

    return user_data
