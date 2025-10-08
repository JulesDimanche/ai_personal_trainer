import os
import google.generativeai as genai
from pymongo import MongoClient
from chromadb import PersistentClient
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
client = MongoClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("DB_NAME")]
workout_col = db["workout_logs"]
diet_col = db["diet_logs"]

def gemini_embedding(text):
    result = genai.embed_content(model='models/gemini-embedding-001', content=text)
    return result['embedding']
chroma_client=PersistentClient(path="./chroma_db")
collection= chroma_client.get_or_create_collection(name='fitness_logs')

def load_user_logs(user_id):
    workout = list(workout_col.find({"user_id": user_id}))
    diets = list(diet_col.find({"user_id": user_id}))
    docs = []
    for w in workout:
        docs.append(f"Workout: {w['summary']}")
    for d in diets:
        docs.append(f"Diet: {d['date']}-Total Calories: {d['total_calories']}")
    return docs
def index_user_data(user_id):
    docs = load_user_logs(user_id)
    for i,doc in enumerate(docs):
        embedding=gemini_embedding(doc)
        collection.add(
            ids=[f"{user_id}_{i}"],
            embeddings=[embedding],
            documents=[doc]
        )
        print(f"Indexed {len(docs)} documents for user {user_id}")
def retrieve_relevant_docs(query, n=3):
    query_embedding = gemini_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n
    )
    return results['documents']
def ask_ai(query):
    relevant_docs = retrieve_relevant_docs(query)
    context = "\n".join(sum(relevant_docs,[]))
    prompt = f"Based on the user's recent logs:\n{context}\n\nAnswer this:{query}"
    model= genai.GenerativeModel('models/gemini-2.0-flash-lite')
    response=model.generate_content(prompt)
    print('Ai response:\n',response.text)
if __name__ == "__main__":
    user_id = "u001"
    index_user_data(user_id)
    ask_ai("how was my calories intake yesterday compared to my workout?")