import re
import os
import faiss
import json
from sentence_transformers import SentenceTransformer
import numpy as np
from datetime import datetime
from statistics import mean
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

# -------------------------
# LLM client (same pattern as other files)
# -------------------------
client_deepseek = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)
MODEL_NAME = "x-ai/grok-4.1-fast"
EXTRA_HEADERS = {
    "HTTP-Referer": os.environ.get("SITE_URL", "http://localhost"),
    "X-Title": os.environ.get("SITE_NAME", "Query Orchestrator")
}

BASE_DIR = os.path.dirname(__file__)
KB_INDEX_PATH = os.path.join(BASE_DIR, "fitness_kb.index")
KB_JSON_PATH = os.path.join(BASE_DIR, "fitness_kb.json")

faiss_index = faiss.read_index(KB_INDEX_PATH)

with open(KB_JSON_PATH, "r") as f:
    KB_MAP = json.load(f)

embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def retrieve_kb_snippets(user_query: str, top_k: int = 4) -> list:
    query_embedding = embedding_model.encode([user_query])
    query_embedding = np.array(query_embedding).astype("float32")

    distances, indices = faiss_index.search(query_embedding, top_k)

    results = []
    for idx in indices[0]:
        if idx != -1:
            results.append(KB_MAP[str(idx)])

    return results

def build_context_for_llm(user_query: str, user_data: dict, kb_snippets: list) -> str:
    context = []

    context.append("### USER DATA SUMMARY")
    context.append(user_data)

    # 2. Add knowledge base insights
    context.append("\n### EXPERT KNOWLEDGE")
    if kb_snippets:
        for snip in kb_snippets:
            context.append(f"- {snip}")
    else:
        context.append("- No specific KB rules triggered.")

    # 3. Add query
    context.append("\n### USER QUESTION")
    context.append(user_query)

    context ="\n".join(map(str, context))
    #print('The context before return is : ',context)
    return context


def generate_final_explanation(user_query: str, context: str) -> str:

    prompt = f"""
You are an expert fitness coach. Using the user's data and the expert knowledge below,
provide a simple, clear, personalized explanation that directly answers the question.

Avoid generic fitness advice. Use ONLY the user's data + KB context.

--- CONTEXT BELOW ---
{context}
--- END CONTEXT ---

Now provide the explanation:
"""
    try:
        response = client_deepseek.chat.completions.create(
            model=MODEL_NAME,  
            messages=[{"role": "system", "content": "You extract structured data from text."},
                      {"role": "user", "content": prompt}],
            temperature=0.1
        )

        text = response.choices[0].message.content.strip()
        return text
    except Exception as e:
        print(f"❌ LLM call error: {str(e)}")



def run_coach_reasoning_engine(user_query: str, user_data: dict):
    """
    Called by the orchestrator.
    - user_query = original full query
    - user_data = DB data you collected
    - llm_call = your LLM wrapper
    - is_conceptual = your classifier output
    """

    # 1. Retrieve relevant knowledge
    kb_snippets = retrieve_kb_snippets(user_query)

    # 2. Build final context
    context = build_context_for_llm(user_query, user_data, kb_snippets)

    # 3. Generate final answer
    return generate_final_explanation(user_query, context)
if __name__ == "__main__":
    # Example usage
    user_data = {
        "exercise": "incline bench press",
        "avg_reps": "10/8/6",
        "weight_used": "60 lbs",
        "sessions_last_10_days": 5,
        "calories_each_session": [50, 50, 50, 50, 45],
    }
    answer = run_coach_reasoning_engine(
        'Why my progress in incline bench press is not improving?',
        user_data)
    print("Final Answer:\n", answer)
