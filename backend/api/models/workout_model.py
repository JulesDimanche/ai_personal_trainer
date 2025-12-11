from pydantic import BaseModel, Field
from typing import Optional,List

class WorkoutRequest(BaseModel):
    user_id: str=Field(..., description="Unique user id")
    text: Optional[str]=''
    date: Optional[str]=''

class Exercise_Set(BaseModel):
    set_number: int
    reps: int
    weight: Optional[float] = None

class WorkoutExercise(BaseModel):
    exercise_name: str
    muscle_group: str
    sets: List[Exercise_Set]

class SaveWorkoutResponse(BaseModel):
    user_id: str
    date: str
    plan_name: str
    workout_data: List[WorkoutExercise]

class WorkoutEditModel(BaseModel):
    user_id: str
    date: str
    exercise_name: str
    reps: List[int]
    weight: List[float]

class WorkoutDeleteSetModel(BaseModel):
    user_id: str
    date: str
    exercise_name: str
    set_index: int