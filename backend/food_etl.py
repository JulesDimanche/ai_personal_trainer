from datetime import datetime
def get_week_key(date_str: str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    year, week, _ = date_obj.isocalendar()
    return f"{year}-W{week}", date_obj
def build_weekly_food_update(raw_food_doc):
    week_key, date_obj = get_week_key(raw_food_doc["date"])

    totals = {
        "total_calories": 0,
        "total_protein": 0,
        "total_fat": 0,
        "total_carb": 0,
        "total_fiber": 0,
        "days_logged": 1
    }

    meal_updates = {}

    for meal in raw_food_doc["plan_data"]:
        meal_type = meal["meal_type"]

        meal_updates.setdefault(meal_type, {
            "total_calories": 0,
            "total_protein": 0,
            "total_fat": 0,
            "total_carb": 0,
            "total_fiber": 0,
            "foods": {}
        })

        ms = meal["meal_summary"]

        meal_updates[meal_type]["total_calories"] += ms["total_calories"]
        meal_updates[meal_type]["total_protein"] += ms["total_protein"]
        meal_updates[meal_type]["total_fat"] += ms["total_fat"]
        meal_updates[meal_type]["total_carb"] += ms["total_carb"]
        meal_updates[meal_type]["total_fiber"] += ms["total_fiber"]

        totals["total_calories"] += ms["total_calories"]
        totals["total_protein"] += ms["total_protein"]
        totals["total_fat"] += ms["total_fat"]
        totals["total_carb"] += ms["total_carb"]
        totals["total_fiber"] += ms["total_fiber"]

        for item in meal["items"]:
            food = item["food"]

            f = meal_updates[meal_type]["foods"].setdefault(food, {
                "times_consumed": 0,
                "total_quantity": 0,
                "total_weight": 0,
                "total_calories": 0
            })

            f["times_consumed"] += 1
            f["total_quantity"] += item["quantity"]
            f["total_weight"] += item.get("weight", 0)
            f["total_calories"] += item["calories"]

    return week_key, date_obj, meal_updates, totals
def upsert_weekly_food_summary(db, raw_food_doc):
    week_key, date_obj, meal_updates, totals = build_weekly_food_update(raw_food_doc)

    base_filter = {
        "user_id": raw_food_doc["user_id"],
        "week": week_key
    }

    update_doc = {
        "$setOnInsert": {
            "user_id": raw_food_doc["user_id"],
            "week": week_key,
            "start_date": date_obj.strftime("%Y-%m-%d")
        },
        "$inc": {
            "nutrition_summary.weekly_totals.total_calories": totals["total_calories"],
            "nutrition_summary.weekly_totals.total_protein": totals["total_protein"],
            "nutrition_summary.weekly_totals.total_fat": totals["total_fat"],
            "nutrition_summary.weekly_totals.total_carb": totals["total_carb"],
            "nutrition_summary.weekly_totals.total_fiber": totals["total_fiber"],
            "nutrition_summary.days_logged": totals["days_logged"]
        }
    }

    for meal_type, m in meal_updates.items():
        meal_prefix = f"nutrition_summary.by_meal_type.{meal_type}"

        update_doc["$inc"].update({
            f"{meal_prefix}.total_calories": m["total_calories"],
            f"{meal_prefix}.total_protein": m["total_protein"],
            f"{meal_prefix}.total_fat": m["total_fat"],
            f"{meal_prefix}.total_carb": m["total_carb"],
            f"{meal_prefix}.total_fiber": m["total_fiber"]
        })

        for food, f in m["foods"].items():
            food_prefix = f"{meal_prefix}.foods.{food}"

            update_doc["$inc"].update({
                f"{food_prefix}.times_consumed": f["times_consumed"],
                f"{food_prefix}.total_quantity": f["total_quantity"],
                f"{food_prefix}.total_weight": f["total_weight"],
                f"{food_prefix}.total_calories": f["total_calories"]
            })

    db.weekly_summary.update_one(
        base_filter,
        update_doc,
        upsert=True
    )
if __name__ == "__main__":
    from backend.db_connection import db

    raw_workout_doc = {
  "_id": {
    "$oid": "693bdc8ce5a64570d3041bed"
  },
  "user_id": "6ff54cd5-593a-4cdd-81a4-bb9dca658c0d",
  "date": "2025-12-12",
  "plan_data": [
    {
      "meal_type": "lunch",
      "items": [
        {
          "food": "chicken biriyani",
          "quantity": 1,
          "weight": 200,
          "calories": 400,
          "proteins": 20,
          "fats": 16,
          "carbs": 44,
          "fiber": 3
        }
      ],
      "meal_summary": {
        "total_calories": 400,
        "total_protein": 20,
        "total_fat": 16,
        "total_carb": 44,
        "total_fiber": 3
      }
    },
    {
      "meal_type": "breakfast",
      "items": [
        {
          "food": "idli",
          "quantity": 2,
          "weight": 100,
          "calories": 130,
          "proteins": 4,
          "fats": 1,
          "carbs": 28,
          "fiber": 2
        }
      ],
      "meal_summary": {
        "total_calories": 130,
        "total_protein": 4,
        "total_fat": 1,
        "total_carb": 28,
        "total_fiber": 2
      }
    }
  ],
  "summary": {
    "total_calories": 530,
    "total_protein": 24,
    "total_fat": 17,
    "total_carb": 72,
    "total_fiber": 5,
    "created_at": "2025-12-12T09:19:25.357449"
  },
  "created_at": {
    "$date": "2025-12-12T09:12:44.550Z"
  }
}

    upsert_weekly_food_summary(db, raw_workout_doc)