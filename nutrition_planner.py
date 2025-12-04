import os
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from google import genai
from google.genai.types import GenerateContentConfig

# Load environment variables
load_dotenv()

# --- 1. DEFINE THE SOURCE OF TRUTH (Pydantic Models) ---
# We define the schema here ONCE. Both the AI and the Python code use this.

class MacroNutrients(BaseModel):
    protein: float = Field(description="Protein content in grams")
    carbs: float = Field(description="Carbohydrate content in grams")
    fats: float = Field(description="Fat content in grams")
    calories: float = Field(description="Total calories")

class FoodItem(BaseModel):
    food_name: str = Field(description="Name of the specific dish or item")
    quantity: float = Field(description="Numeric quantity")
    unit: str = Field(description="Unit of measure (e.g., cups, grams, pieces)")
    macros: MacroNutrients

class Meal(BaseModel):
    meal_name: str = Field(description="Name of the meal (Breakfast, Lunch, etc.)")
    time_of_day: str = Field(description="Suggested time (e.g., 08:00 AM)")
    total_meal_calories: float
    items: List[FoodItem]

class DailySummary(BaseModel):
    total_protein: float
    total_carbs: float
    total_fats: float
    total_calories: float
    cuisine_style: str
    advice_note: str = Field(description="Short advice regarding the plan")

# This is the ROOT object we expect back
class DietPlanResponse(BaseModel):
    summary: DailySummary
    meals: List[Meal]

# --- 2. SETUP CLIENT ---
try:
    client_gemini = genai.Client()
    MODEL_NAME = "gemini-2.5-flash"
except Exception as e:
    print(f"Error initializing Gemini client: {e}")
    client_gemini = None

# --- 3. THE GENERIC GENERATOR ---
def generate_meal_plan(
    target_protein: int, 
    target_carbs: int, 
    target_fats: int, 
    cuisine_style: str = "South Indian"
) -> Optional[DietPlanResponse]:
    
    if not client_gemini:
        print("Client not initialized")
        return None

    # We pass the Pydantic Class directly to response_schema!
    # The SDK converts this to the JSON schema automatically.
    
    user_prompt = f"""
    Create a 1-day meal plan.
    Target: {target_protein}g Protein, {target_carbs}g Carbs, {target_fats}g Fats.
    Cuisine: {cuisine_style}.
    """

    try:
        response = client_gemini.models.generate_content(
            model=MODEL_NAME,
            contents=[
                {"role": "user", "parts": [{"text": user_prompt}]}
            ],
            config=GenerateContentConfig(
                temperature=0.1,
                # KEY FIX: Pass the Pydantic class here
                response_schema=DietPlanResponse, 
                response_mime_type="application/json"
            )
        )
        
        raw_json = response.text.strip()
        
        # Clean potential markdown wrappers
        if raw_json.startswith("```json"):
            raw_json = raw_json.replace("```json", "").replace("```", "").strip()
            
        # Parse into the Object
        diet_plan = DietPlanResponse.model_validate_json(raw_json)
        return diet_plan

    except Exception as e:
        print(f"Error generating/parsing plan: {e}")
        return None

# --- 4. THE DISPLAY LOGIC ---
if __name__ == "__main__":
    p_target, c_target, f_target = 150, 180, 60
    style = "South Indian"

    print(f"Generating plan...")
    
    # result is now a DietPlanResponse OBJECT
    result = generate_meal_plan(p_target, c_target, f_target, style)
    
    if result:
        s = result.summary 
        
        print("\n" + "="*50)
        print(f"🍱 MEAL PLAN SUMMARY ({s.cuisine_style})")
        print("="*50)
        print(f"Target:     P: {p_target}g | C: {c_target}g | F: {f_target}g")
        print(f"Calculated: P: {s.total_protein}g | C: {s.total_carbs}g | F: {s.total_fats}g")
        print(f"Calories:   {s.total_calories} kcal")
        print(f"Note:       {s.advice_note}")
        print("-" * 50)

        for meal in result.meals:
            print(f"\n🔹 {meal.meal_name.upper()} ({meal.time_of_day}) - {meal.total_meal_calories} kcal")
            for item in meal.items:
                print(f"   - {item.food_name} ({item.quantity} {item.unit})")
                print(f"     [P: {item.macros.protein}g | C: {item.macros.carbs}g | F: {item.macros.fats}g]")
    else:
        print("Failed to generate plan.")