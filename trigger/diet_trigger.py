import datetime
from backend.db_connection import summary_col
def handle_summary_trigger(user_id, summary_text, timestamp):
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

        summary_col.update_one(query, update, upsert=True)

        print(f"✅ Daily summary updated for {user_id} on {date_str}")

    except Exception as e:
        print(f"⚠️ Failed to update daily summary: {e}")