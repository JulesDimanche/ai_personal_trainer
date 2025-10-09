import os
from Calorie_tracker import estimate_calories
from Workout_tracker import generate_workout_summary
import datetime
from temp_main import add_food_entry, add_workout_entry

def process_food_input(user__input,meal,user_data,api_key):
    foot_items=estimate_calories(user__input,api_key)
    date=datetime.date.today().isoformat()
    return add_food_entry(date,meal,foot_items['items'],user_data)

def process_workout_input(exercise_list,user_data,api_key):
    exercises=generate_workout_summary(exercise_list,api_key)
    date=datetime.date.today().isoformat()
    return add_workout_entry(date,exercises,user_data)

if __name__ == "__main__":
    user_data={
        'profile':{},
        'food_log':[],
        'workout_log':[],
        'progress':[],}
    api_key=os.getenv("QWEN3_API_KEY")
    process_food_input("I had 2 boiled eggs and a banana for breakfast", "Breakfast", user_data,api_key)
    process_workout_input("I did bench press 3 sets of 10, 8, 6 reps with 60kg and walked for 30 minutes", user_data,api_key)
    print(user_data)