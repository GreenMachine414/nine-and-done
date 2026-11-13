"""Headless league test: auto-plays seasons and prints realism stats.
Usage: python test/simtest.py [seasons] [mode]"""
import os
import random
import sys
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from nd import league as LG, trade as TR, players as P  # noqa: E402


def run(seasons=3, mode="classic", seed=1):
    rng = random.Random(seed)
    L = LG.new_league("Test", 0, mode, seed=seed)
    t0 = time.time()
    tot = dict(pts=0, fga=0, fgm=0, tpa=0, tpm=0, fta=0, ftm=0, orb=0, drb=0, ast=0, stl=0, blk=0, tov=0, pf=0)
    games = 0
    ots = 0
    margins = []
    mins = []
    shares = []
    st_min = []
    for s in range(seasons):
        LG.draft_until_user(L, rng, include_user=True)
        assert L["phase"] == "regular", L["phase"]
        # user team: trim roster if needed
        while len(LG.roster(L, 0)) > 15:
            worst = min(LG.roster(L, 0), key=lambda p: p["ovr"])
            LG.user_release(L, worst["id"])
        if s == 0:
            # exercise trade machinery
            me = sorted(LG.roster(L, 0), key=lambda p: -p["ovr"])
            L["block"]["players"] = [me[3]["id"]]
            offers = TR.block_offers(L, rng)
            print("block offers:", [(o["tid"], o["get"], o["value_to_you"]) for o in offers])
            ev = TR.evaluate(L, 1, {"players": [me[0]["id"]], "picks": []},
                             {"players": [max(LG.roster(L, 1), key=lambda p: p["ovr"])["id"]], "picks": []})
            print("star-for-star eval:", {k: ev[k] for k in ("accept", "msg", "recv", "send", "meter")})
        while L["phase"] in ("regular", "playoffs"):
            docs, ug = LG.sim_day(L, rng)
            for d in docs:
                games += 1
                ots += d["ot"] > 0
                margins.append(abs(d["hs"] - d["as"]))
                tm = {}
                for pid, r in d["box"].items():
                    for k in tot:
                        tot[k] += r[k]
                    tm[r["tid"]] = tm.get(r["tid"], 0) + r["min"]
                    mins.append(r["min"])
                for tid in (d["h"], d["a"]):
                    rows = sorted([r for r in d["box"].values() if r["tid"] == tid], key=lambda r: -r["fga"])
                    shares.append(rows[0]["fga"] / max(1, sum(r["fga"] for r in rows)))
                    st_min.extend(r["min"] for r in rows if r["gs"])
                for v in tm.values():
                    assert abs(v - (240 + 25 * d["ot"])) < 1, (v, d["ot"])
        h = L["history"][-1]
        print(f'Season {h["s"]}: champ {L["teams"][h["champ"]]["abbr"]} over {L["teams"][h["runner"]]["abbr"]} '
              f'{h["fin"]}  MVP {h["names"].get(str(h["awards"].get("MVP")))}')
        # leaders
        key = str(h["s"])
        ps = [(p, LG.per_game(p["stats"][key])) for p in L["players"].values() if key in p["stats"]
              and p["stats"][key]["gp"] >= 5]
        for stat in ("pts", "reb", "ast"):
            top = sorted(ps, key=lambda x: -x[1][stat])[:3]
            print(f"  {stat}: " + ", ".join(f'{P.short_name(p)} {pg[stat]:.1f} ({p["ovr"]})' for p, pg in top))
        rep = L["offseason"]["report"]
        print("  progression sample:", [(r["before"], r["after"]) for r in rep[:8]])
        print("  payrolls:", [LG.payroll(L, t) for t in range(10)])
        for pid in list(L["resign"]):
            LG.user_resign(L, pid, 2)
        LG.advance_season(L, rng)
    tg = games * 2
    print(f"\n{games} games in {time.time() - t0:.1f}s  OT games: {ots}")
    print(f"PPG/team {tot['pts'] / tg:.1f}  FG% {tot['fgm'] / tot['fga']:.3f}  3P% {tot['tpm'] / tot['tpa']:.3f} "
          f"3PA {tot['tpa'] / tg:.1f}  FGA {tot['fga'] / tg:.1f}  FT% {tot['ftm'] / tot['fta']:.3f} "
          f"FTA {tot['fta'] / tg:.1f}")
    print(f"REB {(tot['orb'] + tot['drb']) / tg:.1f} (OREB {tot['orb'] / tg:.1f})  AST {tot['ast'] / tg:.1f}  "
          f"STL {tot['stl'] / tg:.1f}  BLK {tot['blk'] / tg:.1f}  TOV {tot['tov'] / tg:.1f}  PF {tot['pf'] / tg:.1f}")
    margins.sort()
    print(f"median margin {margins[len(margins) // 2]}  max min {max(mins):.1f}")
    print(f"top FGA share {sum(shares)/len(shares):.3f}  starter avg min {sum(st_min)/len(st_min):.1f}")
    print("state size KB:", len(json.dumps(L)) // 1024)
    print("stars dist:", {s: sum(1 for p in L["players"].values() if p["tid"] >= 0 and p["stars"] == s)
                          for s in range(1, 6)})


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 3, sys.argv[2] if len(sys.argv) > 2 else "classic")
