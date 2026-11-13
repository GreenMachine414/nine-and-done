"""Drives the HTTP API through a full season + offseason. Run with the server up:  python test/apitest.py"""
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
        return {"error": json.loads(e.read()).get("error"), "code": e.code}


def act(sid, t, **kw):
    r = call(f"s/{sid}/act", {"type": t, **kw})
    if "error" in r:
        print("  !", t, r["error"])
        return None, None
    return r["result"], r["state"]


mode = sys.argv[1] if len(sys.argv) > 1 else "classic"
sid = call("saves", {"name": "API Test", "team": 3, "mode": mode})["id"]
st = call(f"s/{sid}/state")
print("created", sid, st["phase"], "on clock:", st["derived"]["on_clock"], "players:", len(st["players"]))
_, st = act(sid, "draft_auto_pick")
_, st = act(sid, "draft_sim", to="end")
print("after draft:", st["phase"], "roster:", sum(1 for p in st["players"].values() if p["tid"] == 3))
mine = [p for p in st["players"].values() if p["tid"] == 3]
while len(mine) > 15:
    w = min(mine, key=lambda p: p["ovr"])
    _, st = act(sid, "release", pid=w["id"])
    mine = [p for p in st["players"].values() if p["tid"] == 3]
_, st = act(sid, "set_strategy", strategy={"pace": "fast", "star": "heliocentric"})
r, st = act(sid, "sim_day")
print("sim_day user gid:", r["user_gid"])
g = call(f"s/{sid}/game/{r['user_gid']}")
print("game events:", len(g["events"]), "names:", len(g["names"]), "score", g["hs"], g["as"])
# trade eval
other = [p for p in st["players"].values() if p["tid"] == 1]
ev, _ = act(sid, "trade_eval", tid=1, give={"players": [mine[0]["id"]], "picks": []},
            get={"players": [max(other, key=lambda p: p["ovr"])["id"]], "picks": []})
print("eval:", ev["eval"]["msg"], ev["eval"]["meter"], ev["eval"]["ask"])
_, st = act(sid, "block_set", players=[sorted(mine, key=lambda p: -p["ovr"])[4]["id"]], picks=[])
r, st = act(sid, "block_offers")
print("offers:", len(r["offers"]))
if r["offers"]:
    _, st = act(sid, "offer_accept", id=r["offers"][0]["id"])
    print("accepted offer; tx:", st["tx"][-1]["txt"])
fa = sorted([p for p in st["players"].values() if p["tid"] == -1], key=lambda p: -p["ovr"])
r, st = act(sid, "sign", pid=fa[-1]["id"], yrs=1)
r, st = act(sid, "sim_until", until="champion")
print("phase:", st["phase"], "champion:", st["history"][-1]["champ"], "user games:", len(r["user_gids"]))
for pid in st["resign"]:
    act(sid, "resign", pid=pid, yrs=2)
r, st = act(sid, "advance")
print("advanced:", st["season"], st["phase"], "lottery:", bool(st["draft"]["lottery"]))
print("saves:", [(s["id"], s["phase"]) for s in call("saves")][:3])
call(f"saves/{sid}", method="DELETE")
print("OK")
