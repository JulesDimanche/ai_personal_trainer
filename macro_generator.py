import json

def generate_macro(user_data):
    age=user_data.get('age')
    gender=user_data.get('gender','male').lower()
    weight=user_data.get('weight_kg')
    height=user_data.get('height_cm')
    activity_level=user_data.get('activity_level','moderate').lower()
    goal=user_data.get('goal','maintain').lower()
    target_week=user_data.get('target_weeks',8)
    target_weight=user_data.get('target_weight_kg')

    if gender=='male':
        bmr=10*weight+6.25*height-5*age+5
    else:
        bmr=10*weight+6.25*height-5*age-161
    activity_factor={
        'sedentary':1.2,
        'light':1.375,
        'moderate':1.55,
        'active':1.725,
        'very active':1.9
    }
    tdee=bmr*activity_factor.get(activity_level,1.55)
    daily_adjustment=0
    weekly_change=0.0
    if target_weight:
        delta_kg=target_weight-weight
        weekly_change=delta_kg/target_week
        daily_adjustment=weekly_change*7700/7
        goal_calories=tdee+daily_adjustment
    else:
        if goal in ['fat_loss','weight_loss']:
            goal_calories=tdee-500
            weekly_change=-0.5
        elif goal in ['muscle_gain','weight_gain']:
            goal_calories=tdee+300
            weekly_change=0.3
        else:
            goal_calories=tdee
            weekly_change=0.0

    target_change=round(weekly_change*target_week,2)

    protein_kcal = goal_calories * 0.25
    fat_kcal = goal_calories * 0.25
    carb_kcal = goal_calories * 0.50

    macros = {
        "Protein_g": round(protein_kcal / 4, 1),
        "Fats_g": round(fat_kcal / 9, 1),
        "Carbs_g": round(carb_kcal / 4, 1),
        "Fiber_g": round((goal_calories / 1000) * 14, 1)
    }
    if target_weight:
        change_type = "gain" if target_weight > weight else "loss"
        goal_summary = f"Target: {change_type} {abs(target_change):.1f} kg in {target_week} weeks"
    else:
        if weekly_change > 0:
            goal_summary = f"Expected gain: +{target_change} kg in {target_week} weeks"
        elif weekly_change < 0:
            goal_summary = f"Expected loss: {target_change} kg in {target_week} weeks"
        else:
            goal_summary = "Maintenance goal (no weight change planned)"
    plan = {
        "BMR": round(bmr, 1),
        "TDEE": round(tdee, 1),
        "Goal_Calories": round(goal_calories, 1),
        "Weekly_Change": f"{weekly_change:+.2f} kg",
        "Target_Change": goal_summary,
        "Macros": macros
    }

    return plan
if __name__ == "__main__":
    user_profile_1 = {
        "age": 25,
        "gender": "male",
        "weight_kg": 70,
        "height_cm": 175,
        "activity_level": "moderate",
        "goal": "muscle_gain",
        "target_period_weeks": 8
    }
    user_profile_2 = {
        "age": 28,
        "gender": "female",
        "weight_kg": 68,
        "target_weight_kg": 63,
        "height_cm": 165,
        "activity_level": "light",
        "goal": "weight_loss",
        "target_period_weeks": 10
    }
    print('user1 info--------------')
    result = generate_macro(user_profile_1)
    print(json.dumps(result, indent=2))

    print('user2 info--------------')
    result = generate_macro(user_profile_2)
    print(json.dumps(result, indent=2))