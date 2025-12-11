import os
import json
import requests
from datetime import date
from google import genai
from google.genai import types
from dotenv import load_dotenv  
load_dotenv()

try:
    api_key=os.getenv("WORKOUT_GEMINI_KEY")
    client_gemini = genai.Client(api_key=api_key)
except Exception as e:
    print(f"Error initializing Gemini client: {e}")
    client_gemini = None
MODEL_NAME = "gemini-2.5-flash" 
WorkoutExercise = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "exercise_name": types.Schema(
            type=types.Type.STRING,
            description="Name of the exercise (e.g., bench press, running)."
        ),
        "muscle_group": types.Schema(
            type=types.Type.STRING,
            description="Primary muscle group targeted."
        ),
        "sets": types.Schema(
            type=types.Type.INTEGER,
            nullable=True,
            description="Number of sets performed. Null for cardio exercises."
        ),
        "reps": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(type=types.Type.INTEGER),
            nullable=True,
            description="List of reps per set. Null for cardio exercises."
        ),
        "weight": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(type=types.Type.NUMBER),
            nullable=True,
            description="Weight lifted per set. Null for cardio exercises."
        ),
        "duration_minutes": types.Schema(
            type=types.Type.NUMBER,
            description="Duration of the exercise in minutes."
        ),
        "calories_burned": types.Schema(
            type=types.Type.NUMBER,
            description="Estimated calories burned for this exercise."
        ),
    }
)
WorkoutPlan = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "detailed_exercises": types.Schema(
            type=types.Type.ARRAY,
            items=WorkoutExercise,
            description="Complete list of exercises in the generated workout plan."
        )
    }
)

SYSTEM_PROMPT="""You are a workout parser.
Extract exercises and estimate duration and calories.
Infer sets, reps, and weight when clearly implied.
Avoid any text. Output only structured data.
"""
def generate_workout_summary(workout_input):
    response=client_gemini.models.generate_content(
        model=MODEL_NAME,
        contents=[types.Content(role="user", parts=[types.Part(text=workout_input)]),],
        config=types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        response_mime_type="application/json",
        response_schema=WorkoutPlan,
        candidate_count=1,
    ),
    )
    print('the response is ',response)
    if response.candidates and response.candidates[0].content:
      raw_json_string = response.candidates[0].content.parts[0].text
      try:
        food_json = json.loads(raw_json_string)
        return food_json
      except json.JSONDecodeError as e:
        print(f"Error decoding JSON from model output: {e}")
        print("Raw text output:", raw_json_string)
        return None
    return None

if __name__=='__main__':
    workout_input='I did 3 sets of 10, 8, and 6 reps of bench press at 60kg. Then I walked for 30 minutes.'
    result=generate_workout_summary(workout_input)
    print(json.dumps(result, indent=2))