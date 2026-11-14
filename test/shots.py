"""Headless Edge screenshots of app routes.  python test/shots.py <sid> route1 route2 ...  (server must be up)
Writes PNGs to test/shots/."""
import os
import subprocess
import sys
import tempfile
import time

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUT = os.path.join(os.path.dirname(__file__), "shots")
os.makedirs(OUT, exist_ok=True)
sid = sys.argv[1]
w, h = map(int, os.environ.get("ND_SIZE", "1500,1000").split(","))
for route in sys.argv[2:]:
    name = (os.environ.get("ND_PREFIX", "") + (route.replace("/", "_").replace("?", "_").replace("=", "") or "landing"))
    path = os.path.join(OUT, f"{name}.png")
    owner = os.environ.get("ND_OWNER", "")
    oq = f"&owner={owner}" if owner else ""
    url = f"http://127.0.0.1:8777/?sid={sid}{oq}#/{route}" if sid != "0" else f"http://127.0.0.1:8777/?x=1{oq}"
    prof = tempfile.mkdtemp()
    if os.path.exists(path):
        os.remove(path)
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={prof}",
                    f"--window-size={w},{h}", "--virtual-time-budget=6000", f"--screenshot={path}", url],
                   capture_output=True, timeout=60)
    for _ in range(40):          # Edge can return before the PNG is flushed
        if os.path.exists(path) and os.path.getsize(path) > 0:
            break
        time.sleep(0.25)
    time.sleep(1.0)
    print(path, os.path.exists(path))
