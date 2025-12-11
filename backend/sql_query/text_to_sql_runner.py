import os
import re
import duckdb
from functools import lru_cache
from typing import Tuple

try:
    from backend.orchestrator_new import client_deepseek, EXTRA_HEADERS
except Exception:
    client_deepseek = None
    EXTRA_HEADERS = {}

MODEL_NAME = os.getenv("SQL_MODEL_NAME", "x-ai/grok-4.1-fast")
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "trainer.duckdb")
TEMPERATURE = float(os.getenv("SQL_TEMPERATURE", "0.1"))
MAX_TOKENS = int(os.getenv("SQL_MAX_TOKENS", "512"))
MAX_RETRIES = int(os.getenv("SQL_MAX_RETRIES", "2"))

FORBIDDEN = {
    "insert", "update", "delete", "drop", "alter",
    "create", "attach", "pragma", "replace"
}

def is_sql_safe(sql: str) -> Tuple[bool, str]:
    if not sql:
        return False, "Empty SQL."

    stripped = sql.strip().rstrip(";")
    lower = stripped.lower()

    if ";" in stripped:
        return False, "Multiple statements or semicolon detected."

    for bad in FORBIDDEN:
        if re.search(r'\b' + re.escape(bad) + r'\b', lower):
            return False, f"Forbidden keyword: {bad}"

    if not re.search(r'^\s*select\b', lower):
        return False, "Only SELECT queries allowed."

    return True, ""


def inject_user_clause(sql: str, user_id: str) -> str:
    if not user_id:
        return sql

    lower = sql.lower()
    if "user_id" in lower:
        return sql

    match = re.search(r'\b(group by|order by|limit)\b', lower)
    if match:
        idx = match.start()
        return sql[:idx] + f" WHERE user_id = '{user_id}' " + sql[idx:]

    if "where" in lower:
        return sql + f" AND user_id = '{user_id}'"
    return sql + f" WHERE user_id = '{user_id}'"

def build_system_message(user_id: str) -> str:
    schema = (
        "Tables:\n"
        "foods(user_id,date,meal_type,food,quantity,weight,calories,proteins,fats,carbs,fiber,source_row_id)\n"
        "workouts(user_id,date,exercise_name,muscle_group,sets,reps,weight,duration_minutes,calories_burned,source_row_id)\n"
    )

    rules = (
        "You generate ONE valid DuckDB SELECT query. "
        "No commentary. No markdown. "
        "Always ensure results are filtered by user_id='{uid}'. "
        "Prefer aggregation/grouping for trends. "
        "Return only SQL."
    )

    return (schema + rules).replace("{uid}", user_id)


def build_user_message(question: str) -> str:
    question = question.strip() or "Provide a sample SELECT query."
    return f"Question: {question}"


def extract_sql(raw: str) -> str:
    if not raw:
        return ""
    raw = re.sub(r"```(?:sql)?", "", raw, flags=re.IGNORECASE).strip()
    m = re.search(r"(select\b[\s\S]*?)(?=;|\Z)", raw, re.IGNORECASE)
    sql = m.group(1).strip() if m else raw.strip()
    return sql.strip(" `\"';")


@lru_cache(maxsize=512)
def generate_sql_cached(question: str, user_id: str) -> str:
    return generate_sql(question, user_id)


def generate_sql(question: str, user_id: str, max_retries: int = MAX_RETRIES) -> str:
    if client_deepseek is None:
        raise RuntimeError("client_deepseek is not initialized.")

    system_msg = build_system_message(user_id)
    user_msg = build_user_message(question)

    attempt = 0
    last_error = None

    while attempt <= max_retries:
        attempt += 1

        try:
            resp = client_deepseek.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                extra_headers=EXTRA_HEADERS,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )
            raw = resp.choices[0].message.content.strip()
        except Exception as e:
            last_error = f"API error: {e}"
            continue

        sql = extract_sql(raw)

        if not sql:
            last_error = "Empty SQL from model."
            continue

        if "user_id" not in sql.lower():
            sql = inject_user_clause(sql, user_id)

        safe, reason = is_sql_safe(sql)
        if safe:
            return sql

        last_error = reason
        user_msg += f" NOTE: previous output unsafe ({reason}). Provide a safe SELECT only."

    raise ValueError(f"Failed to generate safe SQL: {last_error or 'unknown error'}")


def clean_result(df):
    drop = ["source_row_id", "source_doc_id", "created_at", "updated_at"]
    return df.drop(columns=[c for c in drop if c in df.columns], errors="ignore")


def execute_sql_on_duckdb(sql: str, duckdb_path: str = DUCKDB_PATH):
    con = duckdb.connect(duckdb_path)
    try:
        if "limit" not in sql.lower():
            sql = sql.rstrip(";") + " LIMIT 2000"
        df = con.execute(sql).df()
        return clean_result(df)
    finally:
        con.close()

if __name__ == "__main__":
    q = "show all chest workouts"
    user = "u001"
    sql = generate_sql(q, user)
    print("Generated SQL:", sql)
    print(execute_sql_on_duckdb(sql))
