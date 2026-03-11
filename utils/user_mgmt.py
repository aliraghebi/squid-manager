# lib/user_mgmt.py
import curses
import secrets
import string
from subprocess import run, DEVNULL
from utils.config import PASSWD_FILE
from lib.utils import COLORS

# ----------------- Backend -----------------
def list_users():
    if not os.path.exists(PASSWD_FILE):
        return []
    with open(PASSWD_FILE) as f:
        return [line.split(":")[0] for line in f if ":" in line]

def run_htpasswd(username, password=None, delete=False):
    if delete:
        cmd = ["htpasswd", "-D", PASSWD_FILE, username]
    else:
        if not password:
            password = ''.join(secrets.choice(string.ascii_letters + string.digits + "@!-_#:|") for _ in range(24))
            print(f"Generated password for {username}: {password}")
        cmd = ["htpasswd", "-b", PASSWD_FILE, username, password]
    run(cmd, stdout=DEVNULL, stderr=DEVNULL)
    return password if not delete else None

# ----------------- Curses TUI Wrappers -----------------
def input_hidden_password(stdscr, prompt, y):
    allowed_chars = string.ascii_letters + string.digits + "@!-_#:|"
    curses.noecho()
    passwd = []
    x_start = len(prompt)
    stdscr.addstr(y, 0, prompt, COLORS["white"])
    stdscr.move(y, x_start)
    while True:
        ch = stdscr.getch()
        if ch in (10, 13):
            break
        elif ch in (8, 127, curses.KEY_BACKSPACE):
            if passwd: passwd.pop()
        else:
            try:
                c = chr(ch)
                if c in allowed_chars: passwd.append(c)
            except ValueError:
                pass
        stdscr.move(y, x_start)
        stdscr.clrtoeol()
        stdscr.addstr(y, x_start, "*"*len(passwd))
        stdscr.move(y, x_start + len(passwd))
    return "".join(passwd)

def add_user(stdscr, username=None):
    curses.echo()
    stdscr.clear()
    if username:
        stdscr.addstr(0, 0, f"Creating user {username}\n", curses.A_BOLD)
    else:
        stdscr.addstr(0,0,"Create new user:\n", curses.A_BOLD)
        stdscr.addstr(1,0,"Username: ")
        stdscr.refresh()
        username = stdscr.getstr().decode().strip()
    curses.noecho()
    if username:
        password = input_hidden_password(stdscr, "Password (leave empty to generate): ", 2)
        if not password: password = None
        run_htpasswd(username, password)
        stdscr.addstr(4, 0, "User created. Press any key...")
        stdscr.getch()

def change_password(stdscr, username=None):
    users = list_users()
    curses.echo()
    stdscr.clear()
    stdscr.addstr(0,0,"Change user password:\n")
    if not username:
        stdscr.addstr(1,0,"Username: ")
        stdscr.refresh()
        username = stdscr.getstr().decode().strip()
    curses.noecho()
    if username:
        if username not in users:
            stdscr.addstr(3,0,f"User '{username}' does not exist. Create new user? (y/N): ")
            stdscr.refresh()
            ch = stdscr.getch()
            if chr(ch).lower() == "y":
                add_user(stdscr, username=username)
            return
        password = input_hidden_password(stdscr, "New Password (leave empty to generate): ", 4)
        if not password: password = None
        run_htpasswd(username, password)
        stdscr.addstr(6,0,"Password updated. Press any key...")
        stdscr.getch()

def delete_user(stdscr, username=None):
    curses.echo()
    stdscr.clear()
    stdscr.addstr(0,0,"Delete user:\n")
    if not username:
        stdscr.addstr(1,0,"Username: ")
        stdscr.refresh()
        username = stdscr.getstr().decode().strip()
    curses.noecho()
    if username:
        stdscr.addstr(3,0,f"Confirm delete {username}? (y/N): ")
        stdscr.refresh()
        ch = stdscr.getch()
        if chr(ch).lower() == "y":
            run_htpasswd(username, delete=True)
            stdscr.addstr(5,0,"User deleted. Press any key...")
            stdscr.getch()