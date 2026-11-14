"""Headless league test: 20 teams, 8-team playoffs (BO3 rounds, BO5 Finals), lottery day, team options,
fog-based drafting, aging. python test/configtest.py"""
import os
import random
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from nd import league as LG, players as P, franchise as FR  # noqa: E402
from nd.data import SEASON_DAYS  # noqa: E402


def check_schedule(L):
    sched = L["schedule"]
    assert len(sched) == SEASON_DAYS
    seen = set()
    for day in sched:
        teams = sorted([g["h"] for g in day] + [g["a"] for g in day])
        assert teams == list(range(20)), "every team plays every day"
        for g in day:
            k = (min(g["h"], g["a"]), max(g["h"], g["a"]))
            assert k not in seen, "no rematches"
            seen.add(k)


def run(start, seed):
    rng = random.Random(seed)
    L = LG.new_league("T", rng.randrange(20), settings={"start": start, "teams": 12, "committee": True}, seed=seed)
    assert len(L["teams"]) == 20 and not L["settings"]["committee"] and L["settings"]["playoff"] == 8
    u = L["user"]
    out = [f"{start} seed {seed}:"]
    for season in range(2):
        check_schedule(L)
        LG.draft_until_user(L, rng, include_user=True)
        while len(LG.roster(L, u)) > 15:
            LG.user_release(L, min(LG.roster(L, u), key=lambda p: p["ovr"])["id"])
        while L["phase"] in ("regular", "playoffs"):
            LG.sim_day(L, rng)
            if L.get("allstar") and L["allstar"]["status"] == "ready":
                FR.allstar_run(L, rng)
            if L["phase"] == "playoffs" and L["playoffs"]:
                for s in L["playoffs"]["series"]:
                    need = 3 if s["rd"] == L["playoffs"]["rounds"] else 2
                    assert s["need"] == need and max(s["w"]) <= need and sum(s["w"]) <= 2 * need - 1, s
        po = L["playoffs"]
        rounds = Counter(s["rd"] for s in po["series"])
        fin = [s for s in po["series"] if s["rd"] == 3][0]
        assert rounds == {1: 4, 2: 2, 3: 1}, rounds
        assert max(fin["w"]) == 3 and all(max(s["w"]) == 2 for s in po["series"] if s["rd"] < 3)
        for s in po["series"]:   # the team with more wins advances
            assert s["winner"] == (s["hi"] if s["w"][0] > s["w"][1] else s["lo"]), s
            if s["rd"] < 3:
                assert any(s["winner"] in (x["hi"], x["lo"]) for x in po["series"] if x["rd"] == s["rd"] + 1), s
        h = L["history"][-1]
        out.append(f'  {h["s"]}: champ {L["teams"][h["champ"]]["abbr"]} finals {fin["w"]} | '
                   f'rounds {dict(rounds)} | user {h["user"]["res"]}')
        # lottery day happens in the offseason, before the draft
        assert L["phase"] == "offseason" and not (L.get("lottery") and L["lottery"]["season"] == L["season"] + 1)
        lot = LG.run_lottery(L, rng)
        assert len(lot["order"]) == 20 and len(lot["lottery"]) == 12
        movers = [x for x in lot["lottery"] if x["pick"] < x["seed"]]
        out.append(f'  lottery {lot["season"]}: #1 {L["teams"][lot["order"][0]]["abbr"]} (seed '
                   f'{next(x["seed"] for x in lot["lottery"] if x["pick"] == 1)}), {len(movers)} jumped up')
        for pid in list(L.get("options", [])):
            LG.user_team_option(L, pid, True)
            out.append(f'  exercised team option on {P.full_name(LG.pl(L, pid))}: {LG.pl(L, pid)["contract"]}')
        for pid in list(L["resign"]):
            try:
                LG.user_resign(L, pid, 2)
            except LG.GameError:
                pass
        LG.advance_season(L, rng)
        assert L["draft"]["lottery"] == lot["lottery"], "draft uses the lottery-day order"
        opts = sum(1 for p in L["players"].values() if (p.get("contract") or {}).get("opt"))
        out.append(f'  players on deals with a team option: {opts}')
    return out


def aging_check():
    rng = random.Random(7)
    by_age = defaultdict(list)
    dage = Counter()
    for i in range(6000):
        age = rng.randint(24, 36)
        p = P.generate(rng, 900000 + i, rng.uniform(55, 85), age)
        dage[p["decline_age"]] += 1
        before = P.stars_for(p["ovr"])
        P.develop(p, rng, 0, 0, rng.uniform(-1, 1))
        by_age[age].append(P.stars_for(p["ovr"]) - before)
    print("decline ages assigned:", dict(sorted(dage.items())))
    print("avg star change by age:", {a: round(sum(v) / len(v), 2) for a, v in sorted(by_age.items())})
    # decline phase: change = -0.12 constant +/-0.15 random +/-0.15 performance (raw points are whole numbers)
    res = {}
    for perf in (1.0, 0.0, -1.0):
        d = []
        for i in range(3000):
            p = P.generate(rng, 960000 + i, rng.uniform(55, 85), 33)
            p["decline_age"] = 31
            b = p["ovr"]
            P.develop(p, random.Random(i), 0, 0, perf)
            d.append((p["ovr"] - b) / P.STAR_RAW)
        lo, hi, avg = min(d), max(d), sum(d) / len(d)
        exp = -0.12 + 0.15 * perf
        assert abs(avg - exp) < 0.02 and lo >= exp - 0.15 - 0.05 and hi <= exp + 0.15 + 0.05, (perf, lo, avg, hi)
        res[perf] = d
        print(f"decline phase, perf {perf:+.0f}: avg {avg:+.2f} stars, range {lo:+.2f}..{hi:+.2f}, "
              f"{sum(x > 0 for x in d) / len(d):.0%} improved, {sum(x == 0 for x in d) / len(d):.0%} unchanged")
    pre = []
    for i in range(3000):
        p = P.generate(rng, 990000 + i, 70, 28)
        p["decline_age"] = 32
        b = p["ovr"]
        P.develop(p, random.Random(i), 0, 0, 1.0)
        P.develop(dict(p, a=dict(p["a"])), random.Random(i), 0, 0, -1.0)
        pre.append(p["ovr"] - b)
    print(f"age 28 (before decline): avg change {sum(pre) / len(pre) / P.STAR_RAW:+.2f} stars (performance ignored)")


if __name__ == "__main__":
    for start, seed in (("classic", 101), ("fantasy", 202)):
        print("\n".join(run(start, seed)))
    aging_check()
    print("ALL OK")
