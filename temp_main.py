import json
def create_or_update_user(profile_data,user_data):
    user_data['profile'].update(profile_data)
    return user_data
def add_food_entry(date,meal,items,user_data):
    if isinstance(items,str):
        items=json.loads(items)
    total_calories=sum(item['calories'] for item in items)
    entry={
        'date':date,
        'meal':meal,
        'items':items,
        'total_calories':total_calories
    }
    user_data['food_log'].append(entry)
    return entry
def add_workout_entry(date,exercise,user_data):
    if isinstance(exercise,str):
        exercise=json.loads(exercise)
    total_burned=sum(e.get('calories_burned',0) for e in exercise)
    entry={
        'date':date,
        'exercise':exercise,
        'total_calories_burned':total_burned
    }
    user_data['workout_log'].append(entry)
    return entry
def log_progress(date,weight_kg,body_fat_percent,user_data):
    entry={
        'date':date,
        'weight_kg':weight_kg,
        'body_fat_percent':body_fat_percent
    }
    user_data['progress_log'].append(entry)
    return entry
def get_daily_summary(date,user_data):
    total_calories_consumed=sum(entry['total_calories'] for entry in user_data['food_log'] if entry['date']==date)
    total_calories_burned=sum(entry['total_calories_burned'] for entry in user_data['workout_log'] if entry['date']==date)
    net_calories=total_calories_consumed-total_calories_burned
    summary={
        'date':date,
        'total_calories_consumed':total_calories_consumed,
        'total_calories_burned':total_calories_burned,
        'net_calories':net_calories,
    }
    return summary
def print_summary(date,user_data):
    summary=get_daily_summary(date,user_data)
    print(f"Summary for {summary['date']}:")
    print(f"  Total Calories Consumed: {summary['total_calories_consumed']} kcal")
    print(f"  Total Calories Burned: {summary['total_calories_burned']} kcal")
    print(f"  Net Calories: {summary['net_calories']} kcal")