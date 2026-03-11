import os, secrets, string, subprocess
from utils.config import PASSWD_FILE

def list_users():
    if not os.path.exists(PASSWD_FILE): return []
    with open(PASSWD_FILE) as f:
        return [line.split(":")[0] for line in f if ":" in line]

def run_htpasswd(username, password=None, delete=False):
    if delete:
        cmd = ["htpasswd", "-D", PASSWD_FILE, username]
    else:
        if not password:
            password = ''.join(secrets.choice(string.ascii_letters+string.digits+"@!-_#:|") for _ in range(24))
            print(f"Generated password: {password}")
        cmd = ["htpasswd","-b",PASSWD_FILE,username,password]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return password if not delete else None