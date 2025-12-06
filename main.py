from fastapi import FastAPI
from api.routes.macros_route import router as macro_router
from api.routes.user_route import router as user_router
from api.routes.calories_route import router as calories_router
from api.routes.workout_route import router as workout_router
#from api.routes.query_route import router as query_router
app = FastAPI(title="Macro API Wrapper")

# register your routes
app.include_router(macro_router)
app.include_router(user_router)
app.include_router(calories_router)
app.include_router(workout_router)
#app.include_router(query_router)
@app.get("/health")
def health():
    return {"status": "ok"}
