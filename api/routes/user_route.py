from fastapi import APIRouter, HTTPException
from api.models.user_model import UserRequest
from api.services.user_service import generate_user_data
router = APIRouter(prefix="/user", tags=["user"])

@router.post("/generate")
async def create_or_update_macro(payload: UserRequest):
    try:
        plan = generate_user_data(payload.dict())
        return {"success": True, "user_data": plan}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
