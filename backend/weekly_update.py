"""
weekly_adaptation_cron.py

This script is executed daily by Render Cron Tasks.
Its purpose:
1. Loop through all users' macro documents.
2. Identify the week whose end_date == yesterday.
3. Trigger aggregate_and_adapt_week(user_id, start_date)
"""

from datetime import datetime, timedelta
from backend.db_connection import macro_collection
from tracker.progress_tracker import aggregate_and_adapt_week
import traceback

def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")

def run_weekly_adaptation():
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)
    yesterday_str = iso(yesterday)

    print(f"[CRON] Weekly adaptation running for date: {yesterday_str}")

    # Fetch all user plans
    plans = list(macro_collection.find({}))

    for plan in plans:
        user_id = plan.get("user_id")
        weekly_plan = plan.get("Weekly_Plan", [])

        if not user_id or not weekly_plan:
            continue

        # Find which week ends yesterday
        for week in weekly_plan:
            end_date = week.get("end_date")
            start_date = week.get("start_date")

            if not end_date or not start_date:
                continue

            if end_date == yesterday_str:
                print(f"[CRON] Match found → User: {user_id}, Week ending: {end_date}")

                try:
                    # Call main function
                    result = aggregate_and_adapt_week(user_id, start_date)
                    print(f"[CRON] Adaptation completed for {user_id}")
                    print(result.get("weekly_summary", {}))

                except Exception as e:
                    print(f"[CRON] ERROR for user {user_id}: {str(e)}")
                    traceback.print_exc()

    print("[CRON] Weekly adaptation process completed.")


if __name__ == "__main__":
    run_weekly_adaptation()
