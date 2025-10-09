import os
import requests
import json
from dotenv import load_dotenv  
load_dotenv()

def estimate_calories(food_text, api_key):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"}
    prompt=f"""
You are a calorie estimation assistant.
User describes what they ate in natural language.
Output a JSON object with:
- Each food item (name, quantity,weight, estimated calories, proteins, fats, carbs, fiber)
- Total macros (sum of all of individual macros)
Round numbers sensibly.

Example input:
"I had 1 boiled eggs and 200 ml of milk."

Example output:
{{
  "items": [
    {{"food": "boiled egg", "quantity": 1, "Weight":45, "calories": 70, "Proteins":6, "Fats":5, "Carbs":1, "Fiber":0}},
    {{"food": "milk", "quantity": 1, "Weight":250, "calories": 168, "Proteins":8, "Fats":10, "Carbs":12, "Fiber":0}}
  ],
  "total_calories": 238,
  "total_protein": 14,
  "total_fat": 15,
  "total_carb": 13,
  "total_fiber": 0
}}

Now process:
\"\"\"{food_text}\"\"\"
    """

    data = {
        "model": "qwen/qwen-2.5-coder-32b-instruct:free",
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
'''if __name__ == "__main__":
    OPENROUTER_API_KEY = os.getenv("QWEN3_API_KEY")
    food_input = "I had 100g of paneer and a egg."
    reuslt=estimate_calories(food_input, OPENROUTER_API_KEY)
    print(json.dumps(reuslt,indent=2))'''