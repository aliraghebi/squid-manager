import os, gzip, re
from datetime import datetime, timedelta
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.config import LOG_DIR, LOG_PREFIX, PERIODS

LINE_RE = re.compile(
    rb"^(?P<ts>\d+)\s+"
    rb"(?P<user>\S+)\s+"
    rb"(?P<ip>\S+)\s+"
    rb"(?P<method>\S+)\s+"
    rb"(?P<url>\S+)\s+"
    rb"(?P<status>\d+)\s+"
    rb"(?P<upload>\d+)\s+"
    rb"(?P<download>\d+)\s*$"
)

def get_since(period):
    now = datetime.now()
    if period=="hour": return now - timedelta(hours=1)
    elif period=="day": return datetime(now.year, now.month, now.day)
    elif period=="week": return now - timedelta(days=now.weekday())
    else: return datetime(now.year, now.month, 1)

def parse_file(path, since):
    stats = defaultdict(lambda: {"up":0,"down":0,"last":None,"ips":defaultdict(lambda: {"up":0,"down":0,"last":None,"hits":0})})
    future_grace = timedelta(days=400)
    open_func = gzip.open if path.endswith(".gz") else open
    with open_func(path,"rb") as f:
        for line in f:
            m = LINE_RE.match(line.strip())
            if not m: continue
            user = m.group(b"user").lstrip(b"[").strip()
            if user in (b"-",b"none",b""): continue
            user = user.decode()
            ts = int(m.group(b"ts"))
            dt = datetime.fromtimestamp(ts)
            if dt - datetime.now() > future_grace: dt = datetime.now()
            if dt < since: continue
            up = int(m.group(b"upload"))
            down = int(m.group(b"download"))
            ip = m.group(b"ip").decode()

            s = stats[user]
            s["up"] += up
            s["down"] += down
            if not s["last"] or dt > s["last"]: s["last"] = dt

            ip_stats = s["ips"][ip]
            ip_stats["up"] += up
            ip_stats["down"] += down
            ip_stats["hits"] += 1
            if not ip_stats["last"] or dt > ip_stats["last"]: ip_stats["last"] = dt
    return stats

def merge_stats(all_stats):
    merged = defaultdict(lambda: {"up":0,"down":0,"last":None,"ips":defaultdict(lambda: {"up":0,"down":0,"last":None,"hits":0})})
    for s in all_stats:
        for user, udata in s.items():
            m = merged[user]
            m["up"] += udata["up"]
            m["down"] += udata["down"]
            if not m["last"] or (udata["last"] and udata["last"] > m["last"]): m["last"] = udata["last"]
            for ip, ipdata in udata["ips"].items():
                mip = m["ips"][ip]
                mip["up"] += ipdata["up"]
                mip["down"] += ipdata["down"]
                mip["hits"] += ipdata["hits"]
                if not mip["last"] or (ipdata["last"] and ipdata["last"] > mip["last"]): mip["last"] = ipdata["last"]
    return merged

def iter_logs():
    for name in os.listdir(LOG_DIR):
        if name==LOG_PREFIX or name.startswith(LOG_PREFIX+"."):
            yield os.path.join(LOG_DIR,name)

def load_usage(period="day", max_workers=4):
    since = get_since(period)
    files = list(iter_logs())
    stats_list = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(parse_file, f, since) for f in files]
        for fut in as_completed(futures):
            stats_list.append(fut.result())
    return merge_stats(stats_list)