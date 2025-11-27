from fastapi import APIRouter, HTTPException
from api.models.workout_model import WorkoutRequest
from api.services.workout_service import calculate_workout
router = APIRouter(prefix="/workout", tags=["workout"])
@router.post("/calculate")
async def calculate_workout_data(payload: WorkoutRequest):
    try:
        calorie_plan = calculate_workout(payload.dict())
        return {"success": True, "calorie_plan": calorie_plan}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")