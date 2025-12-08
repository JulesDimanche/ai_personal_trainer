from pydantic import BaseModel, Field
from typing import Optional

class MacroRequest(BaseModel):
    user_id: str = Field(..., description="Unique user id")
    age: int
    name:str
    gender: Optional[str] = "male"
    weight_kg: float
    height_cm: float
    activity_level: Optional[str] = "moderate"
    goal: Optional[str] = "maintain"
    target_weeks: Optional[int] = 8
    target_weight_kg: Optional[float] = None
