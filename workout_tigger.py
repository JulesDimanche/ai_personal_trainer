import datetime
from db_connection import workout_summary_col
def handle_wo_summary_trigger(user_id, summary_text, timestamp):
    try:
        date_str = timestamp.strftime("%Y-%m-%d")
        query = {"user_id": user_id, "date": date_str}

        new_summary = summary_text.get("daily_summary", summary_text)

        update = {
            "$inc": {
                "summary_text.total_exercises": new_summary.get("total_exercises", 0),
                "summary_text.total_sets": new_summary.get("total_sets", 0),
                "summary_text.total_reps": new_summary.get("total_reps", 0),
                "summary_text.total_duration_minutes": new_summary.get("total_duration_minutes", 0),
                "summary_text.total_calories_burned": new_summary.get("total_calories_burned", 0),
            },
            "$setOnInsert": {
                "user_id": user_id,
                "date": date_str,
                "summary_text.created_at": new_summary.get("created_at", datetime.datetime.utcnow().isoformat()),
                "created_at": datetime.datetime.utcnow()
            },
            "$set": {
                "updated_at": datetime.datetime.utcnow()
            }
        }

        workout_summary_col.update_one(query, update, upsert=True)

        print(f"✅ Daily summary updated for {user_id} on {date_str}")

    except Exception as e:
        print(f"⚠️ Failed to update daily summary: {e}")