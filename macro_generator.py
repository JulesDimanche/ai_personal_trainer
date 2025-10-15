import json
from datetime import datetime

def generate_macro(user_data):
    age = user_data.get('age')
    gender = user_data.get('gender', 'male').lower()
    weight = user_data.get('weight_kg')
    height = user_data.get('height_cm')
    activity_level = user_data.get('activity_level', 'moderate').lower()
    goal = user_data.get('goal', 'maintain').lower()
    target_weeks = user_data.get('target_weeks', 8)
    target_weight = user_data.get('target_weight_kg')

    if gender == 'male':
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161

    activity_factor = {
        'sedentary': 1.2,
        'light': 1.375,
        'moderate': 1.55,
        'active': 1.725,
        'very active': 1.9
    }
    tdee = bmr * activity_factor.get(activity_level, 1.55)

    daily_adjustment = 0
    weekly_change = 0.0
    if target_weight:
        delta_kg = target_weight - weight
        weekly_change = delta_kg / target_weeks
        daily_adjustment = weekly_change * 7700 / 7
        goal_calories = tdee + daily_adjustment
    else:
        if goal in ['fat_loss', 'weight_loss']:
            goal_calories = tdee - 500
            weekly_change = -0.5
        elif goal in ['muscle_gain', 'weight_gain']:
            goal_calories = tdee + 300
            weekly_change = 0.3
        else:
            goal_calories = tdee
            weekly_change = 0.0

    total_change = round(weekly_change * target_weeks, 2)
    target_weight = round(weight + total_change, 1) if not target_weight else target_weight

    def calc_macros(calories):
        protein_kcal = calories * 0.25
        fat_kcal = calories * 0.25
        carb_kcal = calories * 0.50
        return {
            "Protein_g": round(protein_kcal / 4, 1),
            "Fats_g": round(fat_kcal / 9, 1),
            "Carbs_g": round(carb_kcal / 4, 1),
            "Fiber_g": round((calories / 1000) * 14, 1)
        }

    base_macros = calc_macros(goal_calories)

    weekly_plan = []
    for week in range(1, target_weeks + 1):
        expected_weight = round(weight + (week * weekly_change), 1)
        adjustment = -50 if weekly_change < 0 else 50
        expected_calories = round(goal_calories + ((week - 1) // 2) * adjustment, 1)
        expected_macros = calc_macros(expected_calories)

        weekly_plan.append({
            "week_number": week,
            "expected_weight_kg": expected_weight,
            "expected_calories": expected_calories,
            "expected_macros": expected_macros
        })

    if weekly_change > 0:
        goal_summary = f"Expected gain: +{abs(total_change)} kg in {target_weeks} weeks"
    elif weekly_change < 0:
        goal_summary = f"Expected loss: {total_change} kg in {target_weeks} weeks"
    else:
        goal_summary = "Maintenance goal (no weight change planned)"

    plan = {
        "user_id": user_data.get('user_id', 'unknown'),
        "BMR": round(bmr, 1),
        "TDEE": round(tdee, 1),
        "Goal_Calories": round(goal_calories, 1),
        "goal_type": goal,
        "start_weight_kg": weight,
        "target_weight_kg": target_weight,
        "total_weeks": target_weeks,
        "weekly_target_change_kg": round(weekly_change, 2),
        "Target_Change": goal_summary,
        "Macros": base_macros,
        "Weekly_Plan": weekly_plan,
        "created_at": datetime.utcnow().isoformat()
    }

    return plan

'''
# --- Optional: Example test ---
if __name__ == "__main__":
    user_profile = {
        "user_id": "u001",
        "age": 25,
        "gender": "male",
        "weight_kg": 75,
        "target_weight_kg": 70,
        "height_cm": 175,
        "activity_level": "moderate",
        "goal": "fat_loss",
        "target_weeks": 8
    }

    result = generate_macro(user_profile)
    print(json.dumps(result, indent=2))
'''