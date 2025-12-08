from fastapi import APIRouter, HTTPException
from api.models.calories_model import CaloriesRequest,DeleteFood
from api.services.calories_service import calculate_calories,view_calories,delete_food
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
@router.get("/view")
async def view_calories_intake(user_id,date):
    try:
        calorie_data = view_calories(user_id,date)
        return {"success": True, "calorie_data": calorie_data}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
@router.post("/delete")
async def delete(data:DeleteFood):
    return delete_food(data)