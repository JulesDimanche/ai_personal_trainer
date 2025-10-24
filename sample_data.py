import os
from db_connection import user_col, workout_col, diet_col, progress_col,macro_collection
import datetime
from macro_generator import generate_macro
from Calorie_tracker import estimate_calories
from Workout_tracker import generate_workout_summary
from diet_trigger import handle_summary_trigger
from workout_tigger import handle_wo_summary_trigger
from progress_tracker import update_daily_progress

'''user_col.insert_one({
    "user_id": "u001",
    "name": "John Doe",
    "age": 25,
    "gender": "male",
    "height_cm": 178,
    "weight_kg": 72,
    "goal": "fat_loss",
    "target_duration_weeks": 12,
    "activity_level": "moderate"
})

workout_col.insert_one({
    "user_id": "u001",
    "date": "2025-10-06",
    "type": "strength_training",
    "summary": "Chest and triceps workout, 45 mins, 400 kcal burned.",
    "duration_min": 45,
    "calories_burned": 400
})

diet_col.insert_one({
    "user_id": "u001",
    "date": "2025-10-06",
    "meals": [
        {"meal": "breakfast", "items": ["oats", "banana", "milk"], "calories": 350},
        {"meal": "lunch", "items": ["chicken", "rice", "salad"], "calories": 600},
        {"meal": "dinner", "items": ["eggs", "veggies"], "calories": 400}
    ],
    "total_calories": 1350
})
progress_col.insert_one({
    "user_id": "u001",
    "week": 1,
    "weight_kg": 71.5,
    "body_fat_pct": 19.0,
    "notes": "Started training, energy levels improving."
})'''

def insert_macro_plan(macro_data):
    try:
        document={
            **macro_data,
            'created_at':datetime.datetime.utcnow()
        }
        result=macro_collection.insert_one(document)
        print(f"Macro plan inserted with ID: {result.inserted_id}")
        return str(result.inserted_id)
    except Exception as e:
        print(f"Error inserting macro plan: {e}")
        return None
def get_latest_macro_plan(user_id):
    try:
        result=macro_collection.find_one(
            {'user_id':user_id},
            sort=[('created_at',-1)]
        )  
        return result
    except Exception as e:
        print(f"Error retrieving macro plan: {e}")
        return None

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

def insert_calories_plan(user_id, calorie_data):
    try:
        today_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        incoming_meals = calorie_data.get("meals", [])
        if not incoming_meals:
            print("⚠️ No meals provided.")
            return None

        doc = diet_col.find_one({"user_id": user_id, "date": today_str})

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
            result = diet_col.insert_one(new_doc)
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
                    existing_items.extend(new_items)
                    existing_meal["items"] = existing_items
                    existing_meal["meal_summary"] = compute_totals_from_items(existing_items)
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
                "created_at": doc.get("summary", {}).get("created_at", datetime.datetime.utcnow().isoformat())
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

            diet_col.update_one(
                {"user_id": user_id, "date": today_str},
                {
                    "$set": {
                        "plan_data": plan_data,
                        "summary": overall
                    }
                }
            )
            print(f"🔁 Merged updates into existing daily plan for {user_id} on {today_str}")

        update_daily_progress(user_id, datetime.datetime.utcnow())
        latest_doc = diet_col.find_one({"user_id": user_id, "date": today_str})
        latest_summary = latest_doc.get("summary", {}) if latest_doc else {}
        handle_summary_trigger(user_id, latest_summary, datetime.datetime.utcnow())

        return True

    except Exception as e:
        print(f"❌ Error inserting/updating calorie plan: {e}")
        return None


def get_latest_calorie(user_id):
    try:
        result=diet_col.find_one(
            {'user_id':user_id},
            sort=[('created_at',-1)]
        )  
        return result
    except Exception as e:
        print(f"Error retrieving macro plan: {e}")
        return None

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


def insert_workout_plan(user_id, workout_data):
    try:
        today_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")
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
                {"$set": {"workout_data": existing_data, "summary": new_summary}}
            )

            print(f"🔁 Workout plan updated for {user_id} on {today_str}")

        update_daily_progress(user_id, datetime.datetime.utcnow())
        latest_doc = workout_col.find_one({"user_id": user_id, "date": today_str})
        latest_summary = latest_doc.get("summary", {}) if latest_doc else {}
        handle_wo_summary_trigger(user_id, latest_summary, datetime.datetime.utcnow())

        return True

    except Exception as e:
        print(f"❌ Error inserting/updating workout plan: {e}")
        return None

    
def get_latest_workout(user_id):
    try:
        result=workout_col.find_one(
            {'user_id':user_id},
            sort=[('created_at',-1)]
        )  
        return result
    except Exception as e:
        print(f"Error retrieving macro plan: {e}")
        return None
if __name__=='__main__':
    user_data={
        'user_id':"u001",
        "age": 25,
        "gender": "male",
        "weight_kg": 70,
        "height_cm": 175,
        "activity_level": "moderate",
        "goal": "fat_loss",
        "target_period_weeks": 8
    }
    #macro_data=generate_macro(user_data)
    #insert_macro_plan(macro_data)
    #print("Latest Macro Plan-------")
    #plan=get_latest_macro_plan(user_id)
    #print(plan)
    user_id="u001"
    #calorie_data=estimate_calories('I had 1 egg for snacks and 200 g of chicken for lunch',os.getenv("QWEN3_API_KEY"))
    #insert_calories_plan(user_id,calorie_data)
    #diet=get_latest_calorie(user_id)
    #print("calore Plan-------")
    #print(diet)
    workout_data=generate_workout_summary('I made 1 set of 6 reps of incline bench press at 60kg',os.getenv("QWEN3_API_KEY"))
    insert_workout_plan(user_id,workout_data)
    WO=get_latest_workout(user_id)
    print("Workout Plan-------")
    print(WO)
