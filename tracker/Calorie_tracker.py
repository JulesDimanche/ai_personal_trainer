import os
import requests
import json
from dotenv import load_dotenv  
load_dotenv()
OPENROUTER_API_KEY = os.getenv("QWEN3_API_KEY")


def estimate_calories(food_text):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"}
    prompt = f"""
You are a **personal nutrition and fitness assistant** that analyzes a user's meals for calorie and macro tracking.

The user will describe **one or more meals** in natural language (for example: "I had oats for breakfast and chicken rice for lunch").

Your task is to output a **JSON object** with:
1. **Detailed nutrition breakdown** for each food item under each meal.
2. **Daily summary totals** combining all meals.

### Output Format:
{{
  "user_id": "<user_id_if_available_or_placeholder>",
  "date": "<YYYY-MM-DD>",
  "meals": [
    {{
      "meal_type": "<breakfast/lunch/dinner/snack/preworkout/postworkout>",
      "items": [
        {{
          "food": "<food name>",
          "quantity": <numeric>,
          "weight": <grams_or_ml>,
          "calories": <numeric>,
          "proteins": <grams>,
          "fats": <grams>,
          "carbs": <grams>,
          "fiber": <grams>
        }},
        ...
      ],
      "meal_summary": {{
        "total_calories": <sum of meal calories>,
        "total_protein": <sum of meal proteins>,
        "total_fat": <sum of meal fats>,
        "total_carb": <sum of meal carbs>,
        "total_fiber": <sum of meal fiber>
      }}
    }},
    ...
  ],
  "daily_summary": {{
    "total_calories": <sum of all meal calories>,
    "total_protein": <sum of all meal proteins>,
    "total_fat": <sum of all meal fats>,
    "total_carb": <sum of all meal carbs>,
    "total_fiber": <sum of all meal fiber>,
    "created_at": "<current_timestamp>"
  }}
}}

### Guidelines:
- Identify and separate multiple meals if mentioned (e.g., breakfast, lunch, dinner, snacks).
- Round numbers sensibly — no long decimals.
- If quantity or weight isn’t specified, estimate reasonably based on common portions.
- Ensure that `daily_summary` equals the sum of all meal summaries.
- Return only the JSON object — no extra text or explanation.
Now process:
\"\"\"{food_text}\"\"\"
    """

    data = {
        "model": "x-ai/grok-4.1-fast",
        "messages": [
            {"role": "system", "content": "Respond ONLY with valid JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    text=response.json()['choices'][0]['message']['content']
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print("Did not return")
        print(text)
        return None
if __name__ == "__main__":
    #OPENROUTER_API_KEY = os.getenv("QWEN3_API_KEY")
    food_input = "I had 100g of paneer and a egg."
    reuslt=estimate_calories(food_input)
    print(json.dumps(reuslt,indent=2))