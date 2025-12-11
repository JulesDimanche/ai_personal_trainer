from pydantic import BaseModel, Field
from typing import Optional

class CaloriesRequest(BaseModel):
    user_id: str=Field(..., description="Unique user id")
    date: Optional[str]=''
    text: Optional[str]=''
class DeleteFood(BaseModel):
    user_id:str
    date:str
    meal_type:str
    food_name:str