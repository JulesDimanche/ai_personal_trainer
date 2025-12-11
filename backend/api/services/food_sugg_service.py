import os
import sys
from typing import List,Dict
from backend.suggest.food_sug import pick_top_base_foods,pick_top_protein_boosters,normalize_item,build_prompt,call_llm
from backend.api.models.food_sugg_model import SuggestedComponent,SuggestedOption
try:
    from backend.db_connection import db as db_
    food_normal_col=db_['food_normal']
    print('food_normal is imported from db')
    food_protein_col=db_['food_protein']
    print('food_protein is imported from db')
except Exception as e:
    raise RuntimeError("Please provide food_normal_col and food_protein_col in config.py") from e

def fetch_base_foods(cuisine: str, meal_type: str) -> List[Dict]:
    docs = list(food_normal_col.find({"cuisine": cuisine, "meal_type": meal_type}, {"_id": 0}))
    return docs

def fetch_protein_boosters() -> List[Dict]:
    docs = list(food_protein_col.find({}, {"_id": 0}))
    return docs

def suggest_food(req):
    target = req.target_macros
    consumed = req.consumed_macros
    remaining = {
        "calories": max(0, target.get("calories", 0) - consumed.get("calories", 0)),
        "protein": max(0, target.get("protein", 0) - consumed.get("protein", 0)),
        "carbs": max(0, target.get("carbs", 0) - consumed.get("carbs", 0)),
        "fat": max(0, target.get("fat", 0) - consumed.get("fat", 0))
    }
    print('The remaining is ',remaining)

    base_foods_all = fetch_base_foods(req.cuisine, req.meal_type.lower())
    protein_boosters_all = fetch_protein_boosters()

    if not base_foods_all:
        return ('food base is not present')

    top_bases = pick_top_base_foods(base_foods_all, remaining.get("calories", 0), n=5)
    top_boosters = pick_top_protein_boosters(protein_boosters_all, n=2)

    top_bases = [normalize_item(it) for it in top_bases]
    top_boosters = [normalize_item(it) for it in top_boosters]

    prompt = build_prompt(top_bases, top_boosters, remaining)
    try:
        llm_json=call_llm(prompt)
    except NotImplementedError as e:
        return (f'the error is {e}')
    except Exception as e:
        return (f'the error is {e}')

    try:
        suggestions_raw = llm_json.get("suggestions", [])
        suggestions = []
        for s in suggestions_raw:
            comps = []
            for c in s.get("components", []):
                comp = SuggestedComponent(
                    food_name=c["food_name"],
                    quantity=c.get("quantity", "1 serving"),
                    calories=float(c.get("calories", 0)),
                    protein=float(c.get("protein", 0)),
                    carbs=float(c.get("carbs", 0)),
                    fat=float(c.get("fat", 0))
                )
                comps.append(comp)
            tot = {k: float(v) for k, v in s.get("total_macros", {}).items()}
            suggestions.append(SuggestedOption(components=comps, total_macros=tot))
        return suggestions
    except Exception as e:
        return (f"the error is {e}")