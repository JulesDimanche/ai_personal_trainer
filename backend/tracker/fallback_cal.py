import os
import requests
import json
from google import genai
from google.genai import types
import psycopg2
from dotenv import load_dotenv  

load_dotenv()
try:
    api_key=os.getenv("CALORIES_GEMINI_KEY")
    client_gemini = genai.Client(api_key=api_key)
except Exception as e:
    print(f"Error initializing Gemini client: {e}")
    client_gemini = None
MODEL_NAME = "gemini-2.5-flash"

SYSTEM_PROMPT_FALLBACK = """
You are a nutrition expert.
Estimate calories and macros for the given food and weight.
Return values for the full item.
Output JSON only.
"""
FoodItem = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "food": types.Schema(type=types.Type.STRING),
        "quantity": types.Schema(type=types.Type.NUMBER),
        "weight": types.Schema(type=types.Type.NUMBER),
        "calories": types.Schema(type=types.Type.NUMBER),
        "proteins": types.Schema(type=types.Type.NUMBER),
        "fats": types.Schema(type=types.Type.NUMBER),
        "carbs": types.Schema(type=types.Type.NUMBER),
        "fiber": types.Schema(type=types.Type.NUMBER),
    },
)

def estimate_food_with_llm(food: str, weight: float):
    prompt = f"{food}, {weight} grams"

    response = client_gemini.models.generate_content(
        model=MODEL_NAME,
        contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT_FALLBACK,
            response_mime_type="application/json",
            response_schema=FoodItem,
            candidate_count=1,
        ),
    )

    raw = response.candidates[0].content.parts[0].text
    data = json.loads(raw)

    return data
