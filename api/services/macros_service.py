import os
from datetime import datetime,date
from typing import Dict, Any
from macro_generator import generate_macro
from tracker.progress_tracker import generate_initial_week
macro_collection = None

try:
    from db_connection import db as _db
    macro_collection = _db['macro_plans']
    print("Using macro_collection from db_connection module")
except Exception:
    try:
        import db as _db_mod 
        if hasattr(_db_mod, "__getitem__"):
            macro_collection = _db_mod['macro_pans']
        else:
            db_obj = getattr(_db_mod, "db", None) or getattr(_db_mod, "get_db", None)
            if callable(db_obj):
                macro_collection = db_obj()['macro_plans']
            elif db_obj is not None:
                macro_collection = db_obj['macro_plans']
    except Exception:
        macro_collection = None

if macro_collection is None:
    try:
        from pymongo import MongoClient
        MONGO_URI = os.getenv("MONGO_URI")
        if MONGO_URI:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            db_from_uri = client.get_default_database() or client["mydb"]
            macro_collection = db_from_uri["macros"]
            print("Using macro_collection from direct MongoDB connection")
    except Exception:
        macro_collection = None

def generate_and_upsert_macro(user_payload: Dict[str, Any]) -> Dict[str, Any]:

    if "user_id" not in user_payload:
        raise ValueError("user_payload must include 'user_id'")

    plan = generate_macro(user_payload)

    now_iso = datetime.utcnow().isoformat()
    plan_doc = dict(plan)
    plan_doc["updated_at"] = now_iso
    plan_doc.pop("created_at", None)

    if macro_collection is None:
        raise RuntimeError(
            "No MongoDB collection available as 'macro_collection'.\n"
            "Provide one of the following in your environment:\n"
            " - a module `db_connection` exposing `db` (pymongo.Database),\n"
            " - a module `db` exposing a `db` (pymongo.Database),\n"
            " - set MONGO_URI environment variable so the service can connect directly.\n"
            "Or adapt `api/services/macro_service.py` to your project's DB loader."
        )

    filter_q = {"user_id": plan_doc["user_id"]}
    update_q = {
        "$set": plan_doc,
        "$setOnInsert": {"created_at": now_iso}
    }

    result = macro_collection.update_one(filter_q, update_q, upsert=True)

    stored_doc = macro_collection.find_one(filter_q, {"_id": 0})
    try:
        generate_initial_week(plan["user_id"], date.today())
    except Exception as e:
        print(f"generate_initial_week failed for {plan_doc['user_id']}: {e}")
    return stored_doc or plan_doc
