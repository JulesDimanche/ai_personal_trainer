import os
from db_connection import user_col, workout_col, diet_col, progress_col,macro_collection
import datetime
from macro_generator import generate_macro
from Calorie_tracker import estimate_calories
from Workout_tracker import generate_workout_summary
from diet_trigger import handle_summary_trigger
from workout_tigger import handle_wo_summary_trigger
from progress_tracker import update_daily_progress

'''user_col.insert_one({
    "user_id": "u001",
    "name": "John Doe",
    "age": 25,
    "gender": "male",
    "height_cm": 178,
    "weight_kg": 72,
    "goal": "fat_loss",
    "target_duration_weeks": 12,
    "activity_level": "moderate"
})

workout_col.insert_one({
    "user_id": "u001",
    "date": "2025-10-06",
    "type": "strength_training",
    "summary": "Chest and triceps workout, 45 mins, 400 kcal burned.",
    "duration_min": 45,
    "calories_burned": 400
})

diet_col.insert_one({
    "user_id": "u001",
    "date": "2025-10-06",
    "meals": [
        {"meal": "breakfast", "items": ["oats", "banana", "milk"], "calories": 350},
        {"meal": "lunch", "items": ["chicken", "rice", "salad"], "calories": 600},
        {"meal": "dinner", "items": ["eggs", "veggies"], "calories": 400}
    ],
    "total_calories": 1350
})
progress_col.insert_one({
    "user_id": "u001",
    "week": 1,
    "weight_kg": 71.5,
    "body_fat_pct": 19.0,
    "notes": "Started training, energy levels improving."
})'''

def insert_macro_plan(macro_data):
    try:
        document={
            **macro_data,
            'created_at':datetime.datetime.utcnow()
        }
        result=macro_collection.insert_one(document)
        print(f"Macro plan inserted with ID: {result.inserted_id}")
        return str(result.inserted_id)
    except Exception as e:
        print(f"Error inserting macro plan: {e}")
        return None
def get_latest_macro_plan(user_id):
    try:
        result=macro_collection.find_one(
            {'user_id':user_id},
            sort=[('created_at',-1)]
        )  
        return result
    except Exception as e:
        print(f"Error retrieving macro plan: {e}")
        return None
    
def insert_calories_plan(user_id,calorie_data):
    try:
        today_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        document={
            'user_id':user_id,
            'date':today_str,
            "plan_data":calorie_data.get("meals",{}),
            "summary":calorie_data.get("daily_summary",""),
            'created_at':datetime.datetime.utcnow()
        }
        result=diet_col.insert_one(document)
        print(f"Macro plan inserted with ID: {result.inserted_id}")
        update_daily_progress(user_id,datetime.datetime.utcnow())
        handle_summary_trigger(user_id,calorie_data.get("daily_summary",{}),datetime.datetime.utcnow())
        return str(result.inserted_id)
    except Exception as e:
        print(f"Error inserting macro plan: {e}")
        return None
    
def get_latest_calorie(user_id):
    try:
        result=diet_col.find_one(
            {'user_id':user_id},
            sort=[('created_at',-1)]
        )  
        return result
    except Exception as e:
        print(f"Error retrieving macro plan: {e}")
        return None
def insert_workout_plan(user_id,workout_data):
    try:
        today_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        document={
            'user_id':user_id,
            "date": today_str,
            "workout_data":workout_data.get("detailed_exercises",{}),
            "summary":workout_data.get("summary",""),
            'created_at':datetime.datetime.utcnow()
        }
        result=workout_col.insert_one(document)
        print(f"Workout plan inserted with ID: {result.inserted_id}")
        update_daily_progress(user_id,datetime.datetime.utcnow())
        handle_wo_summary_trigger(user_id,workout_data.get("summary",{}))
        return str(result.inserted_id)
    except Exception as e:
        print(f"Error inserting macro plan: {e}")
        return None
    
def get_latest_workout(user_id):
    try:
        result=workout_col.find_one(
            {'user_id':user_id},
            sort=[('created_at',-1)]
        )  
        return result
    except Exception as e:
        print(f"Error retrieving macro plan: {e}")
        return None
if __name__=='__main__':
    user_data={
        'user_id':"u001",
        "age": 25,
        "gender": "male",
        "weight_kg": 70,
        "height_cm": 175,
        "activity_level": "moderate",
        "goal": "fat_loss",
        "target_period_weeks": 8
    }
    #macro_data=generate_macro(user_data)
    #insert_macro_plan(macro_data)
    #print("Latest Macro Plan-------")
    #plan=get_latest_macro_plan(user_id)
    #print(plan)
    user_id="u001"
    calorie_data=estimate_calories('I had 1 egg for breakfast',os.getenv("QWEN3_API_KEY"))
    insert_calories_plan(user_id,calorie_data)
    diet=get_latest_calorie(user_id)
    print("calore Plan-------")
    print(diet)
    #workout_data=generate_workout_summary('I made 3 sets of 10, 8, and 6 reps of bench press at 60kg. Then I walked for 30 minutes.Total duration of the exercise is 45 min.',os.getenv("QWEN3_API_KEY"))
    #insert_workout_plan(user_id,workout_data)
    #WO=get_latest_workout(user_id)
    #print("Workout Plan-------")
    #print(WO)
