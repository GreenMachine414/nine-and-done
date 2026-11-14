"""Nine & Done — local web server.  Run:  python server.py  (then open http://127.0.0.1:8777)"""
import json
import re
import signal
import mimetypes
import os
import random
import sys
import threading
import traceback
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

from nd import league as LG, trade as TR, players as P, franchise as FR, office as OF
from nd.data import CONFERENCES
from nd.data import TEAMS, SALARY_CAP, HARD_APRON, ROSTER_MAX, ROSTER_MIN, TRADE_DEADLINE_DAY, SEASON_DAYS
from nd.store import Store

ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(ROOT, "static")
PORT = int(os.environ.get("PORT") or os.environ.get("NINE_PORT") or 8777)
HOSTED = bool(os.environ.get("PORT") or os.environ.get("RAILWAY_ENVIRONMENT"))
HOST = os.environ.get("HOST") or ("0.0.0.0" if HOSTED else "127.0.0.1")
store = Store(os.path.join(ROOT, "data", "ninedone.db"), os.environ.get("DATABASE_URL"))
OWNER_OK = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
READ_ONLY = {"trade_eval"}
LOCK = threading.RLock()
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("image/svg+xml", ".svg")


def view(L):
    """League state + derived data for the client."""
    ranks = LG.strength_ranks(L)
    out = dict(L)
    out.pop("draft_log", None)
    out["players"] = {}
    sc_lvl = FR.lvl(L, L["user"], "scouting")
    D = P.disp
    for k, p in L["players"].items():
        q = dict(p)
        q.pop("t", None)
        q["t"] = {kk: vv for kk, vv in p["t"].items() if kk != "_n"}
        q["tv"] = TR.player_value(L, p)
        # players are shown only as half-star ratings; raw numbers stay for sorting
        q["hist"] = [{**h, "st": P.stars_for(h["ovr"])} for h in p.get("hist", [])]
        if p["tid"] == -2 and p.get("prospect"):
            rep = P.scout_report(p, L["scout"]["lv"].get(k, 0), sc_lvl)
            rep["cost"] = OF.scout_cost(L, p["id"])
            q.update({"fog": True, "scout": rep, "a": rep["known"], "tags": rep["tags"], "t": None, "tv": None,
                      "stars": round(sum(rep["ovr"]) / 2, 1), "pstars": round(sum(rep["pot"]) / 2, 1),
                      # sort keys come only from the scouted ranges: nothing true leaks to the browser
                      "ovr": round(sum(rep["ovr"]) / 2 * 20, 1), "pot": round(sum(rep["pot"]) / 2 * 20, 1),
                      "clutch": None, "dur": None, "trait": None, "morale": None})
        if p["tid"] == -1:
            q["ask"] = P.contract_ask(p, LG.fa_mood(L, L["user"]))
        out["players"][k] = q
    if L.get("offseason"):
        out["offseason"] = {**L["offseason"], "report": [{**r, "before": P.stars_for(r["before"]),
                                                            "after": P.stars_for(r["after"])}
                                                           for r in L["offseason"].get("report", [])]}
    out["retired"] = [{**r, "peak": P.stars_for(r["peak"])} for r in L.get("retired", [])]
    # committee: only the playoff spots and the first two teams out are public; no formula details
    if L.get("rankings"):
        cut = (L["settings"].get("playoff") or 4) + 2
        out["rankings"] = [{"day": r["day"], "final": r.get("final"), "order": r["order"][:cut],
                            "prev": {str(t): (r["info"].get(str(t)) or {}).get("prev") for t in r["order"][:cut]}}
                           for r in L["rankings"]]
    race = LG.award_race(L) if L["phase"] == "regular" and L["day"] >= 1 else {}
    race_out = {}
    for key, rows in race.items():
        top = rows[:10 if key == "MVP" else 6]
        best = top[0][1] if top else 1
        lo = min((s for _, s in top), default=0)
        race_out[key] = [{"pid": pid, "score": round(sc, 2),
                          "share": round(100 * (sc - lo + 1) / max(1e-6, best - lo + 1))} for pid, sc in top]
    out["picks"] = [{**pk, "tv": TR.pick_value(L, pk, None, ranks), "label": TR.pick_label(L, pk)}
                    for pk in L["picks"]]
    ok, why = LG.trades_open(L)
    out["derived"] = {
        "standings": LG.standings(L),
        "payroll": [LG.payroll(L, t["tid"]) for t in L["teams"]],
        "strength": [LG.team_strength(L, t["tid"]) for t in L["teams"]],
        "mode": [LG.team_mode(L, t["tid"], ranks) for t in L["teams"]],
        "on_clock": LG.on_clock(L) if L["phase"] == "draft" else None,
        "trades_open": ok, "trades_why": why,
        "draft_log": (L.get("draft_log") or {}).get("order") if L.get("draft_log") else None,
        "draft_log_season": (L.get("draft_log") or {}).get("season"),
        "chem": [FR.chemistry(L, t["tid"]) for t in L["teams"]],
        "live": bool(L.get("live")),
        "three_pending": FR.user_needs_three(L),
        "race": race_out,
        "conf_standings": LG.conf_standings(L) if L["settings"].get("conf") else None,
        # team strength spans a narrow band, so teams get their own, wider star scale
        "team_stars": [round(min(5.0, max(1.0, 1 + (LG.team_strength(L, t["tid"]) - 61) * 0.27)), 1) for t in L["teams"]],
    }
    out["consts"] = {"cap": SALARY_CAP, "apron": HARD_APRON, "roster_max": ROSTER_MAX, "roster_min": ROSTER_MIN,
                     "deadline": TRADE_DEADLINE_DAY, "days": SEASON_DAYS, "mle": LG.MLE,
                     "ceil": P.CEIL, "attr_label": P.ATTR_LABEL, "attrs": P.ATTRS, "award_names": LG.AWARD_NAMES,
                     "traits": P.TRAITS, "tiers": FR.TIERS, "allstar_day": FR.ALLSTAR_DAY, "cost": FR.COST,
                     "tracks": [{"key": k, "name": n, "desc": d,
                                 "fx": [FR.effect_text(k, l) for l in range(FR.MAX_LVL + 1)]}
                                for k, n, d in FR.TRACKS],
                     "as_teams": FR.AS_TEAMS, "conferences": CONFERENCES, "philo": FR.PHILO_LABEL}
    return out


# ---------------------------------------------------------------- live coaching sessions (in memory)
LIVE = {}


def live_meta(L, g):
    lv = L["live"]
    names = {}
    for t in g.T:
        for gp in t.players:
            p = gp.p
            names[str(gp.id)] = {"n": P.short_name(p), "fn": P.full_name(p), "pos": p["pos"], "num": p["num"],
                                 "stars": p["stars"], "trait": p.get("trait"), "morale": p.get("morale", 65)}
    return {"gid": lv["gid"], "h": lv["h"], "a": lv["a"], "side": g.live_side, "po": lv["po"],
            "series": lv["series"], "rival": FR.rival_tier(L, lv["h"], lv["a"]),
            "rosters": [[gp.id for gp in t.players] for t in g.T], "names": names,
            "starters": [[gp.id for gp in t.players if gp.started] for t in g.T],
            "chem": [t.chem for t in g.T]}


def live_payload(sess, extra=None):
    g = sess["g"]
    ev = g.events[sess["cur"]:]
    sess["cur"] = len(g.events)
    out = {"events": ev, "snap": g.snapshot()}
    if extra:
        out.update(extra)
    return out


def live(sid, L, body):
    cmd = body.get("cmd")
    sess = LIVE.get(sid)
    if sess and sess.get("L") is not L:   # save was reloaded from disk: the old session is stale
        LIVE.pop(sid, None)
        sess = None
    if cmd == "start":
        if L.get("live"):
            if not sess:   # server restarted mid-game: replay the matchup from tip-off
                rng = random.Random()
                g = LG.live_game(L, rng)
                g.start()
                sess = LIVE[sid] = {"g": g, "rng": rng, "cur": 0, "dr": set(), "film": False, "L": L}
            sess["cur"] = 0
            return live_payload(sess, {"meta": live_meta(L, sess["g"]), "resumed": True})
        rng = random.Random()
        docs, pend = LG.sim_day(L, rng, skip_user=True)
        store.put_games(sid, docs)
        if not isinstance(pend, tuple):
            store.save(sid, L)
            return {"nogame": True, "user_gid": pend}
        g = LG.live_game(L, rng)
        g.start()
        sess = LIVE[sid] = {"g": g, "rng": rng, "cur": 0, "dr": set(), "film": False, "L": L}
        store.save(sid, L)
        return live_payload(sess, {"meta": live_meta(L, g)})
    if not sess or not L.get("live"):
        raise LG.GameError("No live game in progress.")
    g = sess["g"]
    side = g.live_side
    extra = {}
    if cmd == "step":
        d = g.run_chunk(float(body.get("secs") or 45))
        if d and d["type"] == "final":
            ev = g.events[sess["cur"]:]
            snap = g.snapshot()
            doc = LG.finish_live(L, g, sess["rng"])
            store.put_games(sid, [doc])
            store.save(sid, L)
            LIVE.pop(sid, None)
            return {"events": ev, "snap": snap, "final": True, "gid": doc["gid"],
                    "challenges": doc.get("challenges", [])}
        if d and d["type"] == "break" and d.get("halftime"):
            sess["film"] = True
        extra["decision"] = d
    elif cmd == "sim_rest":
        doc = LG.finish_live(L, g, sess["rng"])
        store.put_games(sid, [doc])
        store.save(sid, L)
        LIVE.pop(sid, None)
        return {"events": [], "final": True, "gid": doc["gid"], "skipped": True}
    elif cmd == "timeout":
        if not g.timeout(side):
            raise LG.GameError("No timeouts left.")
        extra["huddle"] = g.huddle_prompt()
        if f"dr{g.q}" not in sess["dr"]:
            extra["read"] = g.def_read_prompt()
    elif cmd == "huddle":
        extra["result"] = g.resolve_huddle(body.get("choice"))
    elif cmd == "def_read":
        key = f"dr{g.q}"
        if key in sess["dr"]:
            raise LG.GameError("You already made a defensive adjustment this quarter.")
        sess["dr"].add(key)
        extra["result"] = g.resolve_def_read(int(body["pid"]), body.get("choice"))
    elif cmd in ("film", "half"):
        if not sess.get("film"):
            raise LG.GameError("Halftime adjustments happen at halftime.")
        sess["film"] = False
        extra["result"] = g.resolve_halftime(body.get("choice") or body.get("zone"))
    elif cmd == "final_play":
        extra["result"] = g.call_final_play(body.get("call"), float(body.get("acc", 1)))
    elif cmd == "sub":
        err = g.manual_sub(side, int(body["out"]), int(body["in"]))
        if err:
            raise LG.GameError(err)
    elif cmd == "strategy":
        g.set_strategy(side, body.get("k"), body.get("v"))
    else:
        raise LG.GameError(f"Unknown live command {cmd}")
    return live_payload(sess, extra)


def act(sid, L, body):
    t = body.get("type")
    rng = random.Random()
    res = {}
    if L.get("live") and t not in ("rename",):
        raise LG.GameError("You have a live game in progress. Finish it (or sim the rest) first.")
    if t == "upgrade":
        FR.buy(L, body.get("key"))
    elif t == "nego_open":
        res["nego"] = OF.open_talks(L, int(body["pid"]), body.get("kind", "fa"))
    elif t == "negotiate":
        res["nego"] = OF.negotiate(L, int(body["pid"]), body.get("sal"), body.get("yrs"), body.get("kind", "fa"))
    elif t == "scout":
        res["report"] = OF.scout(L, int(body["pid"]))
    elif t == "untouchable":
        res["pid"] = OF.set_untouchable(L, int(body.get("pid") or 0))
    elif t == "talk":
        res["talk"] = FR.talk(L, int(body["pid"]), body.get("approach"))
    elif t == "allstar_three":
        if not FR.user_needs_three(L):
            raise LG.GameError("Your player isn't shooting right now.")
        FR.three_round(L, [float(x) for x in (body.get("accs") or [])][:25], rng)
    elif t == "allstar_run":
        doc = FR.allstar_run(L, rng)
        if doc:
            store.put_games(sid, [doc])
    elif t == "sim_day":
        docs, ug = LG.sim_day(L, rng)
        store.put_games(sid, docs)
        res["user_gid"] = ug
    elif t == "sim_until":
        target = body.get("until")  # 'playoffs' | 'champion' | 'deadline'
        all_docs, gids = [], []
        start_phase = L["phase"]
        while L["phase"] in ("regular", "playoffs"):
            if target == "playoffs" and L["phase"] == "playoffs":
                break
            if target == "deadline" and (L["phase"] != "regular" or L["day"] >= TRADE_DEADLINE_DAY):
                break
            docs, ug = LG.sim_day(L, rng)
            all_docs += docs
            if ug:
                gids.append(ug)
        store.put_games(sid, all_docs)
        res["user_gids"] = gids
        res["from"] = start_phase
    elif t == "draft_pick":
        if LG.on_clock(L) != L["user"]:
            raise LG.GameError("You're not on the clock.")
        LG.make_pick(L, int(body["pid"]), rng)
        if L["phase"] == "draft":
            LG.draft_until_user(L, rng)
    elif t == "draft_sim":
        LG.draft_until_user(L, rng, include_user=body.get("to") == "end")
    elif t == "draft_auto_pick":
        if LG.on_clock(L) != L["user"]:
            raise LG.GameError("You're not on the clock.")
        LG.make_pick(L, LG.ai_pick_choice(L, L["user"], rng)["id"], rng)
        if L["phase"] == "draft":
            LG.draft_until_user(L, rng)
    elif t == "set_lineup":
        LG.set_lineup(L, body["order"])
    elif t == "auto_lineup":
        LG.auto_lineup(L, L["user"])
    elif t == "set_strategy":
        LG.set_strategy(L, body.get("strategy") or {})
    elif t == "release":
        LG.user_release(L, int(body["pid"]))
    elif t == "sign":
        LG.user_sign(L, int(body["pid"]), body.get("yrs"))
    elif t == "resign":
        LG.user_resign(L, int(body["pid"]), body.get("yrs"))
    elif t in ("trade_eval", "trade_propose"):
        give = {"players": [int(x) for x in body.get("give", {}).get("players", [])],
                "picks": list(body.get("give", {}).get("picks", []))}
        get = {"players": [int(x) for x in body.get("get", {}).get("players", [])],
               "picks": list(body.get("get", {}).get("picks", []))}
        if t == "trade_eval":
            res["eval"] = TR.evaluate(L, int(body["tid"]), give, get)
        else:
            res["eval"] = TR.user_propose(L, int(body["tid"]), give, get)
    elif t == "block_set":
        u = L["user"]
        L["block"] = {
            "players": [int(x) for x in body.get("players", []) if LG.pl(L, int(x)) and LG.pl(L, int(x))["tid"] == u],
            "picks": [x for x in body.get("picks", []) if any(pk["id"] == x and pk["owner"] == u
                                                              for pk in L["picks"])]}
        L["offers"] = []
    elif t == "block_offers":
        res["offers"] = TR.block_offers(L, rng)
    elif t == "offer_accept":
        TR.accept_offer(L, body["id"])
    elif t == "advance":
        LG.advance_season(L, rng)
    elif t == "rename":
        L["name"] = str(body.get("name") or L["name"])[:40]
    else:
        raise LG.GameError(f"Unknown action {t}")
    return res


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send_json(self, obj, code=200):
        data = json.dumps(obj, separators=(",", ":")).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def static(self, path):
        if path in ("", "/"):
            path = "/index.html"
        full = os.path.normpath(os.path.join(STATIC, path.lstrip("/")))
        if not full.startswith(STATIC) or not os.path.isfile(full):
            full = os.path.join(STATIC, "index.html")
        with open(full, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(full)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def route(self, method):
        parts = [x for x in urlparse(self.path).path.split("/") if x]
        if not parts or parts[0] != "api":
            if method == "GET":
                return self.static(urlparse(self.path).path)
            return self.send_json({"error": "not found"}, 404)
        try:
            with LOCK:
                return self.api(method, parts[1:])
        except LG.GameError as e:
            return self.send_json({"error": str(e)}, 400)
        except Exception as e:  # noqa
            traceback.print_exc()
            return self.send_json({"error": f"Server error: {e}"}, 500)

    def owner(self):
        o = (self.headers.get("X-ND-Owner") or "").strip()
        if not OWNER_OK.match(o):
            raise LG.GameError("Missing player id. Reload the page.")
        return o

    def api(self, method, parts):
        if parts == ["health"]:
            return self.send_json({"ok": True, "db": store.kind})
        if parts == ["meta"]:
            return self.send_json({"teams": TEAMS})
        owner = self.owner()
        if parts == ["saves"]:
            if method == "GET":
                return self.send_json(store.list_saves(owner))
            b = self.body()
            L = LG.new_league(b.get("name"), int(b.get("team", 0)), b.get("mode", "classic"),
                              settings=b.get("settings") or {})
            if L["phase"] == "draft":
                LG.draft_until_user(L, random.Random())
            sid = store.create(L, owner)
            return self.send_json({"id": sid})
        if len(parts) == 2 and parts[0] == "saves" and method == "DELETE":
            if not store.delete(parts[1], owner):
                return self.send_json({"error": "Save not found"}, 404)
            LIVE.pop(int(parts[1]), None)
            return self.send_json({"ok": True})
        if len(parts) >= 3 and parts[0] == "s":
            sid = int(parts[1])
            L = store.load(sid, owner)
            if L is None:
                return self.send_json({"error": "Save not found"}, 404)
            LG.migrate(L)
            if parts[2] == "live" and method == "POST":
                return self.send_json(live(sid, L, self.body()))
            if parts[2] == "state":
                return self.send_json(view(L))
            if parts[2] == "game" and len(parts) == 4:
                doc = store.get_game(sid, parts[3])
                if not doc:
                    return self.send_json({"error": "Game not found"}, 404)
                ids = set(doc["box"].keys())
                if doc.get("events"):
                    for e in doc["events"]:
                        for k in ("out", "in"):
                            if k in e:
                                ids.add(str(e[k]))
                names = {}
                for pid in ids:
                    p = L["players"].get(str(pid))
                    if p:
                        names[pid] = {"n": P.short_name(p), "fn": P.full_name(p), "pos": p["pos"],
                                      "num": p["num"], "stars": p["stars"]}
                    else:
                        r = next((x for x in L["retired"] if str(x["id"]) == str(pid)), None)
                        names[pid] = {"n": r["name"] if r else "Retired", "fn": r["name"] if r else "Retired",
                                      "pos": r["pos"] if r else "", "num": "", "ovr": 0}
                doc["names"] = names
                return self.send_json(doc)
            if parts[2] == "act" and method == "POST":
                b = self.body()
                if L.get("live") and b.get("type") != "rename":
                    raise LG.GameError("You have a live game in progress. Finish it (or sim the rest) first.")
                if b.get("type") in READ_ONLY:
                    return self.send_json({"result": act(sid, L, b)})
                snapshot = json.dumps(L)
                try:
                    res = act(sid, L, b)
                except Exception:
                    # roll back partial mutations
                    L.clear()
                    L.update(json.loads(snapshot))
                    raise
                store.save(sid, L)   # queued; written to the DB in the background
                if b.get("lite"):     # optimistic client: it already applied the change itself
                    return self.send_json({"result": res, "ok": True})
                return self.send_json({"result": res, "state": view(L)})
        return self.send_json({"error": "not found"}, 404)

    def do_GET(self):
        self.route("GET")

    def do_POST(self):
        self.route("POST")

    def do_DELETE(self):
        self.route("DELETE")


def main():
    srv = ThreadingHTTPServer((HOST, PORT), H)
    url = f"http://127.0.0.1:{PORT}"
    print(f"Nine & Done running on {HOST}:{PORT} ({store.kind})  (Ctrl+C to stop)", flush=True)
    if "--no-browser" not in sys.argv and not HOSTED:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    def stop(*_):
        store.flush()     # never lose a queued save on redeploy / Ctrl+C
        os._exit(0)
    signal.signal(signal.SIGTERM, stop)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        stop()


if __name__ == "__main__":
    main()
