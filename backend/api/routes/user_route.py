from fastapi import APIRouter, HTTPException
from backend.api.models.user_model import UserRequest
from backend.api.services.user_service import generate_user_data,view_user
router = APIRouter(prefix="/user", tags=["user"])

'''@router.post("/generate")
async def create_or_update_macro(payload: UserRequest):
    try:
        plan = generate_user_data(payload.dict())
        return {"success": True, "user_data": plan}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")'''
@router.get("/view")
async def view_user_detail(user_id):
    try:
        user_data = view_user(user_id)
        return {"success": True, "user_data": user_data}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")