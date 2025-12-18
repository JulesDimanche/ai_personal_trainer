from datetime import datetime
from collections import defaultdict

def get_week_key(date_str: str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    year, week, _ = date_obj.isocalendar()
    return f"{year}-W{week}", date_obj

def build_weekly_workout_update(raw_doc):

    week_key, date_obj = get_week_key(raw_doc["date"])

    muscle_updates = {}
    totals = {
        "training_days": 1,
        "total_exercises": 0,
        "total_sets": 0,
        "total_reps": 0,
        "total_duration_minutes": 0,
        "total_calories_burned": 0
    }

    for workout in raw_doc["workout_data"]:
        muscle = workout["muscle_group"]
        exercise = workout["exercise_name"]

        sets = workout["sets"]
        reps = sum(workout["reps"])
        calories = workout.get("calories_burned", 0)
        duration = workout.get("duration_minutes", 0)

        avg_weight = round(sum(workout["weight"]) / len(workout["weight"]), 2)
        max_weight = max(workout["weight"])

        totals["total_exercises"] += 1
        totals["total_sets"] += sets
        totals["total_reps"] += reps
        totals["total_duration_minutes"] += duration
        totals["total_calories_burned"] += calories

        muscle_updates.setdefault(muscle, {
            "total_sets": 0,
            "total_reps": 0,
            "total_calories": 0,
            "exercises": {}
        })

        muscle_updates[muscle]["total_sets"] += sets
        muscle_updates[muscle]["total_reps"] += reps
        muscle_updates[muscle]["total_calories"] += calories

        ex = muscle_updates[muscle]["exercises"].setdefault(exercise, {
            "sessions": 0,
            "total_sets": 0,
            "total_weight": 0,
            "max_weight": 0,
            "rep_min": 999,
            "rep_max": 0,
            "last_trained": raw_doc["date"]
        })

        ex["sessions"] += 1
        ex["total_sets"] += sets
        ex["total_weight"] += avg_weight * sets
        ex["max_weight"] = max(ex["max_weight"], max_weight)
        ex["rep_min"] = min(ex["rep_min"], min(workout["reps"]))
        ex["rep_max"] = max(ex["rep_max"], max(workout["reps"]))
        ex["last_trained"] = raw_doc["date"]

    return week_key, date_obj, muscle_updates, totals
def upsert_weekly_workout_summary(db, raw_doc):
    week_key, date_obj, muscle_updates, totals = build_weekly_workout_update(raw_doc)

    base_filter = {
        "user_id": raw_doc["user_id"],
        "week": week_key
    }

    update_doc = {
        "$setOnInsert": {
            "user_id": raw_doc["user_id"],
            "week": week_key,
            "start_date": date_obj.strftime("%Y-%m-%d")
        },
        "$inc": {
            "workout_summary.totals.training_days": totals["training_days"],
            "workout_summary.totals.total_exercises": totals["total_exercises"],
            "workout_summary.totals.total_sets": totals["total_sets"],
            "workout_summary.totals.total_reps": totals["total_reps"],
            "workout_summary.totals.total_duration_minutes": totals["total_duration_minutes"],
            "workout_summary.totals.total_calories_burned": totals["total_calories_burned"]
        }
    }

    for muscle, m_data in muscle_updates.items():
        prefix = f"workout_summary.by_muscle_group.{muscle}"

        update_doc["$inc"].update({
            f"{prefix}.total_sets": m_data["total_sets"],
            f"{prefix}.total_reps": m_data["total_reps"],
            f"{prefix}.total_calories": m_data["total_calories"]
        })

        for ex_name, ex in m_data["exercises"].items():
            ex_prefix = f"{prefix}.exercises.{ex_name}"

            update_doc["$inc"].update({
                f"{ex_prefix}.sessions": ex["sessions"],
                f"{ex_prefix}.total_sets": ex["total_sets"],
                f"{ex_prefix}.total_weight": ex["total_weight"]
            })

            update_doc.setdefault("$max", {}).update({
                f"{ex_prefix}.max_weight": ex["max_weight"]
            })

            update_doc.setdefault("$set", {}).update({
                f"{ex_prefix}.rep_range": [ex["rep_min"], ex["rep_max"]],
                f"{ex_prefix}.last_trained": ex["last_trained"]
            })

    db.weekly_summary.update_one(
        base_filter,
        update_doc,
        upsert=True
    )
if __name__ == "__main__":
    from backend.db_connection import db

    raw_workout_doc = { "_id": { "$oid": "693bde4e3c796625f6006901" }, "user_id": "6ff54cd5-593a-4cdd-81a4-bb9dca658c0d", "date": "2025-12-13", "workout_data": [ { "exercise_name": "bench press", "muscle_group": "Chest", "sets": 3, "reps": [ 10, 8, 6], "weight": [ 55, 50, 50 ], "duration_minutes": 6, "calories_burned": 35 } ], "summary": { "total_exercises": 1, "total_sets": 3, "total_reps": 24, "total_duration_minutes": 6, "total_calories_burned": 35 }, "created_at": { "$date": "2025-12-13T09:20:14.159Z" } }

    upsert_weekly_workout_summary(db, raw_workout_doc)