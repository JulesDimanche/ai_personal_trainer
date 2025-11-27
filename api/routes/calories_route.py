from fastapi import APIRouter, HTTPException
from api.models.calories_model import CaloriesRequest
from api.services.calories_service import calculate_calories
router = APIRouter(prefix="/calories", tags=["calories"])
@router.post("/calculate")
async def calculate_calorie_intake(payload: CaloriesRequest):
    try:
        calorie_plan = calculate_calories(payload.dict())
        return {"success": True, "calorie_plan": calorie_plan}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")