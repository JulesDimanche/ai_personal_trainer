# query_orchestrator.py
import os
import json
import re
from datetime import datetime
from typing import List, Dict, Any

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
MODEL_NAME = "deepseek/deepseek-chat-v3.1:free"
EXTRA_HEADERS = {
    "HTTP-Referer": os.environ.get("SITE_URL", "http://localhost"),
    "X-Title": os.environ.get("SITE_NAME", "Query Orchestrator")
}

# -------------------------
# Try to import existing handlers (fall back gracefully)
# -------------------------
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

# DuckDB SQL generators / executors
try:
    import text_to_sql_runner as sql_runner
except Exception:
    sql_runner = None

try:
    import text_to_sql_prog as sql_progress
except Exception:
    sql_progress = None

'''try:
    import text_to_sql_weekly as sql_weekly
except Exception:
    sql_weekly = None'''

# -------------------------
# Utility: small date helper
# -------------------------
def days_between(start_iso: str, end_iso: str) -> int:
    try:
        s = datetime.fromisoformat(start_iso).date()
        e = datetime.fromisoformat(end_iso).date()
        return abs((e - s).days)
    except Exception:
        return 0

# -------------------------
# 1) Split user query into domain sub-queries using LLM
# -------------------------
SPLIT_PROMPT = """
You are an assistant that breaks a user's natural-language fitness question into a list of sub-questions each mapped to an intent.
Return valid JSON: a list of objects with keys: intent, subquery, start_date (ISO or null), end_date (ISO or null).
Intents allowed: calories, workout, daily_progress, weekly_progress, other.
Example output:
[
  {{"intent":"calories", "subquery":"show calories for last 7 days", "start_date":"2025-10-20", "end_date":"2025-10-26"}},
  {{"intent":"workout", "subquery":"how intense were my workouts this week","start_date":null,"end_date":null}}
]
User question: "{user_question}"
"""

def split_into_subqueries(user_question: str) -> List[Dict[str, Any]]:
    prompt = SPLIT_PROMPT.format(user_question=user_question)
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
        # try to extract JSON
        m = re.search(r'(\[.*\])', raw, re.S)
        if not m:
            # try to parse raw
            data = json.loads(raw)
        else:
            data = json.loads(m.group(1))
        return data if isinstance(data, list) else []
    except Exception as e:
        # fallback: treat entire query as a generic "other" single subquery
        return [{"intent":"other", "subquery": user_question, "start_date": None, "end_date": None}]

# -------------------------
# 2) Router: which backend to use for a subquery?
#    rules:
#      - daily (<=2 days) -> mongo if available
#      - weekly_progress or long date range (>2 days) -> duckdb if available
#      - progress intents -> duckdb preferred
# -------------------------
def choose_backend_for_subquery(intent: str, start_date: str, end_date: str) -> str:
    intent = (intent or "").lower()
    if intent in ("daily_progress", "progress"):
        return "duckdb"
    if intent == "weekly_progress" or intent == "weekly":
        return "mongo"
    # for calories/workout, use mongo for short ranges, duckdb for long range / heavy aggregations
    if intent in ("calories","workout"):
        if start_date and end_date:
            days = days_between(start_date, end_date)
            if days <= 2:
                return "mongo"
            else:
                return "duckdb"
        # if no dates provided, prefer mongo for quick recent queries
        return "mongo"
    # default
    return "mongo"

# -------------------------
# 3) Execute one subquery by calling the appropriate module
#    Each handler returns a serializable Python object (list/dict) and a short text summary.
# -------------------------
def run_subquery_item(item: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    intent = (item.get("intent") or "other").lower()
    text = item.get("subquery") or item.get("query") or ""
    start_date = item.get("start_date")
    end_date = item.get("end_date")

    backend = choose_backend_for_subquery(intent, start_date, end_date)

    result = {"intent": intent, "backend": backend, "query_text": text, "data": None, "summary": None}

    # MONGO path
    if backend == "mongo":
        try:
            if intent == "calories" and mongo_calories:
                q = mongo_calories.build_query(text, user_id)
                rows = mongo_calories.execute_query(q)
                result["data"] = rows
                try:
                    result["summary"] = mongo_calories.format_response(text, rows)
                except Exception:
                    result["summary"] = None
                return result

            if intent == "workout" and mongo_workout:
                q = mongo_workout.build_query(text, user_id)
                rows = mongo_workout.execute_query(q)
                result["data"] = rows
                try:
                    result["summary"] = mongo_workout.format_response(text, rows)
                except Exception:
                    result["summary"] = None
                return result

            if intent == "weekly_progress" and mongo_weekly:
                q = mongo_weekly.build_query(text, user_id)
                rows = mongo_weekly.execute_query(q)
                result["data"] = rows
                try:
                    result["summary"] = mongo_weekly.format_response(text, rows)
                except Exception:
                    result["summary"] = None
                return result

            # generic fallback: try calories module then weekly
            if mongo_calories:
                q = mongo_calories.build_query(text, user_id)
                rows = mongo_calories.execute_query(q)
                result["data"] = rows
                result["summary"] = None
                return result

            # if none available
            result["data"] = []
            return result

        except Exception as e:
            result["error"] = str(e)
            return result

    # DUCKDB path
    else:
        try:
            # progress table (daily progress)
            if intent in ("daily_progress","progress") and sql_progress:
                sql = sql_progress.generate_sql(text, user_id)
                df = sql_progress.execute_sql_on_duckdb(sql)
                result["data"] = json.loads(df.to_json(orient="records", date_format="iso"))
                result["summary"] = None
                return result

            # weekly analytic
            """if intent in ("weekly_progress","weekly") and sql_weekly:
                sql = sql_weekly.generate_sql(text, user_id)
                df = sql_weekly.execute_sql_on_duckdb(sql)
                result["data"] = json.loads(df.to_json(orient="records", date_format="iso"))
                result["summary"] = None
                return result"""

            # foods / workouts analytics via sql_runner
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

            # fallback
            result["data"] = []
            return result

        except Exception as e:
            result["error"] = str(e)
            return result

# -------------------------
# 4) Merge results into context & ask final LLM to answer like a personal trainer
# -------------------------
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

# -------------------------
# Orchestrator entrypoint
# -------------------------
def answer_user_query(user_question: str, user_id: str) -> Dict[str, Any]:
    # 1. split
    subqueries = split_into_subqueries(user_question)

    # 2. run each subquery and collect
    collected = {}
    details = []
    for item in subqueries:
        res = run_subquery_item(item, user_id)
        details.append(res)
        k = res["intent"]
        # append or set
        if k in collected:
            collected[k].append(res)
        else:
            collected[k] = [res]

    # 3. final LLM synthesis
    final_answer = synthesize_final_answer(user_question, collected)

    return {"answer": final_answer, "details": details}

# -------------------------
# Quick test when run directly
# -------------------------
if __name__ == "__main__":
    user_id = "u001"
    q = "How did my calories and workout intensity compare today and 24-10-2025? Any recommendations?"
    out = answer_user_query(q, user_id)
    print("FINAL ANSWER:\n", out["answer"])
    print("\nDETAILS:\n", json.dumps(out["details"], indent=2, default=str))
