from datetime import datetime, timedelta
import json
from pymongo import MongoClient
from db_connection import db

def date_to_week(date_str: str) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d")
    year, week, _ = d.isocalendar()
    return f"{year}-W{week}"
def get_weeks_between(start_date: str, end_date: str) -> list[str]:
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    weeks = set()
    curr = start
    while curr <= end:
        weeks.add(date_to_week(curr.strftime("%Y-%m-%d")))
        curr += timedelta(days=1)

    return sorted(list(weeks))

def build_weekly_food_query(
    user_id: str,
    start_date: str,
    end_date: str,
    food: str | None = None,
    food_breakdown: bool = False
):
    if start_date and not end_date:
        end_date = datetime.today().strftime("%Y-%m-%d")

    if end_date and not start_date:
        start_date = "2025-01-01"

    if not start_date and not end_date:
        weeks = None
    else:
        weeks = get_weeks_between(start_date, end_date)
    if food:
        food = food.strip().lower()


    if not food and not food_breakdown:
        return {
        "collection": "weekly_summary",
        "pipeline": [
            {
                {
                    "$match": {
                        "user_id": user_id,
                        **({"week": {"$in": weeks}} if weeks else {})
                    }
                }

            },

            {
                "$project": {
                    "week": 1,
                    "weekly_totals": "$nutrition_summary.weekly_totals",
                    "days_logged": "$nutrition_summary.days_logged",
                    "meals": {
                        "$objectToArray": "$nutrition_summary.by_meal_type"
                    }
                }
            },

            {
                "$facet": {

                    "overall": [
                        {
                            "$group": {
                                "_id": None,
                                "total_calories": {"$sum": "$weekly_totals.total_calories"},
                                "total_protein": {"$sum": "$weekly_totals.total_protein"},
                                "total_fat": {"$sum": "$weekly_totals.total_fat"},
                                "total_carb": {"$sum": "$weekly_totals.total_carb"},
                                "total_fiber": {"$sum": "$weekly_totals.total_fiber"},
                                "days_logged": {"$sum": "$days_logged"}
                            }
                        },
                        {
                            "$addFields": {
                                "avg_calories_per_day": {
                                    "$cond": [
                                        {"$gt": ["$days_logged", 0]},
                                        {"$divide": ["$total_calories", "$days_logged"]},
                                        0
                                    ]
                                }
                            }
                        },
                        {"$project": {"_id": 0}}
                    ],

                    "per_week": [
                        {
                            "$project": {
                                "week": 1,
                                "total_calories": "$weekly_totals.total_calories",
                                "total_protein": "$weekly_totals.total_protein",
                                "total_fat": "$weekly_totals.total_fat",
                                "total_carb": "$weekly_totals.total_carb",
                                "total_fiber": "$weekly_totals.total_fiber",
                                "days_logged": 1
                            }
                        }
                    ],

                    "per_meal": [
                        {"$unwind": "$meals"},
                        {
                            "$group": {
                                "_id": "$meals.k",
                                "total_calories": {"$sum": "$meals.v.total_calories"},
                                "total_protein": {"$sum": "$meals.v.total_protein"},
                                "total_fat": {"$sum": "$meals.v.total_fat"},
                                "total_carb": {"$sum": "$meals.v.total_carb"},
                                "total_fiber": {"$sum": "$meals.v.total_fiber"}
                            }
                        },
                        {
                            "$project": {
                                "meal_type": "$_id",
                                "_id": 0,
                                "total_calories": 1,
                                "total_protein": 1,
                                "total_fat": 1,
                                "total_carb": 1,
                                "total_fiber": 1
                            }
                        }
                    ]
                }
            }
        ]
    }
    if food:
        return {
        "collection": "weekly_summary",
        "pipeline": [
            {
                {
                    "$match": {
                        "user_id": user_id,
                        **({"week": {"$in": weeks}} if weeks else {})
                    }
                }

            },
            {
                "$project": {
                    "meals": {
                        "$objectToArray": "$nutrition_summary.by_meal_type"
                    }
                }
            },
            {"$unwind": "$meals"},
            {
                {
                "$project": {
                    "food": {
                        "$getField": {
                            "field": food,
                            "input": {
                                "$arrayToObject": {
                                    "$map": {
                                        "input": {
                                            "$objectToArray": "$meals.v.foods"
                                        },
                                        "as": "f",
                                        "in": {
                                            "k": {"$toLower": "$$f.k"},
                                            "v": "$$f.v"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            },
            {"$match": {"food": {"$exists": True}}},
            {
                "$group": {
                    "_id": None,
                    "times_consumed": {
                        "$sum": "$food.times_consumed"
                    },
                    "total_quantity": {
                        "$sum": "$food.total_quantity"
                    },
                    "total_weight": {
                        "$sum": "$food.total_weight"
                    },
                    "total_calories": {
                        "$sum": "$food.total_calories"
                    }
                }
            },
            {"$project": {"_id": 0}}
        ]
    }
    return {
        "collection": "weekly_summary",
        "pipeline": [
            {
                {
                    "$match": {
                        "user_id": user_id,
                        **({"week": {"$in": weeks}} if weeks else {})
                    }
                }

            },
            {
                "$project": {
                    "meals": {
                        "$objectToArray": "$nutrition_summary.by_meal_type"
                    }
                }
            },
            {"$unwind": "$meals"},
            {
                "$project": {
                    "foods": {
                        "$objectToArray": "$meals.v.foods"
                    }
                }
            },
            {"$unwind": "$foods"},
            {
                "$group": {
                    "_id": "$foods.k",
                    "times_consumed": {
                        "$sum": "$foods.v.times_consumed"
                    },
                    "total_quantity": {
                        "$sum": "$foods.v.total_quantity"
                    },
                    "total_weight": {
                        "$sum": "$foods.v.total_weight"
                    },
                    "total_calories": {
                        "$sum": "$foods.v.total_calories"
                    },
                    "total_protein": {
                        "$sum": "$foods.v.total_protein"
                    },
                    "total_fat": {
                        "$sum": "$foods.v.total_fat"
                    },
                    "total_carb": {
                        "$sum": "$foods.v.total_carb"
                    },
                    "total_fiber": {
                        "$sum": "$foods.v.total_fiber"
                    }
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "food": "$_id",
                    "times_consumed": 1,
                    "total_quantity": 1,
                    "total_weight": 1,
                    "total_calories": 1,
                    "total_protein": 1,
                    "total_fat": 1,
                    "total_carb": 1,
                    "total_fiber": 1
                }
            },
            {
                "$sort": {
                    "times_consumed": -1
                }
            }
        ]
    }

def execute_query(query_json):
    try:
        if isinstance(query_json, str):
            query_json = json.loads(query_json)

        collection_name = query_json.get("collection", "diet_logs")
        collection = db[collection_name]

        if "pipeline" in query_json:
            pipeline = query_json["pipeline"]
            results = list(collection.aggregate(pipeline))
            return results

        elif "filter" in query_json:
            mongo_filter = query_json.get("filter", {})
            projection = query_json.get("projection", None)
            results = list(collection.find(mongo_filter, projection))
            return results

        elif isinstance(query_json, dict):
            results = list(collection.find(query_json))
            return results

        else:
            print("⚠️ Unsupported query format, returning empty result.")
            return []

    except Exception as e:
        print(f"❌ Query execution error: {str(e)}")
        return []
def handle_food_summary_query(entities, user_id):

    start_date = entities["start_date"]
    end_date = entities["end_date"]
    food = entities.get("food") 
    food_breakdown = entities.get("food_breakdown", False)

    query_json = build_weekly_food_query(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        food=food,
        food_breakdown=food_breakdown
    )

    return execute_query(query_json)
def to_toon_compact(data):
    if isinstance(data, dict):
        items = []
        for k, v in data.items():
            items.append(f"{k}:{to_toon_compact(v)}")
        return "(" + ",".join(items) + ")"

    elif isinstance(data, list):
        items = [to_toon_compact(i) for i in data]
        return "[" + ",".join(items) + "]"

    elif isinstance(data, str):
        return f"\"{data}\""

    else:
        return str(data)


if __name__ == "__main__":
    test_entities_1 = {
        "start_date": "2025-12-01",
        "end_date": "2025-12-30",
        "food":None,
        "food_breakdown": True}
    test_user_id = "6ff54cd5-593a-4cdd-81a4-bb9dca658c0d"

    result_1 = handle_food_summary_query(test_entities_1, test_user_id)
    print("Test Case 1 - Macros Summary:")
    print(result_1)
    fine=to_toon_compact(result_1)
    print('Compact Format:')
    print(fine)