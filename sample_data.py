from db_connection import user_col, workout_col, diet_col, progress_col
user_col.insert_one({
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
})
print("Sample data inserted successfully!")
