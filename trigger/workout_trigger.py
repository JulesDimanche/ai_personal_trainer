import datetime
from db_connection import workout_summary_col
def handle_wo_summary_trigger(user_id, summary_text, timestamp):
    try:
        date_str=timestamp
        #date_str = timestamp.strftime("%Y-%m-%d")
        query = {"user_id": user_id, "date": date_str}

        new_summary = summary_text.get("daily_summary", summary_text)

        update = {
            "$set": {
                "user_id": user_id,
                "date": date_str,
                "summary_text": new_summary,
                "updated_at": datetime.datetime.utcnow()
            },
            "$setOnInsert": {
                "created_at": datetime.datetime.utcnow()
            }
        }

        workout_summary_col.update_one(query, update, upsert=True)

        print(f"✅ Daily workout summary saved for {user_id} on {date_str}")

    except Exception as e:
        print(f"⚠️ Failed to update workout summary: {e}")
