"""Scheduler wrapper - runs Gmail monitor every 15 minutes."""

import time
import schedule
from monitor import main as check_gmail

schedule.every(15).minutes.do(check_gmail)

# Run immediately on startup
check_gmail()

while True:
    schedule.run_pending()
    time.sleep(30)
