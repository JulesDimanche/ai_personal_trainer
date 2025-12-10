import os
import json
import re
from datetime import datetime
from typing import List, Dict, Any
from Fitness_kb.fitness_coach import run_coach_reasoning_engine
from concurrent.futures import ThreadPoolExecutor, as_completed
from google.genai.types import Type
from google import genai
from google.genai.errors import APIError
from openai import OpenAI
from dotenv import load_dotenv

try:
    import query.calories_query as mongo_calories
except Exception:
    mongo_calories = None

try:
    import query.workout_query as mongo_workout
except Exception:
    mongo_workout = None

try:
    import query.weekly_prog_query as mongo_weekly
except Exception:
    mongo_weekly = None

try:
    import query.macros_query as mongo_macros
except Exception:
    mongo_macros = None
try:
    import sql_query.text_to_sql_runner as sql_runner
except Exception:
    sql_runner = None
try:
    import sql_query.text_to_sql_prog as sql_progress
except Exception:
    sql_progress = None

load_dotenv()
client_deepseek = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)
MODEL_NAME = "x-ai/grok-4.1-fast"
EXTRA_HEADERS = {
    "HTTP-Referer": os.environ.get("SITE_URL", "http://localhost"),
    "X-Title": os.environ.get("SITE_NAME", "Query Orchestrator")
}
try:
    client_gemini = genai.Client()
except Exception as e:
    print(f"Error initializing Gemini client: {e}")
    client_gemini = None
    
SPLIT_MODEL_NAME = "gemini-2.5-flash" 
FINAL_MODEL_NAME = "gemini-2.0-flash-lite" 

def days_between(start_iso: str, end_iso: str) -> int:
    try:
        s = datetime.fromisoformat(start_iso).date()
        e = datetime.fromisoformat(end_iso).date()
        return abs((e - s).days)
    except Exception:
        return 0

SYSTEM_PROMPT = """
You are an expert assistant that breaks a user's natural-language fitness question into a JSON list of precise sub-queries.
Adhere strictly to the JSON schema and rules. Today's date is {today_date}.

--- RULES ---
2. **Intent Types**: "calories", "workout", "daily_progress", "weekly_progress", "macros", "other", "reasoning".
3. **Data Fetching Order**: Data intents MUST come first ("calories", "workout", etc.).
4. **Final Intents**: "reasoning" (for 'why', 'explain', 'stagnation') or "other" (for general summary/comparison) MUST come last.
5. **Reasoning Intent Logic**: For any 'why', 'explain', or stagnation question (e.g., 'why not growing'), automatically include all required data intents first: 'workout' (always), 'calories' (always), 'macros' (if related to weight/muscle), and then 'reasoning' as the final step.
6. **Date Logic**: Convert explicit dates to ISO format. Dates are `null` for "other" or "reasoning" unless the user specifies a range for the analysis. Always include start_date and end_date, if date not present set it as null.
7. **Subquery Text**: Keep it short and actionable.
"""

def split_into_subqueries(user_question: str) -> List[Dict[str, Any]]:
    if not client_gemini:
        return [{"intent": "other", "subquery": user_question, "start_date": None, "end_date": None}]

    today_str = datetime.now().date().isoformat()
    
    user_prompt = f"""
    User question: "{user_question}"
    
    Generate the JSON list of subqueries based on the rules. Ensure the output is ONLY the JSON array.
    """
    try:
        response = client_gemini.models.generate_content(
            model=SPLIT_MODEL_NAME,
            contents=[
                {"role": "user", "parts": [{"text": user_prompt}]}
            ],
            config=genai.types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT.format(today_date=today_str),
                temperature=0.0,
                response_schema={"type": Type.ARRAY, "items": {"type": Type.OBJECT, "properties": {
                    "intent": {"type": Type.STRING},
                    "subquery": {"type": Type.STRING},
                    
                    "start_date": {"type": Type.STRING, "nullable": True}, 
                    "end_date": {"type": Type.STRING, "nullable": True}
                    
                }}}
            )
        )
        
        raw = response.text.strip()
        m = re.search(r'(\[.*\])', raw, re.DOTALL | re.IGNORECASE)
        if m:
            json_str = m.group(1).strip()
        else:
            json_str = re.sub(r'```json|```', '', raw.strip(), flags=re.IGNORECASE).strip()

        json_str = json_str.strip()
        if json_str.startswith('"') and json_str.endswith('"'):
            json_str = json_str[1:-1].strip()
        
        json_str = re.sub(r'```json|```', '', json_str.strip(), flags=re.IGNORECASE).strip()

        data = json.loads(json_str)

        return data if isinstance(data, list) else []
        
    except (APIError, json.JSONDecodeError, Exception) as e:
        if 'json_str' in locals():
            print(f"Failed to parse cleaned string (start): '{json_str[:100]}...'")
        
        print(f"Error splitting query: {e}")
        return [{"intent": "other", "subquery": user_question, "start_date": None, "end_date": None}]


def choose_backend_for_subquery(intent: str, start_date: str, end_date: str) -> str:
    intent = (intent or "").lower()
    days = 0
    if start_date and end_date:
        days = days_between(start_date, end_date)

    if intent in ("daily_progress", "progress"):
        return "duckdb"

    if intent == "weekly_progress":
        return "mongo"
    if intent=="macros":
        return "mongo"
    if intent in ("calories", "workout"):
        if days > 0 or (not start_date and not end_date):
            return "duckdb"
        elif days == 0 and (not start_date or not end_date):
            return "mongo"
        else:
            return "mongo"

    if intent == "other":
        return "duckdb" if days > 2 else "mongo"

    return "mongo"

def run_subquery_item(item: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    intent = (item.get("intent") or "other").lower()
    text = item.get("subquery") or item.get("query") or ""
    start_date = item.get("start_date")
    end_date = item.get("end_date")

    backend = choose_backend_for_subquery(intent, start_date, end_date)

    result = {"intent": intent, "backend": backend, "query_text": text, "data": [], "summary": None}
    
    if backend == "mongo":
         try:
            if intent == "calories" and mongo_calories:
                q = mongo_calories.build_query(item, user_id)
                rows = mongo_calories.execute_query(q)
                rows=mongo_calories.to_toon_compact(rows)
                result["data"] = rows
                return result

            if intent == "workout" and mongo_workout:
                q = mongo_workout.build_workout_query(item, user_id)
                rows = mongo_workout.execute_workout_query(q)
                rows = mongo_workout.to_toon_compact(rows)
                result["data"] = rows
                return result

            if intent == "weekly_progress" and mongo_weekly:
                q = mongo_weekly.build_query(item, user_id)
                rows = mongo_weekly.execute_query(q)
                rows = mongo_weekly.to_toon_compact(rows)
                result["data"] = rows
                return result
            if intent == "macros" and mongo_macros:
                q = mongo_macros.build_macros_query(item, user_id)
                rows = mongo_macros.execute_macros_query(q)
                rows = mongo_macros.to_toon_compact(rows)
                result["data"] = rows
                return result

            if mongo_calories:
                q = mongo_calories.build_query(item, user_id)
                rows = mongo_calories.execute_query(q)
                rows = mongo_calories.to_toon_compact(rows)
                result["data"] = rows
                result["summary"] = None
                return result

            result["data"] = []
            return result

         except Exception as e:
            result["error"] = str(e)
            return result

    else:
        try:
            if intent in ("daily_progress","progress") and sql_progress:
                sql = sql_progress.generate_sql(text, user_id)
                df = sql_progress.execute_sql_on_duckdb(sql)
                result["data"] = json.loads(df.to_json(orient="records", date_format="iso"))
                result["summary"] = None
                return result

            if intent == "calories" and sql_runner:
                sql = sql_runner.generate_sql(text, user_id)
                df = sql_runner.execute_sql_on_duckdb(sql)
                result["data"] = json.loads(df.to_json(orient="records", date_format="iso"))
                return result

            if intent == "workout" and sql_runner:
                sql = sql_runner.generate_sql(text, user_id)
                df = sql_runner.execute_sql_on_duckdb(sql)
                result["data"] = json.loads(df.to_json(orient="records", date_format="iso"))
                return result

            result["data"] = []
            return result

        except Exception as e:
            result["error"] = str(e)
            return result


FINAL_PROMPT_TEMPLATE = """
You are an expert personal trainer and data-informed coach.
The user asked: "{user_question}"

You have the following retrieved data (as JSON) from multiple backends. Use these to answer the user's question as a single, concise and actionable personal trainer response. Mention insights, comparisons, and one or two actionable recommendations.

Data:
{collected_json}

Rules:
- Be concise (1-3 short paragraphs).
- Explain notable trends and any numeric comparisons (percent change, averages) where helpful.
- If data is missing for a requested intent, say so briefly.
- Avoid giving medical advice. Focus on training/nutrition suggestions.
"""

def synthesize_final_answer(user_question: str, collected: Dict[str, Any]) -> str:
    if not client_gemini:
        return "Error: Gemini client not initialized."

    ctx = json.dumps(collected, default=str, indent=2)
    prompt = FINAL_PROMPT_TEMPLATE.format(user_question=user_question, collected_json=ctx)
    
    system_instr = "You are a helpful personal-trainer assistant who uses data to advise users. Be concise (4-8 short paragraphs)."

    try:
        response = client_gemini.models.generate_content(
            model=FINAL_MODEL_NAME,
            contents=[
                {"role": "user", "parts": [{"text": prompt}]}
            ],
            config=genai.types.GenerateContentConfig(
                system_instruction=system_instr,
                temperature=0.2,
                max_output_tokens=800
            )
        )
        return response.text.strip()
    except APIError as e:
        return f"Error synthesizing final answer: {e}"

def temp_final_answer(collected: Dict[str, Any]) -> str:
    context = json.dumps(collected, indent=2, default=str)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant. "
                "Your job is to read the provided data and explain it to the user "
                "in clear, human-friendly language. "
                "Never return JSON. Only return plain English text."
            )
        },
        {
            "role": "user",
            "content": f"Here is the user's data:\n\n{context}\n\n"
                       f"Now give the answer in simple English, no JSON, no objects."
        }
    ]

    resp = client_deepseek.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.3,
        max_tokens=700,
        extra_headers=EXTRA_HEADERS
    )

    return resp.choices[0].message.content.strip()

def answer_user_query(user_question: str, user_id: str) -> Dict[str, Any]:
    subqueries = split_into_subqueries(user_question)
    print ("Subqueries generated:", subqueries)
    collected = {}
    details = []
    data_subqueries=[]
    main_user_query =""
    reason_user_query=""
    for item in subqueries:
        intent = (item.get("intent") or "").lower()
        if intent == "other":
            main_user_query = item.get("subquery", "")
        elif intent == "reasoning":
            reason_user_query = item.get("subquery", "")
        else:
            data_subqueries.append(item)
    MAX_THREADS = 5
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        future_to_item = {executor.submit(run_subquery_item, item, user_id): item 
                          for item in data_subqueries}
        for future in as_completed(future_to_item):
            item = future_to_item[future]
            try:
                res = future.result()
            except Exception as e:
                res = {
                    "intent": (item.get("intent") or "unknown"),
                    "backend": None,
                    "query_text": item.get("subquery", ""),
                    "data": None,
                    "error": str(e),
                }
            details.append(res)
            k = res.get("intent","unknown")
            if k not in collected:
                collected[k] = []
            collected[k].append(res.get("data"))
    print("Collected subquery results:", collected)
    final_answer = synthesize_final_answer(main_user_query, collected) if main_user_query else ""
    resoning_answer=run_coach_reasoning_engine(reason_user_query, collected) if reason_user_query else ""
    temp_ans=temp_final_answer(collected)if (final_answer=="" and reason_user_query=="") else ""
    return {"answer": final_answer+resoning_answer+temp_ans}

if __name__ == "__main__":
    user_id = "b441ef92-d75b-492e-be51-c2c8b46f4048"
    q = "how is my workout yesterday."
    out = answer_user_query(q, user_id)
    print("the query is :",out)
    #print("FINAL ANSWER:\n", out["answer"])
    #print("\nDETAILS:\n", json.dumps(out["details"], indent=2, default=str))