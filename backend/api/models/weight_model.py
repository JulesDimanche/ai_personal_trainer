from pydantic import BaseModel,Field

class Weight_save(BaseModel):
    user_id:str=Field(..., description="Unique user id")
    date:str
    weight:float