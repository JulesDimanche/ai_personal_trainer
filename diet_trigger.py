import datetime
from db_connection import summary_col
def handle_summary_trigger(user_id, summary_text, timestamp):
    try:
        date_str = timestamp.strftime("%Y-%m-%d")

        query = {"user_id": user_id, "date": date_str}

        new_summary = summary_text.get("daily_summary", summary_text)

        update = {
            "$inc": {
                "summary_text.total_calories": new_summary.get("total_calories", 0),
                "summary_text.total_protein": new_summary.get("total_protein", 0),
                "summary_text.total_fat": new_summary.get("total_fat", 0),
                "summary_text.total_carb": new_summary.get("total_carb", 0),
                "summary_text.total_fiber": new_summary.get("total_fiber", 0),
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

        summary_col.update_one(query, update, upsert=True)

        print(f"✅ Daily summary updated for {user_id} on {date_str}")

    except Exception as e:
        print(f"⚠️ Failed to update daily summary: {e}")