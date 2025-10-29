"""
progress_adaptive.py

Adaptive 7-day rolling progress generator for a fitness app.

Requirements:
- pip install pymongo
- MongoDB reachable at MONGO_URI (default localhost)

Collections assumed (names can be changed):
- plans          : stores user's plan metadata (start_date, end_date, base targets)
- macros         : stores expected macros (if you store these separately)
- calories       : stores daily calorie intake documents { user_id, date, calories, macros:{protein_g,carbs_g,fats_g} }
- workouts       : stores workout sessions documents { user_id, date, calories_burned, intensity_score }
- weights        : stores weight logs { user_id, date, weight_kg }
- progress       : stores per-day progress documents (we create/update these)
- weekly_summary : stores weekly summary & adjustments

This module provides:
- generate_initial_week(user_id, plan_id)
- update_daily_progress(user_id, date)
- aggregate_and_adapt_week(user_id, week_start_date)
- generate_next_week_docs(user_id, adjusted_targets, start_date)
"""

from pymongo import MongoClient, ASCENDING
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import math
import os
from db_connection import progress_col, diet_col, workout_col, user_col, macro_collection,progress_weekly_col,weight_col,summary_col,workout_summary_col

# ---------- Helpers ----------

def iso_date(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")

def parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d")

def date_range(start_date: datetime, days: int):
    for i in range(days):
        yield start_date + timedelta(days=i)

# simple intensity mapping from workout documents (if you store a textual intensity, adapt)
def compute_workout_intensity_for_day(user_id: str, date_str: str) -> Optional[float]:
    """
    Compute daily workout intensity score from workouts collection.
    Returns None if no workouts recorded.
    Assumes workouts docs have 'calories_burned' (number) and/or 'intensity_score' (number 0-100).
    We'll combine both heuristically.
    """
    docs = list(workout_summary_col.find({"user_id": user_id, "date": date_str}))
    if not docs:
        return None
    # weighted score example: normalize calories and intensity_score
    total_cal = 0
    scores = []
    for doc in docs:
        summary = doc.get("summary_text", {})
        total_cal += summary.get("total_calories_burned", 0)
        if summary.get("total_duration_minutes") is not None:
            scores.append(summary["total_duration_minutes"])
    avg_score = (sum(scores) / len(scores)) if scores else None

    # heuristics: calories -> mapped to 0-100 based on typical range (100-800)
    if total_cal <= 0 and avg_score is None:
        return None
    cal_mapped = min(100, (total_cal / 800) * 100) if total_cal > 0 else 0
    if avg_score is None:
        return cal_mapped
    # combine evenly
    return (cal_mapped * 0.5) + (avg_score * 0.5)

def fetch_daily_calories_and_macros(user_id: str, date_str: str) -> Dict[str, Any]:
    doc = summary_col.find_one({"user_id": user_id, "date": date_str})
    if not doc or "summary_text" not in doc:
        return {"calories": None, "macros": None}

    summary = doc["summary_text"]
    return {
        "calories": summary.get("total_calories"),
        "macros": {
            "protein_g": summary.get("total_protein"),
            "carbs_g": summary.get("total_carb"),
            "fats_g": summary.get("total_fat")
        }
    }

def fetch_weight_for_date(user_id: str, date_str: str) -> Optional[float]:
    doc = weight_col.find_one({"user_id": user_id,"date": date_str})
    if not doc:
        return None
    # Adjust to match your actual schema field
    weight_value = doc.get("weight") or doc.get("weight_kg")
    try:
        return float(weight_value)
    except (TypeError, ValueError):
        return None

# ---------- Core functions ----------

def create_or_update_progress_doc(user_id: str, date_str: str, expected: Dict[str, Any], achieved: Dict[str, Any], week_number: int, goal: str):
    """
    Insert or update a daily progress document.
    Notes:
      - progress_percentage will NOT include a 'weight' key anymore (we use weight_kg in weekly aggregation).
      - achieved should contain 'weight_kg' when available.
    """
    # calculate progress percentages where possible
    progress_percentage = {}
    # calories percentage
    try:
        if expected.get("daily_calories") and achieved.get("calories") is not None:
            progress_percentage["calories"] = round((achieved["calories"] / expected["daily_calories"]) * 100, 2)
        else:
            progress_percentage["calories"] = None
    except Exception:
        progress_percentage["calories"] = None

    progress_percentage["macros"] = {}
    if expected.get("daily_macros") and achieved.get("macros"):
        for k in ["protein_g", "carbs_g", "fats_g"]:
            exp_val = expected["daily_macros"].get(k)
            ach_val = achieved["macros"].get(k)
            try:
                progress_percentage["macros"][k] = round((ach_val / exp_val) * 100, 2) if exp_val and ach_val is not None else None
            except Exception:
                progress_percentage["macros"][k] = None
    else:
        progress_percentage["macros"] = {"protein_g": None, "carbs_g": None, "fats_g": None}

    # We do NOT compute a daily 'weight' percentage here. Weekly aggregation will handle weight comparisons using weight_kg.
    doc = {
        "user_id": user_id,
        "date": date_str,
        "week_number": week_number,
        "goal": goal,
        "expected": expected,
        "achieved": achieved,
        "progress_percentage": progress_percentage,
        "remarks": None
    }
    progress_col.update_one({"user_id": user_id, "date": date_str}, {"$set": doc}, upsert=True)
    return doc


def generate_initial_week(user_id: str, plan_id: str, start_date: Optional[str] = None):
    """
    Generate the initial 7-day progress docs for a plan.
    plan document expected to contain: daily_calories, daily_macros, target_weight_kg, workout_intensity, goal, time_period_days, start_date
    """
    plan = macro_collection.find_one({"user_id": user_id})
    if not plan:
        raise ValueError(f"{user_id} not found")

    if start_date:
        start_dt = parse_date(start_date)
    else:
        start_dt = parse_date(plan.get("start_date")) if plan.get("start_date") else datetime.utcnow()

    base_expected = {
    "daily_calories": plan.get("Goal_Calories"),
    "daily_macros": {
        "protein_g": plan["Macros"]["Protein_g"],
        "fats_g": plan["Macros"]["Fats_g"],
        "carbs_g": plan["Macros"]["Carbs_g"],
        "fiber_g":plan['Macros']['Fiber_g']
    },
    "target_weight_kg": plan.get("Target_weight_kg"),   # or None if unavailable
    "workout_intensity": plan.get("workout_intensity", 55.0)# fallback
}

    goal = plan.get("goal_type","maintain")
    week_number=1

    week_data=plan['Weekly_Plan'][0]
    base_expected['daily_calories']=week_data['expected_calories']
    base_expected['daily_macros']={'protein_g':week_data['expected_macros']['Protein_g'],
                                  'fats_g':week_data['expected_macros']['Fats_g'],
                                  'carbs_g':week_data['expected_macros']['Carbs_g'],
                                  'fiber_g':plan['Macros']['Fiber_g']}
    base_expected['target_weight_kg']=week_data['expected_weight_kg']

    for d in date_range(start_dt, 7):
        date_str = iso_date(d)
        # initial achieved fields null / placeholders
        achieved = {"calories": None, "macros": None, "workout_intensity": None, "weight_kg": None}
        create_or_update_progress_doc(user_id=user_id, date_str=date_str, expected=base_expected, achieved=achieved, week_number=week_number, goal=goal)
    return {"status": "ok", "generated_from": iso_date(start_dt), "days": 7}

def update_daily_progress(user_id: str, date_obj: datetime):
    """
    Pull data from calories/workouts/weights collections for the date and update the progress doc.
    If expected isn't present (no progress doc), this function will attempt to compute expected from plan.
    """
    date_str = iso_date(date_obj)
    # fetch existing progress doc to get expected values
    existing = progress_col.find_one({"user_id": user_id, "date": date_str})
    if existing:
        expected = existing["expected"]
        week_number = existing.get("week_number", 0)
        goal = existing.get("goal", "unspecified")
    else:
        # fallback: try to fetch latest plan and compute expected
        plan = macro_collection.find_one({"user_id": user_id}, sort=[("start_date", ASCENDING)])
        if not plan:
            raise ValueError("No plan or progress doc found for user/date")
        expected = {
            "daily_calories": plan.get("daily_calories"),
            "daily_macros": plan.get("daily_macros"),
            "target_weight_kg": plan.get("target_weight_kg"),
            "workout_intensity": plan.get("workout_intensity")
        }
        week_number = 0
        goal = plan.get("goal", "unspecified")

    # fetch achieved pieces
    cal_and_macros = fetch_daily_calories_and_macros(user_id, date_str)
    achieved_calories = cal_and_macros["calories"]
    achieved_macros = cal_and_macros["macros"]

    workout_intensity = compute_workout_intensity_for_day(user_id, date_str)
    weight_kg = fetch_weight_for_date(user_id,date_str)

    achieved = {
        "calories": achieved_calories,
        "macros": achieved_macros,
        "workout_intensity": workout_intensity,
        "weight_kg": weight_kg
    }

    updated_doc = create_or_update_progress_doc(user_id=user_id, date_str=date_str, expected=expected, achieved=achieved, week_number=week_number, goal=goal)
    return updated_doc

def _safe_avg(values: List[float]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return (sum(vals) / len(vals)) if vals else None

def aggregate_and_adapt_week(user_id: str, week_start_date: str):
    """
    Aggregates the 7-day window starting at week_start_date (YYYY-MM-DD), compares expected vs achieved,
    computes adjustments, stores a weekly_summary doc, and generates the next 7-day window with adjusted targets.

    Key fixes:
      - weights are collected as (date, weight_kg) tuples and sorted by date.
      - weekly weight comparison is computed using weight_kg.
      - adjusted macros fallback to the plan's next-week macros when our computed adjusted_macros are incomplete.
    """
    start_dt = parse_date(week_start_date)
    dates = [iso_date(start_dt + timedelta(days=i)) for i in range(7)]
    docs = list(progress_col.find({"user_id": user_id, "date": {"$in": dates}}))

    if len(docs) < 1:
        raise ValueError("No progress documents found for the week start")

    # collect aggregates
    achieved_calories_list = []
    achieved_protein = []
    achieved_carbs = []
    achieved_fats = []
    weights_by_date = []  # will store tuples (date_str, weight_kg)
    workout_scores = []
    expected_calories_values = []
    expected_macros_list = []

    for doc in docs:
        ach = doc.get("achieved", {})
        exp = doc.get("expected", {})

        if ach.get("calories") is not None:
            achieved_calories_list.append(ach.get("calories"))

        macros = ach.get("macros")
        if macros:
            achieved_protein.append(macros.get("protein_g"))
            achieved_carbs.append(macros.get("carbs_g"))
            achieved_fats.append(macros.get("fats_g"))

        # collect weights as (date, value) only when present
        if ach.get("weight_kg") is not None:
            weights_by_date.append((doc["date"], ach.get("weight_kg")))

        if ach.get("workout_intensity") is not None:
            workout_scores.append(ach.get("workout_intensity"))

        if exp.get("daily_calories") is not None:
            expected_calories_values.append(exp.get("daily_calories"))

        if exp.get("daily_macros"):
            expected_macros_list.append(exp.get("daily_macros"))

    avg_ach_cal = _safe_avg(achieved_calories_list)
    avg_ach_protein = _safe_avg(achieved_protein)
    avg_ach_carbs = _safe_avg(achieved_carbs)
    avg_ach_fats = _safe_avg(achieved_fats)
    avg_workout = _safe_avg(workout_scores)
    avg_expected_cal = _safe_avg(expected_calories_values)

    # average expected macros by key
    def avg_expected_macro_field(field):
        vals = []
        for m in expected_macros_list:
            val = m.get(field)
            try:
                if val is not None:
                    vals.append(float(val))
            except Exception:
                continue
        return _safe_avg(vals)

    avg_expected_protein = avg_expected_macro_field("protein_g")
    avg_expected_carbs = avg_expected_macro_field("carbs_g")
    avg_expected_fats = avg_expected_macro_field("fats_g")

    # handle weights: sort by date and compute first/last/recent_avg
    weights_sorted = sorted(weights_by_date, key=lambda x: x[0])  # sort by ISO date string OK
    first_weight = weights_sorted[0][1] if weights_sorted else None
    last_weight = weights_sorted[-1][1] if weights_sorted else None
    # recent average of last up-to-3 recorded values
    recent_weights_only = [w for (_, w) in weights_sorted[-3:]] if weights_sorted else []
    recent_avg_weight = _safe_avg(recent_weights_only)
    actual_change = (last_weight - first_weight) if (first_weight is not None and last_weight is not None) else None

    plan = macro_collection.find_one({"user_id": user_id})
    last_week_doc = progress_weekly_col.find_one({"user_id": user_id}, sort=[("week_number", -1)])
    week_number = (last_week_doc["week_number"] + 1) if last_week_doc else 1

    # expected weight for this week and next expected weight from plan if available
    expected_weight = None
    next_expected_weight = None
    if plan and "Weekly_Plan" in plan:
        # plan Weekly_Plan is expected to be a list corresponding to weeks (0-indexed)
        if len(plan["Weekly_Plan"]) >= week_number:
            expected_weight = plan["Weekly_Plan"][week_number - 1].get("expected_weight_kg")
        if len(plan["Weekly_Plan"]) > week_number:
            next_expected_weight = plan["Weekly_Plan"][week_number].get("expected_weight_kg")

    # Determine adjustment logic (kept and clarified)
    goal = docs[0].get("goal", "unspecified")
    adjustment_reason = ""
    adjusted_daily_calories = int(round(avg_expected_cal)) if avg_expected_cal is not None else (int(round(avg_ach_cal)) if avg_ach_cal is not None else None)
    adjusted_macros = {
        "protein_g": avg_expected_protein,
        "carbs_g": avg_expected_carbs,
        "fats_g": avg_expected_fats
    }

    # Apply rules using weight_kg comparison to plan expected weight
    if expected_weight is not None and recent_avg_weight is not None:
        diff = recent_avg_weight - expected_weight
        if "lose" in goal.lower():
            if diff > 0.3:
                adjusted_daily_calories = round((adjusted_daily_calories or avg_ach_cal or 0) * 0.94)
                adjustment_reason = f"Weight above expected by {diff:.2f} kg; reducing calories by ~6%."
            elif diff < -0.7:
                adjusted_daily_calories = round((adjusted_daily_calories or avg_ach_cal or 0) * 1.08)
                adjustment_reason = f"Weight below expected by {abs(diff):.2f} kg; increasing calories by ~8%."
            else:
                adjustment_reason = "Weight on track with expected; keeping calories similar."
        elif "gain" in goal.lower() or "muscle" in goal.lower():
            if diff < -0.2:
                adjusted_daily_calories = round((adjusted_daily_calories or avg_ach_cal or 0) * 1.06)
                adjustment_reason = f"Weight below expected by {abs(diff):.2f} kg; increasing calories by ~6%."
            elif diff > 0.8:
                adjusted_daily_calories = round((adjusted_daily_calories or avg_ach_cal or 0) * 0.95)
                adjustment_reason = f"Weight above expected by {diff:.2f} kg; reducing calories by ~5%."
            else:
                adjustment_reason = "Gaining as expected; keeping calories stable."
        else:
            adjustment_reason = "Goal not specified; minor/no adjustment applied."
    else:
        adjustment_reason = "Insufficient weight data or expected weight missing; falling back to adherence rules."

    # If losing and actual_change indicates slow loss, slightly increase protein
    if "lose" in goal.lower() and adjusted_macros.get("protein_g"):
        if actual_change is not None and actual_change > -0.3:
            adjusted_macros["protein_g"] = round(adjusted_macros["protein_g"] * 1.08)
            adjustment_reason += " Increased protein by 8% to support fat loss."

    # If any macro is None, try to fetch from plan Weekly_Plan for the next week (fallback)
    if plan and "Weekly_Plan" in plan:
        # next week index in Weekly_Plan is week_number (0-indexed current week_number-1)
        if len(plan["Weekly_Plan"]) > week_number:
            candidate = plan["Weekly_Plan"][week_number].get("expected_macros") or {}
            # normalize keys if stored differently
            candidate_norm = {
                "protein_g": candidate.get("Protein_g") or candidate.get("protein_g"),
                "carbs_g": candidate.get("Carbs_g") or candidate.get("carbs_g"),
                "fats_g": candidate.get("Fats_g") or candidate.get("fats_g")
            }
            # fill missing macros from candidate
            for k in ["protein_g", "carbs_g", "fats_g"]:
                if adjusted_macros.get(k) is None and candidate_norm.get(k) is not None:
                    try:
                        adjusted_macros[k] = float(candidate_norm[k])
                    except Exception:
                        adjusted_macros[k] = adjusted_macros.get(k)

    # final fallback: if adjusted_macros still incomplete, use plan-level macros
    if plan and plan.get("Macros"):
        for src_k, tgt_k in [("Protein_g", "protein_g"), ("Carbs_g", "carbs_g"), ("Fats_g", "fats_g")]:
            if adjusted_macros.get(tgt_k) is None and plan["Macros"].get(src_k) is not None:
                try:
                    adjusted_macros[tgt_k] = float(plan["Macros"].get(src_k))
                except Exception:
                    pass

    weekly_doc = {
        "user_id": user_id,
        "week_number": week_number,
        "start_date": week_start_date,
        "end_date": iso_date(parse_date(week_start_date) + timedelta(days=6)),
        "average_achieved": {
        "calories": round(avg_ach_cal, 2) if avg_ach_cal is not None else None,
        "protein_g": round(avg_ach_protein, 2) if avg_ach_protein is not None else None,
        "carbs_g": round(avg_ach_carbs, 2) if avg_ach_carbs is not None else None,
        "fats_g": round(avg_ach_fats, 2) if avg_ach_fats is not None else None,
        "workout_intensity": round(avg_workout, 2) if avg_workout is not None else None,
        "recent_avg_weight_kg": round(recent_avg_weight, 2) if recent_avg_weight is not None else None,
        "first_week_weight_kg": round(first_weight, 2) if first_weight is not None else None,
        "last_week_weight_kg": round(last_weight, 2) if last_weight is not None else None,
        "weight_change_kg": round(actual_change, 2) if actual_change is not None else None
    },
        "adjusted_targets": {
            "daily_calories": adjusted_daily_calories,
            "daily_macros": adjusted_macros,
            "workout_intensity": avg_workout if avg_workout is not None else (docs[0].get("expected", {}).get("workout_intensity")),
            "target_weight_kg": next_expected_weight
        },
        "adjustment_reason": adjustment_reason,
        "generated_at": iso_date(datetime.utcnow())
    }

    # store weekly summary
    progress_weekly_col.update_one(
        {"user_id": user_id, "week_number": week_number, "start_date": week_start_date},
        {"$set": weekly_doc},
        upsert=True
    )

    # generate next 7 days using adjusted targets
    next_week_start = parse_date(week_start_date) + timedelta(days=7)
    generated_info = generate_next_week_docs(
        user_id=user_id,
        adjusted_targets=weekly_doc["adjusted_targets"],
        start_date=iso_date(next_week_start),
        week_number=(week_number + 1),
        goal=goal
    )

    return {"weekly_summary": weekly_doc, "generated_next_week": generated_info}

def generate_next_week_docs(user_id: str, adjusted_targets: Dict[str, Any], start_date: str, week_number: int, goal: str):
    """
    Create 7 new progress documents starting at start_date with adjusted targets.
    If adjusted_targets['daily_macros'] is missing/incomplete, try to fetch next-week macros from plan.
    """
    # ensure adjusted_targets keys are present and normalized
    daily_calories = adjusted_targets.get("daily_calories")
    daily_macros = adjusted_targets.get("daily_macros") or {}
    target_weight = adjusted_targets.get("target_weight_kg")
    workout_intensity = adjusted_targets.get("workout_intensity")

    # If macros incomplete, try to fetch from plan's Weekly_Plan for the corresponding week_index
    plan = macro_collection.find_one({"user_id": user_id})
    if plan and (not daily_macros or any(daily_macros.get(k) is None for k in ["protein_g", "carbs_g", "fats_g"])):
        # next_week_index = week_number - 1 (because generate_next_week_docs is called for next week)
        plan_index = week_number - 1
        if "Weekly_Plan" in plan and len(plan["Weekly_Plan"]) > plan_index:
            candidate = plan["Weekly_Plan"][plan_index].get("expected_macros") or {}
            # normalize keys
            candidate_norm = {
                "protein_g": candidate.get("Protein_g") or candidate.get("protein_g"),
                "carbs_g": candidate.get("Carbs_g") or candidate.get("carbs_g"),
                "fats_g": candidate.get("Fats_g") or candidate.get("fats_g")
            }
            for k in ["protein_g", "carbs_g", "fats_g"]:
                if daily_macros.get(k) is None and candidate_norm.get(k) is not None:
                    try:
                        daily_macros[k] = float(candidate_norm[k])
                    except Exception:
                        daily_macros[k] = daily_macros.get(k)

    # final fallback to plan-level Macros
    if plan and plan.get("Macros"):
        mapping = {"protein_g": "Protein_g", "carbs_g": "Carbs_g", "fats_g": "Fats_g"}
        for tgt, src in mapping.items():
            if daily_macros.get(tgt) is None and plan["Macros"].get(src) is not None:
                try:
                    daily_macros[tgt] = float(plan["Macros"].get(src))
                except Exception:
                    pass

    start_dt = parse_date(start_date)
    created = []
    for d in date_range(start_dt, 7):
        date_str = iso_date(d)
        expected = {
            "daily_calories": daily_calories,
            "daily_macros": daily_macros,
            "target_weight_kg": target_weight,
            "workout_intensity": workout_intensity
        }
        achieved = {"calories": None, "macros": None, "workout_intensity": None, "weight_kg": None}
        doc = create_or_update_progress_doc(user_id=user_id, date_str=date_str, expected=expected, achieved=achieved, week_number=week_number, goal=goal)
        created.append(doc["date"])
    return {"start_date": start_date, "created_dates": created, "week_number": week_number}

# ---------- Example usage ----------
if __name__ == "__main__":
    # Example: adapt for user 'user123' and plan with id 'plan123'
    # You must replace with actual user_id and plan _id from your DB

    USER_ID = "u001"
    PLAN_ID = "68e7d0f5c735f1588a6fff17"  # replace with actual ObjectId or string key used in your plans collection

    # 1) Generate initial week (call when plan is created / user confirms)
    try:
        print("Generating initial week...")
        res = generate_initial_week(USER_ID, PLAN_ID)
        print(res)
    except Exception as e:
        print("Initial week generation error:", e)

    # 2) Daily update (call every day or on event)
    today = datetime.utcnow()
    try:
        print("Updating today's progress...")
        updated = update_daily_progress(USER_ID, today)
        print("Updated doc date:", updated["date"])
    except Exception as e:
        print("Daily update error:", e)

    # 3) At week end, aggregate & adapt (provide the week start date)
    # Suppose week starts on 2025-10-06
    WEEK_START = "2025-10-13"
    try:
        print("Aggregating & adapting week starting:", WEEK_START)
        adapt_res = aggregate_and_adapt_week(USER_ID, WEEK_START)
        print("Adaptation result:", adapt_res["weekly_summary"]["adjustment_reason"])
        print("Next week created:", adapt_res["generated_next_week"])
    except Exception as e:
        print("Weekly aggregation error:", e)