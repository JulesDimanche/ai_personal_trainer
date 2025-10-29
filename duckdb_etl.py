# duckdb_etl.py
import os
import json
import time
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
import duckdb

# try to reuse your existing db_connection module (calories_query.py used this)
try:
    import db_connection as dbc
    mongo_db = dbc.db
    diet_col = getattr(dbc, "diet_col", mongo_db["diet_logs"])
    workout_col = getattr(dbc, "workout_col", mongo_db["workouts_logs"])
    progress_col = getattr(dbc, "progress_col", mongo_db["progress"])
except Exception:
    # fallback to environment variables if db_connection is not available
    from pymongo import MongoClient
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DB_NAME = os.getenv("DB_NAME", "test")
    client = MongoClient(MONGO_URI)
    mongo_db = client[DB_NAME]
    diet_col = mongo_db["diet_logs"]
    workout_col = mongo_db["workouts_logs"]
    progress_col = mongo_db["progress"]

DUCKDB_PATH = os.getenv("DUCKDB_PATH", "trainer.duckdb")
ETL_METADATA_TABLE = "etl_metadata"

con = duckdb.connect(DUCKDB_PATH)


def init_schema():
    """
    Creates the foods and workouts tables if they don't exist.
    Also creates the etl metadata table.
    """
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS foods (
            source_row_id TEXT PRIMARY KEY,
            user_id TEXT,
            date DATE,
            meal_type TEXT,
            food TEXT,
            quantity DOUBLE,
            weight DOUBLE,
            calories DOUBLE,
            proteins DOUBLE,
            fats DOUBLE,
            carbs DOUBLE,
            fiber DOUBLE,
            source_doc_id TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        );
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS workouts (
            source_row_id TEXT PRIMARY KEY,
            user_id TEXT,
            date DATE,
            exercise_name TEXT,
            muscle_group TEXT,
            sets INTEGER,
            reps TEXT, -- JSON string of reps list
            weight DOUBLE,
            duration_minutes DOUBLE,
            calories_burned DOUBLE,
            source_doc_id TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        );
        """
    )
    con.execute(
    """
    CREATE TABLE IF NOT EXISTS daily_progress (
        source_doc_id TEXT PRIMARY KEY,
        user_id TEXT,
        date DATE,
        goal TEXT,
        achieved_calories DOUBLE,
        achieved_weight_kg DOUBLE,
        achieved_workout_intensity DOUBLE,
        expected_daily_calories DOUBLE,
        expected_target_weight_kg DOUBLE,
        expected_workout_intensity DOUBLE,
        progress_calories DOUBLE,
        progress_protein DOUBLE,
        progress_carbs DOUBLE,
        progress_fats DOUBLE,
        remarks TEXT,
        week_number INTEGER,
        created_at TIMESTAMP,
        updated_at TIMESTAMP
    );
    """
    )

    # metadata table to store last_etl_run as ISO timestamp
    con.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {ETL_METADATA_TABLE} (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """
    )
    # insert initial last_etl_run if not exists
    res = con.execute(f"SELECT value FROM {ETL_METADATA_TABLE} WHERE key='last_etl_run'").fetchall()
    if not res:
        con.execute(f"INSERT INTO {ETL_METADATA_TABLE} VALUES ('last_etl_run', NULL);")


"""def get_last_etl_run() -> datetime:
    row = con.execute(f"SELECT value FROM {ETL_METADATA_TABLE} WHERE key='last_etl_run'").fetchall()
    if row and row[0][0]:
        return datetime.fromisoformat(row[0][0])
    return None"""


def set_last_etl_run(ts: datetime):
    iso = ts.isoformat()
    con.execute(f"INSERT OR REPLACE INTO {ETL_METADATA_TABLE} VALUES ('last_etl_run', ?)", [iso])


def flatten_diet_doc(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Turns a single Mongo diet_logs doc into multiple rows for the foods table.
    Handles created_at/updated_at consistently:
      - If both exist, use them.
      - If only created_at exists, use it for both.
      - If neither exists, fallback to current UTC time.
    """
    rows = []
    _id = str(doc.get("_id"))
    user_id = doc.get("user_id")
    date = doc.get("date")

    # --- Timestamp normalization ---
    created_at = doc.get("created_at")
    updated_at = doc.get("updated_at")

    # Convert BSON/Datetime objects to ISO string
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()
    if isinstance(updated_at, datetime):
        updated_at = updated_at.isoformat()

    # Fallback logic
    if not created_at and not updated_at:
        created_at = updated_at = datetime.utcnow().isoformat()
    elif created_at and not updated_at:
        updated_at = created_at
    elif updated_at and not created_at:
        created_at = updated_at

    # --- Flatten meals ---
    plan_data = doc.get("plan_data", []) or []
    for mi, meal in enumerate(plan_data):
        meal_type = meal.get("meal_type")
        items = meal.get("items", []) or []
        for ii, it in enumerate(items):
            source_row_id = f"{_id}::meal::{mi}::item::{ii}"
            rows.append({
                "source_row_id": source_row_id,
                "user_id": user_id,
                "date": date,
                "meal_type": meal_type,
                "food": it.get("food"),
                "quantity": float(it.get("quantity")) if it.get("quantity") is not None else None,
                "weight": float(it.get("weight")) if it.get("weight") is not None else None,
                "calories": float(it.get("calories")) if it.get("calories") is not None else None,
                "proteins": float(it.get("proteins")) if it.get("proteins") is not None else None,
                "fats": float(it.get("fats")) if it.get("fats") is not None else None,
                "carbs": float(it.get("carbs")) if it.get("carbs") is not None else None,
                "fiber": float(it.get("fiber")) if it.get("fiber") is not None else None,
                "source_doc_id": _id,
                "created_at": created_at,
                "updated_at": updated_at
            })
    return rows

def flatten_workout_doc(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Turns a single Mongo workouts_logs doc into multiple rows for the workouts table.
    Handles created_at/updated_at consistently:
      - If both exist, use them.
      - If only created_at exists, use it for both.
      - If neither exists, fallback to current UTC time.
    """
    rows = []
    _id = str(doc.get("_id"))
    user_id = doc.get("user_id")
    date = doc.get("date")

    # --- Timestamp normalization ---
    created_at = doc.get("created_at")
    updated_at = doc.get("updated_at")

    # Convert BSON/Datetime objects to ISO string
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()
    if isinstance(updated_at, datetime):
        updated_at = updated_at.isoformat()

    # Fallback logic
    if not created_at and not updated_at:
        created_at = updated_at = datetime.utcnow().isoformat()
    elif created_at and not updated_at:
        updated_at = created_at
    elif updated_at and not created_at:
        created_at = updated_at

    # --- Flatten workout data ---
    workout_data = doc.get("workout_data", []) or []
    for wi, ex in enumerate(workout_data):
        source_row_id = f"{_id}::exercise::{wi}"
        rows.append({
            "source_row_id": source_row_id,
            "user_id": user_id,
            "date": date,
            "exercise_name": ex.get("exercise_name"),
            "muscle_group": ex.get("muscle_group"),
            "sets": int(ex.get("sets") or 0),
            "reps": json.dumps(ex.get("reps") or []),
            "weight": float(ex.get("weight") or 0) if ex.get("weight") is not None else None,
            "duration_minutes": float(ex.get("duration_minutes") or 0) if ex.get("duration_minutes") is not None else None,
            "calories_burned": float(ex.get("calories_burned") or 0) if ex.get("calories_burned") is not None else None,
            "source_doc_id": _id,
            "created_at": created_at,
            "updated_at": updated_at
        })
    return rows


def flatten_progress_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    _id = str(doc.get("_id"))
    achieved = doc.get("achieved", {}) or {}
    expected = doc.get("expected", {}) or {}
    progress = doc.get("progress_percentage", {}) or {}
    macros = progress.get("macros", {}) or {}

    return {
        "source_doc_id": _id,
        "user_id": doc.get("user_id"),
        "date": doc.get("date"),
        "goal": doc.get("goal"),
        "achieved_calories": achieved.get("calories"),
        "achieved_weight_kg": achieved.get("weight_kg"),
        "achieved_workout_intensity": achieved.get("workout_intensity"),
        "expected_daily_calories": expected.get("daily_calories"),
        "expected_target_weight_kg": expected.get("target_weight_kg"),
        "expected_workout_intensity": expected.get("workout_intensity"),
        "progress_calories": progress.get("calories"),
        "progress_protein": macros.get("protein_g"),
        "progress_carbs": macros.get("carbs_g"),
        "progress_fats": macros.get("fats_g"),
        "remarks": doc.get("remarks"),
        "week_number": doc.get("week_number"),
        "created_at": doc.get("created_at") or datetime.utcnow().isoformat(),
        "updated_at": doc.get("updated_at") or datetime.utcnow().isoformat()
    }

def etl_incremental():
    """
    Incremental ETL:
    - Syncs only documents created or updated since last_etl_run.
    - Handles both datetime and string timestamps.
    - Works correctly even if ETL runs multiple times per day.
    """
    init_schema()
    today_str = datetime.utcnow().strftime("%Y-%m-%d")  # always use fresh current UTC timestamp
    query={"date": today_str}
    # Fetch changed documents
    diet_docs = list(diet_col.find(query))
    workout_docs = list(workout_col.find(query))
    progress_docs = list(progress_col.find())

    # Flatten documents
    diet_rows, diet_ids_to_delete = [], []
    for d in diet_docs:
        rows = flatten_diet_doc(d)
        diet_rows.extend(rows)
        diet_ids_to_delete.extend([r["source_row_id"] for r in rows])

    wo_rows, wo_ids_to_delete = [], []
    for w in workout_docs:
        rows = flatten_workout_doc(w)
        wo_rows.extend(rows)
        wo_ids_to_delete.extend([r["source_row_id"] for r in rows])

    progress_rows, progress_ids_to_delete = [], []
    for p in progress_docs:
        row = flatten_progress_doc(p)
        progress_rows.append(row)
        progress_ids_to_delete.append(row["source_doc_id"])

    # Delete and insert new rows
    if diet_ids_to_delete:
        con.execute("DELETE FROM foods WHERE source_row_id IN (" + ",".join(["?"] * len(diet_ids_to_delete)) + ")", diet_ids_to_delete)
    if wo_ids_to_delete:
        con.execute("DELETE FROM workouts WHERE source_row_id IN (" + ",".join(["?"] * len(wo_ids_to_delete)) + ")", wo_ids_to_delete)
    if progress_ids_to_delete:
        con.execute("DELETE FROM daily_progress WHERE source_doc_id IN (" + ",".join(["?"] * len(progress_ids_to_delete)) + ")", progress_ids_to_delete)

    if diet_rows:
        df_foods = pd.DataFrame(diet_rows)
        con.register("tmp_foods_df", df_foods)
        con.execute("INSERT INTO foods SELECT * FROM tmp_foods_df")
        con.unregister("tmp_foods_df")

    if wo_rows:
        df_wo = pd.DataFrame(wo_rows)
        con.register("tmp_wo_df", df_wo)
        con.execute("INSERT INTO workouts SELECT * FROM tmp_wo_df")
        con.unregister("tmp_wo_df")

    if progress_rows:
        for r in progress_rows:
            con.execute("DELETE FROM daily_progress WHERE user_id=? AND date=?", [r["user_id"], r["date"]])
        df_progress = pd.DataFrame(progress_rows)
        con.register("tmp_progress_df", df_progress)
        con.execute("INSERT INTO daily_progress SELECT * FROM tmp_progress_df")
        con.unregister("tmp_progress_df")

    # ✅ Save the actual current time as the ETL checkpoint
    set_last_etl_run(datetime.utcnow())

    print(f"ETL complete. diet_docs={len(diet_docs)} workout_docs={len(workout_docs)} progress_docs={len(progress_docs)}. Time={datetime.utcnow().isoformat()}")


if __name__ == "__main__":
    # run the ETL now
    etl_incremental()
