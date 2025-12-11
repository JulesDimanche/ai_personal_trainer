import os
from typing import Dict, Any
from tracker.Calorie_tracker import estimate_calories
from trigger.diet_trigger import handle_summary_trigger
from tracker.progress_tracker import update_daily_progress
import datetime
calories_col = None
try:
    from backend.db_connection import db as _db
    calories_col = _db['diet_logs']
    print("Using calories_col from db_connection module")
except Exception:
    calories_col = None
if calories_col is None:
    try:
        from pymongo import MongoClient
        MONGO_URI = os.getenv("MONGO_URI")
        if MONGO_URI:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            db_from_uri = client.get_default_database() or client["mydb"]
            calories_col = db_from_uri["diet_logs"]
            print("Using calories_col from direct MongoDB connection")
    except Exception:
        calories_col = None
def compute_totals_from_items(items):
    totals = {
        "total_calories": 0.0,
        "total_protein": 0.0,
        "total_fat": 0.0,
        "total_carb": 0.0,
        "total_fiber": 0.0
    }
    for it in items:
        totals["total_calories"] += float(it.get("calories", 0) or 0)
        totals["total_protein"]  += float(it.get("proteins", 0) or 0)
        totals["total_fat"]      += float(it.get("fats", 0) or 0)
        totals["total_carb"]     += float(it.get("carbs", 0) or 0)
        totals["total_fiber"]    += float(it.get("fiber", 0) or 0)
    for k in totals:
        totals[k] = round(totals[k], 2)
    return totals

def calculate_calories(calories_payload: Dict[str, Any]) -> Dict[str, Any]:
    if "user_id" not in calories_payload:
        raise ValueError("calories_payload must include 'user_id'")
    if calories_col is None:
        raise RuntimeError(
            "No MongoDB collection available as 'calories_col'.\n"
            "Provide one of the following in your environment:\n"
            " - a module `db_connection` exposing `db` (pymongo.Database),\n"
            " - a module `db` exposing a `db` (pymongo.Database),\n"
            " - set MONGO_URI environment variable so the service can connect directly.\n"
            "Or adapt `api/services/calories_service.py` to your project's DB loader."
        )
    text=calories_payload["text"]
    user_id=calories_payload["user_id"]
    date=calories_payload.get("date")
    calorie_data = estimate_calories(text)
    try:
        today_str = date
        incoming_meals = calorie_data.get("meals", [])
        if not incoming_meals:
            print("⚠️ No meals provided.")
            return None

        doc = calories_col.find_one({"user_id": user_id, "date": today_str})

        if not doc:
            plan_data = []
            for meal in incoming_meals:
                items = meal.get("items", []) or []
                meal_summary = compute_totals_from_items(items)
                plan_data.append({
                    "meal_type": meal.get("meal_type"),
                    "items": items,
                    "meal_summary": meal_summary
                })

            overall = {
                "total_calories": 0.0,
                "total_protein": 0.0,
                "total_fat": 0.0,
                "total_carb": 0.0,
                "total_fiber": 0.0,
                "created_at": datetime.datetime.utcnow().isoformat()
            }
            for m in plan_data:
                ms = m["meal_summary"]
                overall["total_calories"] += ms.get("total_calories", 0)
                overall["total_protein"]  += ms.get("total_protein", 0)
                overall["total_fat"]      += ms.get("total_fat", 0)
                overall["total_carb"]     += ms.get("total_carb", 0)
                overall["total_fiber"]    += ms.get("total_fiber", 0)
            for k in ["total_calories","total_protein","total_fat","total_carb","total_fiber"]:
                overall[k] = round(overall[k], 2)

            new_doc = {
                "user_id": user_id,
                "date": today_str,
                "plan_data": plan_data,
                "summary": overall,
                "created_at": datetime.datetime.utcnow()
            }
            result = calories_col.insert_one(new_doc)
            print(f"🆕 Created new daily plan for {user_id} on {today_str} (id={result.inserted_id})")
        else:
            plan_data = doc.get("plan_data", [])[:] 
            idx_map = {m["meal_type"]: i for i, m in enumerate(plan_data) if "meal_type" in m}

            for meal in incoming_meals:
                meal_type = meal.get("meal_type")
                if not meal_type:
                    continue
                new_items = meal.get("items", []) or []

                if meal_type in idx_map:
                    i = idx_map[meal_type]
                    existing_meal = plan_data[i]
                    existing_items = existing_meal.get("items", []) or []
                    existing_items = existing_meal.get("items", []) or []
                    merged = {}

                    for it in existing_items:
                        key = it["food"].lower()
                        if key not in merged:
                            merged[key] = it.copy()
                        else:
                            merged[key]["quantity"] += it.get("quantity", 0)
                            merged[key]["weight"] += it.get("weight", 0)
                            merged[key]["calories"] += it.get("calories", 0)
                            merged[key]["proteins"] += it.get("proteins", 0)
                            merged[key]["fats"] += it.get("fats", 0)
                            merged[key]["carbs"] += it.get("carbs", 0)
                            merged[key]["fiber"] += it.get("fiber", 0)

                    for it in new_items:
                        key = it["food"].lower()
                        if key not in merged:
                            merged[key] = it.copy()
                        else:
                            merged[key]["quantity"] += it.get("quantity", 0)
                            merged[key]["weight"] += it.get("weight", 0)
                            merged[key]["calories"] += it.get("calories", 0)
                            merged[key]["proteins"] += it.get("proteins", 0)
                            merged[key]["fats"] += it.get("fats", 0)
                            merged[key]["carbs"] += it.get("carbs", 0)
                            merged[key]["fiber"] += it.get("fiber", 0)

                    final_items = list(merged.values())
                    existing_meal["items"] = final_items
                    existing_meal["meal_summary"] = compute_totals_from_items(final_items)

                    plan_data[i] = existing_meal
                else:
                    meal_entry = {
                        "meal_type": meal_type,
                        "items": new_items,
                        "meal_summary": compute_totals_from_items(new_items)
                    }
                    plan_data.append(meal_entry)
                    idx_map[meal_type] = len(plan_data) - 1

            overall = {
                "total_calories": 0.0,
                "total_protein": 0.0,
                "total_fat": 0.0,
                "total_carb": 0.0,
                "total_fiber": 0.0,
                "created_at": datetime.datetime.utcnow().isoformat()
            }
            for m in plan_data:
                ms = m.get("meal_summary", {})
                overall["total_calories"] += ms.get("total_calories", 0)
                overall["total_protein"]  += ms.get("total_protein", 0)
                overall["total_fat"]      += ms.get("total_fat", 0)
                overall["total_carb"]     += ms.get("total_carb", 0)
                overall["total_fiber"]    += ms.get("total_fiber", 0)
            for k in ["total_calories","total_protein","total_fat","total_carb","total_fiber"]:
                overall[k] = round(overall[k], 2)

            calories_col.update_one(
                {"user_id": user_id, "date": today_str},
                {
                    "$set": {
                        "plan_data": plan_data,
                        "summary": overall
                    }
                }
            )
            print(f"🔁 Merged updates into existing daily plan for {user_id} on {today_str}")

        latest_doc = calories_col.find_one({"user_id": user_id, "date": today_str})
        latest_summary = latest_doc.get("summary", {}) if latest_doc else {}
        handle_summary_trigger(user_id, latest_summary, today_str)
        update_daily_progress(user_id, today_str)

        return plan_data

    except Exception as e:
        print(f"❌ Error inserting/updating calorie plan: {e}")
        return None
def view_calories(user_id: str, date: str) -> Dict[str, Any]:
    if not user_id:
        raise ValueError("user_id is required")
    if not date:
        raise ValueError("date is required")
    if calories_col is None:
        raise RuntimeError(
            "No MongoDB collection available as 'calories_col'.\n"
            "Provide one of the following in your environment:\n"
            " - a module `db_connection` exposing `db` (pymongo.Database),\n"
            " - a module `db` exposing a `db` (pymongo.Database),\n"
            " - set MONGO_URI environment variable so the service can connect directly.\n"
            "Or adapt `api/services/calories_service.py` to your project's DB loader."
        )
    try:
        doc = calories_col.find_one({"user_id": user_id, "date": date})
        if not doc:
            return { "success": True,"calorie_data": { "plan_data": [], "summary": {} } }

        return {
            "plan_data": doc.get("plan_data", []),
            "summary": doc.get("summary", {})
        }
    except Exception as e:
        print(f"❌ Error retrieving calorie data: {e}")
        raise RuntimeError(f"Error retrieving calorie data: {e}")
def delete_food(data):
    doc = calories_col.find_one({"user_id": data.user_id, "date": data.date})
    if not doc:
        return {"status": "error", "message": "Food log not found"}

    plan_data = doc.get("plan_data", [])

    meal = None
    for m in plan_data:
        if m["meal_type"].lower() == data.meal_type.lower():
            meal = m
            break

    if not meal:
        return {"status": "error", "message": "Meal type not found"}

    items = meal.get("items", [])

    new_items = [i for i in items if i["food"].lower() != data.food_name.lower()]

    if len(new_items) == len(items):
        return {"status": "error", "message": "Food item not found"}

    meal["items"] = new_items

    meal["meal_summary"] = {
        "total_calories": sum(i["calories"] for i in new_items),
        "total_protein": sum(i["proteins"] for i in new_items),
        "total_fat": sum(i["fats"] for i in new_items),
        "total_carb": sum(i["carbs"] for i in new_items),
        "total_fiber": sum(i["fiber"] for i in new_items),
    }

    full_day = {
        "total_calories": 0,
        "total_protein": 0,
        "total_fat": 0,
        "total_carb": 0,
        "total_fiber": 0,
    }

    for m in plan_data:
        full_day["total_calories"] += m["meal_summary"]["total_calories"]
        full_day["total_protein"] += m["meal_summary"]["total_protein"]
        full_day["total_fat"] += m["meal_summary"]["total_fat"]
        full_day["total_carb"] += m["meal_summary"]["total_carb"]
        full_day["total_fiber"] += m["meal_summary"]["total_fiber"]

    doc["summary"] = full_day

    calories_col.update_one(
        {"user_id": data.user_id, "date": data.date},
        {"$set": {"plan_data": plan_data, "summary": full_day}}
    )
    latest_doc = calories_col.find_one({"user_id": data.user_id, "date": data.date})
    latest_summary = latest_doc.get("summary", {}) if latest_doc else {}
    handle_summary_trigger(data.user_id, latest_summary, data.date)
    update_daily_progress(data.user_id, data.date)
    return {"status": "success", "message": "Food deleted"}
