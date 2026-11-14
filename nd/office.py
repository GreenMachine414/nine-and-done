"""Front-office systems: contract negotiation, prospect scouting, untouchables."""
import random

from . import league as LG
from . import players as P
from .data import MIN_SALARY, MAX_SALARY, ROSTER_MAX


def lvl(L, key):
    return LG.team(L, L["user"]).get("upg", {}).get(key, 0)


def day_key(L):
    return f'{L["season"]}-{L["phase"]}-{L["day"]}'


# ======================================================================= NEGOTIATION
def _patience_base(L, p, kind):
    fo = lvl(L, "frontoffice")
    n = 3 + (fo >= 2) + (fo >= 4)
    tr = p.get("trait")
    if tr in ("Mercenary", "Diva"):
        n -= 1
    if tr == "Loyal" and kind == "resign":
        n += 1
    return max(1, n)


def _state(L, p, kind):
    u = L["user"]
    N = L.setdefault("nego", {})
    st = N.get(str(p["id"]))
    if not st or st.get("season") != L["season"] or st.get("kind") != kind:
        if kind == "resign":
            ask = p.get("ask") or P.contract_ask(p, resign=True)
        else:
            ask = P.contract_ask(p, LG.fa_mood(L, u))
        rr = random.Random(p["id"] * 131 + L["season"])
        fo = lvl(L, "frontoffice")
        floor = max(MIN_SALARY, ask["sal"] * rr.uniform(0.84, 0.96) * (1 - 0.02 * fo))
        st = {"season": L["season"], "kind": kind, "ask": ask, "floor": round(floor, 2), "pref": ask["yrs"],
              "day": None, "patience": 0, "log": [], "hint_shift": rr.uniform(-0.5, 0.5)}
        N[str(p["id"])] = st
    if st["day"] != day_key(L):
        st["day"] = day_key(L)
        st["patience"] = _patience_base(L, p, kind)
        st["log"] = []
    return st


def _demand(st, p, yrs):
    d = yrs - st["pref"]
    if p["age"] >= 31 and d > 0:          # veterans pay for security
        mult = 1 - 0.02 * d
    else:
        mult = 1 + 0.035 * abs(d)
    return max(MIN_SALARY, st["floor"] * mult)


def _hint(L, st):
    fo = lvl(L, "frontoffice")
    if fo <= 0:
        return None
    spread = 0.18 - 0.03 * fo
    center = st["floor"] * (1 + st["hint_shift"] * spread * 0.5)
    return [round(center * (1 - spread / 2), 1), round(center * (1 + spread / 2), 1)]


def _view(L, p, st, extra=None):
    out = {"pid": p["id"], "kind": st["kind"], "ask": st["ask"], "pref": st["pref"], "patience": st["patience"],
           "max": _patience_base(L, p, st["kind"]), "log": st["log"], "hint": _hint(L, st),
           "trait": p.get("trait"), "age": p["age"]}
    if extra:
        out.update(extra)
    return out


def _check(L, p, kind):
    u = L["user"]
    if kind == "fa":
        if p["tid"] != -1:
            raise LG.GameError("That player isn't a free agent.")
        if L["phase"] == "playoffs":
            raise LG.GameError("Free agency is closed during the playoffs.")
        if len(LG.roster(L, u)) >= ROSTER_MAX:
            raise LG.GameError(f"Roster full ({ROSTER_MAX}). Release someone first.")
    else:
        if L["phase"] != "offseason" or p["id"] not in L["resign"]:
            raise LG.GameError("That player isn't awaiting a new contract.")
        if p.get("morale", 65) < 25 and p.get("trait") != "Loyal":
            raise LG.GameError(f"{P.full_name(p)} is {LG.FR.mood_label(p.get('morale', 65)).lower()} and refuses "
                               f"to negotiate. He wants out.")


def open_talks(L, pid, kind):
    p = LG.pl(L, pid)
    if not p:
        raise LG.GameError("Unknown player.")
    _check(L, p, kind)
    return _view(L, p, _state(L, p, kind))


LINES = {
    "counter": ["We're close. Meet us here and we have a deal.", "That's in the neighborhood. Come up a little.",
                "My client appreciates it, but he's worth a bit more."],
    "reject": ["That's not going to get it done.", "We're still pretty far apart.",
               "He has other options, you know."],
    "insulted": ["Is that a joke? Don't waste my client's time.", "That's insulting. We're done for now.",
                 "I'll pretend I didn't hear that."],
    "walk": ["That's it — we're taking a break from talks today.", "My client is walking away from the table. "
             "Call us after the next game day."],
}


def negotiate(L, pid, sal, yrs, kind):
    u = L["user"]
    p = LG.pl(L, pid)
    if not p:
        raise LG.GameError("Unknown player.")
    _check(L, p, kind)
    st = _state(L, p, kind)
    if st["patience"] <= 0:
        raise LG.GameError(f"{P.full_name(p)}'s agent isn't taking calls today. Try after the next game day.")
    yrs = max(1, min(5, int(yrs)))
    sal = round(max(MIN_SALARY, min(MAX_SALARY, float(sal))), 1)
    dem = _demand(st, p, yrs)
    rng = random.Random()
    if sal >= dem - 1e-9:
        if kind == "fa":
            ok, how = LG.can_afford(L, u, sal)
            if not ok:
                raise LG.GameError(how)
            if how == "mle":
                LG.team(L, u)["mle"] = True
            LG.sign(L, p, u, {"sal": sal, "yrs": yrs})
            LG.news(L, f"You signed {P.full_name(p)} — {yrs} yr / ${sal}M.", "tx", u)
        else:
            p["contract"] = {"sal": sal, "yrs": yrs}
            p.pop("ask", None)
            L["resign"].remove(p["id"])
            LG.tx(L, f"{LG.team(L, u)['abbr']} re-signed {P.full_name(p)} ({yrs} yr / ${sal}M).")
            LG.news(L, f"{P.full_name(p)} re-signs: {yrs} yr / ${sal}M.", "tx", u)
        st["log"].append({"you": [sal, yrs], "status": "accept"})
        L["nego"].pop(str(p["id"]), None)
        saved = round(st["ask"]["sal"] - sal, 1)
        return _view(L, p, st, {"status": "accept", "msg": "Deal! " + (f"You saved ${saved}M/yr off his opening ask."
                                                                        if saved > 0 else "Pleasure doing business."),
                                "contract": {"sal": sal, "yrs": yrs}})
    ratio = sal / dem
    if ratio >= 0.9:
        status, cost = "counter", 1
    elif ratio >= 0.72:
        status, cost = "reject", 1
    else:
        status, cost = "insulted", 2
    st["patience"] = max(0, st["patience"] - cost)
    # the agent's counter sits between his real number and his opening ask (scaled for the years offered),
    # never above what he originally asked for
    ask_for_yrs = max(dem, st["ask"]["sal"] * dem / max(0.01, st["floor"]))
    raw = dem * (1 + 0.025 * st["patience"] + (0.04 if status != "counter" else 0))
    counter = round(min(MAX_SALARY, max(dem, min(ask_for_yrs, raw, st["ask"]["sal"] if yrs == st["pref"] else 99))), 1)
    if st["patience"] <= 0:
        status = "walk"
    st["log"].append({"you": [sal, yrs], "them": [counter, yrs], "status": status})
    return _view(L, p, st, {"status": status, "msg": rng.choice(LINES[status]), "counter": {"sal": counter, "yrs": yrs}})


# ======================================================================= SCOUTING
def scout_cost(L, pid):
    step = L["scout"]["lv"].get(str(pid), 0)
    return max(2, 4 + step - lvl(L, "scouting") // 2)


def scout(L, pid):
    p = LG.pl(L, pid)
    if not p or p["tid"] != -2 or not p.get("prospect"):
        raise LG.GameError("You can only scout draft prospects.")
    sc = L["scout"]
    step = sc["lv"].get(str(pid), 0)
    if step >= P.SCOUT_MAX_STEP:
        raise LG.GameError("You've already scouted him completely.")
    cost = scout_cost(L, pid)
    if sc["pts"] < cost:
        raise LG.GameError(f"Not enough scouting points ({sc['pts']}/{cost}). You earn {sc.get('daily', 6)} "
                           f"per game day.")
    sc["pts"] -= cost
    sc["lv"][str(pid)] = step + 1
    return P.scout_report(p, step + 1, lvl(L, "scouting"))


# ======================================================================= UNTOUCHABLES
def set_untouchable(L, pid):
    t = LG.team(L, L["user"])
    if not pid:
        t["untouch"] = None
        return None
    p = LG.pl(L, pid)
    if not p or p["tid"] != L["user"]:
        raise LG.GameError("Not on your roster.")
    if t.get("untouch_s") == L["season"] and t.get("untouch") not in (None, pid):
        raise LG.GameError("You can only name one untouchable per season.")
    t["untouch"] = pid
    t["untouch_s"] = L["season"]
    if pid in L["block"]["players"]:
        L["block"]["players"].remove(pid)
    LG.news(L, f"{P.full_name(p)} has been declared untouchable.", "tx", L["user"])
    return pid
