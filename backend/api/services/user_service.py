import os
from datetime import datetime
from typing import Dict, Any
from macro_generator import generate_macro

user_col = None
user_data_col=None

try:
    from db_connection import db as _db
    user_col = _db['users']
    print("Using user_col from db_connection module")
except Exception:
    user_col = None
try:
    from db_connection import db as _db
    user_data_col=_db['user_data']
    print("Using user_data_col from db_connection module")
except Exception:
    user_data_col = None

if user_col is None:
    try:
        from pymongo import MongoClient
        MONGO_URI = os.getenv("MONGO_URI")
        if MONGO_URI:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            DB_NAME = os.getenv("DB_NAME")
            db_from_uri = client[DB_NAME]
            user_col = db_from_uri["users"]
            print("Using user_col from direct MongoDB connection")
    except Exception:
        user_col = None
if user_data_col is None:
    try:
        from pymongo import MongoClient
        MONGO_URI = os.getenv("MONGO_URI")
        if MONGO_URI:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            DB_NAME = os.getenv("DB_NAME")
            db_from_uri = client[DB_NAME]
            user_data_col = db_from_uri["user_data"]
            print("Using user_data_col from direct MongoDB connection")
    except Exception:
        user_data_col = None

def generate_user_data(user_payload: Dict[str, Any]) -> Dict[str, Any]:
    user_payload=dict(user_payload)

    if "user_id" not in user_payload:
        raise ValueError("user_payload must include 'user_id'")

    if user_col is None:
        raise RuntimeError(
            "No MongoDB collection available as 'user_col'.\n"
            "Provide one of the following in your environment:\n"
            " - a module `db_connection` exposing `db` (pymongo.Database),\n"
            " - a module `db` exposing a `db` (pymongo.Database),\n"
            " - set MONGO_URI environment variable so the service can connect directly.\n"
            "Or adapt `api/services/macro_service.py` to your project's DB loader."
        )

    filter_q = {"user_id": user_payload["user_id"]}

    result = user_col.update_one(filter_q, {"$set": user_payload},upsert=True)

    stored_doc = user_col.find_one(filter_q, {"_id": 0})
    return stored_doc or user_payload
def view_user(user_id: str) -> Dict[str, Any]:
    if user_col is None:
        raise RuntimeError(
            "No MongoDB collection available as 'user_col'.\n"
            "Provide one of the following in your environment:\n"
            " - a module `db_connection` exposing `db` (pymongo.Database),\n"
            " - a module `db` exposing a `db` (pymongo.Database),\n"
            " - set MONGO_URI environment variable so the service can connect directly.\n"
            "Or adapt `api/services/macro_service.py` to your project's DB loader."
        )

    filter_q = {"user_id": user_id}

    stored_doc = user_col.find_one(filter_q, {"_id": 0})
    if not stored_doc:
        temp_doc=user_data_col.find_one(filter_q, {"_id": 0, "name": 1})
        return {
          "name": temp_doc["name"],
          "age": 0,
          "gender": 'NA',
          "height_cm": 0,
          "weight_kg": 0,
          "activity_level":"NA",
          "goal": "NA",
          "target_weeks": 0,
          "target_weight_kg": 0,
        }

    return stored_doc