from duckdb_etl import etl_incremental
from weekly_update import run_weekly_adaptation
etl_incremental()
run_weekly_adaptation()