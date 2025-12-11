from backend.tracker.progress_tracker import update_daily_progress
import os

weight_col=None
try:
    from backend.db_connection import db
    weight_col=db["weights"]
    print("weight_col is loaded from mongodb")
except Exception:
    weight_col=None
if weight_col is None:
    try:
        from pymongo import MongoClient
        MONGO_URI = os.getenv("MONGO_URI")
        if MONGO_URI:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            db_from_uri = client.get_default_database() or client["mydb"]
            weight_col = db_from_uri["weights"]
            print("Using weight_col from direct MongoDB connection")
    except Exception:
        weight_col = None

def weight_save(weight_data):
    user_id_check = weight_data.get("user_id") if isinstance(weight_data, dict) else (hasattr(weight_data, "user_id") and weight_data.user_id)
    if not user_id_check:
        raise ValueError("weight_data must include 'user_id'")
    if weight_col is None:
        raise RuntimeError(
            "No MongoDB collection available as 'weight_col'.\n"
            "Provide one of the following in your environment:\n"
            " - a module `db_connection` exposing `db` (pymongo.Database),\n"
            " - a module `db` exposing a `db` (pymongo.Database),\n"
            " - set MONGO_URI environment variable so the service can connect directly.\n"
            "Or adapt `api/services/calories_service.py` to your project's DB loader."
        )
    weight = weight_data.get("weight") if isinstance(weight_data, dict) else weight_data.weight
    today_date = weight_data.get("date") if isinstance(weight_data, dict) else weight_data.date
    user_id = weight_data.get("user_id") if isinstance(weight_data, dict) else weight_data.user_id
    try:
        doc=weight_col.find_one({"user_id": user_id, "date": today_date})
        if not doc:
            document={"user_id":user_id,"date":today_date,"weight":weight}
            weight_col.insert_one(document)
        else:
            weight_col.update_one({"user_id":user_id,"date":today_date},
                                   {"$set": {"weight": weight}})
        update_daily_progress(user_id,today_date)
        return {"status": "success", "message": "Weight saved successfully."}
    except Exception as e:
        print(f"❌ Error inserting/updating workout plan: {e}")
        return None
def view_weight(user_id):
    if not user_id:
        raise ValueError("user_id is required")
    try:
        data = list(
            weight_col.find(
                {"user_id": user_id},
                {"_id": 0, "date": 1, "weight": 1}
            ).sort("date", 1)
        )

        return {
            "status": "success",
            "weights": data
        }
    except Exception as e:
        print(f"❌ Error fetching weight data: {e}")
        return {"status": "error", "message": str(e)}