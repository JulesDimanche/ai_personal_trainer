from fastapi import APIRouter, Body, HTTPException
from backend.api.models.workout_model import WorkoutRequest,SaveWorkoutResponse,WorkoutDeleteSetModel,WorkoutEditModel
from backend.api.services.workout_service import calculate_workout,view_workout,create_or_update_workout_plan,get_workout_plan,save_plan_and_daily,delete_set,edit_set
router = APIRouter(prefix="/workout", tags=["workout"])
@router.post("/calculate")
async def calculate_workout_data(payload: WorkoutRequest):
    try:
        workout_plan = calculate_workout(payload.dict())
        return {"success": True, "workout_plan": workout_plan}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
@router.get("/view")
async def view_calories_intake(user_id,date):
    try:
        workout_data = view_workout(user_id,date)
        return {"success": True, "workout_data": workout_data}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
@router.post("/save")
async def save_workout_data(payload:SaveWorkoutResponse):
    try:
        for exercise in payload.workout_data:
            sets_list = [s.dict() for s in exercise.sets]
            print("SETS LIST:", sets_list)
            create_or_update_workout_plan(
                user_id=payload.user_id,
                plan_name=payload.plan_name,
                exercise_name=exercise.exercise_name,
                sets_list=sets_list
            )
        return {"success": True, "message": "Workout saved successfully"}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
@router.get("/plan_view")
async def view_workout_plan(user_id: str, plan_name: str | None = None,list_only: bool = False):
    try:
        return get_workout_plan(user_id=user_id, plan_name=plan_name,list_only=list_only)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
@router.post("/plan_save_and_upsert")
async def plan_save_and_upsert(payload: dict = Body(...)):
    user_id = payload.get("user_id")
    date = payload.get("date")
    plan_name = payload.get("plan_name")
    entries = payload.get("entries", [])

    result = save_plan_and_daily(user_id=user_id, date=date, plan_name=plan_name, frontend_exercises=entries)
    return result
@router.post("/edit")
async def edit(payload: WorkoutEditModel):
    return edit_set(payload)

@router.post("/delete")
async def delete_set_ex(data: WorkoutDeleteSetModel):
    return delete_set(data)
