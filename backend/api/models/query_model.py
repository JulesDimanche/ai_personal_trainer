from pydantic import BaseModel,Field
from typing import Optional

class QueryRequest(BaseModel):
    user_id: str = Field(..., description="Unique user id")
    query: Optional[str] = ''