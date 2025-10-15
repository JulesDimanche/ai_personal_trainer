import os
import json
import requests
from datetime import date
from dotenv import load_dotenv  
load_dotenv()
def generate_workout_summary(workout_input,api_key):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"}
    system_prompt = """
You are a fitness tracking assistant. The user will describe their workout in natural language, 
and your task is to extract structured details about each exercise they performed and also provide a summary.

Return ONLY a valid JSON object (no explanation, no extra text).
Do not include anything outside the JSON. The JSON should be directly parsable using json.loads().

The JSON object should contain two keys:
1. "detailed_exercises": a list of all exercises with full details.
2. "summary": a concise summary including total exercises, total sets, total reps, total duration (for cardio), and estimated total calories burned.

For each exercise in "detailed_exercises", include:
- exercise_name
- muscle_group
- sets
- reps (can be a number or a list if reps vary per set)
- weight (if mentioned, else null)
- duration_minutes (if it’s a cardio activity like running, cycling, etc.)
- calories_burned (approximate, based on intensity if not given)

Example output:
{
  "detailed_exercises": [
    {
      "exercise_name": "bench press",
      "muscle_group": "chest",
      "sets": 3,
      "reps": [10, 8, 6],
      "weight": 60,
      "duration_minutes": null,
      "calories_burned": 50
    },
    {
      "exercise_name": "running",
      "muscle_group": "legs",
      "sets": null,
      "reps": null,
      "weight": null,
      "duration_minutes": 30,
      "calories_burned": 250
    }
  ],
  "summary": {
    "total_exercises": 2,
    "total_sets": 3,
    "total_reps": 24,
    "total_duration_minutes": 30,
    "total_calories_burned": 300
  }
}
"""

    user_prompt=f""" Workout description:
    \"\"\"{workout_input}\"\"\"
    Today's date is {date.today()}.
    Generate the structured JSON summary.
    """
    data={
        'model':"qwen/qwen-2.5-coder-32b-instruct:free",
        'messages':[
            {'role':'system', 'content':system_prompt},
            {'role':'user', 'content':user_prompt}
        ],
        'temperature':0.3,
    }
    response=requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    text=response.json()['choices'][0]['message']['content'].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print("Failed to parse JSON from model response")
        print(text)
        return None
'''
if __name__=='__main__':
    OPENROUTER_API_KEY=os.getenv('QWEN3_API_KEY')
    workout_input='I made 3 sets of 10, 8, and 6 reps of bench press at 60kg. Then I walked for 30 minutes.'
    result=generate_workout_summary(workout_input, OPENROUTER_API_KEY)
    print(json.dumps(result, indent=2))'''