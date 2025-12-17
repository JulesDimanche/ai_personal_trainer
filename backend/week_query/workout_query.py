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
def build_weekly_workout_query(
    user_id: str,
    start_date: str | None =None,
    end_date: str | None =None,
    exercise: str | None = None,
    muscle_group: str | None = None,
    exercise_breakdown: bool = False
):
    if start_date and not end_date:
        end_date = datetime.today().strftime("%Y-%m-%d")

    if end_date and not start_date:
        start_date = "2025-01-01"

    if not start_date and not end_date:
        weeks = None
    else:
        weeks = get_weeks_between(start_date, end_date)

    if exercise:
        exercise = exercise.strip().lower()

    if muscle_group:
        muscle_group = muscle_group.strip().lower()

    if exercise:
        return {
            "collection": "weekly_summary",
            "pipeline": [
                {
                    "$match": {
                        "user_id": user_id,
                        **({"week": {"$in": weeks}} if weeks else {})
                    }
                }
                ,
                {
                    "$project": {
                        "muscles": {
                            "$objectToArray": "$workout_summary.by_muscle_group"
                        }
                    }
                },
                {"$unwind": "$muscles"},
                {
                    "$project": {
                        "exercise": {
                            "$getField": {
                                "field": exercise,
                                "input": {
                                    "$arrayToObject": {
                                        "$map": {
                                            "input": {
                                                "$objectToArray": "$muscles.v.exercises"
                                            },
                                            "as": "e",
                                            "in": {
                                                "k": {"$toLower": "$$e.k"},
                                                "v": "$$e.v"
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                {"$match": {"exercise": {"$exists": True}}},
                {
                    "$group": {
                        "_id": None,
                        "sessions": {"$sum": "$exercise.sessions"},
                        "total_sets": {"$sum": "$exercise.total_sets"},
                        "total_weight": {"$sum": "$exercise.total_weight"},
                        "max_weight": {"$max": "$exercise.max_weight"}
                    }
                },
                {"$project": {"_id": 0}}
            ]
        }

    if muscle_group:
        return {
            "collection": "weekly_summary",
            "pipeline": [
                {
                    "$match": {
                        "user_id": user_id,
                        **({"week": {"$in": weeks}} if weeks else {})
                    }
                }
                ,
                {
                    "$project": {
                        "muscle": {
                            "$getField": {
                                "field": muscle_group,
                                "input": {
                                    "$arrayToObject": {
                                        "$map": {
                                            "input": {
                                                "$objectToArray": "$workout_summary.by_muscle_group"
                                            },
                                            "as": "m",
                                            "in": {
                                                "k": {"$toLower": "$$m.k"},
                                                "v": "$$m.v"
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                {"$match": {"muscle": {"$exists": True}}},
                {
                    "$facet": {
                        "muscle_totals": [
                            {
                                "$group": {
                                    "_id": None,
                                    "total_sets": {"$sum": "$muscle.total_sets"},
                                    "total_reps": {"$sum": "$muscle.total_reps"},
                                    "total_calories": {"$sum": "$muscle.total_calories"}
                                }
                            },
                            {"$project": {"_id": 0}}
                        ],
                        "exercises": [
                            {
                                "$project": {
                                    "exercises": {
                                        "$objectToArray": "$muscle.exercises"
                                    }
                                }
                            },
                            {"$unwind": "$exercises"},
                            {
                                "$group": {
                                    "_id": "$exercises.k",
                                    "sessions": {"$sum": "$exercises.v.sessions"},
                                    "total_sets": {"$sum": "$exercises.v.total_sets"},
                                    "total_weight": {"$sum": "$exercises.v.total_weight"},
                                    "max_weight": {"$max": "$exercises.v.max_weight"}
                                }
                            },
                            {
                                "$project": {
                                    "_id": 0,
                                    "exercise": "$_id",
                                    "sessions": 1,
                                    "total_sets": 1,
                                    "total_weight": 1,
                                    "max_weight": 1
                                }
                            },
                            {"$sort": {"sessions": -1}}
                        ]
                    }
                }
            ]
        }

    if exercise_breakdown:
        return {
            "collection": "weekly_summary",
            "pipeline": [
                {
                    "$match": {
                        "user_id": user_id,
                        **({"week": {"$in": weeks}} if weeks else {})
                    }
                }
                ,
                {
                    "$project": {
                        "muscles": {
                            "$objectToArray": "$workout_summary.by_muscle_group"
                        }
                    }
                },
                {"$unwind": "$muscles"},
                {
                    "$project": {
                        "exercises": {
                            "$objectToArray": "$muscles.v.exercises"
                        }
                    }
                },
                {"$unwind": "$exercises"},
                {
                    "$group": {
                        "_id": "$exercises.k",
                        "sessions": {"$sum": "$exercises.v.sessions"},
                        "total_sets": {"$sum": "$exercises.v.total_sets"},
                        "total_weight": {"$sum": "$exercises.v.total_weight"},
                        "max_weight": {"$max": "$exercises.v.max_weight"}
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "exercise": "$_id",
                        "sessions": 1,
                        "total_sets": 1,
                        "total_weight": 1,
                        "max_weight": 1
                    }
                },
                {"$sort": {"sessions": -1}}
            ]
        }

    return {
        "collection": "weekly_summary",
        "pipeline": [
            {
                    "$match": {
                        "user_id": user_id,
                        **({"week": {"$in": weeks}} if weeks else {})
                    }
                }
                ,
            {
                "$project": {
                    "week": 1,
                    "totals": "$workout_summary.totals",
                    "muscles": {
                        "$objectToArray": "$workout_summary.by_muscle_group"
                    }
                }
            },
            {
                "$facet": {
                    "overall": [
                        {
                            "$group": {
                                "_id": None,
                                "total_calories_burned": {
                                    "$sum": "$totals.total_calories_burned"
                                },
                                "total_duration_minutes": {
                                    "$sum": "$totals.total_duration_minutes"
                                },
                                "total_sets": {"$sum": "$totals.total_sets"},
                                "total_reps": {"$sum": "$totals.total_reps"},
                                "training_days": {"$sum": "$totals.training_days"}
                            }
                        },
                        {"$project": {"_id": 0}}
                    ],
                    "per_week": [
                        {
                            "$project": {
                                "week": 1,
                                "total_calories_burned": "$totals.total_calories_burned",
                                "total_duration_minutes": "$totals.total_duration_minutes",
                                "total_sets": "$totals.total_sets",
                                "total_reps": "$totals.total_reps",
                                "training_days": "$totals.training_days"
                            }
                        }
                    ],
                    "per_muscle": [
                        {"$unwind": "$muscles"},
                        {
                            "$group": {
                                "_id": "$muscles.k",
                                "total_sets": {"$sum": "$muscles.v.total_sets"},
                                "total_reps": {"$sum": "$muscles.v.total_reps"},
                                "total_calories": {"$sum": "$muscles.v.total_calories"}
                            }
                        },
                        {
                            "$project": {
                                "_id": 0,
                                "muscle_group": "$_id",
                                "total_sets": 1,
                                "total_reps": 1,
                                "total_calories": 1
                            }
                        }
                    ]
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
def handle_workout_summary_query(entities, user_id):

    start_date = entities["start_date"]
    end_date = entities["end_date"]
    exercise = entities.get("exercise") 
    muscle_group=entities.get("muscle_group")
    exercise_breakdown = entities.get("exercise_breakdown", False)

    query_json = build_weekly_workout_query(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        exercise=exercise,
        muscle_group=muscle_group,
        exercise_breakdown=exercise_breakdown
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
        "exercise":'Bench Press',
        "exercise_breakdown": False,
        "muscle_group":'None'}
    test_user_id = "6ff54cd5-593a-4cdd-81a4-bb9dca658c0d"

    result_1 = handle_workout_summary_query(test_entities_1, test_user_id)
    print("Test Case 1 - workout Summary:")
    print(result_1)
    fine=to_toon_compact(result_1)
    print('Compact Format:')
    print(fine)