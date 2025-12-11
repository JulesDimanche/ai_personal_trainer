from fastapi import APIRouter, HTTPException
from api.models.query_model import QueryRequest
from api.services.query_service import query_answer_sevice 
router = APIRouter(prefix="/query", tags=["query"])
@router.post("/answer")
async def answer_query(payload: QueryRequest):
    try:
        answer = query_answer_sevice(payload.dict())
        return {"success": True, "answer": answer}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")