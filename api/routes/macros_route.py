from fastapi import APIRouter, HTTPException
from api.models.macros_model import MacroRequest
from api.services.macros_service import generate_and_upsert_macro

router = APIRouter(prefix="/macros", tags=["macros"])

@router.post("/generate")
async def create_or_update_macro(payload: MacroRequest):
    try:
        plan = generate_and_upsert_macro(payload.dict())
        return {"success": True, "macro_plan": plan}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
