"""Headless test of every league configuration: schedules, playoffs, committee, lottery, negotiation, scouting,
untouchables, trade energy and the display-rating distribution.  python test/configtest.py"""
import os
import random
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from nd import league as LG, trade as TR, players as P, office as OF, franchise as FR  # noqa: E402
from nd.data import SEASON_DAYS  # noqa: E402

CONFIGS = [
    {"teams": 10, "conf": False, "committee": False, "start": "classic"},
    {"teams": 12, "conf": True, "committee": False, "start": "classic"},
    {"teams": 14, "conf": False, "committee": True, "start": "fantasy"},
    {"teams": 16, "conf": True, "committee": True, "start": "classic"},
    {"teams": 18, "conf": True, "committee": False, "start": "classic"},
    {"teams": 20, "conf": True, "committee": True, "start": "classic"},
]


def check_schedule(L):
    n = len(L["teams"])
    sched = L["schedule"]
    assert len(sched) == SEASON_DAYS, len(sched)
    seen = set()
    games = Counter()
    intra = Counter()
    for day in sched:
        teams = [g["h"] for g in day] + [g["a"] for g in day]
        assert sorted(teams) == list(range(n)), "every team plays every day"
        for g in day:
            k = (min(g["h"], g["a"]), max(g["h"], g["a"]))
            assert k not in seen, "no rematches"
            seen.add(k)
            games[g["h"]] += 1
            games[g["a"]] += 1
            if L["teams"][g["h"]]["conf"] == L["teams"][g["a"]]["conf"]:
                intra[g["h"]] += 1
                intra[g["a"]] += 1
    return dict(Counter(intra.values())) if L["settings"]["conf"] else None


def run(cfg, seed):
    rng = random.Random(seed)
    user_fid = rng.randrange(20)
    L = LG.new_league("T", user_fid, settings=cfg, seed=seed)
    n = cfg["teams"]
    assert len(L["teams"]) == n
    assert L["teams"][L["user"]]["fid"] == user_fid
    intra = check_schedule(L)
    out = [f'{n} teams conf={cfg["conf"]} committee={cfg["committee"]} {cfg["start"]}: intra-conf games {intra}']
    u = L["user"]
    for season in range(2):
        LG.draft_until_user(L, rng, include_user=True)
        while len(LG.roster(L, u)) > 15:
            LG.user_release(L, min(LG.roster(L, u), key=lambda p: p["ovr"])["id"])
        if season == 0:
            # untouchable + trade energy
            mine = sorted(LG.roster(L, u), key=lambda p: -p["ovr"])
            OF.set_untouchable(L, mine[0]["id"])
            try:
                OF.set_untouchable(L, mine[1]["id"])
                raise AssertionError("second untouchable allowed")
            except LG.GameError:
                pass
            other = (u + 1) % n
            probs = TR.validate(L, u, other, {"players": [mine[0]["id"]], "picks": []}, {"players": [], "picks": []})
            assert any("untouchable" in x for x in probs), probs
            calls = L["energy"]["trade"]
            pk = next(x for x in L["picks"] if x["owner"] == u and x["rd"] == 2)
            for _ in range(calls):
                TR.user_propose(L, other, {"players": [], "picks": []}, {"players": [], "picks": [
                    next(x for x in L["picks"] if x["owner"] == other)["id"]]})
            try:
                TR.user_propose(L, other, {"players": [], "picks": [pk["id"]]}, {"players": [], "picks": []})
                raise AssertionError("trade energy not enforced")
            except LG.GameError as e:
                assert "trade calls" in str(e), e
            # negotiation with a free agent
            while len(LG.roster(L, u)) >= 15:
                LG.user_release(L, min(LG.roster(L, u), key=lambda p: p["ovr"])["id"])
            fa = max((p for p in L["players"].values() if p["tid"] == -1), key=lambda p: p["ovr"])
            st = OF.open_talks(L, fa["id"], "fa")
            r1 = OF.negotiate(L, fa["id"], st["ask"]["sal"] * 0.78, st["ask"]["yrs"], "fa")
            r2 = r1 if r1["status"] in ("walk", "accept") else OF.negotiate(L, fa["id"], st["ask"]["sal"] * 0.93, st["ask"]["yrs"], "fa")
            out.append(f'  nego: ask {st["ask"]} -> lowball {r1["status"]} (pat {r1["patience"]}), '
                       f'93% {r2["status"]} counter {r2.get("counter")}')
            if r2["status"] not in ("accept", "walk"):
                r3 = OF.negotiate(L, fa["id"], r2["counter"]["sal"], st["ask"]["yrs"], "fa")
                out.append(f'  nego: met counter -> {r3["status"]}')
        while L["phase"] in ("regular", "playoffs"):
            LG.sim_day(L, rng)
            if L["phase"] == "regular" and L["day"] == 3:
                race = LG.award_race(L)
                assert race["MVP"], "award race populated"
            if L.get("allstar") and L["allstar"]["status"] == "ready":
                FR.allstar_run(L, rng)
        po = L["history"][-1]
        playoffs = [t for t in L["teams"] if t["hist"][-1]["res"] != "Lottery"]
        assert len(playoffs) == 4, len(playoffs)
        assert not L["settings"]["conf"]
        if cfg["committee"]:
            assert L["rankings"] and L["rankings"][-1]["final"]
        out.append(f'  season {L["season"]}: field {len(playoffs)}, rounds {len(set(r for r in [s["rd"] for s in []]))}'
                   f' champ {L["teams"][po["champ"]]["abbr"]}, MVP {po["names"].get(str(po["awards"].get("MVP")))}, '
                   f'user res {po["user"]["res"]}')
        for pid in list(L["resign"]):
            LG.user_resign(L, pid, 2)
        LG.advance_season(L, rng)
        assert L["draft"]["lottery"], "lottery ran"
        check_schedule(L)
    # scouting
    pros = [p for p in L["players"].values() if p["tid"] == -2 and p.get("prospect")]
    p0 = pros[0]
    before = P.scout_report(p0, 0)
    L["scout"]["pts"] = 99
    after = OF.scout(L, p0["id"])
    assert len(after["known"]) > len(before["known"])
    assert after["ovr"][1] - after["ovr"][0] <= before["ovr"][1] - before["ovr"][0]
    lo, hi = after["ovr"]
    assert lo <= P.stars_for(p0["ovr"]) <= hi, (lo, P.stars_for(p0["ovr"]), hi)
    out.append(f'  scouting: {len(before["known"])}->{len(after["known"])} attrs, OVR {before["ovr"]}->{after["ovr"]}'
               f' (true {P.stars_for(p0["ovr"])}), POT {before["pot"]}->{after["pot"]} (true {P.stars_for(p0["pot"])})')
    act = [p for p in L["players"].values() if p["tid"] >= 0]
    d = sorted((P.stars_for(p["ovr"]) for p in act), reverse=True)
    out.append(f'  stars: 5.0 x{sum(1 for x in d if x == 5)}, 4.5 x{sum(1 for x in d if x == 4.5)}, median {d[len(d) // 2]}, '
               f'AI upgrades bought {sum(sum(t["upg"].values()) for t in L["teams"] if t["tid"] != u)}')
    return out


if __name__ == "__main__":
    for i, cfg in enumerate(CONFIGS):
        for line in run(cfg, 100 + i):
            print(line)
    print("ALL CONFIGS OK")
