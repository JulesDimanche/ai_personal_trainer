import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from duckdb_etl import etl_incremental
from weekly_update import run_weekly_adaptation
etl_incremental()
run_weekly_adaptation()