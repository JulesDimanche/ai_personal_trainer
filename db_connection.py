from pymongo import MongoClient
import os
from dotenv import load_dotenv
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
client = MongoClient(MONGO_URI)
db=client[DB_NAME]

user_col=db["users"]
workout_col=db["workouts_logs"]
diet_col=db["diet_logs"]
progress_col=db["progress"]

print("MongoDB connected")