from backend.db_connection import food_normal_col,food_protein_col
import json
from pymongo import UpdateOne


def load_json(filepath):
    with open(filepath,'r',encoding="utf-8") as f:
        return json.load(f)
    
def bulk_upsert(collection, data, unique_fields):
    ops = []

    for item in data:
        unique_filter = {field: item[field] for field in unique_fields}

        ops.append(
            UpdateOne(unique_filter, {"$set": item}, upsert=True)
        )

    if ops:
        result = collection.bulk_write(ops)
        print(f"Inserted: {result.upserted_count}, Updated: {result.modified_count}")
normal_data = load_json("food_data_normal.json")
protein_data = load_json("food_data_protein.json")
bulk_upsert(
    collection=food_normal_col,
    data=normal_data,
    unique_fields=["cuisine", "meal_type", "food_name"]
)

bulk_upsert(
    collection=food_protein_col,
    data=protein_data,
    unique_fields=["food_name"]
)