from pydantic import BaseModel, Field
from typing import Optional

class UserRequest(BaseModel):
    user_id: str = Field(..., description="Unique user id")
    name: str
    age: int
    gender: Optional[str] = "male"
    weight_kg: float
    height_cm: float
    activity_level: Optional[str] = "moderate"
    goal: Optional[str] = "maintain"
    target_weeks: Optional[int] = 8
    target_weight_kg: Optional[float] = None
