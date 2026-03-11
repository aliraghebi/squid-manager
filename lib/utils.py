# Helpers for bytes formatting and date utils
from datetime import datetime, timedelta

def fmt_bytes(num):
    for unit in ["B","KB","MB","GB","TB"]:
        if num < 1024:
            return f"{num:.2f} {unit}"
        num /= 1024
    return f"{num:.2f} PB"

def week_start(dt):
    return dt - timedelta(days=dt.weekday())

def month_start(dt):
    return datetime(dt.year, dt.month, 1)