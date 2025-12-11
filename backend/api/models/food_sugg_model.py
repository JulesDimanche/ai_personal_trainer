from pydantic import BaseModel
from typing import List, Dict, Any

class FoodSuggestionRequest(BaseModel):
    user_id: str
    cuisine: str
    meal_type: str
    target_macros: Dict[str, float]   # {"calories": .., "protein": .., "carbs": .., "fat": ..}
    consumed_macros: Dict[str, float] # same shape

class FoodItem(BaseModel):
    food_name: str
    cuisine: str = None
    meal_type: str = None
    serving_size: str = None
    calories: float
    protein: float
    carbs: float
    fat: float
    extra: Dict[str, Any] = {}

class SuggestedComponent(BaseModel):
    food_name: str
    quantity: str   # e.g. "1 serving", "100g"
    calories: float
    protein: float
    carbs: float
    fat: float

class SuggestedOption(BaseModel):
    components: List[SuggestedComponent]
    total_macros: Dict[str, float]

class FoodSuggestionResponse(BaseModel):
    target_macros: Dict[str, float]
    remaining_macros: Dict[str, float]
    suggestions: List[SuggestedOption]
