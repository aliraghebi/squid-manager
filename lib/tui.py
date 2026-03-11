import curses
from lib.config import PERIODS
from lib.utils import fmt_bytes
from lib.log_parser import load_usage
from lib.user_mgmt import list_users, run_htpasswd

# ------------------ COLORS ----------------
COLORS = {}

def setup_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)
    curses.init_pair(2, curses.COLOR_YELLOW, -1)
    curses.init_pair(3, curses.COLOR_RED, -1)
    curses.init_pair(4, curses.COLOR_CYAN, -1)
    global COLORS
    COLORS = {
        "green": curses.color_pair(1),
        "yellow": curses.color_pair(2),
        "red": curses.color_pair(3),
        "cyan": curses.color_pair(4)|curses.A_BOLD,
        "selected": curses.A_REVERSE,
        "white": curses.A_NORMAL
    }

# ------------------ HELP & COLORS ----------------
def get_color_for_usage(val, period):
    if val==0: return COLORS["yellow"]
    limits={"hour":2*1024**3,"day":5*1024**3,"week":40*1024**3,"month":200*1024**3}
    if val>limits.get(period,"month"): return COLORS["red"]
    return COLORS["white"]

def draw_help(stdscr,text):
    h,w = stdscr.getmaxyx()
    stdscr.attron(COLORS["cyan"])
    stdscr.addstr(h-1,0,text[:w-1])
    stdscr.attroff(COLORS["cyan"])

# ------------------ HEADER BUILD ----------------
def build_header(cols, widths, sort_column, sort_reverse):
    header=""
    for i, col in enumerate(cols):
        arrow = "↑" if sort_reverse and i==sort_column else "↓" if i==sort_column else ""
        header += f"{col}{arrow}".ljust(widths[i])
    return header

# ------------------ SORT KEY ----------------
def sort_key(x, col_idx):
    val = x[col_idx]
    if val is None:
        if col_idx==3: return 0
        return 0
    if isinstance(val,int): return val
    return val

# ------------------ PAGINATION & SEARCH ----------------
def paginate_list(lst, page, per_page):
    start = page*per_page
    end = start+per_page
    return lst[start:end], len(lst)

def search_modal(stdscr,prompt):
    curses.echo()
    stdscr.clear()
    stdscr.addstr(0,0,prompt)
    stdscr.refresh()
    s = stdscr.getstr().decode().strip()
    curses.noecho()
    return s

# ------------------ USER LIST SCREEN ----------------
def user_list_screen(stdscr):
    cols=["Username","Up","Down","Last Seen","IPs"]
    col_widths=[20,15,15,20,10]
    period_idx=1
    stats=load_usage(PERIODS[period_idx])
    selected_idx=0
    sort_column=3
    sort_reverse=False
    page=0
    per_page=20
    search_filter=""

    while True:
        users=list_users()
        users_with_stats=[]
        for u in users:
            s=stats.get(u,{"up":0,"down":0,"last":None,"ips":{}})
            users_with_stats.append((u,s["up"],s["down"],s["last"],len(s["ips"])))
        if search_filter:
            users_with_stats=[u for u in users_with_stats if search_filter.lower() in u[0].lower()]
        users_sorted=sorted(users_with_stats,key=lambda x: sort_key(x,sort_column),reverse=not sort_reverse)

        paged_users,total=len(users_sorted),(len(users_sorted))
        paged_users,page_total=paginate_list(users_sorted,page,per_page), (len(users_sorted)+per_page-1)//per_page

        stdscr.clear()
        stdscr.addstr(0,0,f"USER LIST (Period: {PERIODS[period_idx].upper()})  Page {page+1}/{page_total}\n",COLORS["cyan"])
        stdscr.addstr(1,0,build_header(cols,col_widths,sort_column,sort_reverse),COLORS["cyan"])
        for idx,u in enumerate(paged_users):
            color=get_color_for_usage(u[1]+u[2],PERIODS[period_idx])
            if idx==selected_idx%per_page: color|=curses.A_REVERSE
            last_str=u[3].strftime("%Y-%m-%d %H:%M") if u[3] else "-"
            fmt=f"{{:<{col_widths[0]}}}{{:<{col_widths[1]}}}{{:<{col_widths[2]}}}{{:<{col_widths[3]}}}{{:<{col_widths[4]}}}"
            stdscr.addstr(2+idx,0,fmt.format(u[0],fmt_bytes(u[1]),fmt_bytes(u[2]),last_str,u[4]),color)

        draw_help(stdscr,"↑↓ Navigate  1-5 Sort  / Search  P Period  R Refresh  ENTER View IPs  B Back  Q Quit")
        stdscr.refresh()
        key=stdscr.getch()

        if key in (curses.KEY_UP,ord('k')): selected_idx=max(0,selected_idx-1)
        elif key in (curses.KEY_DOWN,ord('j')): selected_idx=min(len(users_sorted)-1,selected_idx+1)
        elif key in (ord('q'),ord('Q')): return
        elif key in (ord('b'),ord('B')): return
        elif key in (ord('p'),ord('P')):
            period_idx=(period_idx+1)%len(PERIODS)
            stats=load_usage(PERIODS[period_idx])
        elif key in (ord('r'),ord('R')):
            stats=load_usage(PERIODS[period_idx])
        elif key==ord('/'):
            search_filter=search_modal(stdscr,"Search username:")
            selected_idx=0
            page=0
        elif key in (10,13):
            ip_list_screen(stdscr,users_sorted[selected_idx][0],PERIODS[period_idx],stats)
        elif key in (ord(str(i)) for i in range(1,6)):
            col=int(chr(key))-1
            if col==sort_column: sort_reverse=not sort_reverse
            else: sort_column=col; sort_reverse=False
        # pagination keys
        elif key==curses.KEY_NPAGE: page=min(page+1,page_total-1)
        elif key==curses.KEY_PPAGE: page=max(page-1,0)

# ------------------ IP LIST SCREEN ----------------
def ip_list_screen(stdscr,user,period,stats):
    cols=["IP","Up","Down","Last Seen","Hits"]
    col_widths=[20,15,15,20,10]
    period_idx=PERIODS.index(period)
    selected_idx=0
    sort_column=3
    sort_reverse=False
    page=0
    per_page=20
    user_stats=stats.get(user,{"ips":{}})
    while True:
        ip_list=[(ip,s["up"],s["down"],s["last"],s["hits"]) for ip,s in user_stats["ips"].items()]
        ip_sorted=sorted(ip_list,key=lambda x: sort_key(x,sort_column),reverse=not sort_reverse)
        paged_ip,page_total=paginate_list(ip_sorted,page,per_page),(len(ip_sorted)+per_page-1)//per_page

        stdscr.clear()
        stdscr.addstr(0,0,f"CONNECTED IPs for {user}  (Period: {PERIODS[period_idx].upper()})  Page {page+1}/{page_total}\n",COLORS["cyan"])
        stdscr.addstr(1,0,build_header(cols,col_widths,sort_column,sort_reverse),COLORS["cyan"])
        for idx,ip in enumerate(paged_ip):
            color=get_color_for_usage(ip[1]+ip[2],PERIODS[period_idx])
            if idx==selected_idx%per_page: color|=curses.A_REVERSE
            last_str=ip[3].strftime("%Y-%m-%d %H:%M") if ip[3] else "-"
            fmt=f"{{:<{col_widths[0]}}}{{:<{col_widths[1]}}}{{:<{col_widths[2]}}}{{:<{col_widths[3]}}}{{:<{col_widths[4]}}}"
            stdscr.addstr(2+idx,0,fmt.format(ip[0],fmt_bytes(ip[1]),fmt_bytes(ip[2]),last_str,ip[4]),color)
        draw_help(stdscr,"↑↓ Navigate  1-5 Sort  / Search  P Period  R Refresh  B Back  Q Quit")
        stdscr.refresh()
        key=stdscr.getch()
        if key in (curses.KEY_UP,ord('k')): selected_idx=max(0,selected_idx-1)
        elif key in (curses.KEY_DOWN,ord('j')): selected_idx=min(len(ip_sorted)-1,selected_idx+1)
        elif key in (ord('q'),ord('Q')): return
        elif key in (ord('b'),ord('B')): return
        elif key in (ord('p'),ord('P')):
            period_idx=(period_idx+1)%len(PERIODS)
            stats=load_usage(PERIODS[period_idx])
            user_stats=stats.get(user,{"ips":{}})
        elif key in (ord('r'),ord('R')):
            stats=load_usage(PERIODS[period_idx])
            user_stats=stats.get(user,{"ips":{}})
        elif key==ord('/'):
            # search IP modal
            search_filter=search_modal(stdscr,"Search IP:")
            ip_sorted=[ip for ip in ip_sorted if search_filter in ip[0]]
            page=0
            selected_idx=0
        elif key in (ord(str(i)) for i in range(1,6)):
            col=int(chr(key))-1
            if col==sort_column: sort_reverse=not sort_reverse
            else: sort_column=col; sort_reverse=False
        elif key==curses.KEY_NPAGE: page=min(page+1,page_total-1)
        elif key==curses.KEY_PPAGE: page=max(page-1,0)