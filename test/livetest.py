"""Drives live coaching, upgrades, talks and the All-Star weekend over HTTP. Server must be running.
Usage: python test/livetest.py [keep]   (pass 'keep' to leave the test league in the save list)"""
import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8777/api/"


def call(path, body=None, method=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method or ("POST" if data else "GET"),
                                 headers={"Content-Type": "application/json", "X-ND-Owner": "test-runner-0001"})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": json.loads(e.read()).get("error")}


sid = call("saves", {"name": "Live Test", "team": 5, "mode": "classic"})["id"]
st = call(f"s/{sid}/act", {"type": "draft_sim", "to": "end"})["state"]
mine = [p for p in st["players"].values() if p["tid"] == 5]
while len(mine) > 15:
    w = min(mine, key=lambda p: p["ovr"])
    st = call(f"s/{sid}/act", {"type": "release", "pid": w["id"]})["state"]
    mine = [p for p in st["players"].values() if p["tid"] == 5]
print("talk:", call(f"s/{sid}/act", {"type": "talk", "pid": mine[0]["id"], "approach": "praise"})["result"])
print("talk again:", call(f"s/{sid}/act", {"type": "talk", "pid": mine[0]["id"], "approach": "praise"}).get("error"))
print("upgrade (should be unaffordable at start):", call(f"s/{sid}/act", {"type": "upgrade", "key": "analytics"}).get("error"))

for game in range(6):
    r = call(f"s/{sid}/live", {"cmd": "start"})
    if r.get("error"):
        print("start err", r["error"])
        break
    side = r["meta"]["side"]
    print(f"game {game}: {len(r['meta']['rosters'][0])} v {len(r['meta']['rosters'][1])} players, rival tier",
          r["meta"]["rival"])
    blocked = call(f"s/{sid}/act", {"type": "sim_day"}).get("error")
    assert blocked and "live" in blocked, blocked
    n, decisions = 0, []
    while True:
        r = call(f"s/{sid}/live", {"cmd": "step"})
        assert "error" not in r, r
        n += 1
        if r.get("final"):
            print(f"   final after {n} chunks, challenges {r['challenges']}, decisions {decisions}")
            break
        d = r.get("decision")
        if n == 3:
            on = r["snap"]["on"][side]
            bench = [p for p in r["meta"]["rosters"][side]] if "meta" in r else None
            sub = call(f"s/{sid}/live", {"cmd": "strategy", "k": "pace", "v": "fast"})
            assert "error" not in sub, sub
        if not d:
            continue
        decisions.append(d["type"])
        if d["type"] == "run":
            t = call(f"s/{sid}/live", {"cmd": "timeout"})
            if "error" not in t:
                call(f"s/{sid}/live", {"cmd": "huddle", "choice": "fire"})
                if t.get("read"):
                    call(f"s/{sid}/live", {"cmd": "def_read", "pid": t["read"]["pid"], "choice": "three"})
        elif d["type"] == "break" and d.get("halftime"):
            call(f"s/{sid}/live", {"cmd": "half", "choice": (d["halftime"].get("options") or ["rim"])[0] if isinstance((d["halftime"].get("options") or ["rim"])[0], str) else d["halftime"]["options"][0]["pid"]})
        elif d["type"] == "final_play":
            print("   final play!", call(f"s/{sid}/live", {"cmd": "final_play", "call": "iso", "acc": 0.03})["result"])
    st = call(f"s/{sid}/state")
    if st.get("allstar") and st["allstar"]["status"] == "ready":
        print("allstar ready; user needs three:", st["derived"]["three_pending"])
        if st["derived"]["three_pending"]:
            st = call(f"s/{sid}/act", {"type": "allstar_three", "accs": [0.02] * 25})["state"]
        st = call(f"s/{sid}/act", {"type": "allstar_run"})["state"]
        a = st["allstar"]
        print("   ASG", a["score"], "3pt winner", a["three"]["winner"], "game doc:",
              bool(call(f"s/{sid}/game/{a['gid']}").get("events")))
t = st["teams"][5]
print("FP", t["fp"], "chem", st["derived"]["chem"][5], "rivals with us:",
      {k: round(v["score"]) for k, v in st["rivals"].items() if "5" in k.split("-") and v["score"] > 5})
print("morale:", sorted((round(p["morale"]), p["trait"]) for p in st["players"].values() if p["tid"] == 5)[:5])
if "keep" not in sys.argv:
    call(f"saves/{sid}", method="DELETE")
print("OK", sid)
