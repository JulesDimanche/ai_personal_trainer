from typing import List, Dict
import math
import random
from google import genai
import re
from dotenv import load_dotenv
load_dotenv()
try:
    client_gemini = genai.Client()
except Exception as e:
    print(f"Error initializing Gemini client: {e}")
    client_gemini = None


def normalize_item(item: Dict) -> Dict:
    def get_key(d, keys, default=0):
        for k in keys:
            if k in d:
                return d[k]
        return default

    calories = float(get_key(item, ["calories", "cal", "kcal"], 0) or 0)
    protein = float(get_key(item, ["protein", "protein_g", "protein_gm"], 0) or 0)
    carbs = float(get_key(item, ["carbs", "carbs_g", "carbohydrates"], 0) or 0)
    fat = float(get_key(item, ["fat", "fat_g"], 0) or 0)

    return {
        **item,
        "calories": calories,
        "protein": protein,
        "carbs": carbs,
        "fat": fat
    }

def protein_density(item: Dict) -> float:
    # protein per calorie
    cal = item.get("calories", 0) or 0.0001
    return item.get("protein", 0) / cal

def pick_top_base_foods(items: List[Dict], remaining_calories: float, n=5) -> List[Dict]:

    normalized = [normalize_item(it) for it in items]

    # reasonable per-meal bounds
    min_c = max(80, remaining_calories * 0.15)    # at least 15% of remaining or 80 kcal
    max_c = max(120, remaining_calories * 0.65)   # at most 65% of remaining or 120 kcal

    filtered = [it for it in normalized if (it["calories"] >= min_c and it["calories"] <= max_c)]

    # if too few, relax bounds progressively
    if len(filtered) < n:
        filtered = [it for it in normalized if (it["calories"] <= remaining_calories * 0.9)]
    if len(filtered) < n:
        filtered = normalized

    # sort by protein density then protein then calories proximity to remaining/3
    def score(it):
        pd = protein_density(it)
        prot = it.get("protein", 0)
        # prefer calories closer to remaining/3 (typical lunch size when 3 meals left)
        cal_diff = abs(it.get("calories", 0) - (remaining_calories / 3 if remaining_calories>0 else it.get("calories",0)))
        return (pd, prot, -cal_diff)

    filtered.sort(key=score, reverse=True)

    # pick top n (if too many, randomly sample from top 2n to keep variety)
    top_candidates = filtered[: min(len(filtered), max(n*2, n))]
    if len(top_candidates) <= n:
        result = top_candidates[:n]
    else:
        result = random.sample(top_candidates[: max(n, min(len(top_candidates), n*2))], n)

    return result

def pick_top_protein_boosters(items: List[Dict], n=2) -> List[Dict]:
    normalized = [normalize_item(it) for it in items]
    # prefer items with highest protein per calorie
    normalized.sort(key=lambda it: protein_density(it), reverse=True)
    return normalized[:n]

def sum_macros_of_components(components: List[Dict]) -> Dict[str, float]:
    total = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
    for c in components:
        total["calories"] += c.get("calories", 0)
        total["protein"] += c.get("protein", 0)
        total["carbs"] += c.get("carbs", 0)
        total["fat"] += c.get("fat", 0)
    # round
    for k in total:
        total[k] = round(total[k], 2)
    return total

# services/llm_service.py
import json
from typing import List, Dict, Any
from google.genai.types import Type

# Example: openai usage. Replace with your LLM client or adapt the call_llm function.
# The function below sends a small payload to LLM and expects strict JSON output.

def build_prompt(base_foods: List[Dict], protein_boosters: List[Dict], remaining_macros: Dict[str, float]) -> str:
    def line(it):
        return f"{it.get('food_name')} | cal: {it.get('calories')}, prot: {it.get('protein')}, carb: {it.get('carbs')}, fat: {it.get('fat')}"

    base_list = "\n".join([line(it) for it in base_foods])
    prot_list = "\n".join([line(it) for it in protein_boosters])

    prompt =f"""
You are a nutrition assistant. The user has the following REMAINING daily macros (for the whole day):
Calories: {remaining_macros.get('calories',0)}, Protein: {remaining_macros.get('protein',0)} g, Carbs: {remaining_macros.get('carbs',0)} g, Fat: {remaining_macros.get('fat',0)} g.

We will suggest 3 meal OPTIONS for the chosen meal (e.g., Lunch). You MUST only use foods from the provided lists below. DO NOT invent any food. Each option should be 1 realistic combination made from 1-2 base foods and optionally 1 protein booster.

Base foods (choose from these only):
{base_list}

Protein boosters (optional; choose from these only):
{prot_list}

Constraints & output format:
- Output ONLY a JSON object with key "suggestions" which is an array of 3 suggestion objects.
- Each suggestion object must have:
  - "components": array of items, each with {{"food_name": "...", "quantity": "...", "calories": number, "protein": number, "carbs": number, "fat": number}}
  - "total_macros": {{"calories": number, "protein": number, "carbs": number, "fat": number}}
Return valid JSON only.
"""

    return prompt

def call_llm(prompt: str) -> Dict:
    try:
        response = client_gemini.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=[
                {"role": "user", "parts": [{"text": prompt}]}
            ],
            config=genai.types.GenerateContentConfig(
                temperature=0.0
            )
        )
        raw = response.text.strip()
        json_str = re.sub(r'```json|```', '', raw.strip(), flags=re.IGNORECASE).strip()
        data=json.loads(json_str)
        return data
    except Exception as e:
        raise NotImplementedError("Please implement call_llm() using your LLM provider. See comments in file.")
