import os
import json
import re
from datetime import datetime
from typing import List, Dict, Any
from fitness_coach import run_coach_reasoning_engine
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from dotenv import load_dotenv
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
    import calories_query as mongo_calories
except Exception:
    mongo_calories = None

try:
    import workout_query as mongo_workout
except Exception:
    mongo_workout = None

try:
    import weekly_prog_query as mongo_weekly
except Exception:
    mongo_weekly = None

try:
    import macros_query as mongo_macros
except Exception:
    mongo_macros = None
try:
    import text_to_sql_runner as sql_runner
except Exception:
    sql_runner = None

try:
    import text_to_sql_prog as sql_progress
except Exception:
    sql_progress = None


def days_between(start_iso: str, end_iso: str) -> int:
    try:
        s = datetime.fromisoformat(start_iso).date()
        e = datetime.fromisoformat(end_iso).date()
        return abs((e - s).days)
    except Exception:
        return 0

SPLIT_PROMPT = """
You are an assistant that breaks a user's natural-language fitness question into a list of precise sub-queries.
Today's date is {today_date}.

Each subquery must be a JSON object with keys:
  - intent: one of ["calories", "workout", "daily_progress", "weekly_progress", "macros", "other", "reasoning"]
  - subquery: short actionable text to send to the backend module
  - start_date: ISO format YYYY-MM-DD or null
  - end_date: ISO format YYYY-MM-DD or null

================ RULES ================

1. **INTENT: reasoning**
   Use this when the user asks *why*, *explain*, *reason*, *what caused*, *why not improving*, 
   or any deep analysis question that requires reasoning beyond data lookup.
   - reasoning intent DOES NOT fetch data.
   - reasoning intent is sent to a separate reasoning module.
   - reasoning intent must appear **after** the data-fetch intents.

   Example:
     User: "why my bench press strength is not improving?"
     Output:
       - workout → fetch relevant exercises data
       - reasoning → "explain why bench press strength not improving"

2. **INTENT: other**
   Use this when the user is asking for:
   - general answering
   - comparisons
   - insights
   - summary
   - general explanation that does NOT require deep reasoning.

   Example:
     User: "compare my weekly macros"
       - macros  → fetch data
       - other   → final answering

3. **Data intents**
   (calories, workout, daily_progress, weekly_progress, macros)
   Trigger these only when needed to fetch actual data.

4. **Date handling rules**
   - If user gives explicit dates → convert them to ISO
   - If user gives ranges → produce period queries
   - If reasoning or other intent → dates should be null unless user explicitly mentions them

5. **Order of generated subqueries**
   - Always list data-fetch intents first
   - reasoning or other intents must always be last

6. **Comparison logic**
   - For comparing discrete dates → one subquery per date
   - For continuous ranges → one subquery covering full range
   - reasoning → always null dates
   - other → null dates unless range comparison

7. **Keep subquery short and actionable**
   Example: 
     "show weekly macros from 2025-01-10 to 2025-01-17"
     "explain why bench strength not improving"
8. For any "why", "reason", "explain", or stagnation-related questions 
   (e.g., "why my muscle not growing", "why strength not improving"):
   - Automatically include ALL relevant data intents required for analysis:
       • workout (always)
       • calories (always)
       • macros (if related to muscle, strength, weight, or nutrition)
       • progress data if the question mentions growth, improvement, regression
   - The reasoning intent must ALWAYS come last.
   - Dates must be null unless the user specifies time periods.

----------------------------------------

User question: "{user_question}"
"""




def split_into_subqueries(user_question: str) -> List[Dict[str, Any]]:
    today_str=datetime.now().date().isoformat()
    prompt = SPLIT_PROMPT.format(user_question=user_question,today_date=today_str)
    try:
        resp = client_deepseek.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role":"system","content":"You split user fitness questions into intent-level sub-queries."},
                {"role":"user","content":prompt}
            ],
            temperature=0.0,
            extra_headers=EXTRA_HEADERS,
            max_tokens=600
        )
        raw = resp.choices[0].message.content.strip()
        m = re.search(r'(\[.*\])', raw, re.S)
        if not m:
            data = json.loads(raw)
        else:
            data = json.loads(m.group(1))
        return data if isinstance(data, list) else []
    except Exception as e:
        return [{"intent":"other", "subquery": user_question, "start_date": None, "end_date": None}]

def choose_backend_for_subquery(intent: str, start_date: str, end_date: str) -> str:

    intent = (intent or "").lower()

    days = 0
    if start_date and end_date:
        try:
            s = datetime.fromisoformat(start_date).date()
            e = datetime.fromisoformat(end_date).date()
            days = abs((e - s).days)
        except Exception:
            days = 0

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

    result = {"intent": intent, "backend": backend, "query_text": text, "data": None, "summary": None}
    if backend == "mongo":
        try:
            if intent == "calories" and mongo_calories:
                q = mongo_calories.build_query(item, user_id)
                rows = mongo_calories.execute_query(q)
                result["data"] = rows
                return result

            if intent == "workout" and mongo_workout:
                q = mongo_workout.build_workout_query(item, user_id)
                rows = mongo_workout.execute_workout_query(q)
                result["data"] = rows
                return result

            if intent == "weekly_progress" and mongo_weekly:
                q = mongo_weekly.build_query(item, user_id)
                rows = mongo_weekly.execute_query(q)
                result["data"] = rows
                return result
            if intent == "macros" and mongo_macros:
                q = mongo_macros.build_macros_query(item, user_id)
                rows = mongo_macros.execute_macros_query(q)
                result["data"] = rows
                return result

            if mongo_calories:
                q = mongo_calories.build_query(item, user_id)
                rows = mongo_calories.execute_query(q)
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

You have the following retrieved data (as JSON) from multiple backends (MongoDB/DuckDB). Use these to answer the user's question as a single, concise and actionable personal trainer response. Mention insights, comparisons, and one or two actionable recommendations.

Data:
{collected_json}

Rules:
- Be concise (4-8 short paragraphs).
- Explain notable trends and any numeric comparisons (percent change, averages) where helpful.
- If data is missing for a requested intent, say so briefly.
- Avoid giving medical advice. Focus on training/nutrition suggestions.
"""

def synthesize_final_answer(user_question: str, collected: Dict[str, Any]) -> str:
    ctx = json.dumps(collected, default=str, indent=2)
    prompt = FINAL_PROMPT_TEMPLATE.format(user_question=user_question, collected_json=ctx)
    resp = client_deepseek.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role":"system","content":"You are a helpful personal-trainer assistant who uses data to advise users."},
            {"role":"user","content":prompt}
        ],
        temperature=0.2,
        extra_headers=EXTRA_HEADERS,
        max_tokens=800
    )
    return resp.choices[0].message.content.strip()

def answer_user_query(user_question: str, user_id: str) -> Dict[str, Any]:
    subqueries = split_into_subqueries(user_question)
    #print("Subqueries generated:", subqueries)
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
    #check the collected dict
    #print("Collected subquery results:", collected)
    final_answer = synthesize_final_answer(main_user_query, collected) if main_user_query else ""
    resoning_answer=run_coach_reasoning_engine(reason_user_query, collected) if reason_user_query else ""
    return {"answer": final_answer+resoning_answer, "details": details}

if __name__ == "__main__":
    user_id = "u001"
    q = "Why my chest is not growing."
    out = answer_user_query(q, user_id)
    #print("the query is :",out)
    print("FINAL ANSWER:\n", out["answer"])
    #print("\nDETAILS:\n", json.dumps(out["details"], indent=2, default=str))
