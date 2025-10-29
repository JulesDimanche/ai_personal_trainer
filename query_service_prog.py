# query_service.py
import duckdb
import pandas as pd
import re
from text_to_sql_prog import generate_sql, execute_sql_on_duckdb
from duckdb_etl import init_schema, etl_incremental, DUCKDB_PATH

def answer_user_query(user_id: str, user_question: str, run_etl_if_needed: bool = False):
    if run_etl_if_needed:
        # cautious: ETL can be heavy; run only when caller requests it
        etl_incremental()

    # ensure DuckDB schema exists
    init_schema()

    # generate SQL (may raise ValueError if model fails)
    sql = generate_sql(user_question, user_id)

    # execute
    sql = (
        sql.replace("{{user_id}}", f"{user_id}")
        .replace("{user_id}", f"{user_id}")
        .replace("'user_id_placeholder'", f"'{user_id}'")
        .replace("user_id_placeholder", f"'{user_id}'")
    )  
    sql = re.sub(
    r"date_sub\s*\(\s*current_date\s*,\s*interval\s+(\d+)\s+day\s*\)",
    r"current_date - interval \1 day",
    sql,
    flags=re.IGNORECASE
)
    print("Generated SQL:\n", sql)
    df = execute_sql_on_duckdb(sql, duckdb_path=DUCKDB_PATH)
    df = df.drop(columns=[c for c in ['source_row_id', 'source_doc_id'] if c in df.columns])
    return df


if __name__ == "__main__":
    # quick demo
    user_id = "u001"
    q = "Give the progress for the last week"
    # for demo we run ETL first so DuckDB is populated
    print("Running ETL...")
    etl_incremental()
    print("Answering query...")
    df = answer_user_query(user_id, q, run_etl_if_needed=False)
    print(df)
