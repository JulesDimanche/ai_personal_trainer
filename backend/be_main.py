from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import timedelta
import uuid
from dependencies import get_current_user
import sys
sys.path.append('..')
from api.routes.macros_route import router as macro_router
from api.routes.calories_route import router as calories_router
from api.routes.workout_route import router as workout_router
#from api.routes.query_route import router as query_router
from api.routes.user_route import router as user_router
from api.routes.weight_route import router as weight_router
from api.routes.food_sug_rotue import router as food_sug_router
from db_connection import user_data
from auth import hash_password, verify_password, create_access_token

app = FastAPI()
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserCreate(BaseModel):
    name:str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

@app.post("/auth/signup")
def signup(user: UserCreate):
    if user_data.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = str(uuid.uuid4()) 
    hashed_pw = hash_password(user.password)
    user_data.insert_one({"user_id":user_id,"name":user.name,"email": user.email, "password": hashed_pw})

    token = create_access_token({"sub": user.email,"user_id":user_id})
    return {"token": token,"user_id": user_id,"name":user.name}

@app.post("/auth/login")
def login(user: UserLogin):
    db_user = user_data.find_one({"email": user.email})
    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    if not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    user_id=db_user['user_id']
    token = create_access_token({"sub": user.email,"user_id":user_id})
    return {"token": token,"user_id": user_id,"name":db_user["name"]}
@app.get("/dashboard")
def dashboard(user = Depends(get_current_user)):
    return {
        "message": "Welcome",
        "user_id": user["user_id"]
    }
app.include_router(macro_router)
app.include_router(calories_router)
app.include_router(workout_router)
#app.include_router(query_router)
app.include_router(user_router)
app.include_router(weight_router)
app.include_router(food_sug_router)