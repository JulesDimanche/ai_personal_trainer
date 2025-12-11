from fastapi import APIRouter, HTTPException
from api.models.food_sugg_model import FoodSuggestionRequest
from api.services.food_sugg_service import suggest_food
router=APIRouter(prefix="/food")
@router.post("/suggest")
async def suggest_food_main(req: FoodSuggestionRequest):
    try:
        res=suggest_food(req)
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

