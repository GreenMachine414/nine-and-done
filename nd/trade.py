"""Trade valuation, validation, AI acceptance and trade-block offer generation."""
import itertools
import random

from . import players as P
from .data import SALARY_CAP, HARD_APRON, ROSTER_MAX
from . import league as LG

MODE_MULT = {
    "contend": {"youth": 0.6, "pick": 0.75, "old": 1.12, "now": 1.08},
    "neutral": {"youth": 1.0, "pick": 1.0, "old": 1.0, "now": 1.0},
    "rebuild": {"youth": 1.35, "pick": 1.3, "old": 0.7, "now": 0.92},
}


def base_value(eff_ovr):
    return max(0.0, eff_ovr - 40) ** 2.8 / 300.0


def player_value(L, p, mode=None, ignore_contract=False):
    m = MODE_MULT[mode or "neutral"]
    ovr, pot, age = p["ovr"], p["pot"], p["age"]
    youth = 0.6 if age <= 21 else 0.45 if age <= 23 else 0.25 if age <= 25 else 0
    eff = ovr + max(0, pot - ovr) * youth * m["youth"]
    v = base_value(eff) * m["now"]
    if age >= 31:
        v *= max(0.3, 1 - 0.11 * (age - 30) / m["old"])
    inj = p.get("inj") or {}
    if inj.get("games", 0) >= 5:
        v *= 0.85
    c = p.get("contract")
    if c and not ignore_contract:
        surplus = P.market_salary(ovr, age) - c["sal"]
        v += surplus * min(c["yrs"], 3) * (0.9 if surplus < 0 else 0.45)
    return round(max(v, -45), 1)


def pick_slot_estimate(L, pk, ranks):
    d = L.get("draft")
    if d and d["season"] == pk["season"] and d["type"] == "rookie":
        for slot in d["order"]:
            if slot["orig"] == pk["orig"] and slot["rd"] == pk["rd"]:
                return slot["no"] - (10 if pk["rd"] == 2 else 0)
    est = 11 - ranks[pk["orig"]]
    years_out = pk["season"] - L["season"] - (0 if L["phase"] in ("offseason",) else 1)
    years_out = max(0, years_out)
    if years_out >= 1:
        est = 5.5 + (est - 5.5) * 0.5
    return est


def pick_value(L, pk, mode=None, ranks=None):
    ranks = ranks or LG.strength_ranks(L)
    m = MODE_MULT[mode or "neutral"]
    est = pick_slot_estimate(L, pk, ranks)
    if pk["rd"] == 1:
        v = 92 * (0.82 ** (est - 1))
    else:
        v = max(1.5, 6.5 - est * 0.45)
    years_out = max(0, pk["season"] - L["season"] - (1 if L["phase"] in ("regular", "playoffs") else 0))
    v *= 0.88 ** years_out
    return round(v * m["pick"], 1)


def pick_label(L, pk):
    return f'{pk["season"]} {"1st" if pk["rd"] == 1 else "2nd"} ({L["teams"][pk["orig"]]["abbr"]})'


def assets_value(L, assets, mode, ranks):
    v = 0.0
    for pid in assets.get("players", []):
        v += player_value(L, LG.pl(L, pid), mode)
    for pkid in assets.get("picks", []):
        v += pick_value(L, find_pick(L, pkid), mode, ranks)
    return round(v, 1)


def find_pick(L, pkid):
    pk = next((x for x in L["picks"] if x["id"] == pkid), None)
    if not pk:
        raise LG.GameError("Unknown draft pick.")
    return pk


def salary_of(L, pids):
    return round(sum((LG.pl(L, i)["contract"] or {}).get("sal", 0) for i in pids), 1)


def validate(L, a, b, give, get):
    """give: assets a sends to b. get: assets b sends to a. Returns list of problems."""
    probs = []
    ok, why = LG.trades_open(L)
    if not ok:
        return [why]
    if not (give.get("players") or give.get("picks")) and not (get.get("players") or get.get("picks")):
        return ["Add something to the trade."]
    for side, tid, assets in (("You", a, give), ("They", b, get)):
        for pid in assets.get("players", []):
            p = LG.pl(L, pid)
            if not p or p["tid"] != tid:
                probs.append("A player in this deal is no longer on that roster.")
            elif pid in L.get("resign", []):
                probs.append(f"{P.full_name(p)} is unsigned and can't be traded.")
        for pkid in assets.get("picks", []):
            pk = next((x for x in L["picks"] if x["id"] == pkid), None)
            if not pk or pk["owner"] != tid:
                probs.append("A pick in this deal isn't owned by that team.")
    if probs:
        return probs
    for tid, out_, in_ in ((a, give, get), (b, get, give)):
        n = len(LG.roster(L, tid)) - len(out_.get("players", [])) + len(in_.get("players", []))
        name = "Your" if tid == L["user"] else LG.team(L, tid)["abbr"]
        if n > ROSTER_MAX:
            probs.append(f"{name} roster would be {n} players (max {ROSTER_MAX}).")
        if n < 8:
            probs.append(f"{name} roster would drop to {n} players (min 8).")
        sal_out = salary_of(L, out_.get("players", []))
        sal_in = salary_of(L, in_.get("players", []))
        after = LG.payroll(L, tid) - sal_out + sal_in
        if after > SALARY_CAP and sal_in > sal_out * 1.25 + 0.5:
            probs.append(f"{name} payroll would be ${after:.1f}M (over the ${SALARY_CAP}M cap): incoming salary "
                         f"(${sal_in}M) must be ≤ 125% of outgoing (${sal_out}M) + $0.5M.")
        elif after > HARD_APRON and sal_in > sal_out:
            probs.append(f"{name} payroll would exceed the ${HARD_APRON}M hard apron.")
    return probs


def evaluate(L, other, give, get):
    """From the AI's point of view: it receives `give`, sends `get`."""
    ranks = LG.strength_ranks(L)
    mode = LG.team_mode(L, other, ranks)
    recv = assets_value(L, give, mode, ranks)
    send = assets_value(L, get, mode, ranks)
    need = 2.0 + 0.05 * max(0, send)
    fo = LG.team(L, L["user"]).get("upg", {}).get("frontoffice", 0)
    # AI protects its franchise player
    top = max(LG.roster(L, other), key=lambda p: p["ovr"])
    if top["id"] in get.get("players", []):
        need += 0.1 * send
    need *= 1 - 0.08 * fo
    gain = recv - send
    accept = gain >= need
    problems = validate(L, L["user"], other, give, get)
    ratio = (recv / (send + need)) if (send + need) > 0 else 2
    if accept:
        mood = "Deal. Pleasure doing business." if gain > need * 2.5 else "We can live with that."
    elif ratio > 0.85:
        mood = "Close. Sweeten it a little and we're there."
    elif ratio > 0.55:
        mood = "Interesting, but you're going to need to add real value."
    else:
        mood = "Not even close. Try again."
    return {"accept": accept and not problems, "problems": problems, "mode": mode,
            "meter": round(min(1.5, ratio), 3), "msg": mood if not problems else problems[0],
            "recv": recv, "send": send, "ask": suggest_addition(L, other, give, get, need - gain, mode, ranks)
            if not accept else None}


def suggest_addition(L, other, give, get, shortfall, mode, ranks):
    """Smallest single user asset that would close the gap."""
    u = L["user"]
    opts = []
    for p in LG.roster(L, u):
        if p["id"] in give.get("players", []) or p["id"] in L.get("resign", []):
            continue
        v = player_value(L, p, mode)
        if v >= shortfall:
            opts.append((v, {"type": "player", "id": p["id"], "label": P.full_name(p)}))
    for pk in L["picks"]:
        if pk["owner"] != u or pk["id"] in give.get("picks", []):
            continue
        v = pick_value(L, pk, mode, ranks)
        if v >= shortfall:
            opts.append((v, {"type": "pick", "id": pk["id"], "label": pick_label(L, pk)}))
    if not opts:
        return None
    return min(opts, key=lambda o: o[0])[1]


def execute(L, a, b, give, get):
    names_a, names_b = [], []
    for pid in give.get("players", []):
        p = LG.pl(L, pid)
        _move(L, p, b)
        names_a.append(P.full_name(p))
    for pid in get.get("players", []):
        p = LG.pl(L, pid)
        _move(L, p, a)
        names_b.append(P.full_name(p))
    for pkid in give.get("picks", []):
        pk = find_pick(L, pkid)
        pk["owner"] = b
        names_a.append(pick_label(L, pk))
        _move_draft_slot(L, pk, b)
    for pkid in get.get("picks", []):
        pk = find_pick(L, pkid)
        pk["owner"] = a
        names_b.append(pick_label(L, pk))
        _move_draft_slot(L, pk, a)
    ta, tb = LG.team(L, a), LG.team(L, b)
    text = f'TRADE: {ta["abbr"]} send {", ".join(names_a) or "nothing"} to {tb["abbr"]} for ' \
           f'{", ".join(names_b) or "nothing"}.'
    LG.tx(L, text)
    LG.news(L, text, "trade", a)
    for tid in (a, b):
        if tid != L["user"]:
            LG.auto_lineup(L, tid)
        else:
            LG.fix_lineup(L, tid)
    blk = L["block"]
    blk["players"] = [i for i in blk["players"] if LG.pl(L, i) and LG.pl(L, i)["tid"] == L["user"]]
    blk["picks"] = [i for i in blk["picks"] if any(pk["id"] == i and pk["owner"] == L["user"] for pk in L["picks"])]
    L["offers"] = []


def _move(L, p, to):
    frm = LG.team(L, p["tid"])
    if p["id"] in frm["lineup"]:
        frm["lineup"].remove(p["id"])
    p["tid"] = to
    LG.team(L, to)["lineup"].append(p["id"])
    p["morale"] = 78 if p.get("treq") else 60 if p.get("trait") == "Loyal" else 64
    p["treq"] = False
    p.setdefault("mlog", []).append({"t": "traded", "d": 0})


def _move_draft_slot(L, pk, owner):
    d = L.get("draft")
    if d and d["season"] == pk["season"]:
        for slot in d["order"]:
            if slot["orig"] == pk["orig"] and slot["rd"] == pk["rd"] and slot["pid"] is None:
                slot["tid"] = owner


def user_propose(L, other, give, get):
    other = int(other)
    if other == L["user"]:
        raise LG.GameError("Pick another team.")
    ev = evaluate(L, other, give, get)
    if ev["problems"]:
        raise LG.GameError(ev["problems"][0])
    if ev["accept"]:
        execute(L, L["user"], other, give, get)
    return ev


def block_offers(L, rng=None):
    """Each AI team builds its best package for the assets on the user's trade block."""
    rng = rng or random.Random()
    ok, why = LG.trades_open(L)
    if not ok:
        raise LG.GameError(why)
    blk = L["block"]
    give = {"players": list(blk["players"]), "picks": list(blk["picks"])}
    if not give["players"] and not give["picks"]:
        raise LG.GameError("Put at least one player or pick on the trade block.")
    ranks = LG.strength_ranks(L)
    u = L["user"]
    umode = LG.team_mode(L, u, ranks)
    offers = []
    for t in L["teams"]:
        tid = t["tid"]
        if tid == u:
            continue
        mode = LG.team_mode(L, tid, ranks)
        target = assets_value(L, give, mode, ranks)
        if target <= 3:
            continue
        max_give = (target - 2) / 1.05
        top = max(LG.roster(L, tid), key=lambda p: p["ovr"])
        cands = []
        for p in LG.roster(L, tid):
            if p["id"] == top["id"] and mode == "contend":
                continue
            cands.append(("p", p["id"], player_value(L, p, mode)))
        for pk in L["picks"]:
            if pk["owner"] == tid:
                cands.append(("k", pk["id"], pick_value(L, pk, mode, ranks)))
        cands = [c for c in cands if 0.5 < c[2] <= max_give]
        cands.sort(key=lambda c: -c[2])
        cands = cands[:11]
        best = None
        for n in (1, 2, 3):
            for combo in itertools.combinations(cands, n):
                v = sum(c[2] for c in combo)
                if v > max_give or v < max_give * 0.55:
                    continue
                get = {"players": [c[1] for c in combo if c[0] == "p"],
                       "picks": [c[1] for c in combo if c[0] == "k"]}
                if validate(L, u, tid, give, get):
                    continue
                score = v + rng.uniform(0, 3)
                if not best or score > best[0]:
                    best = (score, get)
        if best:
            get = best[1]
            offers.append({"id": f"o{tid}-{rng.randint(1000, 9999)}", "tid": tid, "give": give, "get": get,
                           "value_to_you": assets_value(L, get, umode, ranks),
                           "value_out": assets_value(L, give, umode, ranks)})
    offers.sort(key=lambda o: -o["value_to_you"])
    L["offers"] = offers[:5]
    return L["offers"]


def accept_offer(L, oid):
    o = next((x for x in L["offers"] if x["id"] == oid), None)
    if not o:
        raise LG.GameError("That offer has expired.")
    probs = validate(L, L["user"], o["tid"], o["give"], o["get"])
    if probs:
        L["offers"] = [x for x in L["offers"] if x["id"] != oid]
        raise LG.GameError(probs[0])
    execute(L, L["user"], o["tid"], o["give"], o["get"])
