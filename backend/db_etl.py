import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
import pandas as pd
import duckdb
from pymongo import MongoClient
from workout_etl import upsert_weekly_workout_summary
from food_etl import upsert_weekly_food_summary
from dotenv import load_dotenv
load_dotenv()
try:
    MONGO_URI = os.environ.get("MONGO_URI")
    DB_NAME = os.environ.get("DB_NAME")
    client = MongoClient(MONGO_URI)
    mongo_db = client[DB_NAME]
    diet_col = mongo_db["diet_logs"]
    workout_col = mongo_db["workouts_logs"]
except Exception:
    import db_connection as dbc
    mongo_db = dbc.db
    diet_col = getattr(dbc, "diet_col", mongo_db["diet_logs"])
    workout_col = getattr(dbc, "workout_col", mongo_db["workouts_logs"])

def start_etl():
    today=datetime.utcnow().date()-timedelta(days=1)
    diet_docs = list(
            diet_col.find({
                "summary.created_at": {"$gte":today.strftime("%Y-%m-%d")}
            })
        )
    workout_docs = list(
            workout_col.find({
                "created_at": {"$gte": today.strftime("%Y-%m-%d")}
            })
        )
    for doc in diet_docs:
        upsert_weekly_food_summary(mongo_db, doc)
    for doc in workout_docs:
        upsert_weekly_workout_summary(mongo_db, doc)    
    return 
if __name__ == "__main__":
    start_etl()