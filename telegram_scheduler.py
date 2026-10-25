"""Windows logon entry point for StudyFlow's automatic Telegram reminders."""

import argparse
import os
import sys


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from services.telegram_scheduler import run_forever


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path")
    args = parser.parse_args()
    run_forever(args.db_path)
