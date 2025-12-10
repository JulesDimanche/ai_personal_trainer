import os
import re
import duckdb
from functools import lru_cache
import sys
sys.path.append('..')
from typing import Tuple

try:
    from orchestrator_new import client_deepseek, EXTRA_HEADERS
except Exception:
    client_deepseek = None
    EXTRA_HEADERS = {}

MODEL_NAME = os.getenv("SQL_MODEL_NAME", "x-ai/grok-4.1-fast")
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "trainer.duckdb")
MAX_TOKENS = int(os.getenv("SQL_MAX_TOKENS", "512"))
TEMPERATURE = float(os.getenv("SQL_TEMPERATURE", "0.1"))
MAX_RETRIES = int(os.getenv("SQL_MAX_RETRIES", "2"))

FORBIDDEN = {"insert", "update", "delete", "drop", "alter", "create", "attach", "pragma", "replace"}

def is_sql_safe(sql: str) -> Tuple[bool, str]:
    if not sql:
        return False, "Empty SQL."
    sql_strip = sql.strip().rstrip(";")
    lower = sql_strip.lower()
    if ";" in sql_strip:
        return False, "Semicolons / multiple statements detected."
    for bad in FORBIDDEN:
        if re.search(r'\b' + re.escape(bad) + r'\b', lower):
            return False, f"Forbidden keyword detected: {bad}"
    if not re.search(r'^\s*select\b', lower, re.IGNORECASE):
        return False, "Only SELECT queries are allowed."
    return True, ""

def inject_user_clause(sql: str, user_id: str) -> str:
    if not user_id:
        return sql
    lower = sql.lower()
    if "user_id" in lower:
        return sql
    m = re.search(r'\b(group by|order by|limit)\b', lower)
    where_clause = f" WHERE user_id = '{user_id}' "
    if m:
        idx = m.start()
        if re.search(r'\bwhere\b', lower):
            return sql
        return sql[:idx] + where_clause + sql[idx:]
    else:
        if re.search(r'\bwhere\b', lower):
            return sql + f" AND user_id = '{user_id}'"
        return sql + where_clause

def build_system_message(user_id: str) -> str:
    schema = (
        "Table daily_progress(user_id,date,goal,"
        "achieved_calories,achieved_weight_kg,achieved_workout_intensity,"
        "expected_daily_calories,expected_target_weight_kg,expected_workout_intensity,"
        "progress_calories,progress_protein,progress_carbs,progress_fats,"
        "remarks,week_number,created_at,updated_at)"
    )
    rules = (
        "You are an expert SQL generator (DuckDB). Output ONE valid SELECT query only, no commentary. "
        "Always ensure results are filtered by user_id = '{uid}'. Prefer grouping, aggregation, date summaries. "
        "Use DuckDB-compatible SQL. Output only the SQL text (no markdown)."
    )
    return f"{schema}\n{rules}".replace("{uid}", user_id)

def build_user_message(user_question: str) -> str:
    question = user_question.strip()
    if not question:
        question = "Provide a basic SELECT example from daily_progress."
    return f"Question: {question}"

@lru_cache(maxsize=1024)
def generate_sql_cached(user_question: str, user_id: str) -> str:
    return generate_sql(user_question, user_id)

def _extract_sql_from_model(raw: str) -> str:

    if not raw:
        return ""
    raw = re.sub(r"```(?:sql)?", "", raw, flags=re.IGNORECASE).strip()
    m = re.search(r"(select\b[\s\S]*?)(?=;|\Z)", raw, re.IGNORECASE)
    sql_candidate = m.group(1).strip() if m else raw.strip()
    sql_candidate = sql_candidate.strip("`\"' \n;")
    return sql_candidate

def generate_sql(user_question: str, user_id: str, max_retries: int = MAX_RETRIES) -> str:

    if client_deepseek is None:
        raise RuntimeError("client_deepseek is not configured. Import or initialize it in orchestrator_new.")

    system_msg = build_system_message(user_id)
    user_msg = build_user_message(user_question)

    attempt = 0
    last_error = None

    while attempt <= max_retries:
        attempt += 1
        try:
            response = client_deepseek.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                extra_headers=EXTRA_HEADERS,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )
            raw = ""
            try:
                raw = response.choices[0].message.content.strip()
            except Exception:
                raw = getattr(response.choices[0].message, "content", "") or str(response.choices[0])
        except Exception as e:
            last_error = f"API error: {e}"
            continue

        sql_candidate = _extract_sql_from_model(raw)

        if not sql_candidate:
            last_error = "Model returned empty SQL."
            continue

        if "user_id" not in sql_candidate.lower():
            sql_candidate = inject_user_clause(sql_candidate, user_id)

        safe, reason = is_sql_safe(sql_candidate)
        if safe:
            return sql_candidate
        else:
            last_error = f"Unsafe SQL ({reason})."
            user_msg += f" NOTE: previous output unsafe ({reason}). Please return a safe SELECT only."

    raise ValueError(f"Failed to produce valid SQL after {max_retries+1} attempts: {last_error or 'unknown'}")

def execute_sql_on_duckdb(sql: str, duckdb_path: str = DUCKDB_PATH, limit: int = 2000):

    con = duckdb.connect(duckdb_path)
    try:
        if re.search(r'\blimit\b', sql, flags=re.IGNORECASE) is None:
            sql_exec = sql.rstrip().rstrip(";") + f" LIMIT {limit}"
        else:
            sql_exec = sql
        df = con.execute(sql_exec).df()
        return df
    finally:
        con.close()

if __name__ == "__main__":
    test_question = "Total achieved_calories by date for the last 7 days"
    test_user = os.getenv("TEST_USER_ID", "u001")
    try:
        query = generate_sql(test_question, test_user)
        print("Generated SQL:\n", query)
        df = execute_sql_on_duckdb(query)
        print(df.head())
    except Exception as exc:
        print("Error:", exc)
