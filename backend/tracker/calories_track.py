import os
import requests
import json
from google import genai
from google.genai import types
import psycopg2
from tracker.fallback_cal import estimate_food_with_llm
from dotenv import load_dotenv  

load_dotenv()
try:
    api_key=os.getenv("CALORIES_GEMINI_KEY")
    client_gemini = genai.Client(api_key=api_key)
except Exception as e:
    print(f"Error initializing Gemini client: {e}")
    client_gemini = None
MODEL_NAME = "gemini-2.5-flash" 
SUPABASE_DB_URL = os.getenv("P_DATABASE_URL")

FoodItem = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "food": types.Schema(
            type=types.Type.STRING,
            description="Name of the food item."
        ),
        "quantity": types.Schema(
            type=types.Type.NUMBER,
            description="Quantity consumed. If missing, assume 1."
        ),
        "weight": types.Schema(
            type=types.Type.NUMBER,
            description="Weight of the food item in grams, if available."
        ),
    },
    required=["food"]
)


FoodMeal = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "meal_type": types.Schema(
            type=types.Type.STRING,
            description="Meal time (breakfast, lunch, dinner, snack)."
        ),
        "items": types.Schema(
            type=types.Type.ARRAY,
            items=FoodItem
        ),
    },
    required=["meal_type", "items"]
)


FoodDaySchema = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "meals": types.Schema(
            type=types.Type.ARRAY,
            items=FoodMeal
        ),
    },
    required=["meals"]
)

SYSTEM_PROMPT = """
You are a food intake parser.

Extract: food name,quantity, weight (in grams), meal type

Do NOT estimate calories or nutrition.
If quantity is missing, assume quantity 1 and if weight missing consider as 100 g
Return only JSON matching the schema.
"""


def insert_food_macros_100g(
    food_name: str,
    calories_100g: float,
    protein_100g: float,
    carbs_100g: float,
    fat_100g: float,
    fiber_100g: float,
):
    conn = psycopg2.connect(SUPABASE_DB_URL)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO foods (food_name, calories, protein, carbs, fat, fiber)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (food_name_lower) DO NOTHING;
    """, (
        food_name,
        calories_100g,
        protein_100g,
        carbs_100g,
        fat_100g,
        fiber_100g,
    ))

    conn.commit()
    cursor.close()
    conn.close()

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


def get_food_macros(food_name: str):
    conn = psycopg2.connect(SUPABASE_DB_URL)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT calories, protein, carbs, fat, fiber
        FROM foods
        WHERE food_name_lower = %s
        LIMIT 1;
    """, (food_name.lower(),))

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    if not row:
        return None

    calories, protein, carbs, fat, fiber = row

    return {
        "calories_100g": float(calories),
        "protein_100g": float(protein),
        "carbs_100g": float(carbs),
        "fat_100g": float(fat),
        "fiber_100g": float(fiber),
    }


def calculate_macros(food_name: str, weight: float,quantity: float):

    macros = get_food_macros(food_name)
    if not macros:
        llm_data= estimate_food_with_llm(food_name, weight)
        factor_100g = 100.0 / weight

        calories_100g = llm_data["calories"] * factor_100g
        protein_100g  = llm_data["proteins"] * factor_100g
        carbs_100g    = llm_data["carbs"] * factor_100g
        fat_100g      = llm_data["fats"] * factor_100g
        fiber_100g    = llm_data["fiber"] * factor_100g

        insert_food_macros_100g(
            food_name=food_name,
            calories_100g=round(calories_100g, 2),
            protein_100g=round(protein_100g, 2),
            carbs_100g=round(carbs_100g, 2),
            fat_100g=round(fat_100g, 2),
            fiber_100g=round(fiber_100g, 2),
        )

        return llm_data

    factor = weight / 100.0

    return {
        "food": food_name,
        "weight": weight,
        "quantity": quantity,
        "calories": round(macros["calories_100g"] * factor, 2),
        "protein": round(macros["protein_100g"] * factor, 2),
        "carbs": round(macros["carbs_100g"] * factor, 2),
        "fat": round(macros["fat_100g"] * factor, 2),
        "fiber": round(macros["fiber_100g"] * factor, 2),
    }
def enrich_with_macros(llm_output):
    meals = []

    for meal in llm_output["meals"]:
        items = []

        for item in meal["items"]:
            food = item["food"]
            weight = item.get("weight", 100)
            quantity = item.get("quantity", 1)

            macros = calculate_macros(food, weight, quantity)

            if macros:
                items.append({
                    "food": food,
                    "quantity": quantity,
                    "weight": weight,
                    "calories": macros["calories"],
                    "proteins": macros["protein"], 
                    "fats": macros["fat"],         
                    "carbs": macros["carbs"],
                    "fiber": macros.get("fiber", 0.0)
                })

        meals.append({
            "meal_type": meal["meal_type"],
            "items": items
        })

    return {"meals": meals}

if __name__ == "__main__":
    food_input = "I had paneer for breakfast and a egg for lunch."
    #result=estimate_calories(food_input)
    #print('the res ',result)
    fin=enrich_with_macros({'meals': [{'meal_type': 'breakfast', 'items': [{'food': 'paneer', 'quantity': 1, 'weight': 100}]}, {'meal_type': 'lunch', 'items': [{'food': 'egg', 'quantity': 1, 'weight': 100}]}]})
    print('the fin ',fin)
