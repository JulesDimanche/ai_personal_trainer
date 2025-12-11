from backend.duckdb_etl import etl_incremental
from backend.weekly_update import run_weekly_adaptation
etl_incremental()
run_weekly_adaptation()