import datetime
from db_connection import workout_summary_col
def handle_wo_summary_trigger(user_id, summary_text):
    try:
        summary_doc = {
            "user_id": user_id,
            "summary_text": summary_text,
            "created_at": datetime.datetime.utcnow()
        }
        workout_summary_col.insert_one(summary_doc)
        print("📄 Summary stored in 'workout_summary' collection.")
    except Exception as e:
        print(f"⚠️ Failed to store summary: {e}")
