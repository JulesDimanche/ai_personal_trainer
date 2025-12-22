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
workout_plan_col = None
try:
    from db_connection import db as _db
    workout_plan_col = _db['workout_plan']
    print("Using workout_plan_col from db_connection module")
except Exception:
    workout_plan_col = None
if workout_plan_col is None:
    try:
        from pymongo import MongoClient
        MONGO_URI = os.getenv("MONGO_URI")
        if MONGO_URI:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            DB_NAME = os.getenv("DB_NAME")
            db_from_uri = client[DB_NAME]
            workout_plan_col = db_from_uri["workout_plan"]
            print("Using workout_plan_col from direct MongoDB connection")
    except Exception:
        workout_plan_col = None
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

def calculate_workout(workout_payload: Dict[str, Any]) -> Dict[str, Any]:
    if "user_id" not in workout_payload:
        raise ValueError("workout_payload must include 'user_id'")
    if workout_col is None:
        raise RuntimeError(
            "No MongoDB collection available as 'workout_col'.\n"
            "Provide one of the following in your environment:\n"
            " - a module `db_connection` exposing `db` (pymongo.Database),\n"
            " - a module `db` exposing a `db` (pymongo.Database),\n"
            " - set MONGO_URI environment variable so the service can connect directly.\n"
            "Or adapt `api/services/calories_service.py` to your project's DB loader."
        )
    text=workout_payload["text"]
    user_id=workout_payload["user_id"]
    date=workout_payload["date"]
    workout_data = generate_workout_summary(text)
    try:
        today_str =date
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
                reps = ex.get("reps")
                if isinstance(reps, (int, float)):
                    ex["reps"] = [reps]
                elif reps is None:
                    ex["reps"] = []

                weight = ex.get("weight")
                if isinstance(weight, (int, float)):
                    ex["weight"] = [weight]
                elif weight is None:
                    ex["weight"] = []
                if name in idx_map:
                    existing_ex = existing_data[idx_map[name]]

                    existing_sets = existing_ex.get("sets") or 0
                    incoming_sets = ex.get("sets") or 0
                    existing_ex["sets"] = existing_sets + incoming_sets


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

                    new_weight = ex.get("weight")

                    if "weight" not in existing_ex:
                        existing_ex["weight"] = []

                    elif isinstance(existing_ex["weight"], (int, float)):
                        existing_ex["weight"] = [existing_ex["weight"]]

                    if new_weight is not None:
                        if isinstance(new_weight, list):
                            existing_ex["weight"].extend(new_weight)
                        else:
                            existing_ex["weight"].append(new_weight)

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
def view_workout(user_id: str, date: str) -> Dict[str, Any]:
    if not user_id:
        raise ValueError("user_id is required")
    if not date:
        raise ValueError("date is required")
    if workout_col is None:
        raise RuntimeError(
            "No MongoDB collection available as 'calories_col'.\n"
            "Provide one of the following in your environment:\n"
            " - a module `db_connection` exposing `db` (pymongo.Database),\n"
            " - a module `db` exposing a `db` (pymongo.Database),\n"
            " - set MONGO_URI environment variable so the service can connect directly.\n"
            "Or adapt `api/services/calories_service.py` to your project's DB loader."
        )
    try:
        doc = workout_col.find_one({"user_id": user_id, "date": date})
        if not doc:
            return { "success": True,"workout_data": { "plan_data": [], "summary": {} } }

        return {
            "workout_data": doc.get("workout_data", []),
            "summary": doc.get("summary", {})
        }
    except Exception as e:
        print(f"❌ Error retrieving calorie data: {e}")
        raise RuntimeError(f"Error retrieving calorie data: {e}")
def create_or_update_workout_plan(user_id: str, plan_name: str, exercise_name: str, sets_list: list):
    if not user_id:
        return {"error": "User ID is required."}
    if not plan_name:
        return {"error": "Plan name is required."}
    if not exercise_name:
        return {"error": "Exercise name is required."}
    if workout_plan_col is None:
        raise RuntimeError(
            "No MongoDB collection available as 'calories_col'.\n"
            "Provide one of the following in your environment:\n"
            " - a module `db_connection` exposing `db` (pymongo.Database),\n"
            " - a module `db` exposing a `db` (pymongo.Database),\n"
            " - set MONGO_URI environment variable so the service can connect directly.\n"
            "Or adapt `api/services/calories_service.py` to your project's DB loader."
        )

    plan_name = plan_name.strip().title()
    exercise_name = exercise_name.strip().title()

    user_data = workout_plan_col.find_one({"user_id": user_id})

    exercise_obj = {
        "name": exercise_name,
        "sets": sets_list,
        "updated_at": datetime.datetime.utcnow()
    }

    if not user_data:
        new_doc = {
            "user_id": user_id,
            "plans": [
                {
                    "name": plan_name,
                    "created_at":datetime.datetime.utcnow(),
                    "updated_at": datetime.datetime.utcnow(),
                    "exercises": [exercise_obj]
                }
            ],
            "created_at": datetime.datetime.utcnow(),
            "updated_at": datetime.datetime.utcnow()
        }
        workout_plan_col.insert_one(new_doc)
        return {"status": "created", "message": "Workout plan created with exercise."}

    plans = user_data.get("plans", [])
    for plan in plans:
        if plan["name"].lower() == plan_name.lower():

            for ex in plan.get("exercises", []):
                if ex["name"].lower() == exercise_name.lower():
                    ex["sets"] = sets_list       # update list of sets
                    ex["updated_at"] = datetime.datetime.utcnow()

                    workout_plan_col.update_one(
                        {"user_id": user_id},
                        {"$set": {"plans": plans, "updated_at": datetime.datetime.utcnow()}}
                    )
                    return {"status": "updated", "message": "Exercise sets updated."}

            plan["exercises"].append(exercise_obj)
            workout_plan_col.update_one(
                {"user_id": user_id},
                {"$set": {"plans": plans, "updated_at": datetime.datetime.utcnow()}}
            )
            return {"status": "added", "message": "Exercise added to plan."}

    new_plan = {
        "name": plan_name,
        "created_at": datetime.datetime.utcnow(),
        "updated_at": datetime.datetime.utcnow(),
        "exercises": [exercise_obj]
    }

    workout_plan_col.update_one(
        {"user_id": user_id},
        {"$push": {"plans": new_plan}, "$set": {"updated_at": datetime.datetime.utcnow()}}
    )

    return {"status": "plan_created", "message": "New plan created with exercise."}
def get_workout_plan(user_id: str, plan_name: str = None, list_only: bool = False):
    if not user_id:
        return {"error": "User ID is required."}
    
    if workout_plan_col is None:
        raise RuntimeError(
            "No MongoDB collection available as 'calories_col'.\n"
            "Provide one of the following in your environment:\n"
            " - a module `db_connection` exposing `db` (pymongo.Database),\n"
            " - a module `db` exposing a `db` (pymongo.Database),\n"
            " - set MONGO_URI environment variable so the service can connect directly.\n"
            "Or adapt `api/services/calories_service.py` to your project's DB loader."
        )
    user_data = workout_plan_col.find_one({"user_id": user_id}, {"_id": 0})

    if not user_data:
        return {"error": "User has no workout plans."}
    plans = user_data.get("plans", [])
    if list_only:
            return {
                "status": "success",
                "plans": [p["name"] for p in plans]
            }
    if not plan_name:
        return {"error": "Plan name is required."}
    plan_name = plan_name.strip().title()
    for plan in user_data.get("plans", []):
        if plan["name"].lower() == plan_name.lower():
            return {
                "status": "success",
                "plan": plan
            }

    return {"error": "Plan not found."}

def save_plan_and_daily(user_id: str, date: str, plan_name: str, frontend_exercises: list):

    if not user_id:
        return {"error": "User ID is required."}
    if not date:
        return {"error": "Date is required."}
    if not plan_name:
        return {"error": "Plan name is required."}
    if workout_plan_col is None or workout_col is None:
        return {"error": "Database not initialised."}

    try:
        plan_exercises = []
        for ex in frontend_exercises:
            reps_arr = ex.get("reps", [])
            sets_list = []
            if reps_arr and all(isinstance(r, (int, float)) for r in reps_arr):
                for i, r in enumerate(reps_arr):
                    weights = ex.get("weight", [])
                    weight_value = weights[i] if isinstance(weights, list) and len(weights) > i else None

                    sets_list.append({
                        "set_number": i + 1,
                        "reps": r,
                        "weight": weight_value,
                        "updated_at": datetime.datetime.utcnow()
                    })
            else:
                sets_list.append({
                    "set_number": 1,
                    "reps": reps_arr if not isinstance(reps_arr, (int, float)) else reps_arr,
                    "weight": ex.get("weight"),
                    "updated_at": datetime.datetime.utcnow()
                })

            plan_exercises.append({
                "name": ex.get("exercise_name") or ex.get("name"),
                "muscle_group": ex.get("muscle_group"),
                "sets": sets_list,
                "duration_minutes": ex.get("duration_minutes", 0),
                "calories_burned": ex.get("calories_burned", 0),
                "updated_at": datetime.datetime.utcnow()
            })

        user_plan_doc = workout_plan_col.find_one({"user_id": user_id})
        if not user_plan_doc:
            new_plan = {
                "name": plan_name.strip().title(),
                "created_at": datetime.datetime.utcnow(),
                "updated_at": datetime.datetime.utcnow(),
                "exercises": plan_exercises
            }
            new_doc = {
                "user_id": user_id,
                "plans": [new_plan],
                "created_at": datetime.datetime.utcnow(),
                "updated_at": datetime.datetime.utcnow()
            }
            workout_plan_col.insert_one(new_doc)
        else:
            plans = user_plan_doc.get("plans", [])
            new_plans = []
            plan_found = False

            for plan in plans:
                if plan.get("name", "").lower() == plan_name.strip().lower():
                    new_plans.append({
                        "name": plan_name.strip().title(),
                        "created_at": plan.get("created_at", datetime.datetime.utcnow()),
                        "updated_at": datetime.datetime.utcnow(),
                        "exercises": plan_exercises
                    })
                    plan_found = True
                else:
                    new_plans.append(plan)

            if not plan_found:
                new_plans.append({
                    "name": plan_name.strip().title(),
                    "created_at": datetime.datetime.utcnow(),
                    "updated_at": datetime.datetime.utcnow(),
                    "exercises": plan_exercises
                })

            workout_plan_col.update_one(
                {"user_id": user_id},
                {"$set": {"plans": new_plans, "updated_at": datetime.datetime.utcnow()}}
            )
        workout_data_for_day = []
        for ex in frontend_exercises:
            reps = ex.get("reps", [])
            sets_count = ex.get("sets", len(reps) if isinstance(reps, list) else (1 if reps else 0))
            workout_data_for_day.append({
                "exercise_name": ex.get("exercise_name") or ex.get("name"),
                "muscle_group": ex.get("muscle_group", "Other"),
                "reps": reps,
                "weight": ex.get("weight"),
                "sets": sets_count,
                "duration_minutes": ex.get("duration_minutes", 0),
                "calories_burned": ex.get("calories_burned", 0),
                "updated_at": datetime.datetime.utcnow()
            })

        summary = compute_workout_summary(workout_data_for_day)

        workout_col.update_one(
            {"user_id": user_id, "date": date},
            {"$set": {
                "user_id": user_id,
                "date": date,
                "workout_data": workout_data_for_day,
                "summary": summary,
                "created_at": datetime.datetime.utcnow()
            }},
            upsert=True
        )

        handle_wo_summary_trigger(user_id, summary, date)
        update_daily_progress(user_id, date)

        return {"status": "success", "message": "Plan and daily workout updated.", "workout_data": workout_data_for_day, "summary": summary}

    except Exception as e:
        print(f"❌ Error in save_plan_and_daily: {e}")
        return {"error": str(e)}
def delete_set(data):
    doc = workout_col.find_one({"user_id": data.user_id, "date": data.date})
    if not doc:
        return {"status": "error", "message": "Workout log not found"}

    workouts = doc.get("workout_data", [])


    for i, w in enumerate(workouts):
        if w["exercise_name"].lower() == data.exercise_name.lower():
            old_sets = w["sets"] or 1
            avg_duration = (w.get("duration_minutes", 0) or 0) / old_sets
            avg_calories = (w.get("calories_burned", 0) or 0) / old_sets
            if data.set_index < 0 or data.set_index >= len(w["reps"]):
                return {"status": "error", "message": "Invalid set index"}

            w["reps"].pop(data.set_index)
            if isinstance(w.get("weight"), list):
                w["weight"].pop(data.set_index)

            if len(w["reps"]) == 0:
                workouts.pop(i)
            else:
                w["sets"] = len(w["reps"])
            new_sets = w["sets"]
            w["duration_minutes"] = round(avg_duration * new_sets, 2)
            w["calories_burned"] = round(avg_calories * new_sets, 2)

            summary = compute_workout_summary(workouts)
            workout_col.update_one(
                {"user_id": data.user_id, "date": data.date},
                {"$set": {"workout_data": workouts,"summary": summary}}
            )

            latest_doc = workout_col.find_one({"user_id": data.user_id, "date": data.date})
            latest_summary = latest_doc.get("summary", {}) if latest_doc else {}
            handle_wo_summary_trigger(data.user_id, latest_summary,data.date)
            update_daily_progress(data.user_id,data.date)
            return {"status": "success", "message": "Set deleted"}

    return {"status": "error", "message": "Exercise not found"}

def edit_set(data):
    doc = workout_col.find_one({"user_id": data.user_id, "date": data.date})
    if not doc:
        return {"status": "error", "message": "Workout log not found"}

    workouts = doc.get("workout_data", [])

    found = None
    for w in workouts:
        if w["exercise_name"].lower() == data.exercise_name.lower():
            found = w
            break

    if not found:
        return {"status": "error", "message": "Exercise not found"}
    old_sets = found["sets"] or 1
    avg_duration = (found.get("duration_minutes", 0) or 0) / old_sets
    avg_calories = (found.get("calories_burned", 0) or 0) / old_sets
    found["reps"] = data.reps
    found["weight"] = data.weight
    found["sets"] = len(data.reps)
    new_sets = found["sets"]
    found["duration_minutes"] = round(avg_duration * new_sets, 2)
    found["calories_burned"] = round(avg_calories * new_sets, 2)

    summary = compute_workout_summary(workouts)
    workout_col.update_one(
        {"user_id": data.user_id, "date": data.date},
        {"$set": {"workout_data": workouts,"summary": summary}}
    )
    latest_doc = workout_col.find_one({"user_id": data.user_id, "date": data.date})
    latest_summary = latest_doc.get("summary", {}) if latest_doc else {}
    handle_wo_summary_trigger(data.user_id, latest_summary,data.date)
    update_daily_progress(data.user_id,data.date)
    return {"status": "success", "message": "Exercise updated"}
