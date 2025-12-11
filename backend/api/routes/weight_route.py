from fastapi import HTTPException, APIRouter
from api.models.weight_model import Weight_save
from api.services.weight_service import weight_save,view_weight
router = APIRouter(prefix="/progress", tags=["workout"])
@router.post("/weight_save")
async def save_weight(payload: Weight_save):
    try:
        result = weight_save(payload.dict())
        if result is None:
            raise HTTPException(status_code=500, detail="Failed to save weight")
        return {"success": True, "message": result.get("message", "Weight saved successfully")}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
@router.get("/weight_view")
async def weight_view(user_id):
    try:
        result = view_weight(user_id)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")