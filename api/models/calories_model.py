from pydantic import BaseModel, Field
from typing import Optional

class CaloriesRequest(BaseModel):
    user_id: str=Field(..., description="Unique user id")
    text: Optional[str]=''