# text_to_sql_progress.py
import os
import re
import duckdb
from openai import OpenAI
from functools import lru_cache
from typing import Tuple
from orchestrator_new import client_deepseek, EXTRA_HEADERS

# --------------------------------------------------------------------
# API CLIENT CONFIG (OpenRouter + DeepSeek)
# --------------------------------------------------------------------
'''client_deepseek = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)


EXTRA_HEADERS = {
    "HTTP-Referer": os.environ.get("SITE_URL", "http://localhost"),
    "X-Title": os.environ.get("SITE_NAME", "Progress SQL Generator")
}'''
MODEL_NAME = "x-ai/grok-4.1-fast"

DUCKDB_PATH = os.getenv("DUCKDB_PATH", "trainer.duckdb")

# --------------------------------------------------------------------
# SQL SAFETY HELPERS
# --------------------------------------------------------------------
FORBIDDEN = ["insert", "update", "delete", "drop", "alter", "create", "attach", "pragma"]

def is_sql_safe(sql: str) -> Tuple[bool, str]:
    lower = sql.lower()
    sql_stripped = sql.strip()
    if sql_stripped.endswith(";"):
        sql_stripped = sql_stripped[:-1] 
        sql = sql_stripped

    if ";" in sql_stripped:
        return False, "Multiple statements or semicolon detected."
    for bad in FORBIDDEN:
        if bad in lower:
            return False, f"Forbidden keyword detected: {bad}"
    if not re.search(r'^\s*select\s+', lower):
        return False, "Only SELECT queries are allowed."
    return True, ""

def inject_user_clause(sql: str, user_id: str) -> str:
    lower = sql.lower()
    if "user_id" in lower:
        return sql
    match = re.search(r'\b(group by|order by|limit)\b', lower)
    if match:
        idx = match.start()
        return sql[:idx] + f" WHERE user_id = '{user_id}' " + sql[idx:]
    else:
        return sql + f" WHERE user_id = '{user_id}'"

# --------------------------------------------------------------------
# PROMPT GENERATION
# --------------------------------------------------------------------
def build_schema_prompt(user_id) -> str:
    return (
        "### DATABASE SCHEMA ###\n"
        "Table daily_progress(\n"
        "  user_id TEXT,\n"
        "  date DATE,\n"
        "  goal TEXT,\n"
        "  achieved_calories DOUBLE,\n"
        "  achieved_weight_kg DOUBLE,\n"
        "  achieved_workout_intensity DOUBLE,\n"
        "  expected_daily_calories DOUBLE,\n"
        "  expected_target_weight_kg DOUBLE,\n"
        "  expected_workout_intensity DOUBLE,\n"
        "  progress_calories DOUBLE,\n"
        "  progress_protein DOUBLE,\n"
        "  progress_carbs DOUBLE,\n"
        "  progress_fats DOUBLE,\n"
        "  remarks TEXT,\n"
        "  week_number INTEGER,\n"
        "  created_at TIMESTAMP,\n"
        "  updated_at TIMESTAMP\n"
        ")\n\n"
        "### TASK ###\n"
        "You are an expert SQL generator. Produce **one DuckDB-compatible SQL query** that answers the question below.\n"
        "- Use only SELECT statements (no modifications).\n"
        f"- Always filter results by the user's ID `user_id = '{user_id}'`.\n"
        "- Prefer grouping, aggregation, and date-based summaries.\n"
        "- Output only SQL — no commentary, no markdown.\n"
        
    )

def build_prompt(user_question: str, user_id: str) -> str:
    schema = build_schema_prompt(user_id)
    return (
        f"{schema}\n"
        f"### USER QUESTION ###\n{user_question}\n"
        f"### OUTPUT ###\nSQL Query:\n"
    )

# --------------------------------------------------------------------
# SQL GENERATION (REMOTE MODEL)
# --------------------------------------------------------------------
@lru_cache(maxsize=256)
def generate_sql_cached(user_question: str, user_id: str) -> str:
    return generate_sql(user_question, user_id)

def generate_sql(user_question: str, user_id: str, max_retries: int = 2) -> str:
    prompt = build_prompt(user_question, user_id)
    attempt = 0
    last_error = None
    sql_candidate = None

    while attempt <= max_retries:
        attempt += 1
        try:
            response = client_deepseek.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert SQL generator specialized in DuckDB. Always output valid SQL only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                extra_headers=EXTRA_HEADERS,
                temperature=0.1,
                max_tokens=512,
            )
            raw = response.choices[0].message.content.strip()
        except Exception as e:
            last_error = str(e)
            continue

        # Extract SQL text
        raw = re.sub(r"```+\s*sql", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"```+", "", raw).strip()
        m = re.search(r"(select[\s\S]*?)(?=;|\Z)", raw, re.IGNORECASE)
        sql_candidate = m.group(1).strip() if m else raw.strip()
        sql_candidate = re.sub(r";+", "", sql_candidate).strip()
        sql_candidate = re.sub(r"^`+|`+$", "", sql_candidate).strip()

        # Safety & user_id injection
        safe, reason = is_sql_safe(sql_candidate)
        if not safe:
            last_error = reason
            prompt += f"\n\n# Correction needed: previous SQL was unsafe ({reason}). Please fix."
            continue

        if "user_id" not in sql_candidate.lower():
            sql_candidate = inject_user_clause(sql_candidate, user_id)

        safe, reason = is_sql_safe(sql_candidate)
        if safe:
            return sql_candidate
        else:
            last_error = reason

    raise ValueError(f"❌ Failed to produce valid SQL: {last_error or 'unknown error'}")

def execute_sql_on_duckdb(sql: str, duckdb_path: str = DUCKDB_PATH):
    con = duckdb.connect(duckdb_path)
    if re.search(r'\blimit\b', sql, flags=re.IGNORECASE) is None:
        sql_exec = sql + " LIMIT 2000"
    else:
        sql_exec = sql
    try:
        df = con.execute(sql_exec).df()
        return df
    finally:
        con.close()
if __name__=="__main__":
    gen=generate_sql('fetch daily calorie intake data','u001')
    print('the query is: ',gen)
    ans=execute_sql_on_duckdb(gen)
    print('Then ans is: ',ans)