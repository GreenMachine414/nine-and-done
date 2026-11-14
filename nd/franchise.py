"""Franchise systems: upgrade tracks + franchise points, personalities/morale/chemistry, rivalries,
and the All-Star break."""
import random

from . import league as LG
from . import players as P
from .sim import Game, STAT_KEYS, meter_grade

# ======================================================================= UPGRADES
TRACKS = [
    ("dev", "Player Development", "Training staff and facilities. Young players grow faster and veterans age slower."),
    ("arena", "Arena & Crowd", "A louder building. Your home shooting improves and visitors miss more free throws."),
    ("medical", "Sports Medicine", "Fewer injuries, and quicker returns from the ones that happen."),
    ("conditioning", "Strength & Conditioning", "Players tire more slowly on the floor and recover faster on the bench."),
    ("analytics", "Analytics Dept.", "Better shot selection and scouting reports. Every shot gets a little more efficient."),
    ("scouting", "Scouting Network", "Tighter draft ranges, and every player you draft arrives with more potential."),
    ("culture", "Locker Room Culture", "Raises the morale floor, speeds up mood recovery and boosts team chemistry."),
    ("frontoffice", "Front Office", "Sharper negotiators. Cheaper contracts, and other teams accept your trades more easily."),
    ("coaching", "Coaching Staff", "Extra timeouts, wider challenge windows and stronger results from your live-coaching calls."),
]
TRACK_KEYS = [t[0] for t in TRACKS]
COST = [12, 20, 30, 42, 56]   # 160 FP to max one track; ~1,440 to max everything
MAX_LVL = 5


def effect_text(key, l):
    if key == "dev":
        return f"+{0.35 * l:.2f} growth/yr for players ≤25 · −{6 * l}% age decline"
    if key == "arena":
        return f"+{0.4 * l:.1f}% home shooting · visitors −{l}% FT"
    if key == "medical":
        return f"−{12 * l}% injury risk" + (f" · −{(l + 1) // 2} game{'s' if (l + 1) // 2 > 1 else ''} per injury" if l else "")
    if key == "conditioning":
        return f"−{4.5 * l:.1f}% fatigue · +{6 * l}% bench recovery"
    if key == "analytics":
        return f"+{0.35 * l:.2f}% make chance on every shot"
    if key == "scouting":
        return f"Draft ranges ±{max(1, 6 - l)} · your draftees +{l} potential"
    if key == "culture":
        return f"Morale floor {10 + 5 * l} · +{8 * l}% morale gains · +{1.5 * l:.1f} chemistry"
    if key == "frontoffice":
        return f"−{3 * l}% contract asks · trade acceptance bar −{8 * l}%"
    if key == "coaching":
        return f"{4 + (l >= 2) + (l >= 4)} timeouts · {12 * l}% wider meters · +{10 * l}% coaching effects"
    return ""


def lvl(L, tid, key):
    return LG.team(L, tid).get("upg", {}).get(key, 0)


def earn(L, tid, n, why):
    if tid is None or tid < 0 or tid >= len(L["teams"]) or n <= 0:
        return
    t = LG.team(L, tid)
    t["fp"] = t.get("fp", 0) + n
    t["fp_total"] = t.get("fp_total", 0) + n
    if tid == L["user"]:
        log = t.setdefault("fp_log", [])
        log.append({"s": L["season"], "n": n, "txt": why})
        if len(log) > 60:
            del log[:-60]


def buy(L, key):
    if key not in TRACK_KEYS:
        raise LG.GameError("Unknown upgrade.")
    t = LG.team(L, L["user"])
    cur = t["upg"].get(key, 0)
    if cur >= MAX_LVL:
        raise LG.GameError("Already maxed out.")
    cost = COST[cur]
    if t.get("fp", 0) < cost:
        raise LG.GameError(f"Not enough franchise points ({t.get('fp', 0)}/{cost}).")
    t["fp"] -= cost
    t["upg"][key] = cur + 1
    name = dict((k, n) for k, n, _ in TRACKS)[key]
    LG.news(L, f"Franchise upgrade: {name} is now level {cur + 1}.", "big", L["user"])


PHILOSOPHIES = ["builder", "contender", "moneyball", "culture", "balanced"]
PHILO_PREFS = {   # how much each front-office philosophy values each track
    "builder": {"dev": 3.0, "scouting": 2.4, "culture": 1.4, "medical": 1.2},
    "contender": {"analytics": 2.6, "conditioning": 2.2, "coaching": 1.8, "arena": 1.8, "medical": 1.4},
    "moneyball": {"frontoffice": 3.0, "analytics": 2.2, "scouting": 1.8, "dev": 1.4},
    "culture": {"culture": 3.0, "coaching": 1.8, "arena": 1.6, "dev": 1.2},
    "balanced": {},
}
PHILO_LABEL = {"builder": "Player builders", "contender": "Win-now", "moneyball": "Moneyball",
               "culture": "Culture first", "balanced": "Balanced"}


def ai_spend(L, rng):
    """Called every game day: each AI front office picks the upgrade it wants most (by philosophy, current
    levels and how its season is going) and buys it once it can afford it, sometimes saving up first."""
    for t in L["teams"]:
        if t["tid"] == L["user"]:
            continue
        prefs = PHILO_PREFS.get(t.get("philo"), {})
        gp = t["w"] + t["l"]
        struggling = gp >= 3 and t["w"] / gp < 0.4

        def want(k):
            lv = t["upg"].get(k, 0)
            if lv >= MAX_LVL:
                return -1
            w = prefs.get(k, 1.0) / (1 + 0.45 * lv)
            if struggling and k in ("dev", "scouting"):
                w *= 1.3
            return w * rng.uniform(0.8, 1.2)
        target = max(TRACK_KEYS, key=want)
        if want(target) < 0:
            continue
        cost = COST[t["upg"].get(target, 0)]
        if t["fp"] >= cost and rng.random() < 0.7:
            t["fp"] -= cost
            t["upg"][target] = t["upg"].get(target, 0) + 1
            t.setdefault("upg_log", []).append({"s": L["season"], "d": L["day"], "k": target,
                                                 "lv": t["upg"][target]})


# ======================================================================= MORALE / CHEMISTRY
EXPECT_MIN = [32, 31, 30, 26, 24, 20, 17, 13, 10, 6, 3, 2, 2, 2, 2]
TALK = {   # trait -> {approach: quality}
    "Leader": {"challenge": "best", "praise": "ok", "role": "bad"},
    "Mentor": {"role": "best", "praise": "ok", "challenge": "bad"},
    "Competitor": {"challenge": "best", "role": "ok", "praise": "bad"},
    "Diva": {"praise": "best", "role": "ok", "challenge": "bad"},
    "Loyal": {"praise": "best", "role": "ok", "challenge": "ok"},
    "Mercenary": {"role": "best", "praise": "ok", "challenge": "bad"},
    "Professional": {"role": "best", "praise": "ok", "challenge": "ok"},
    "Hothead": {"role": "best", "praise": "ok", "challenge": "bad"},
    "Gym Rat": {"challenge": "best", "role": "ok", "praise": "ok"},
}


def mood_label(m):
    return "Ecstatic" if m >= 88 else "Happy" if m >= 72 else "Content" if m >= 55 else \
        "Frustrated" if m >= 38 else "Unhappy" if m >= 25 else "Furious"


def _log(p, txt, d):
    log = p.setdefault("mlog", [])
    log.append({"t": txt, "d": round(d, 1)})
    if len(log) > 6:
        del log[:-6]


def _set_morale(L, p, val):
    tid = p["tid"]
    floor = 10 + 5 * lvl(L, tid, "culture") if tid >= 0 else 5
    p["morale"] = round(max(floor, min(100, val)), 1)
    if tid == L["user"]:
        if p["morale"] < 28 and not p.get("treq"):
            p["treq"] = True
            LG.news(L, f"{P.full_name(p)} has requested a trade. He's {mood_label(p['morale']).lower()} "
                       f"with his situation.", "big", tid)
        elif p["morale"] > 45 and p.get("treq"):
            p["treq"] = False
            LG.news(L, f"{P.full_name(p)} has rescinded his trade request.", "info", tid)


def chemistry(L, tid):
    ps = sorted(LG.roster(L, tid), key=lambda p: -p["ovr"])[:9]
    if not ps:
        return 50
    base = sum(p.get("morale", 65) for p in ps) / len(ps)
    leaders = min(2, sum(1 for p in ps if p.get("trait") == "Leader" and p.get("morale", 65) >= 50))
    sour_divas = sum(1 for p in ps if p.get("trait") == "Diva" and p.get("morale", 65) < 40)
    treqs = sum(1 for p in ps if p.get("treq"))
    c = base + leaders * 4 - sour_divas * 5 - treqs * 6 + 1.5 * lvl(L, tid, "culture")
    return int(max(15, min(99, round(c))))


def after_game(L, doc, rival_tier):
    """Update morale for both rosters after a game."""
    for tid, won in ((doc["h"], doc["hs"] > doc["as"]), (doc["a"], doc["as"] > doc["hs"])):
        ps = LG.roster(L, tid)
        ranked = sorted(ps, key=lambda p: -p["ovr"])
        rank = {p["id"]: i for i, p in enumerate(ranked)}
        gain = 1 + 0.08 * lvl(L, tid, "culture")
        has_leader = any(p.get("trait") == "Leader" for p in ps)
        for p in ps:
            tr = p.get("trait")
            row = doc["box"].get(p["id"]) or doc["box"].get(str(p["id"]))
            res = (2.0 if won else -2.0) * (1 + 0.3 * rival_tier) * (1.5 if doc.get("po") else 1)
            res *= {"Competitor": 1.8, "Mercenary": 0.3, "Professional": 0.35}.get(tr, 1.0)
            d = res
            why = "big win" if won and rival_tier else "win" if won else "loss"
            hurt = p.get("inj") and p["inj"].get("games", 0) > 0
            if not hurt:
                mins = row["min"] if row else 0
                exp = EXPECT_MIN[min(rank[p["id"]], len(EXPECT_MIN) - 1)]
                md = max(-3.0, min(1.5, (mins - exp) / 6))
                if md < 0:
                    md *= {"Diva": 2.0, "Loyal": 0.5, "Professional": 0.4, "Mercenary": 1.3}.get(tr, 1.0)
                    if md < -1:
                        why = "minutes"
                d += md
            if row and row["pts"] >= 25:
                d += 1.0
            if d < 0 and has_leader and tr != "Leader":
                d *= 0.8
            if d > 0:
                d *= gain
            m = p.get("morale", 65)
            m += d
            m += (65 - m) * (0.1 if tr == "Professional" else 0.035)
            _log(p, why, d)
            _set_morale(L, p, m)


def talk(L, pid, approach):
    p = LG.pl(L, pid)
    if not p or p["tid"] != L["user"]:
        raise LG.GameError("You can only talk to your own players.")
    if approach not in ("praise", "challenge", "role"):
        raise LG.GameError("Unknown approach.")
    stamp = f'{L["season"]}-{L["phase"]}-{L["day"]}'
    if p.get("talked") == stamp:
        raise LG.GameError("You already talked to him today. Give it a game.")
    p["talked"] = stamp
    q = TALK.get(p.get("trait"), {}).get(approach, "ok")
    rng = random.Random()
    d = {"best": rng.uniform(7, 12), "ok": rng.uniform(1.5, 4), "bad": -rng.uniform(5, 9)}[q]
    if p.get("trait") == "Professional":
        d *= 0.5
    if d > 0:
        d *= 1 + 0.08 * lvl(L, L["user"], "culture")
    _log(p, f"talk: {approach}", d)
    _set_morale(L, p, p.get("morale", 65) + d)
    lines = {
        "best": ["That's exactly what he needed to hear.", "He's nodding along. You got through to him.",
                 "He leaves your office fired up."],
        "ok": ["He listens politely. Some effect.", "It helps a little.", "He appreciates the conversation."],
        "bad": ["That landed badly. He walks out frustrated.", "Wrong approach — he's stewing now.",
                "He rolls his eyes. That made it worse."],
    }
    return {"quality": q, "delta": round(d, 1), "txt": rng.choice(lines[q]), "morale": p["morale"]}


def offseason_morale(L):
    for p in L["players"].values():
        m = p.get("morale", 65)
        p["morale"] = round(65 + (m - 65) * 0.5, 1)
        p["mlog"] = []
        p["treq"] = False


# ======================================================================= RIVALRIES
SEEDED = [("VOL", "SLC", "The Power Line"), ("ASH", "IRV", "The Furnace Feud"), ("GLP", "CWR", "The Cold Front"),
          ("OBK", "CRH", "Deep Water Derby"), ("SUN", "THV", "Crown & Fang"), ("CPR", "SLT", "The Gold Rush"),
          ("LAK", "PCT", "The Woodpile"), ("DSK", "STF", "Night Sky Series"), ("STP", "NWM", "The Northern Storm"),
          ("BYC", "RVB", "The River Rumble")]


def _seeded_keys(L):
    ab = {t["abbr"]: t["tid"] for t in L["teams"]}
    return {rkey(ab[a], ab[b]): name for a, b, name in SEEDED if a in ab and b in ab}
TIERS = ["None", "Heated", "Bitter", "Blood Feud"]


def rkey(a, b):
    a, b = sorted((int(a), int(b)))
    return f"{a}-{b}"


def ensure_rivals(L):
    if "rivals" not in L:
        L["rivals"] = {}
    for k, name in _seeded_keys(L).items():
        a, b = k.split("-")
        r = L["rivals"].setdefault(k, {"score": 22, "w": {a: 0, b: 0}, "g": 0, "po": 0})
        r.setdefault("name", name)


def tier(score):
    return 3 if score >= 75 else 2 if score >= 45 else 1 if score >= 20 else 0


def rival_tier(L, a, b):
    r = L.get("rivals", {}).get(rkey(a, b))
    return tier(r["score"]) if r else 0


def rivalry_game(L, h, a, hs, as_, ot, playoff):
    k = rkey(h, a)
    r = L["rivals"].setdefault(k, {"score": 0, "w": {str(h): 0, str(a): 0}, "g": 0, "po": 0})
    before = tier(r["score"])
    winner = h if hs > as_ else a
    r["w"][str(winner)] = r["w"].get(str(winner), 0) + 1
    r["g"] += 1
    m = abs(hs - as_)
    r["score"] = min(100, r["score"] + 2 + (3 if m <= 5 else 0) + (3 if ot else 0) + (2 if m >= 20 else 0)
                     + (4 if playoff else 0))
    after = tier(r["score"])
    if after > before:
        ta, tb = LG.team(L, h), LG.team(L, a)
        name = r.get("name") or f"{ta['abbr']}–{tb['abbr']}"
        LG.news(L, f"Rivalry escalates: {ta['name']} vs {tb['name']} is now a {TIERS[after].upper()} "
                   f"rivalry{' (' + name + ')' if r.get('name') else ''}.", "big",
                h if L["user"] in (h, a) else None)
    return before


def rivalry_series(L, winner, loser, games):
    r = L["rivals"].setdefault(rkey(winner, loser), {"score": 0, "w": {str(winner): 0, str(loser): 0},
                                                      "g": 0, "po": 0})
    r["po"] += 1
    r["score"] = min(100, r["score"] + 10 + (8 if games == 5 else 0))


def decay_rivals(L):
    seeded = set(_seeded_keys(L))
    for k, r in L.get("rivals", {}).items():
        r["score"] = round(max(15 if k in seeded else 0, r["score"] * 0.8), 1)


# ======================================================================= ALL-STAR BREAK
ALLSTAR_DAY = 5    # weekend happens after 5 regular-season games
AS_TEAMS = [
    {"tid": 100, "city": "Team", "name": "Volt", "abbr": "VLT", "c1": "#d4ff3a", "c2": "#1d2a0c", "glyph": "bolt",
     "shape": "hex", "arena": "All-Star Weekend"},
    {"tid": 101, "city": "Team", "name": "Flare", "abbr": "FLR", "c1": "#ff5d3a", "c2": "#3a1206", "glyph": "flame",
     "shape": "shield", "arena": "All-Star Weekend"},
]
AS_STRAT = {"pace": "fast", "defense": "conservative", "focus": "perimeter", "star": "share", "rotation": "deep"}


def allstar_setup(L, rng):
    S = L["season"]
    key = str(S)
    cands = []
    for p in L["players"].values():
        if p["tid"] < 0:
            continue
        st = p["stats"].get(key)
        if not st or st["gp"] < 3:
            continue
        pg = LG.per_game(st)
        t = LG.team(L, p["tid"])
        wp = t["w"] / max(1, t["w"] + t["l"])
        fan = rng.uniform(0, 3) + (2 if p.get("trait") == "Diva" else 0)
        cands.append((LG.eff(pg) * (0.8 + 0.4 * wp) + p["ovr"] * 0.12 + fan, p))
    cands.sort(key=lambda x: -x[0])
    sel = [p for _, p in cands[:14]]
    teams = [[], []]
    for i, p in enumerate(sel):
        teams[0 if i % 4 in (0, 3) else 1].append(p["id"])
    shooters = sorted([p for p in L["players"].values() if p["tid"] >= 0 and
                       (p["stats"].get(key) or {}).get("tpa", 0) >= 6],
                      key=lambda p: -(p["a"]["three"] + rng.uniform(0, 4)))[:6]
    dunkers = sorted([p for p in L["players"].values() if p["tid"] >= 0 and p["age"] <= 30],
                     key=lambda p: -(p["a"]["ath"] * 0.65 + p["a"]["ins"] * 0.35 + rng.uniform(0, 5)))[:4]
    L["allstar"] = {
        "s": S, "status": "ready", "teams": teams,
        "three": {"entrants": [p["id"] for p in shooters], "r1": {}, "final": {}, "stage": "r1", "winner": None},
        "dunk": {"entrants": [p["id"] for p in dunkers], "r1": {}, "final": {}, "winner": None},
        "gid": None, "score": None, "mvp": None,
    }
    for p in sel:
        boost = 12 if p.get("trait") == "Diva" else 8
        _set_morale(L, p, p.get("morale", 65) + boost)
        _log(p, "All-Star!", boost)
        p["awards"].append({"s": S, "a": "AS"})
        earn(L, p["tid"], 1, f"All-Star selection: {P.full_name(p)}")
    mine = [p for p in sel if p["tid"] == L["user"]]
    LG.news(L, f"All-Star Weekend is here! {len(sel)} players selected"
               + (f", including your {', '.join(P.short_name(p) for p in mine)}" if mine else "") + ".", "big",
            L["user"] if mine else None)


def _three_round(p, rng, accs=None, coach=0):
    base = max(0.25, min(0.74, 0.28 + (p["a"]["three"] - 60) * 0.011))
    racks = []
    total = 0
    for i in range(25):
        pr = base
        if accs is not None and i < len(accs):
            g = meter_grade(float(accs[i]), coach)
            pr = max(0.04, min(0.96, base + {"perfect": 0.28, "good": 0.13, "ok": 0.0, "miss": -0.25}[g]))
        made = rng.random() < pr
        money = (i % 5) == 4
        total += (2 if money else 1) if made else 0
        racks.append(1 if made else 0)
    return {"score": total, "shots": racks}


def three_round(L, accs=None, rng=None):
    """Advance the 3-point contest one stage. accs = the user's timing results for his entrant this round."""
    rng = rng or random.Random()
    a = L["allstar"]
    th = a["three"]
    coach = lvl(L, L["user"], "coaching")
    if th["stage"] == "r1":
        for pid in th["entrants"]:
            p = LG.pl(L, pid)
            if not p:
                continue
            mine = p["tid"] == L["user"] and accs is not None
            th["r1"][str(pid)] = _three_round(p, rng, accs if mine else None, coach)
            th["r1"][str(pid)]["you"] = mine
        th["stage"] = "final"
        top = sorted(th["r1"].items(), key=lambda kv: -kv[1]["score"])[:3]
        th["finalists"] = [int(k) for k, _ in top]
        return
    if th["stage"] == "final":
        for pid in th["finalists"]:
            p = LG.pl(L, pid)
            mine = p and p["tid"] == L["user"] and accs is not None
            th["final"][str(pid)] = _three_round(p, rng, accs if mine else None, coach)
            th["final"][str(pid)]["you"] = mine
        th["stage"] = "done"
        win = max(th["final"].items(), key=lambda kv: (kv[1]["score"], rng.random()))[0]
        th["winner"] = int(win)
        p = LG.pl(L, win)
        if p:
            p["awards"].append({"s": L["season"], "a": "3PT"})
            _set_morale(L, p, p.get("morale", 65) + 5)
            earn(L, p["tid"], 1, f"3-Point Contest champion: {P.full_name(p)}")
            LG.news(L, f"{P.full_name(p)} wins the 3-Point Contest with {th['final'][win]['score']} in the final.",
                    "big", p["tid"])


def user_needs_three(L):
    a = L.get("allstar")
    if not a or a["status"] != "ready":
        return False
    th = a["three"]
    pool = th["entrants"] if th["stage"] == "r1" else th.get("finalists", []) if th["stage"] == "final" else []
    return any((LG.pl(L, pid) or {}).get("tid") == L["user"] for pid in pool)


def _dunk(p, rng):
    base = 37 + (p["a"]["ath"] - 75) * 0.3 + (p["a"]["ins"] - 75) * 0.12
    return [int(max(30, min(50, round(rng.gauss(base, 4.5))))) for _ in range(2)]


def allstar_run(L, rng=None):
    """Finish everything left in the weekend. Returns the All-Star Game doc to persist."""
    rng = rng or random.Random()
    a = L["allstar"]
    if not a or a["status"] != "ready":
        return None
    while a["three"]["stage"] != "done":
        three_round(L, None, rng)
    dk = a["dunk"]
    for pid in dk["entrants"]:
        p = LG.pl(L, pid)
        if p:
            dk["r1"][str(pid)] = _dunk(p, rng)
    fin = sorted(dk["r1"].items(), key=lambda kv: -sum(kv[1]))[:2]
    for pid, _ in fin:
        dk["final"][pid] = _dunk(LG.pl(L, pid), rng)
    win = max(dk["final"].items(), key=lambda kv: (sum(kv[1]), rng.random()))[0]
    dk["winner"] = int(win)
    p = LG.pl(L, win)
    p["awards"].append({"s": L["season"], "a": "DUNK"})
    earn(L, p["tid"], 1, f"Dunk Contest champion: {P.full_name(p)}")
    LG.news(L, f"{P.full_name(p)} wins the Dunk Contest!", "big", p["tid"])
    # the game
    rosters = [[LG.pl(L, i) for i in side if LG.pl(L, i)] for side in a["teams"]]
    tds = []
    for i, r in enumerate(rosters):
        r.sort(key=lambda p: -p["ovr"])
        tds.append({**AS_TEAMS[i], "strategy": dict(AS_STRAT), "lineup": [p["id"] for p in r], "upg": {}})
    g = Game(tds[0], rosters[0], tds[1], rosters[1], rng=rng, record=True, opts={"exhibition": True})
    res = g.play()
    hs, as_ = res["score"]
    win_side = 0 if hs > as_ else 1
    winners = {str(i) for i in a["teams"][win_side]}
    mvp = max(((pid, r) for pid, r in res["box"].items() if str(pid) in winners),
              key=lambda kv: kv[1]["pts"] + kv[1]["ast"] + kv[1]["orb"] + kv[1]["drb"])[0]
    gid = f'{L["season"]}-ASG'
    a.update({"status": "done", "gid": gid, "score": [hs, as_], "mvp": int(mvp)})
    mp = LG.pl(L, mvp)
    mp["awards"].append({"s": L["season"], "a": "ASMVP"})
    L.setdefault("allstar_hist", []).append({"s": L["season"], "mvp": P.full_name(mp),
                                             "three": P.full_name(LG.pl(L, a["three"]["winner"])),
                                             "dunk": P.full_name(p), "score": [hs, as_]})
    LG.news(L, f"All-Star Game: Team {AS_TEAMS[win_side]['name']} wins {max(hs, as_)}–{min(hs, as_)}. "
               f"MVP: {P.full_name(mp)}.", "big")
    return {"gid": gid, "s": L["season"], "day": L["day"] - 1, "h": 100, "a": 101, "hs": hs, "as": as_,
            "ot": res["ot"], "po": False, "series": None, "pog": int(mvp), "allstar": True, "q": res["q"],
            "box": res["box"], "starters": res["starters"], "events": res["events"], "flow": res["flow"],
            "teams": tds}


# ======================================================================= SELECTION COMMITTEE (CFP-style)
def _opponents(L, tid):
    """Regular-season opponents played so far, with results, from the schedule + results log."""
    out = []
    for r in L["results"]:
        if r.get("po") or r.get("s") != L["season"]:
            continue
        if r["h"] == tid:
            out.append((r["a"], r["hs"] > r["as"], r["hs"] - r["as"]))
        elif r["a"] == tid:
            out.append((r["h"], r["as"] > r["hs"], r["as"] - r["hs"]))
    return out


def committee_rank(L, final=False):
    """Weekly ranking. Factors: record, strength of schedule (opponents + opponents' opponents), quality wins,
    bad losses, capped scoring margin, recent form, an early-season 'eye test' (roster strength), conference
    standing, then a head-to-head check between neighbors. A little committee subjectivity is baked in."""
    teams = L["teams"]
    n = len(teams)
    wp = {t["tid"]: (t["w"] / (t["w"] + t["l"]) if t["w"] + t["l"] else 0.5) for t in teams}
    strength = {t["tid"]: LG.team_strength(L, t["tid"]) for t in teams}
    prev = L["rankings"][-1]["order"] if L.get("rankings") else None
    prev_rank = {tid: i for i, tid in enumerate(prev)} if prev else {}
    # tiers for quality wins / bad losses: last week's committee ranking, or roster strength preseason
    tier_order = prev or sorted(strength, key=lambda t: -strength[t])
    top = set(tier_order[:max(3, n // 3)])
    bottom = set(tier_order[-max(3, n // 3):])
    rng = random.Random(L["season"] * 1000 + L["day"] * 7 + 3)
    info, score = {}, {}
    for t in teams:
        tid = t["tid"]
        games = _opponents(L, tid)
        gp = len(games)
        opp = [o for o, _, _ in games]
        sos = sum(wp[o] for o in opp) / gp if gp else 0.5
        sos2 = 0.5
        if gp:
            vals = [sum(wp[x] for x, _, _ in _opponents(L, o)) / max(1, len(_opponents(L, o))) for o in opp]
            sos2 = sum(vals) / len(vals)
        qw = sum(1 for o, won, _ in games if won and o in top)
        bl = sum(1 for o, won, _ in games if not won and o in bottom)
        margin = sum(max(-15, min(15, m)) for _, _, m in games) / gp if gp else 0
        form = sum(t.get("results", [])[-3:]) / max(1, len(t.get("results", [])[-3:])) if t.get("results") else 0.5
        eye_w = max(0.15, 1 - gp / 6)
        conf_lead = 0
        if L["settings"].get("conf"):
            mates = [x for x in teams if x["conf"] == t["conf"]]
            best = max(x["w"] - x["l"] for x in mates)
            conf_lead = 1 if t["w"] - t["l"] == best and gp else 0
        sc = (42 * (wp[tid] if gp else 0.5) + 20 * sos + 7 * sos2 + 3.5 * qw - 4.5 * bl + 0.45 * margin
              + 4 * form + eye_w * (strength[tid] - 68) * 0.9 + 1.5 * conf_lead + rng.gauss(0, 0.6))
        score[tid] = sc
        info[str(tid)] = {"sos": round(sos, 3), "qw": qw, "bl": bl, "margin": round(margin, 1),
                          "form": "".join("W" if x else "L" for x in t.get("results", [])[-3:]), "gp": gp}
    order = sorted(score, key=lambda t: -score[t])
    # head-to-head: a team that beat the team just above it, with a close score, jumps it
    for _ in range(2):
        for i in range(len(order) - 1):
            a, b = order[i], order[i + 1]
            hb = team_h2h(L, b, a)
            if hb[0] > hb[1] and score[a] - score[b] < 3:
                order[i], order[i + 1] = b, a
    sos_rank = sorted(score, key=lambda t: -info[str(t)]["sos"])
    for tid in score:
        info[str(tid)]["sos_rank"] = sos_rank.index(tid) + 1
        info[str(tid)]["prev"] = (prev_rank[tid] + 1) if tid in prev_rank else None
        info[str(tid)]["score"] = round(score[tid], 1)
    entry = {"day": L["day"], "final": final, "order": order, "info": info}
    if L["rankings"] and L["rankings"][-1]["day"] == L["day"]:
        L["rankings"][-1] = entry
    else:
        L["rankings"].append(entry)
    L["rankings"] = L["rankings"][-12:]
    if L["day"] > 0:
        u = L["user"]
        LG.news(L, f"Committee rankings (week {L['day']}): " + ", ".join(
            f"{i + 1}. {LG.team(L, t)['abbr']}" for i, t in enumerate(order[:4])) +
            f" · first out: {', '.join(LG.team(L, t)['abbr'] for t in order[4:6])}", "info")
    return order


def team_h2h(L, a, b):
    rec = LG.team(L, a)["h2h"].get(str(b), [0, 0])
    return rec


def committee_order(L):
    if not L.get("rankings"):
        committee_rank(L)
    return list(L["rankings"][-1]["order"])
