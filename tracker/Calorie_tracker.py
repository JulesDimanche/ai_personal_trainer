import os
import requests
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv  
load_dotenv()
try:
    client_gemini = genai.Client()
except Exception as e:
    print(f"Error initializing Gemini client: {e}")
    client_gemini = None
MODEL_NAME = "gemini-2.5-flash" 
FoodItem = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "food": types.Schema(type=types.Type.STRING, description="Name of the food item."),
        "quantity": types.Schema(type=types.Type.NUMBER, description="Number of servings or items."),
        "weight": types.Schema(type=types.Type.NUMBER, description="Weight of the item in grams."),
        "calories": types.Schema(type=types.Type.NUMBER, description="Total energy content (kcal)."),
        "proteins": types.Schema(type=types.Type.NUMBER, description="Protein in grams."),
        "fats": types.Schema(type=types.Type.NUMBER, description="Total fat in grams."),
        "carbs": types.Schema(type=types.Type.NUMBER, description="Total carbohydrates in grams."),
        "fiber": types.Schema(type=types.Type.NUMBER, description="Dietary fiber in grams."),
    }
)

FoodMeal = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "meal_type": types.Schema(type=types.Type.STRING, description="The category of the meal (e.g., 'breakfast', 'snack')."),
        "items": types.Schema(
            type=types.Type.ARRAY, 
            items=FoodItem,
            description="List of all food items in the meal."
        ),
    }
)

FoodDaySchema = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "meals": types.Schema(
            type=types.Type.ARRAY, 
            items=FoodMeal,
            description="List of all meals consumed throughout the day."
        ),
    }
)
SYSTEM_PROMPT = """
You are a nutrition parser. 
Extract foods, estimate macros.
Follow common portion sizes if missing.
Avoid text. Output only structured data.
"""


def estimate_calories(food_text):

    response = client_gemini.models.generate_content(
    model=MODEL_NAME,
    contents=[
        types.Content(role="user", parts=[types.Part(text=food_text)]),
    ],
    config=types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        response_mime_type="application/json",
        response_schema=FoodDaySchema,
        candidate_count=1,
    ),
)
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
if __name__ == "__main__":
    food_input = "I had paneer for breakfast and a egg for lunch."
    result=estimate_calories(food_input)
    print('the res ',result)
    print(json.dumps(result,indent=2))