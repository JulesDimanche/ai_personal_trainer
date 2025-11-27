from pydantic import BaseModel, Field
from typing import Optional

class WorkoutRequest(BaseModel):
    user_id: str=Field(..., description="Unique user id")
    text: Optional[str]=''