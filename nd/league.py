"""League state machine: creation, schedule, simulation days, playoffs, draft, awards, offseason, FA."""
import random

from . import players as P
from .players import POS
from .sim import Game, STAT_KEYS, DEFAULT_STRAT
from . import franchise as FR
from .data import (TEAMS, SALARY_CAP, HARD_APRON, MIN_SALARY, ROSTER_MAX, ROSTER_MIN, SEASON_DAYS,
                   START_SEASON, TRADE_DEADLINE_DAY, VALID_TEAM_COUNTS, CONFERENCES, playoff_size)

MLE = 7.5


class GameError(Exception):
    pass


# ======================================================================= helpers
def pl(L, pid):
    return L["players"].get(str(pid))


def team(L, tid):
    return L["teams"][tid]


def roster(L, tid):
    return [p for p in L["players"].values() if p["tid"] == tid]


def payroll(L, tid):
    t = team(L, tid)
    return round(sum((p["contract"] or {}).get("sal", 0) for p in roster(L, tid)) + t.get("dead", 0), 1)


def news(L, text, kind="info", tid=None):
    L["news"].append({"s": L["season"], "d": L["day"], "ph": L["phase"], "txt": text, "k": kind, "tid": tid})
    if len(L["news"]) > 250:
        L["news"] = L["news"][-250:]


def tx(L, text):
    L["tx"].append({"s": L["season"], "ph": L["phase"], "d": L["day"], "txt": text})
    if len(L["tx"]) > 300:
        L["tx"] = L["tx"][-300:]


def new_pid(L):
    L["next_pid"] += 1
    return L["next_pid"]


def tname(L, tid):
    t = team(L, tid)
    return f'{t["city"]} {t["name"]}'


def team_strength(L, tid):
    r = sorted((p["ovr"] for p in roster(L, tid) if not (p.get("inj") and p["inj"]["games"] > 0)), reverse=True)
    r = (r + [40] * 10)[:9]
    w = [1.25, 1.2, 1.15, 1.1, 1.05, 0.8, 0.7, 0.55, 0.4]
    return round(sum(a * b for a, b in zip(r, w)) / sum(w), 1)


def strength_ranks(L):
    order = sorted(range(len(L["teams"])), key=lambda t: -team_strength(L, t))
    return {tid: i + 1 for i, tid in enumerate(order)}


def team_mode(L, tid, ranks=None):
    ranks = ranks or strength_ranks(L)
    r = ranks[tid]
    return "contend" if r <= 4 else "rebuild" if r >= 8 else "neutral"


def used_names(L):
    return {(p["fn"], p["ln"]) for p in L["players"].values()}


# ======================================================================= creation
def _contract_for(rng, p):
    sal = P.market_salary(p["ovr"], p["age"]) * rng.uniform(0.82, 1.15)
    return {"sal": round(max(MIN_SALARY, sal), 1), "yrs": rng.randint(1, 4)}


def _gen_age(rng):
    return int(max(19, min(36, round(rng.gauss(26.3, 3.9)))))


def gen_prospects(L, season, rng, n=None):
    n = n or int(round(2.6 * len(L["teams"])))
    names = used_names(L)
    targets = sorted([max(40, min(68, rng.gauss(52, 6.5))) for _ in range(n)], reverse=True)
    for i in range(4):
        targets[i] += rng.uniform(3, 8) - i
    for tgt in targets:
        age = rng.choice([19, 19, 19, 20, 20, 21, 21, 22, 23])
        p = P.generate(rng, new_pid(L), tgt, age, used_names=names, season=season)
        p["tid"] = -2
        p["dclass"] = season
        p["prospect"] = True
        L["players"][str(p["id"])] = p


def pick_franchises(user_idx, n):
    """League = the user's franchise + the first n-1 others in canonical order."""
    user_idx = max(0, min(len(TEAMS) - 1, int(user_idx)))
    rest = [i for i in range(len(TEAMS)) if i != user_idx]
    chosen = sorted([user_idx] + rest[:n - 1])
    return chosen, chosen.index(user_idx)


def assign_conferences(L):
    """Split into two conferences, keeping seeded rivals together and the sizes equal."""
    abbr_to_tid = {t["abbr"]: t["tid"] for t in L["teams"]}
    pairs = [(abbr_to_tid[a], abbr_to_tid[b]) for a, b, _ in FR.SEEDED if a in abbr_to_tid and b in abbr_to_tid]
    paired = {x for pr in pairs for x in pr}
    singles = [t["tid"] for t in L["teams"] if t["tid"] not in paired]
    conf = {}
    sizes = [0, 0]
    for a, b in pairs:
        c = 0 if sizes[0] <= sizes[1] else 1
        conf[a] = conf[b] = c
        sizes[c] += 2
    for tid in singles:
        c = 0 if sizes[0] <= sizes[1] else 1
        conf[tid] = c
        sizes[c] += 1
    for t in L["teams"]:
        t["conf"] = conf[t["tid"]]


def new_league(name, user_tid, mode="classic", seed=None, settings=None):
    rng = random.Random(seed)
    S = START_SEASON
    st = dict(settings or {})
    n = int(st.get("teams") or 10)
    if n not in VALID_TEAM_COUNTS:
        raise GameError("Leagues can have 10, 12, 14, 16, 18 or 20 teams.")
    mode = st.get("start") or mode
    settings = {"teams": n, "conf": bool(st.get("conf")), "committee": bool(st.get("committee")),
                "start": mode, "playoff": playoff_size(n)}
    franchises, user = pick_franchises(user_tid, n)
    L = {
        "v": 2, "name": name or "Nine & Done League", "user": user, "mode": mode, "season": S,
        "phase": "draft", "day": 0, "next_pid": 0, "teams": [], "players": {}, "picks": [], "schedule": [],
        "results": [], "playoffs": None, "draft": None, "news": [], "tx": [], "history": [], "retired": [],
        "block": {"players": [], "picks": []}, "offers": [], "resign": [], "offseason": None,
        "last_rank": None, "seasons_played": 0, "live": None, "allstar": None, "allstar_hist": [],
        "settings": settings, "rankings": [], "next_schedule": None, "nego": {}, "scout": {"pts": 12, "lv": {}},
        "energy": {}, "season_awards": None,
    }
    for i, fi in enumerate(franchises):
        L["teams"].append({**TEAMS[fi], "fid": fi, "tid": i, "strategy": dict(DEFAULT_STRAT), "lineup": [],
                           "w": 0, "l": 0, "pf": 0, "pa": 0, "h2h": {}, "streak": 0, "hist": [], "dead": 0.0,
                           "mle": False, "titles": 0, "upg": {}, "fp": 4, "fp_total": 0, "fp_log": [],
                           "conf": 0, "philo": rng.choice(FR.PHILOSOPHIES), "untouch": None, "results": []})
    if settings["conf"]:
        assign_conferences(L)
    FR.ensure_rivals(L)
    names = set()
    tiers = [(79, 90), (74, 82), (70, 77), (66, 73), (63, 70), (60, 67), (57, 64), (54, 61), (51, 58),
             (49, 56), (46, 53), (44, 51), (42, 50)]
    pos_plans = [rng.sample(["PG", "SG", "SF", "PF", "C", "PG", "SG", "SF", "PF", "C", "PG", "SF", "C"], 13)
                 for _ in range(n)]
    for ti, (lo, hi) in enumerate(tiers):
        tids = list(range(n))
        rng.shuffle(tids)
        for tid in tids:
            p = P.generate(rng, new_pid(L), rng.uniform(lo, hi), _gen_age(rng), pos=pos_plans[tid][ti],
                           used_names=names, season=S)
            p["contract"] = _contract_for(rng, p)
            p["tid"] = tid
            L["players"][str(p["id"])] = p
    for _ in range(int(n * 1.8)):
        p = P.generate(rng, new_pid(L), rng.uniform(42, 60), _gen_age(rng), used_names=names, season=S)
        p["tid"] = -1
        L["players"][str(p["id"])] = p
    gen_prospects(L, S, rng)

    if mode == "fantasy":
        for p in L["players"].values():
            p["tid"] = -2
            p["dclass"] = S
            p.pop("prospect", None)          # fantasy pool is fully scouted
            if p["contract"] is None and p["age"] > 22:
                p["contract"] = _contract_for(rng, p)
        make_picks(L, [S + 1, S + 2])
        order = list(range(n))
        rng.shuffle(order)
        picks = []
        for rd in range(13):
            seq = order if rd % 2 == 0 else order[::-1]
            for tid in seq:
                picks.append({"no": len(picks) + 1, "rd": rd + 1, "tid": tid, "orig": tid, "pid": None})
        L["draft"] = {"season": S, "type": "fantasy", "order": picks, "cur": 0, "lottery": None}
        news(L, "Fantasy draft is set. Every player in the league is up for grabs — 13 rounds, snake order.", "big")
    else:
        make_picks(L, [S, S + 1, S + 2])
        for t in L["teams"]:
            auto_lineup(L, t["tid"])
        setup_rookie_draft(L, rng, first=True)
        news(L, f"Welcome to the {S} season. The rookie draft opens the year.", "big")
    for p in L["players"].values():
        if p["tid"] == -1:
            p["ask"] = P.contract_ask(p)
    L["schedule"] = make_schedule(rng, L)
    L["next_schedule"] = make_schedule(rng, L)
    refresh_energy(L, full=True)
    ai_untouchables(L, rng)
    if settings["committee"]:
        FR.committee_rank(L)
    return L


def migrate(L):
    """Bring older saves up to the current schema."""
    rng = random.Random(L.get("next_pid", 0))
    for p in L["players"].values():
        if "trait" not in p:
            p["trait"] = P.roll_trait(rng)
        p.setdefault("morale", 65)
        p.setdefault("mlog", [])
    n = len(L["teams"])
    L.setdefault("settings", {"teams": n, "conf": False, "committee": False, "start": L.get("mode", "classic"),
                              "playoff": playoff_size(n)})
    for t in L["teams"]:
        t.setdefault("upg", {})
        t.setdefault("fp", 6)
        t.setdefault("fp_total", 0)
        t.setdefault("fp_log", [])
        t.setdefault("conf", 0)
        t.setdefault("philo", rng.choice(FR.PHILOSOPHIES))
        t.setdefault("untouch", None)
        t.setdefault("results", [])
        t.setdefault("fid", next((i for i, d in enumerate(TEAMS) if d["abbr"] == t["abbr"]), t["tid"]))
    FR.ensure_rivals(L)
    for k, v in (("live", None), ("allstar", None), ("allstar_hist", []), ("rankings", []), ("next_schedule", None),
                 ("nego", {}), ("scout", {"pts": 12, "lv": {}}), ("energy", {}), ("season_awards", None)):
        L.setdefault(k, v)
    if not L["energy"]:
        refresh_energy(L, full=True)
    if L["playoffs"] and "rounds" not in L["playoffs"]:
        po = L["playoffs"]
        po.update({"rounds": 2, "size": 4, "round_names": ["Semifinals", "Finals"],
                   "seed": {str(t): i + 1 for i, t in enumerate(po["seeds"])}, "rank": list(po["seeds"])})
        for s in po["series"]:
            s.setdefault("slot", 0 if s["id"] in ("SF1", "F") else 1)
    return L


def make_picks(L, seasons):
    have = {(pk["season"], pk["rd"], pk["orig"]) for pk in L["picks"]}
    for s in seasons:
        for rd in (1, 2):
            for t in range(len(L["teams"])):
                if (s, rd, t) not in have:
                    L["picks"].append({"id": f"{s}-{rd}-{t}", "season": s, "rd": rd, "orig": t, "owner": t})


def _circle_rounds(rng, n):
    teams = list(range(n))
    rng.shuffle(teams)
    rounds = []
    for _ in range(n - 1):
        rounds.append([(teams[i], teams[n - 1 - i]) for i in range(n // 2)])
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]
    return rounds


def _conf_rounds(rng, n, conf, games):
    """`games` rounds of perfect matchings with an in-conference quota per team (randomized backtracking)."""
    c = n // 2
    intra = min(c - 1, 6)
    cross = games - intra
    for _ in range(400):
        used = set()
        ci = [0] * n
        cx = [0] * n
        rounds = []
        ok = True
        for _r in range(games):
            order = list(range(n))
            rng.shuffle(order)

            def solve(unmatched):
                if not unmatched:
                    return []
                t = unmatched[0]
                opts = [u for u in unmatched[1:] if (min(t, u), max(t, u)) not in used]
                rng.shuffle(opts)
                opts.sort(key=lambda u: 0 if (conf[u] == conf[t]) == (ci[t] < intra) else 1)
                for u in opts:
                    same = conf[u] == conf[t]
                    if same and (ci[t] >= intra or ci[u] >= intra):
                        continue
                    if not same and (cx[t] >= cross or cx[u] >= cross):
                        continue
                    rest = [x for x in unmatched[1:] if x != u]
                    sub = solve(rest)
                    if sub is not None:
                        return [(t, u)] + sub
                return None
            m = solve(order)
            if m is None:
                ok = False
                break
            for a, b in m:
                used.add((min(a, b), max(a, b)))
                if conf[a] == conf[b]:
                    ci[a] += 1
                    ci[b] += 1
                else:
                    cx[a] += 1
                    cx[b] += 1
            rounds.append(m)
        if ok:
            return rounds
    return None


def make_schedule(rng, L):
    """SEASON_DAYS game days; every team plays every day; no repeat opponents."""
    n = len(L["teams"])
    rounds = None
    if L["settings"].get("conf") and n > 10:
        rounds = _conf_rounds(rng, n, [t["conf"] for t in L["teams"]], SEASON_DAYS)
    if rounds is None:
        rounds = _circle_rounds(rng, n)
        rng.shuffle(rounds)
        rounds = rounds[:SEASON_DAYS]
    home = [0] * n
    days = []
    for rnd in rounds:
        day = []
        for a, b in rnd:
            if home[a] > home[b] or (home[a] == home[b] and rng.random() < 0.5):
                a, b = b, a
            home[a] += 1
            day.append({"h": a, "a": b})
        days.append(day)
    return days


def refresh_energy(L, full=False):
    """Daily allowances: trade calls and scouting points."""
    u = L["user"]
    fo = FR.lvl(L, u, "frontoffice")
    sc = FR.lvl(L, u, "scouting")
    e = L.setdefault("energy", {})
    e["trade_max"] = 2 + (fo >= 2) + (fo >= 4)
    e["trade"] = e["trade_max"]
    daily = 6 + 3 * sc
    s = L.setdefault("scout", {"pts": 0, "lv": {}})
    s["daily"] = daily
    s["cap"] = daily * 3
    s["pts"] = min(s["cap"], s.get("pts", 0) + (daily * 2 if full else daily))


def ai_untouchables(L, rng):
    """Rare: some AI franchises declare their cornerstone off-limits for the season."""
    for t in L["teams"]:
        if t["tid"] == L["user"]:
            continue
        t["untouch"] = None
        r = roster(L, t["tid"])
        if not r:
            continue
        best = max(r, key=lambda p: p["ovr"] + (max(0, p["pot"] - p["ovr"]) * 0.5 if p["age"] <= 23 else 0))
        elite = P.disp(best["ovr"]) >= 89 or (best["age"] <= 23 and P.disp(best["pot"]) >= 90)
        if elite and rng.random() < 0.45:
            t["untouch"] = best["id"]


# ======================================================================= lineups
def auto_lineup(L, tid):
    ps = sorted(roster(L, tid), key=lambda p: (-(p["ovr"] - (6 if (p.get("inj") or {}).get("games", 0) > 0 else 0))))
    healthy = [p for p in ps if not ((p.get("inj") or {}).get("games", 0) > 0)]
    starters = []
    for p in healthy:
        if len(starters) == 5:
            break
        cand = starters + [p]
        g = sum(1 for x in cand if x["pos"] in ("PG", "SG"))
        b = sum(1 for x in cand if x["pos"] in ("PF", "C"))
        if g > 3 or b > 3 or sum(1 for x in cand if x["pos"] == "C") > 2:
            continue
        rem = 5 - len(cand)
        if (g == 0 and b == 0 and rem < 2) or ((g == 0 or b == 0) and rem < 1):
            continue
        starters.append(p)
    for p in healthy:
        if len(starters) == 5:
            break
        if p not in starters:
            starters.append(p)
    starters.sort(key=lambda p: POS.index(p["pos"]))
    rest = [p for p in ps if p not in starters]
    team(L, tid)["lineup"] = [p["id"] for p in starters + rest]


def fix_lineup(L, tid):
    t = team(L, tid)
    ids = {p["id"] for p in roster(L, tid)}
    lu = [i for i in t["lineup"] if i in ids]
    missing = sorted([pl(L, i) for i in ids if i not in lu], key=lambda p: -p["ovr"])
    t["lineup"] = lu + [p["id"] for p in missing]


def game_roster(L, tid):
    t = team(L, tid)
    fix_lineup(L, tid)
    ps = [pl(L, i) for i in t["lineup"]]
    healthy = [p for p in ps if not ((p.get("inj") or {}).get("games", 0) > 0)]
    if len(healthy) < 5:
        hurt = sorted([p for p in ps if p not in healthy], key=lambda p: p["inj"]["games"])
        healthy += hurt[:5 - len(healthy)]
    return healthy[:13]


# ======================================================================= games
def blank_line(tid):
    d = dict.fromkeys(STAT_KEYS, 0)
    d.update({"tid": tid, "gp": 0, "gs": 0, "min": 0.0, "pm": 0})
    return d


def make_game(L, home, away, rng, record=False, playoff=False, live_side=None):
    th, ta = team(L, home), team(L, away)
    n = len(L["teams"])
    avg = {k: sum(t.get("upg", {}).get(k, 0) for t in L["teams"]) / n for k in ("arena", "analytics")}
    opts = {"chem": [FR.chemistry(L, home), FR.chemistry(L, away)], "rival": FR.rival_tier(L, home, away),
            "live_side": live_side, "avg_upg": avg}
    return Game(th, game_roster(L, home), ta, game_roster(L, away), rng=rng, record=record, playoff=playoff,
                opts=opts)


def play_match(L, home, away, gid, rng, playoff=False, series=None):
    record = L["user"] in (home, away)
    res = make_game(L, home, away, rng, record=record, playoff=playoff).play()
    return apply_game(L, res, home, away, gid, playoff, series)


def apply_game(L, res, home, away, gid, playoff=False, series=None):
    user = L["user"]
    key = f'{L["season"]}{"p" if playoff else ""}'
    for pid, row in res["box"].items():
        p = pl(L, pid)
        st = p["stats"].setdefault(key, blank_line(row["tid"]))
        st["tid"] = row["tid"]
        st["gp"] += 1
        st["gs"] += row["gs"]
        st["min"] = round(st["min"] + row["min"], 1)
        st["pm"] += row["pm"]
        for k in STAT_KEYS:
            st[k] += row[k]
    for p, itype, games in res["injuries"]:
        p["inj"] = {"type": itype, "games": games, "new": True}
        if games >= 3 or p["tid"] == user:
            news(L, f'{P.full_name(p)} ({team(L, p["tid"])["abbr"]}) injured: {itype}'
                    f'{" — day-to-day" if games == 0 else f", out {games} game" + ("s" if games > 1 else "")}.',
                 "inj", p["tid"])
    hs, as_ = res["score"]
    win, lose = (home, away) if hs > as_ else (away, home)
    if not playoff:
        for tid, pf, pa in ((home, hs, as_), (away, as_, hs)):
            t = team(L, tid)
            t["pf"] += pf
            t["pa"] += pa
        team(L, win)["w"] += 1
        team(L, lose)["l"] += 1
        tw, tl = team(L, win), team(L, lose)
        tw["streak"] = tw["streak"] + 1 if tw["streak"] > 0 else 1
        tl["streak"] = tl["streak"] - 1 if tl["streak"] < 0 else -1
        tw["h2h"].setdefault(str(lose), [0, 0])[0] += 1
        tl["h2h"].setdefault(str(win), [0, 0])[1] += 1
        FR.earn(L, win, 2, "Regular-season win")
        team(L, win)["results"] = (team(L, win).get("results", []) + [1])[-9:]
        team(L, lose)["results"] = (team(L, lose).get("results", []) + [0])[-9:]
    else:
        FR.earn(L, win, 2, "Playoff win")

    def gs(r):
        return r["pts"] + 1.1 * (r["orb"] + r["drb"]) + 1.4 * r["ast"] + 1.8 * (r["stl"] + r["blk"]) - r["tov"]
    pog = max(res["box"].items(), key=lambda kv: gs(kv[1]))[0] if res["box"] else None
    rtier = FR.rival_tier(L, home, away)
    summary = {"gid": gid, "s": L["season"], "day": L["day"], "h": home, "a": away, "hs": hs, "as": as_,
               "ot": res["ot"], "po": playoff, "series": series, "pog": pog, "rival": rtier}
    L["results"].append(summary)
    doc = {**summary, "q": res["q"], "box": res["box"], "starters": res["starters"],
           "events": res["events"], "flow": res["flow"], "challenges": res.get("challenges") or []}
    FR.rivalry_game(L, home, away, hs, as_, res["ot"], playoff)
    if rtier >= 1:
        FR.earn(L, win, 1, f"Rivalry win over {team(L, lose)['abbr']}")
    FR.after_game(L, doc, rtier)
    ok = sum(1 for c in doc["challenges"] if c.get("ok"))
    if ok and user in (home, away):
        FR.earn(L, user, min(2, ok), f"Live-coaching challenges won ({ok})")
    if playoff and series:
        _series_result(L, series, gid, home, away, hs, as_, doc)
    return summary, doc


def _series_result(L, sid, gid, home, away, hs, as_, doc):
    po = L["playoffs"]
    s = next(x for x in po["series"] if x["id"] == sid)
    s["games"].append(gid)
    winner = home if hs > as_ else away
    s["w"][0 if winner == s["hi"] else 1] += 1
    if s["rd"] == po["rounds"]:
        for pid, row in doc["box"].items():
            f = po["fstats"].setdefault(str(pid), dict.fromkeys(STAT_KEYS, 0))
            for k in STAT_KEYS:
                f[k] += row[k]
    if max(s["w"]) == 3:
        s["winner"] = s["hi"] if s["w"][0] == 3 else s["lo"]
        loser = s["lo"] if s["winner"] == s["hi"] else s["hi"]
        po.setdefault("elim", {})[str(loser)] = s["rd"]
        label = po["round_names"][s["rd"] - 1]
        news(L, f'{tname(L, s["winner"])} win the {label} {max(s["w"])}–{min(s["w"])} over '
                f'{team(L, loser)["name"]}.', "big")
        FR.earn(L, s["winner"], 5, f"Won the {label}")
        FR.rivalry_series(L, s["winner"], loser, sum(s["w"]))


def tick_injuries(L):
    for p in L["players"].values():
        inj = p.get("inj")
        if not inj:
            continue
        if inj.pop("new", False):
            if inj["games"] <= 0:
                p["inj"] = None
            continue
        inj["games"] -= 1
        if inj["games"] <= 0:
            p["inj"] = None
            if p["tid"] == L["user"]:
                news(L, f"{P.full_name(p)} has been cleared to return.", "info", p["tid"])


def check_user_roster(L):
    n = len(roster(L, L["user"]))
    if n > ROSTER_MAX:
        raise GameError(f"Your roster has {n} players. Release down to {ROSTER_MAX} before playing.")
    if n < ROSTER_MIN:
        raise GameError(f"Your roster has {n} players. Sign free agents up to at least {ROSTER_MIN}.")


def day_matchups(L):
    """[(home, away, gid, playoff, series_id)] for the next game day."""
    if L["phase"] == "regular":
        day = L["day"]
        return [(m["h"], m["a"], f'{L["season"]}-r{day + 1}-{i}', False, None)
                for i, m in enumerate(L["schedule"][day])]
    if L["phase"] == "playoffs":
        out = []
        for s in L["playoffs"]["series"]:
            if s["winner"] is not None:
                continue
            n = len(s["games"])
            home, away = (s["hi"], s["lo"]) if n in (0, 1, 4) else (s["lo"], s["hi"])
            out.append((home, away, f'{L["season"]}-{s["id"]}-g{n + 1}', True, s["id"]))
        return out
    return []


def sim_day(L, rng=None, skip_user=False):
    """Sim the next game day. Returns (game_docs, user_gid).
    With skip_user=True the user's game is left pending in L["live"] (for live coaching) and the day is
    not closed; user_gid is then the pending matchup tuple."""
    rng = rng or random.Random()
    if L.get("live"):
        raise GameError("Finish your live game first.")
    if L["phase"] not in ("regular", "playoffs"):
        raise GameError("No games to play in this phase.")
    check_user_roster(L)
    docs = []
    if L["phase"] == "regular":
        if L.get("allstar") and L["allstar"].get("status") == "ready":
            asg = FR.allstar_run(L, rng)
            if asg:
                docs.append(asg)
        ai_maintain(L, rng)
    user_gid, pending = None, None
    for m in day_matchups(L):
        home, away, gid, playoff, series = m
        if skip_user and L["user"] in (home, away):
            pending = m
            continue
        _, doc = play_match(L, home, away, gid, rng, playoff=playoff, series=series)
        docs.append(doc)
        if L["user"] in (home, away):
            user_gid = gid
    if pending:
        L["live"] = {"h": pending[0], "a": pending[1], "gid": pending[2], "po": pending[3], "series": pending[4]}
        return docs, pending
    end_day(L, rng)
    return docs, user_gid


def end_day(L, rng):
    tick_injuries(L)
    L["day"] += 1
    refresh_energy(L)
    FR.ai_spend(L, rng)
    if L["phase"] == "regular":
        if L["settings"].get("committee"):
            FR.committee_rank(L)
        if L["day"] == FR.ALLSTAR_DAY and not (L.get("allstar") and L["allstar"].get("s") == L["season"]):
            FR.allstar_setup(L, rng)
        if L["day"] >= SEASON_DAYS:
            start_playoffs(L)
        return
    po = L["playoffs"]
    cur = max(s["rd"] for s in po["series"])
    rs = sorted([s for s in po["series"] if s["rd"] == cur], key=lambda s: s["slot"])
    if any(s["winner"] is None for s in rs):
        return
    if cur == po["rounds"]:
        po["champion"] = rs[0]["winner"]
        finalize_season(L, rng)
        return
    nxt = cur + 1
    made = []
    for k in range(len(rs) // 2):
        a, b = rs[2 * k]["winner"], rs[2 * k + 1]["winner"]
        hi, lo = (a, b) if po["rank"].index(a) < po["rank"].index(b) else (b, a)
        sid = "F" if nxt == po["rounds"] else f"R{nxt}-{k}"
        po["series"].append({"id": sid, "rd": nxt, "slot": k, "hi": hi, "lo": lo, "w": [0, 0], "games": [],
                             "winner": None})
        made.append(f"{team(L, hi)['abbr']} vs {team(L, lo)['abbr']}")
    label = po["round_names"][nxt - 1]
    news(L, f"{'THE FINALS' if nxt == po['rounds'] else label}: " + ", ".join(made) + ".", "big")


def live_game(L, rng):
    """Build the Game object for the pending live matchup."""
    lv = L["live"]
    side = 0 if lv["h"] == L["user"] else 1
    g = make_game(L, lv["h"], lv["a"], rng, record=True, playoff=lv["po"], live_side=side)
    return g


def finish_live(L, g, rng):
    lv = L["live"]
    if not g.done:
        g.live_side = None
        while not g.done:
            g.step()
    res = g.result()
    _, doc = apply_game(L, res, lv["h"], lv["a"], lv["gid"], lv["po"], lv["series"])
    L["live"] = None
    end_day(L, rng)
    return doc


# ======================================================================= standings / playoffs
def standings(L, tids=None):
    """Order by wins, then head-to-head among teams tied on wins, then point differential."""
    ts = [team(L, t) for t in tids] if tids is not None else list(L["teams"])
    base = sorted(ts, key=lambda t: (-t["w"], -(t["pf"] - t["pa"])))
    out = []
    i = 0
    while i < len(base):
        grp = [t for t in base if t["w"] == base[i]["w"]]
        if len(grp) > 1:
            ids = {str(t["tid"]) for t in grp}

            def h2h(t):
                return sum(v[0] for k, v in t["h2h"].items() if k in ids)
            grp.sort(key=lambda t: (-h2h(t), -(t["pf"] - t["pa"])))
        out.extend(grp)
        i += len(grp)
    return [t["tid"] for t in out]


def conf_standings(L):
    order = standings(L)
    return {c: [t for t in order if team(L, t)["conf"] == c] for c in (0, 1)}


def playoff_field(L):
    """Pairs for round 1 (better seed first), seed labels, ranking order for home court, round names."""
    st = L["settings"]
    P = st.get("playoff") or playoff_size(len(L["teams"]))
    committee, conf = st.get("committee"), st.get("conf")
    order = FR.committee_order(L) if committee else standings(L)
    auto = []
    if conf and not committee:
        cs = {c: standings(L, [t for t in order if team(L, t)["conf"] == c]) for c in (0, 1)}
        half = P // 2
        pairs, seed = [], {}
        for c in (0, 1):
            sd = cs[c][:half]
            for i, t in enumerate(sd):
                seed[str(t)] = f"{CONFERENCES[c][0]}{i + 1}"
            pairs += [(sd[0], sd[1])] if half == 2 else [(sd[0], sd[3]), (sd[1], sd[2])]
        field = [t for pr in pairs for t in pr]
        rank = [t for t in standings(L) if t in field]
        names = ["Conference Finals", "Finals"] if P == 4 else ["First Round", "Conference Finals", "Finals"]
    else:
        if committee and conf:
            auto = [next(t for t in order if team(L, t)["conf"] == c) for c in (0, 1)]
            at_large = [t for t in order if t not in auto][:P - len(auto)]
            field = sorted(auto + at_large, key=order.index)
        else:
            field = order[:P]
        seed = {str(t): str(i + 1) for i, t in enumerate(field)}
        idx = [(1, 4), (2, 3)] if P == 4 else [(1, 8), (4, 5), (2, 7), (3, 6)]
        pairs = [(field[a - 1], field[b - 1]) for a, b in idx]
        rank = list(field)
        names = ["Semifinals", "Finals"] if P == 4 else ["Quarterfinals", "Semifinals", "Finals"]
    return pairs, seed, rank, names, auto


def start_playoffs(L):
    if L["settings"].get("committee"):
        FR.committee_rank(L, final=True)
    pairs, seed, rank, names, auto = playoff_field(L)
    L["phase"] = "playoffs"
    rounds = len(names)
    series = []
    for k, (hi, lo) in enumerate(pairs):
        sid = "F" if rounds == 1 else f"R1-{k}"
        series.append({"id": sid, "rd": 1, "slot": k, "hi": hi, "lo": lo, "w": [0, 0], "games": [], "winner": None})
    field = [t for pr in pairs for t in pr]
    L["playoffs"] = {"seeds": field, "seed": seed, "rank": rank, "series": series, "rounds": rounds,
                     "size": len(field), "round_names": names, "champion": None, "fstats": {}, "elim": {},
                     "auto": auto}
    L["block"] = {"players": [], "picks": []}
    L["offers"] = []
    u = L["user"]
    news(L, "Regular season complete. Playoff field: " + ", ".join(
        f"({seed[str(t)]}) {team(L, t)['abbr']}" for t in sorted(field, key=rank.index)) + ".", "big")
    if u in field:
        news(L, f"Your {team(L, u)['name']} are in as the {seed[str(u)]} seed!", "big", u)
    else:
        news(L, "Your team missed the playoffs. The lottery awaits.", "info", u)
    reveal_awards(L)


# ======================================================================= awards & season end
def per_game(st):
    g = max(1, st["gp"])
    reb = st["orb"] + st["drb"]
    return {"gp": st["gp"], "min": st["min"] / g, "pts": st["pts"] / g, "reb": reb / g, "ast": st["ast"] / g,
            "stl": st["stl"] / g, "blk": st["blk"] / g, "tov": st["tov"] / g, "drb": st["drb"] / g,
            "fgm": st["fgm"] / g, "fga": st["fga"] / g, "ftm": st["ftm"] / g, "fta": st["fta"] / g,
            "gs": st["gs"]}


def eff(pg):
    return (pg["pts"] + 1.1 * pg["reb"] + 1.4 * pg["ast"] + 1.8 * pg["stl"] + 1.8 * pg["blk"] - 1.2 * pg["tov"]
            - 0.45 * (pg["fga"] - pg["fgm"]) - 0.3 * (pg["fta"] - pg["ftm"]))


def award_race(L, min_gp=None):
    """Live ladders for every regular-season award: {award: [(pid, score), ...]} best first."""
    S = L["season"]
    key = str(S)
    if min_gp is None:
        min_gp = max(1, int(L["day"] * 0.55)) if L["phase"] == "regular" else 5
    cands = []
    for p in L["players"].values():
        st = p["stats"].get(key)
        if not st or st["gp"] < min_gp or p["tid"] < 0:
            continue
        pg = per_game(st)
        t = team(L, st["tid"])
        wp = t["w"] / max(1, t["w"] + t["l"])
        cands.append((p, pg, eff(pg), wp))
    race = {}
    race["MVP"] = sorted(((c[0]["id"], c[2] * (0.55 + c[3] * 0.9)) for c in cands), key=lambda x: -x[1])
    race["DPOY"] = sorted(((c[0]["id"], c[1]["stl"] * 2.3 + c[1]["blk"] * 2.3 + c[1]["drb"] * 0.45 +
                           (c[0]["a"]["perd"] + c[0]["a"]["intd"] + c[0]["a"]["stl"] + c[0]["a"]["blk"]) / 40 +
                           c[3] * 2) for c in cands), key=lambda x: -x[1])
    race["ROY"] = sorted(((c[0]["id"], c[2]) for c in cands if c[0].get("rookie") == S), key=lambda x: -x[1])
    race["6MOY"] = sorted(((c[0]["id"], c[2]) for c in cands if c[1]["gs"] < c[1]["gp"] / 2), key=lambda x: -x[1])
    prev = str(S - 1)
    mip = []
    for c in cands:
        ps = c[0]["stats"].get(prev)
        if ps and ps["gp"] >= 4:
            mip.append((c[0]["id"], c[2] - eff(per_game(ps))))
    race["MIP"] = sorted(mip, key=lambda x: -x[1])
    return race


def compute_awards(L, rng=None):
    """Regular-season voting: the ladders plus voter variance (so the favorite usually, not always, wins)."""
    rng = rng or random.Random(L["season"] * 31)
    race = award_race(L, min_gp=min(5, max(1, L["day"] - 3)))
    aw = {}
    for k in ("MVP", "DPOY", "ROY", "6MOY", "MIP"):
        top = race[k][:6]
        if not top:
            continue
        lo = min(s for _, s in top)
        voted = max(top, key=lambda x: (x[1] - lo + 1) * rng.gauss(1, 0.06))
        aw[k] = voted[0]
    order = [pid for pid, _ in race["MVP"]]
    slots = {"G": ("PG", "SG"), "F": ("SF", "PF"), "C": ("C",)}
    used = set()
    teams_ = []
    for _ in range(2):
        five = []
        for grp, n in (("G", 2), ("F", 2), ("C", 1)):
            for pid in order:
                if n == 0:
                    break
                p = pl(L, pid)
                if pid in used or p["pos"] not in slots[grp]:
                    continue
                five.append(pid)
                used.add(pid)
                n -= 1
        teams_.append(five)
    aw["ALL1"], aw["ALL2"] = teams_
    return aw


def finals_mvp(L):
    po = L["playoffs"]
    if not po or po.get("champion") is None or not po["fstats"]:
        return None
    best, bv = None, -99
    for pid, f in po["fstats"].items():
        p = pl(L, pid)
        if not p or p["tid"] != po["champion"]:
            continue
        v = f["pts"] + 1.1 * (f["orb"] + f["drb"]) + 1.4 * f["ast"] + 1.8 * (f["stl"] + f["blk"]) - f["tov"]
        if v > bv:
            best, bv = p["id"], v
    return best


def reveal_awards(L):
    """End of the regular season: the votes are in."""
    S = L["season"]
    aw = compute_awards(L)
    L["season_awards"] = {"s": S, "aw": aw}
    for k, v in aw.items():
        for pid in (v if isinstance(v, list) else [v]):
            p = pl(L, pid)
            if p:
                p["awards"].append({"s": S, "a": k})
                if p["tid"] >= 0:
                    FR.earn(L, p["tid"], 2, f"{AWARD_NAMES.get(k, k)}: {P.full_name(p)}")
    for k in ("MVP", "DPOY", "ROY", "6MOY", "MIP"):
        if k in aw:
            p = pl(L, aw[k])
            news(L, f"{AWARD_NAMES[k]}: {P.full_name(p)} ({team(L, p['tid'])['abbr']}).", "big", p["tid"])


AWARD_NAMES = {"MVP": "Most Valuable Player", "DPOY": "Defensive Player of the Year", "ROY": "Rookie of the Year",
               "6MOY": "Sixth Man of the Year", "MIP": "Most Improved Player", "FMVP": "Finals MVP",
               "ALL1": "All-League 1st Team", "ALL2": "All-League 2nd Team"}


def finalize_season(L, rng):
    S = L["season"]
    po = L["playoffs"]
    champ = po["champion"]
    fin = [s for s in po["series"] if s["rd"] == po["rounds"]][0]
    runner = fin["lo"] if fin["winner"] == fin["hi"] else fin["hi"]
    team(L, champ)["titles"] += 1
    sa = L.get("season_awards") or {}
    aw = dict(sa.get("aw") or {}) if sa.get("s") == S else compute_awards(L)
    fm = finals_mvp(L)
    if fm:
        aw["FMVP"] = fm
        p = pl(L, fm)
        p["awards"].append({"s": S, "a": "FMVP"})
        FR.earn(L, p["tid"], 2, f"Finals MVP: {P.full_name(p)}")
    for p in roster(L, champ):
        p["awards"].append({"s": S, "a": "CHAMP"})
    stand = standings(L)
    elim = po.get("elim", {})
    for i, tid in enumerate(stand):
        t = team(L, tid)
        if tid == champ:
            res = "Champion"
        elif tid == runner:
            res = "Finals"
        elif str(tid) in elim:
            res = po["round_names"][elim[str(tid)] - 1]
        else:
            res = "Lottery"
        t["hist"].append({"s": S, "w": t["w"], "l": t["l"], "rank": i + 1, "res": res,
                          "seed": po["seed"].get(str(tid))})
    u = L["user"]
    ut = team(L, u)
    L["history"].append({
        "s": S, "champ": champ, "runner": runner, "fin": list(fin["w"]),
        "awards": {k: (v if isinstance(v, list) else v) for k, v in aw.items()},
        "user": {"w": ut["w"], "l": ut["l"], "res": ut["hist"][-1]["res"]},
        "names": {str(pid): P.full_name(pl(L, pid)) for v in aw.values() for pid in (v if isinstance(v, list) else [v])
                  if pl(L, pid)},
    })
    news(L, f"🏆 {tname(L, champ)} are the {S} champions!", "big", champ)
    if champ == u:
        news(L, "YOU WON THE CHAMPIONSHIP. Parade route is being planned.", "big", u)
    FR.earn(L, champ, 12, "Won the championship")
    # lottery order for next draft: non-playoff worst->best, then playoff teams by how far they went
    field = set(po["seeds"])
    non = [t for t in reversed(stand) if t not in field]
    out = sorted([t for t in field if t not in (champ, runner)],
                 key=lambda t: (elim.get(str(t), 0), -stand.index(t)))
    L["last_rank"] = non + out + [runner, champ]
    start_offseason(L, rng)


def retire_check(p, rng):
    age, ovr = p["age"], p["ovr"]
    if age >= 37:
        return True
    pr = 0.0
    if age >= 33:
        pr = 0.12 + (age - 33) * 0.18
    if ovr < 52 and age >= 30:
        pr += 0.3
    if ovr >= 78:
        pr *= 0.4
    return rng.random() < pr


def start_offseason(L, rng):
    S = L["season"]
    L["phase"] = "offseason"
    report, retired = [], []
    mentors = {t["tid"]: any(p.get("trait") == "Mentor" and p["age"] >= 27 for p in roster(L, t["tid"]))
               for t in L["teams"]}
    avg_dev = sum(t.get("upg", {}).get("dev", 0) for t in L["teams"]) / len(L["teams"])
    for p in list(L["players"].values()):
        if p["tid"] == -3:
            continue
        before = p["ovr"]
        bonus, cut = -0.15, 0.0      # small global offset balances trait/mentor bonuses
        if p.get("trait") == "Gym Rat":
            bonus += 0.6
        if p["tid"] >= 0:
            dev = FR.lvl(L, p["tid"], "dev") - avg_dev   # edge relative to the league
            bonus += 0.35 * dev
            cut = max(-0.3, min(0.3, 0.06 * dev))
            if mentors.get(p["tid"]) and p["age"] <= 23:
                bonus += 0.5
            bonus += (p.get("morale", 65) - 66) / 40 * 0.4
        P.develop(p, rng, bonus, cut)
        p["age"] += 1
        p["hist"].append({"s": S + 1, "ovr": p["ovr"], "age": p["age"]})
        if p["tid"] == L["user"]:
            report.append({"id": p["id"], "before": before, "after": p["ovr"]})
        if p["tid"] >= -1 and retire_check(p, rng):
            retired.append(p)
    for p in retired:
        retire(L, p)
    if retired:
        notable = sorted(retired, key=lambda p: -max(h["ovr"] for h in p["hist"]))[:4]
        news(L, "Retirements: " + ", ".join(f'{P.full_name(p)} ({p["age"]})' for p in notable) +
             (f" and {len(retired) - 4} more" if len(retired) > 4 else "") + ".", "info")
    # contracts tick down
    L["resign"] = []
    ranks = strength_ranks(L)
    for p in list(L["players"].values()):
        if p["tid"] < 0 or not p["contract"]:
            continue
        p["contract"]["yrs"] -= 1
        if p["contract"]["yrs"] > 0:
            continue
        if p["tid"] == L["user"]:
            L["resign"].append(p["id"])
            mood = 0.95 if team(L, p["tid"])["hist"][-1]["res"] in ("Champion", "Finals") else 1.05
            mood *= 1 - 0.03 * FR.lvl(L, p["tid"], "frontoffice")
            p["ask"] = P.contract_ask(p, mood, resign=True)
            continue
        from .trade import player_value
        v = player_value(L, p, team_mode(L, p["tid"], ranks), ignore_contract=True)
        star = p["ovr"] >= 74
        keep = v > 6 and rng.random() < (0.96 if star else 0.72)
        # Bird rights: stars get re-signed even over the apron
        if keep and (star or payroll(L, p["tid"]) + P.contract_ask(p)["sal"] <= HARD_APRON):
            p["contract"] = P.contract_ask(p)
            tx(L, f'{team(L, p["tid"])["abbr"]} re-signed {P.full_name(p)} ({p["contract"]["yrs"]} yr / '
                  f'${p["contract"]["sal"]}M).')
        else:
            to_fa(L, p, f'{P.full_name(p)} enters free agency from {team(L, p["tid"])["abbr"]}.')
    for t in L["teams"]:
        t["dead"] = 0.0
        t["mle"] = False
    for p in L["players"].values():
        if p["tid"] == -1:
            p["ask"] = P.contract_ask(p)
    L["offseason"] = {"report": report, "retired": [p["id"] for p in retired]}
    FR.offseason_morale(L)
    FR.decay_rivals(L)
    FR.ai_spend(L, rng)
    sc = L.setdefault("scout", {"pts": 0, "lv": {}})
    sc["pts"] = min(sc.get("cap", 30), sc.get("pts", 0) + 15 + 5 * FR.lvl(L, L["user"], "scouting"))
    refresh_energy(L)
    L["allstar"] = None
    L["block"] = {"players": [], "picks": []}
    L["offers"] = []
    news(L, "The offseason is here: re-sign your players and shop free agency before the next draft.", "big")


def retire(L, p):
    career = {}
    for k, st in p["stats"].items():
        if k.endswith("p"):
            continue
        for s in ("gp", "pts", "orb", "drb", "ast", "stl", "blk"):
            career[s] = career.get(s, 0) + st.get(s, 0)
    L["retired"].append({"id": p["id"], "name": P.full_name(p), "pos": p["pos"], "age": p["age"],
                         "peak": max(h["ovr"] for h in p["hist"]), "awards": p["awards"], "career": career,
                         "s": L["season"]})
    L["players"].pop(str(p["id"]), None)
    for k in ("players",):
        if p["id"] in L["block"][k]:
            L["block"][k].remove(p["id"])
    for t in L["teams"]:
        if p["id"] in t["lineup"]:
            t["lineup"].remove(p["id"])


def to_fa(L, p, msg=None):
    old = p["tid"]
    p["tid"] = -1
    p["contract"] = None
    p["ask"] = P.contract_ask(p)
    if old >= 0:
        t = team(L, old)
        if p["id"] in t["lineup"]:
            t["lineup"].remove(p["id"])
    if msg:
        tx(L, msg)


def fa_mood(L, tid):
    t = team(L, tid)
    if t["hist"]:
        last = t["hist"][-1]["res"]
        base = 0.9 if last == "Champion" else 0.94 if last == "Finals" else 1.06 if last == "Lottery" else 0.98
    else:
        base = 1.0
    return base * (1 - 0.03 * FR.lvl(L, tid, "frontoffice"))


def can_afford(L, tid, sal):
    pay = payroll(L, tid)
    if sal <= 1.6:
        return True, "min"   # minimum contracts are always allowed
    if pay + sal > HARD_APRON:
        return False, "That deal would put you over the hard apron."
    if pay + sal <= SALARY_CAP or sal <= 1.6:
        return True, "cap"
    if not team(L, tid)["mle"] and sal <= MLE:
        return True, "mle"
    return False, (f"Over the cap (${pay}M of ${SALARY_CAP}M). Only minimum deals (≤$1.6M)"
                   + ("" if team(L, tid)["mle"] else f" or your ${MLE}M mid-level exception") + " are allowed.")


def advance_season(L, rng=None):
    """Offseason -> next season's draft."""
    rng = rng or random.Random()
    if L["phase"] != "offseason":
        raise GameError("You can only advance from the offseason.")
    for pid in list(L["resign"]):
        p = pl(L, pid)
        if p and p["tid"] == L["user"] and (not p["contract"] or p["contract"]["yrs"] <= 0):
            to_fa(L, p, f"{P.full_name(p)} leaves your team for free agency.")
    L["resign"] = []
    ai_free_agency(L, rng)
    # FA retirements / pool cleanup
    fas = sorted([p for p in L["players"].values() if p["tid"] == -1], key=lambda p: p["ovr"])
    for p in fas:
        if (p["age"] >= 33 and rng.random() < 0.5) or (p["ovr"] < 44 and rng.random() < 0.6):
            retire(L, p)
    fas = sorted([p for p in L["players"].values() if p["tid"] == -1], key=lambda p: p["ovr"])
    for p in fas[:max(0, len(fas) - int(3.2 * len(L["teams"])))]:
        retire(L, p)
    # new season
    L["season"] += 1
    L["seasons_played"] += 1
    S = L["season"]
    L["day"] = 0
    L["results"] = []
    L["playoffs"] = None
    L["offseason"] = None
    for t in L["teams"]:
        t.update({"w": 0, "l": 0, "pf": 0, "pa": 0, "h2h": {}, "streak": 0, "results": []})
    # schedules are agreed a year in advance: play last year's published slate, publish next year's
    L["schedule"] = L.get("next_schedule") or make_schedule(rng, L)
    L["next_schedule"] = make_schedule(rng, L)
    L["rankings"] = []
    L["season_awards"] = None
    L["nego"] = {}
    team(L, L["user"]).pop("untouch_s", None)
    ai_untouchables(L, rng)
    refresh_energy(L, full=True)
    if L["settings"].get("committee"):
        FR.committee_rank(L)
    L["picks"] = [pk for pk in L["picks"] if pk["season"] >= S]
    make_picks(L, [S, S + 1, S + 2])
    if not any(p["tid"] == -2 and p.get("dclass") == S for p in L["players"].values()):
        gen_prospects(L, S, rng)
    for p in L["players"].values():
        if p["tid"] == -1:
            p["ask"] = P.contract_ask(p)
    setup_rookie_draft(L, rng)
    news(L, f"The {S} season begins with the draft.", "big")


def ai_free_agency(L, rng):
    signed = True
    rounds = 0
    while signed and rounds < 8:
        signed = False
        rounds += 1
        order = list(range(len(L["teams"])))
        rng.shuffle(order)
        for tid in order:
            if tid == L["user"]:
                continue
            n = len(roster(L, tid))
            if n >= 13 or (n >= 12 and rng.random() < 0.5):
                continue
            fas = sorted([p for p in L["players"].values() if p["tid"] == -1], key=lambda p: -(p["ovr"] + (
                max(0, p["pot"] - p["ovr"]) * 0.3 if p["age"] < 24 else 0)))
            for p in fas:
                ask = p.get("ask") or P.contract_ask(p)
                ok, how = can_afford(L, tid, ask["sal"])
                if not ok:
                    if p["ovr"] >= 64:
                        continue   # good players won't take the minimum
                    ask = {"sal": min(1.6, ask["sal"]), "yrs": 1}
                    how = "min"
                if how == "mle":
                    team(L, tid)["mle"] = True
                sign(L, p, tid, ask)
                signed = True
                break


def sign(L, p, tid, contract):
    p["tid"] = tid
    p["contract"] = {"sal": contract["sal"], "yrs": contract["yrs"]}
    p.pop("ask", None)
    team(L, tid)["lineup"].append(p["id"])
    tx(L, f'{team(L, tid)["abbr"]} signed {P.full_name(p)} ({contract["yrs"]} yr / ${contract["sal"]}M).')


def ai_maintain(L, rng):
    """Keep AI rosters legal & lineups sensible during the season."""
    for t in L["teams"]:
        tid = t["tid"]
        if tid == L["user"]:
            fix_lineup(L, tid)
            continue
        r = roster(L, tid)
        while len(r) > ROSTER_MAX:
            from .trade import player_value
            worst = min(r, key=lambda p: player_value(L, p))
            release(L, worst, tid)
            r = roster(L, tid)
        healthy = [p for p in r if not ((p.get("inj") or {}).get("games", 0) > 0)]
        if len(healthy) < 9 and len(r) < ROSTER_MAX:
            fas = sorted([p for p in L["players"].values() if p["tid"] == -1], key=lambda p: -p["ovr"])
            for p in fas:
                if can_afford(L, tid, 1.1)[0]:
                    sign(L, p, tid, {"sal": max(MIN_SALARY, min(1.6, (p.get("ask") or {}).get("sal", 1.1))),
                                     "yrs": 1})
                    break
        auto_lineup(L, tid)


def release(L, p, tid):
    t = team(L, tid)
    if p["contract"]:
        t["dead"] = round(t.get("dead", 0) + p["contract"]["sal"] * (0.5 if L["phase"] != "offseason" else 0.25), 1)
    to_fa(L, p, f'{t["abbr"]} waived {P.full_name(p)}.')


# ======================================================================= draft
def rookie_contract(no, rd):
    if rd == 1:
        return {"sal": round(max(2.0, 8.6 - (no - 1) * 0.7), 1), "yrs": 3}
    return {"sal": MIN_SALARY, "yrs": 2}


def setup_rookie_draft(L, rng, first=False):
    S = L["season"]
    n = len(L["teams"])
    lottery = None
    if first or not L.get("last_rank"):
        order = list(range(n))
        rng.shuffle(order)
    else:
        rank = L["last_rank"]
        k = max(2, n - (L["settings"].get("playoff") or playoff_size(n)))
        non = rank[:k]
        raw = [(k - i) ** 1.3 for i in range(k)]
        odds = [round(100 * w / sum(raw)) for w in raw]
        pool = list(zip(non, odds))
        winners = []
        for _ in range(3 if k <= 8 else 4):
            pick = rng.choices(pool, weights=[w for _, w in pool])[0]
            winners.append(pick[0])
            pool.remove(pick)
        rest_non = [t for t in non if t not in winners]
        order = winners + rest_non + rank[k:]
        lottery = [{"tid": t, "odds": odds[i], "seed": i + 1, "pick": order.index(t) + 1}
                   for i, t in enumerate(non)]
    picks = []
    for rd in (1, 2):
        for orig in order:
            pk = next((x for x in L["picks"] if x["season"] == S and x["rd"] == rd and x["orig"] == orig), None)
            owner = pk["owner"] if pk else orig
            picks.append({"no": len(picks) + 1, "rd": rd, "tid": owner, "orig": orig, "pid": None})
    L["draft"] = {"season": S, "type": "rookie", "order": picks, "cur": 0, "lottery": lottery}
    L["phase"] = "draft"
    if lottery:
        w = order[0]
        news(L, f'Lottery night: {tname(L, w)} win the #1 pick'
                f'{" (jumped from seed #" + str(non.index(w) + 1) + ")" if non.index(w) > 0 else ""}.', "big")


def draft_pool(L):
    d = L["draft"]
    if not d:
        return []
    return [p for p in L["players"].values() if p["tid"] == -2 and p.get("dclass") == d["season"]]


def on_clock(L):
    d = L["draft"]
    if not d or d["cur"] >= len(d["order"]):
        return None
    return d["order"][d["cur"]]["tid"]


def ai_pick_choice(L, tid, rng):
    d = L["draft"]
    pool = draft_pool(L)
    if not pool:
        return None
    r = roster(L, tid)
    counts = {p: sum(1 for x in r if x["pos"] == p) for p in POS}
    if d["type"] == "fantasy":
        from .trade import player_value
        def score(p):
            v = player_value(L, p, "neutral", ignore_contract=True)
            need = 1.12 if counts[p["pos"]] == 0 and len(r) >= 4 else 0.9 if counts[p["pos"]] >= 3 else 1
            return v * need * rng.uniform(0.9, 1.1)
    else:
        def score(p):
            need = 2 if counts[p["pos"]] == 0 else 0
            return p["ovr"] * 0.45 + p["pot"] * 0.55 + need + rng.uniform(0, 4)
    return max(pool, key=score)


def make_pick(L, pid, rng=None):
    d = L["draft"]
    slot = d["order"][d["cur"]]
    tid = slot["tid"]
    p = pl(L, pid)
    if not p or p["tid"] != -2 or p.get("dclass") != d["season"]:
        raise GameError("That player isn't available.")
    p["tid"] = tid
    slot["pid"] = p["id"]
    sc = FR.lvl(L, tid, "scouting")
    if sc and d["type"] == "rookie":
        p["pot"] = min(97, p["pot"] + sc)
        P.refresh(p)
    if d["type"] == "rookie" or p.get("contract") is None:
        p["contract"] = rookie_contract(slot["no"], slot["rd"]) if d["type"] == "rookie" else \
            {"sal": max(MIN_SALARY, P.market_salary(p["ovr"], p["age"])), "yrs": 3}
    if p.pop("prospect", False):
        p["rookie"] = L["season"]
    p["draft"] = {"s": d["season"], "rd": slot["rd"], "no": slot["no"], "tid": tid}
    team(L, tid)["lineup"].append(p["id"])
    d["cur"] += 1
    if d["type"] == "rookie" and slot["rd"] == 1 and slot["no"] <= 3:
        news(L, f'With pick #{slot["no"]}, {tname(L, tid)} select {P.full_name(p)} ({p["pos"]}, {p["school"]}).',
             "draft", tid)
    if tid == L["user"]:
        news(L, f'You drafted {P.full_name(p)} ({p["pos"]}) at #{slot["no"]}.', "draft", tid)
    if d["cur"] >= len(d["order"]):
        finish_draft(L, rng or random.Random())


def draft_until_user(L, rng=None, include_user=False):
    rng = rng or random.Random()
    while L["phase"] == "draft" and L["draft"]["cur"] < len(L["draft"]["order"]):
        tid = on_clock(L)
        if tid == L["user"] and not include_user:
            return
        choice = ai_pick_choice(L, tid, rng)
        if choice is None:
            finish_draft(L, rng)
            return
        make_pick(L, choice["id"], rng)


def finish_draft(L, rng):
    d = L["draft"]
    S = d["season"]
    left = [p for p in L["players"].values() if p["tid"] == -2 and p.get("dclass") == S]
    for p in left:
        p["tid"] = -1
        if p.pop("prospect", False):
            p["rookie"] = S
        p["contract"] = None
        p["ask"] = P.contract_ask(p)
    L["picks"] = [pk for pk in L["picks"] if pk["season"] != S]
    d["done"] = True
    L["draft_log"] = d
    L["draft"] = None
    L["phase"] = "regular"
    L["day"] = 0
    gen_prospects(L, S + 1, rng)
    make_picks(L, [S + 1, S + 2])
    for t in L["teams"]:
        if t["tid"] == L["user"]:
            fix_lineup(L, t["tid"])
            if d["type"] == "fantasy":
                auto_lineup(L, t["tid"])
        else:
            auto_lineup(L, t["tid"])
    ai_free_agency(L, rng) if d["type"] == "fantasy" else None
    ai_maintain(L, rng)
    news(L, f"Draft complete. Regular season tips off — {SEASON_DAYS} games, top 4 make the playoffs.", "big")


# ======================================================================= user actions
def set_lineup(L, order):
    u = L["user"]
    ids = {p["id"] for p in roster(L, u)}
    order = [int(x) for x in order]
    if set(order) != ids or len(order) != len(ids):
        raise GameError("Lineup must include every rostered player exactly once.")
    team(L, u)["lineup"] = order


def set_strategy(L, strat):
    allowed = {"pace": ("slow", "normal", "fast"), "focus": ("inside", "balanced", "perimeter"),
               "star": ("share", "normal", "heliocentric"), "defense": ("conservative", "normal", "aggressive"),
               "rotation": ("tight", "standard", "deep")}
    t = team(L, L["user"])
    for k, v in strat.items():
        if k in allowed and v in allowed[k]:
            t["strategy"][k] = v


def user_release(L, pid):
    u = L["user"]
    p = pl(L, pid)
    if not p or p["tid"] != u:
        raise GameError("Not on your roster.")
    if L["phase"] == "playoffs":
        raise GameError("Rosters are frozen during the playoffs.")
    if pid in L["resign"]:
        L["resign"].remove(pid)
        to_fa(L, p, f"You renounced {P.full_name(p)}.")
        return
    release(L, p, u)


def user_sign(L, pid, yrs):
    u = L["user"]
    p = pl(L, pid)
    if not p or p["tid"] != -1:
        raise GameError("That player isn't a free agent.")
    if L["phase"] in ("playoffs",):
        raise GameError("Free agency is closed during the playoffs.")
    if len(roster(L, u)) >= ROSTER_MAX:
        raise GameError(f"Roster full ({ROSTER_MAX}). Release someone first.")
    ask = P.contract_ask(p, fa_mood(L, u))
    yrs = max(1, min(5, int(yrs or ask["yrs"])))
    ok, how = can_afford(L, u, ask["sal"])
    if not ok:
        raise GameError(how)
    if how == "mle":
        team(L, u)["mle"] = True
    sign(L, p, u, {"sal": ask["sal"], "yrs": yrs})
    news(L, f"You signed {P.full_name(p)} — {yrs} yr / ${ask['sal']}M.", "tx", u)


def user_resign(L, pid, yrs):
    u = L["user"]
    p = pl(L, pid)
    if L["phase"] != "offseason" or pid not in L["resign"]:
        raise GameError("That player isn't awaiting a new contract.")
    if p.get("morale", 65) < 25 and p.get("trait") != "Loyal":
        raise GameError(f"{P.full_name(p)} is {FR.mood_label(p.get('morale', 65)).lower()} and refuses to "
                        f"negotiate. He wants out.")
    ask = p.get("ask") or P.contract_ask(p, resign=True)
    yrs = max(1, min(5, int(yrs or ask["yrs"])))
    p["contract"] = {"sal": ask["sal"], "yrs": yrs}
    p.pop("ask", None)
    L["resign"].remove(pid)
    tx(L, f"{team(L, u)['abbr']} re-signed {P.full_name(p)} ({yrs} yr / ${ask['sal']}M).")
    news(L, f"{P.full_name(p)} re-signs: {yrs} yr / ${ask['sal']}M.", "tx", u)


def trades_open(L):
    if L["phase"] == "playoffs":
        return False, "Trades are frozen during the playoffs."
    if L["phase"] == "regular" and L["day"] >= TRADE_DEADLINE_DAY:
        return False, f"The trade deadline has passed (after game {TRADE_DEADLINE_DAY})."
    return True, ""
