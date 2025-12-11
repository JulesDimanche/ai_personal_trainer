from db_connection import weight_col
from datetime import datetime
def log_user_weight(user_id: str, weight: float, date: datetime = None):
    if date is None:
        date = datetime.today().strftime("%Y-%m-%d")
    
    result = weight_col.update_one(
        {"user_id": user_id, "date": date},
        {"$set": {"weight": weight}},
        upsert=True
    )
    
    if result.upserted_id:
        print(f"Inserted new weight record for {user_id} on {date}")
    else:
        print(f"Updated weight for {user_id} on {date}")

if __name__ == "__main__":
    weight=input("Enter your weight in kg: ")
    log_user_weight("u001", weight,"2025-10-15")