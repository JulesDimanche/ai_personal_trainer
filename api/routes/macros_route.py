from fastapi import APIRouter, HTTPException
from api.models.macros_model import MacroRequest
from api.services.macros_service import generate_and_upsert_macro, view_macros
from api.services.user_service import generate_user_data

router = APIRouter(prefix="/macros", tags=["macros"])

@router.post("/generate")
async def create_or_update_macro(payload: MacroRequest):
    try:
        save_user=generate_user_data(payload)
        plan = generate_and_upsert_macro(payload.dict())
        return {"success": True,"user_data":save_user, "macro_plan": plan}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
@router.get("/view")
async def view_user_macros(user_id,date):
    try:
        user_data = view_macros(user_id,date)
        return {"success": True, "user_data": user_data}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
