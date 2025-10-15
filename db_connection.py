from pymongo import MongoClient
import os
from dotenv import load_dotenv
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
client = MongoClient(MONGO_URI)
db=client[DB_NAME]

macro_collection=db['macro_plans']
user_col=db["users"]
workout_col=db["workouts_logs"]
workout_summary_col=db["workout_summary"]
diet_col=db["diet_logs"]
summary_col=db['diet_summary']
progress_col=db["progress"]
progress_weekly_col=db["weekly_progress"]
weight_col=db["weights"]

print("MongoDB connected")