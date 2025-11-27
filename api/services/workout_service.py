import os
from typing import Dict, Any
from tracker.Workout_tracker import generate_workout_summary
from trigger.workout_trigger import handle_wo_summary_trigger
from tracker.progress_tracker import update_daily_progress
import datetime
workout_col = None
try:
    from db_connection import db as _db
    workout_col = _db['workouts_logs']
    print("Using workout_col from db_connection module")
except Exception:
    workout_col = None
if workout_col is None:
    try:
        from pymongo import MongoClient
        MONGO_URI = os.getenv("MONGO_URI")
        if MONGO_URI:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            db_from_uri = client.get_default_database() or client["mydb"]
            workout_col = db_from_uri["workouts_logs"]
            print("Using workout_col from direct MongoDB connection")
    except Exception:
        workout_col = None
def compute_workout_summary(exercises):
    summary = {
        "total_exercises": len(exercises),
        "total_sets": 0,
        "total_reps": 0,
        "total_duration_minutes": 0,
        "total_calories_burned": 0
    }

    for ex in exercises:
        summary["total_sets"] += ex.get("sets", 0) or 0

        reps = ex.get("reps", [])
        if isinstance(reps, list):
            summary["total_reps"] += sum(r for r in reps if isinstance(r, (int, float)))
        elif isinstance(reps, (int, float)):
            summary["total_reps"] += reps

        summary["total_duration_minutes"] += ex.get("duration_minutes", 0) or 0
        summary["total_calories_burned"] += ex.get("calories_burned", 0) or 0

    for k in ["total_duration_minutes", "total_calories_burned"]:
        summary[k] = round(summary[k], 2)

    return summary

def calculate_workout(calories_payload: Dict[str, Any]) -> Dict[str, Any]:
    if "user_id" not in calories_payload:
        raise ValueError("calories_payload must include 'user_id'")
    if workout_col is None:
        raise RuntimeError(
            "No MongoDB collection available as 'workout_col'.\n"
            "Provide one of the following in your environment:\n"
            " - a module `db_connection` exposing `db` (pymongo.Database),\n"
            " - a module `db` exposing a `db` (pymongo.Database),\n"
            " - set MONGO_URI environment variable so the service can connect directly.\n"
            "Or adapt `api/services/calories_service.py` to your project's DB loader."
        )
    text=calories_payload["text"]
    user_id=calories_payload["user_id"]
    workout_data = generate_workout_summary(text)
    try:
        today_str = "2025-11-24"
        incoming_exercises = workout_data.get("detailed_exercises", [])
        if not incoming_exercises:
            print("⚠️ No exercises provided.")
            return None

        doc = workout_col.find_one({"user_id": user_id, "date": today_str})

        if not doc:
            summary = compute_workout_summary(incoming_exercises)
            document = {
                "user_id": user_id,
                "date": today_str,
                "workout_data": incoming_exercises,
                "summary": summary,
                "created_at": datetime.datetime.utcnow()
            }
            result = workout_col.insert_one(document)
            print(f"🆕 New workout plan created for {user_id} on {today_str} (id={result.inserted_id})")

        else:
            existing_data = doc.get("workout_data", [])
            idx_map = {ex["exercise_name"].lower(): i for i, ex in enumerate(existing_data) if "exercise_name" in ex}

            for ex in incoming_exercises:
                name = ex.get("exercise_name", "").lower()
                if not name:
                    continue

                if name in idx_map:
                    existing_ex = existing_data[idx_map[name]]

                    existing_ex["sets"] += ex.get("sets", 0) or 0

                    new_reps = ex.get("reps", [])
                    if isinstance(new_reps, list):
                        if isinstance(existing_ex.get("reps"), list):
                            existing_ex["reps"].extend(new_reps)
                        elif isinstance(existing_ex.get("reps"), (int, float)):
                            existing_ex["reps"] = [existing_ex["reps"]] + new_reps
                    elif isinstance(new_reps, (int, float)):
                        if isinstance(existing_ex.get("reps"), list):
                            existing_ex["reps"].append(new_reps)
                        else:
                            existing_ex["reps"] = [existing_ex.get("reps", 0), new_reps]

                    if ex.get("weight"):
                        existing_ex["weight"] = round(
                            (existing_ex.get("weight", 0) + ex["weight"]) / 2, 2
                        )

                    existing_ex["duration_minutes"] = round(
                        (existing_ex.get("duration_minutes", 0) or 0)
                        + (ex.get("duration_minutes", 0) or 0),
                        2,
                    )
                    existing_ex["calories_burned"] = round(
                        (existing_ex.get("calories_burned", 0) or 0)
                        + (ex.get("calories_burned", 0) or 0),
                        2,
                    )

                    existing_data[idx_map[name]] = existing_ex
                else:
                    existing_data.append(ex)
                    idx_map[name] = len(existing_data) - 1

            new_summary = compute_workout_summary(existing_data)

            workout_col.update_one(
                {"user_id": user_id, "date": today_str},
                {"$set": {"workout_data": existing_data, 
                          "summary": new_summary,
                          "created_at": datetime.datetime.utcnow()}
                          }
            )

            print(f"🔁 Workout plan updated for {user_id} on {today_str}")

        latest_doc = workout_col.find_one({"user_id": user_id, "date": today_str})
        latest_summary = latest_doc.get("summary", {}) if latest_doc else {}
        handle_wo_summary_trigger(user_id, latest_summary,today_str)
        update_daily_progress(user_id,today_str)

        return existing_data

    except Exception as e:
        print(f"❌ Error inserting/updating workout plan: {e}")
        return None


    
