"""Possession-by-possession game engine.

Each possession: clock burn -> turnover check -> foul check -> shooter selection (usage x quality x
strategy, so stars get the ball more) -> shot type from tendencies -> assist -> block / foul / make
from attribute matchups -> rebound battle. Players tire, sub on energy + rotation priority, get in
foul trouble, get hurt, and coaches go to crunch-time / garbage-time lineups.

Layered on top: momentum + timeouts, team chemistry and player morale, rivalry intensity, franchise
upgrades, and timed modifiers produced by the user's live-coaching challenges.

The game can be played straight through (play()) or stepped in chunks (start() + run_chunk()) so a
human can coach between chunks.
"""
import math
import random

from .players import POS, short_name
from .data import INJURIES

STAT_KEYS = ["pts", "fgm", "fga", "tpm", "tpa", "ftm", "fta", "orb", "drb", "ast", "stl", "blk", "tov", "pf"]

DEFAULT_STRAT = {"pace": "normal", "focus": "balanced", "star": "normal", "defense": "normal", "rotation": "standard"}
PACE_SECS = {"slow": 17.2, "normal": 15.2, "fast": 13.2}
DEPTH = {"tight": 8, "standard": 10, "deep": 11}
ZONES = ["three", "mid", "rim", "post"]
ZONE_LABEL = {"three": "3PT", "mid": "Mid-range", "rim": "At the rim", "post": "Post-ups"}
METER_BONUS = {"perfect": 0.16, "good": 0.07, "ok": 0.0, "miss": -0.13}


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def wchoice(rng, items, weights):
    tot = sum(weights)
    if tot <= 0:
        return rng.choice(items)
    r = rng.random() * tot
    for it, w in zip(items, weights):
        r -= w
        if r <= 0:
            return it
    return items[-1]


def meter_grade(acc, coaching_lvl=0):
    """acc = 0 (dead center) .. 1 (edge of the bar). The green window widens with the coaching upgrade."""
    w = 0.16 * (1 + 0.12 * coaching_lvl)
    if acc <= w * 0.3:
        return "perfect"
    if acc <= w:
        return "good"
    if acc <= w * 2.2:
        return "ok"
    return "miss"


class GP:
    """A player inside one game."""

    def __init__(self, p, side, slot):
        self.p = p
        self.id = p["id"]
        self.a = p["a"]
        self.t = p["t"]
        self.pi = POS.index(p["pos"])
        self.ovr = p["ovr"]
        self.side = side
        self.slot = slot
        self.energy = 100.0
        self.fouls = 0
        self.s = dict.fromkeys(STAT_KEYS, 0)
        self.z = {z: [0, 0] for z in ZONES}   # made, attempted per zone
        self.sec = 0.0
        self.pm = 0
        self.on = False
        self.started = False
        self.injured = None
        self.name = short_name(p)
        self.trait = p.get("trait")
        m = p.get("morale", 65)
        self.mood = (m - 66) / 40 * (0.5 if self.trait == "Professional" else 1.0)
        self.hold_in = -1.0     # coach-locked on the floor until this elapsed time
        self.hold_out = -1.0    # coach-locked on the bench until this elapsed time

    def fat(self):
        return 0.80 + 0.20 * (self.energy / 100.0)

    def r(self, k):
        return self.a[k] * self.fat()

    def avail(self):
        return self.fouls < 6 and self.injured is None


class Team:
    def __init__(self, t, roster, side, chem=60):
        self.t = t
        self.tid = t["tid"]
        self.side = side
        self.strat = {**DEFAULT_STRAT, **(t.get("strategy") or {})}
        order = {pid: i for i, pid in enumerate(t.get("lineup") or [])}
        roster = sorted(roster, key=lambda p: (order.get(p["id"], 99), -p["ovr"]))
        self.players = [GP(p, side, i) for i, p in enumerate(roster)]
        self.on = []
        self.fouls_q = 0
        self.depth = DEPTH.get(self.strat["rotation"], 10)
        best = sorted(self.players, key=lambda g: -g.ovr)
        self.stars = {g.id for g in best[:2]}
        self.top = best[0].id if best else None
        self.upg = dict(t.get("upg") or {})
        coach = self.upg.get("coaching", 0)
        self.timeouts = 4 + (coach >= 2) + (coach >= 4)
        self.mo = 0.0            # momentum, -1..1
        self.mods = []           # timed modifiers from coaching challenges
        self.chem = chem
        self.zpts = dict.fromkeys(ZONES, 0)
        self.zfga = dict.fromkeys(ZONES, 0)
        self.zfgm = dict.fromkeys(ZONES, 0)
        self.last_to = -999.0

    def lvl(self, k):
        return self.upg.get(k, 0)

    def mod(self, kind, now, pid=None, zone=None):
        v = 0.0
        for m in self.mods:
            if m["k"] != kind or m["until"] < now:
                continue
            if pid is not None and m.get("pid") not in (None, pid):
                continue
            if zone is not None and m.get("z") not in (None, zone):
                continue
            v += m["v"]
        return v

    def mod_weight(self, kind, now, pid=None, zone=None):
        w = 1.0
        for m in self.mods:
            if m["k"] == kind and m["until"] >= now and (pid is None or m.get("pid") == pid) and \
                    (zone is None or m.get("z") == zone):
                w *= m.get("w", 1.0)
        return w


class Game:
    def __init__(self, home_t, home_roster, away_t, away_roster, rng=None, record=False, playoff=False, opts=None):
        opts = opts or {}
        self.rng = rng or random.Random()
        chem = opts.get("chem") or [60, 60]
        self.T = [Team(home_t, home_roster, 0, chem[0]), Team(away_t, away_roster, 1, chem[1])]
        self.rival = opts.get("rival", 0)          # 0..3 rivalry intensity
        self.exhibition = opts.get("exhibition", False)
        self.live_side = opts.get("live_side")      # side index the human is coaching, or None
        self.avg_upg = opts.get("avg_upg") or {}    # league-average upgrade levels (edges are relative)
        self.score = [0, 0]
        self.q = 1
        self.clock = 720.0
        self.qlen = 720.0
        self.elapsed = 0.0
        self.record = record
        self.events = []
        self.qscores = []
        self.playoff = playoff
        self.injuries = []
        self.flow = []
        self.run = [None, 0]          # [side, unanswered points]
        self.done = False
        self.started = False
        self.off, self.mode, self.pb = 0, None, None
        self.q_start = [0, 0]
        self.tip = 0
        self.forced = None
        self.prompted = set()
        self.challenges = []          # results log of live challenges
        self.half_zones = None

    # ------------------------------------------------------------------ helpers
    def ev(self, side, kind, text, deltas=(), shot=None, extra=None):
        if not self.record:
            return
        e = {"e": round(self.elapsed, 1), "q": self.q, "c": round(self.clock, 1), "tm": side, "k": kind,
             "txt": text, "s": list(self.score)}
        if deltas:
            e["d"] = [list(d) for d in deltas]
        if shot:
            e["sh"] = shot
        if extra:
            e.update(extra)
        self.events.append(e)

    def stat(self, gp, k, n=1, deltas=None):
        gp.s[k] += n
        if deltas is not None:
            deltas.append((gp.id, k, n))

    def margin(self, side):
        return self.score[side] - self.score[1 - side]

    def crunch(self):
        return (self.q >= 4 and self.clock <= 300 and abs(self.score[0] - self.score[1]) <= 10) or self.q > 4

    def garbage(self):
        m = abs(self.score[0] - self.score[1])
        return self.q == 4 and ((self.clock <= 420 and m >= 22) or (self.clock <= 240 and m >= 16))

    def by_id(self, pid):
        for t in self.T:
            for g in t.players:
                if g.id == pid:
                    return g
        return None

    # ------------------------------------------------------------------ lineup management
    def start_lineups(self):
        for team in self.T:
            healthy = [g for g in team.players if g.avail()]
            starters = healthy[:5]
            for g in starters:
                g.on = True
                g.started = True
            team.on = starters

    def foul_trouble(self, g):
        if self.q >= 4 and self.clock <= 360:
            return False
        lim = {1: 2, 2: 3, 3: 4, 4: 5}.get(self.q, 6)
        return g.fouls >= lim

    def swap(self, team, out, inn, manual=False):
        out.on = False
        inn.on = True
        team.on[team.on.index(out)] = inn
        self.ev(team.side, "sub", f"{inn.name} checks in for {out.name}" + (" (coach's call)" if manual else ""),
                extra={"out": out.id, "in": inn.id})

    def subs(self, team):
        now = self.elapsed
        crunch = self.crunch()
        garbage = self.garbage()
        bench = [g for g in team.players if not g.on and g.avail() and g.hold_out < now]
        if garbage and team.side != self.live_side:
            deep = sorted([g for g in bench if g.slot >= 5], key=lambda g: -g.slot)
            for g in sorted(team.on, key=lambda g: g.slot):
                if not deep:
                    break
                if g.slot < 5:
                    self.swap(team, g, deep.pop(0))
            return
        for g in sorted(team.on, key=lambda g: g.energy):
            forced = not g.avail()
            if g.hold_in >= now and not forced:
                continue
            thresh = 35 if crunch else (60 if g.slot < 5 else 67 if g.slot < 8 else 72)
            trouble = self.foul_trouble(g) and not crunch
            if not (forced or trouble or g.energy < thresh):
                continue
            cands = [b for b in bench if b.slot < team.depth or forced or len(bench) < 3]
            fresh = [b for b in cands if b.energy >= 80 and not self.foul_trouble(b)]
            pool = fresh or (cands if (forced or trouble) else [])
            if not pool:
                if forced:   # nobody legal on the bench: bring anyone healthy back
                    pool = [b for b in team.players if not b.on and b.avail()]
                if not pool:
                    continue
            best = max(pool, key=lambda b: b.ovr - 4.5 * abs(b.pi - g.pi) + (b.energy - 80) * 0.25
                       - b.slot * 0.6)
            self.swap(team, g, best)
            if best in bench:
                bench.remove(best)
            if g.avail():
                bench.append(g)
        for b in sorted(bench, key=lambda b: b.slot):
            if b.on or b.energy < (55 if crunch else 88) or self.foul_trouble(b) or b.slot >= team.depth:
                continue
            worse = [g for g in team.on if g.slot > b.slot and abs(g.pi - b.pi) <= 1 and g.hold_in < now]
            if crunch:
                worse = [g for g in team.on if g.slot > b.slot and g.hold_in < now] or worse
            if not worse:
                continue
            x = max(worse, key=lambda g: g.slot)
            if crunch or x.energy < 92 or x.slot >= 5:
                self.swap(team, x, b)

    # ------------------------------------------------------------------ clock
    def burn(self, t):
        t = min(t, self.clock)
        self.clock -= t
        self.elapsed += t
        for team in self.T:
            cond = team.lvl("conditioning")
            drain_mult = (1 - 0.045 * cond) * (1 + 0.04 * self.rival)
            rec = 0.06 * (1 + 0.06 * cond)
            for g in team.players:
                if g.on:
                    g.sec += t
                    g.energy = max(15.0, g.energy - t * (0.045 + (100 - g.a["sta"]) * 0.0006) * drain_mult)
                else:
                    g.energy = min(100.0, g.energy + t * rec)
        for team in self.T:
            team.mo *= 0.94 ** (t / 14)
        return t

    def add_points(self, side, n):
        self.score[side] += n
        for g in self.T[side].on:
            g.pm += n
        for g in self.T[1 - side].on:
            g.pm -= n
        hot = 1.25 if any(g.trait == "Hothead" for g in self.T[side].on) else 1.0
        swing = n * 0.035 * hot * (1 + 0.15 * self.rival)
        self.T[side].mo = clamp(self.T[side].mo + swing, -1, 1)
        self.T[1 - side].mo = clamp(self.T[1 - side].mo - n * 0.035, -1, 1)
        if self.run[0] == side:
            self.run[1] += n
        else:
            self.run = [side, n]
            self.prompted.discard("run")

    # ------------------------------------------------------------------ timeouts
    def timeout(self, side, auto=False):
        team = self.T[side]
        if team.timeouts <= 0:
            return False
        team.timeouts -= 1
        team.last_to = self.elapsed
        self.last_to_run = self.run[1] if self.run[0] == 1 - side else 0   # what the huddle is reacting to
        for g in team.players:
            g.energy = min(100.0, g.energy + (8 if g.on else 3))
        self.T[1 - side].mo = 0.0
        team.mo = max(team.mo, 0.0)
        if self.run[0] == 1 - side:
            self.run = [None, 0]
        self.ev(side, "timeout", f"Timeout, {team.t['abbr']}" + (f" ({team.timeouts} left)." if not auto else "."))
        return True

    def ai_timeouts(self):
        for team in self.T:
            if team.side == self.live_side or self.exhibition:
                continue
            opp = 1 - team.side
            if self.run[0] == opp and self.run[1] >= 8 and team.timeouts > 1 and \
                    self.elapsed - team.last_to > 150 and self.clock > 20:
                self.timeout(team.side, auto=True)

    # ------------------------------------------------------------------ sub-actions
    def free_throws(self, side, shooter, n, deltas):
        pct = clamp(0.42 + shooter.a["ft"] * 0.0052, 0.35, 0.95)
        if side == 1:
            pct -= 0.01 * self.T[0].lvl("arena") + 0.008 * self.rival
        if self.crunch():
            pct = clamp(pct + (shooter.p.get("clutch", 50) - 50) * 0.0008, 0.3, 0.96)
        made = 0
        last_miss = False
        for i in range(n):
            self.stat(shooter, "fta", 1, deltas)
            if self.rng.random() < pct:
                self.stat(shooter, "ftm", 1, deltas)
                self.stat(shooter, "pts", 1, deltas)
                self.add_points(side, 1)
                made += 1
                last_miss = False
            else:
                last_miss = True
        return made, last_miss

    def personal_foul(self, team, g, deltas):
        g.fouls += 1
        self.stat(g, "pf", 1, deltas)
        team.fouls_q += 1
        if g.fouls >= 6:
            self.ev(team.side, "info", f"{g.name} has fouled out.")

    def pick_fouler(self, D):
        return wchoice(self.rng, D, [(130 - g.a["iq"]) * (1.6 if g.trait == "Hothead" else 1) for g in D])

    def rebound(self, o, ftmiss=False, blocked=False, three=False):
        O, D = self.T[o].on, self.T[1 - o].on
        ro = sum(g.r("reb") for g in O) / 5
        rd = sum(g.r("reb") for g in D) / 5
        p = 0.235 + (ro - rd) * 0.0055 + (0.012 if three else 0) - (0.06 if blocked else 0)
        p -= self.T[1 - o].mod("dreb", self.elapsed)
        if ftmiss:
            p -= 0.11
        p = clamp(p, 0.06, 0.40)
        if self.rng.random() < p:
            g = wchoice(self.rng, O, [g.r("reb") ** 2.0 * (1 + g.pi * 0.12) for g in O])
            return o, g, True
        g = wchoice(self.rng, D, [g.r("reb") ** 2.0 * (1 + g.pi * 0.12) for g in D])
        return 1 - o, g, False

    def check_injuries(self):
        if self.exhibition:
            return
        for team in self.T:
            med = team.lvl("medical")
            for g in team.on:
                if g.injured:
                    continue
                if self.rng.random() < 0.00013 * (1 + (100 - g.p.get("dur", 75)) / 60) * (1 - 0.12 * med):
                    inj = wchoice(self.rng, INJURIES, [i[3] for i in INJURIES])
                    games = max(0, self.rng.randint(inj[1], inj[2]) - ((med + 1) // 2 if med else 0))
                    g.injured = {"type": inj[0], "games": games}
                    self.injuries.append((g.p, inj[0], games))
                    self.ev(team.side, "inj", f"{g.name} is down — {inj[0]}. He heads to the locker room.")

    # ------------------------------------------------------------------ possession
    def possession(self, o, mode=None, putback=None):
        """Run one possession for side o. Returns (next_side, mode, putback_player)."""
        rng = self.rng
        d = 1 - o
        OT, DT = self.T[o], self.T[d]
        O, D = OT.on, DT.on
        so, sd = OT.strat, DT.strat
        deltas = []
        now = self.elapsed
        forced = self.forced if (self.forced and o == self.live_side and mode != "putback") else None
        if forced:
            self.forced = None

        late = (self.q >= 4 and self.clock <= 40)
        if not forced and late and self.margin(d) < 0 and -9 <= self.margin(d) <= -1 and mode != "putback" \
                and self.clock > 1:
            self.burn(rng.uniform(1.5, 4.0))
            fouled = max(O, key=lambda g: g.r("hand") + rng.random() * 10)
            fouler = rng.choice(D)
            self.personal_foul(DT, fouler, deltas)
            _, miss = self.free_throws(o, fouled, 2, deltas)
            self.ev(o, "ft", f"{fouler.name} fouls {fouled.name} intentionally. {fouled.name} to the line.", deltas)
            return self.after_ft(o, miss)

        # ---- time burn
        if forced:
            t = max(0.5, self.clock - rng.uniform(0.8, 2.6)) if self.clock <= 24 else rng.uniform(14, 20)
        elif mode == "putback":
            t = rng.uniform(1.0, 3.5)
        elif mode == "trans":
            t = rng.uniform(3.5, 8.5)
        elif mode == "reset":
            t = clamp(rng.gauss(9, 3.5), 3, 14)
        else:
            mean = PACE_SECS[so["pace"]] * 0.78 + PACE_SECS[sd["pace"]] * 0.22
            t = clamp(rng.gauss(mean, 4.2), 5, 24)
            if self.q >= 4 and self.clock <= 70 and self.margin(o) > 0:
                t = clamp(rng.gauss(21, 1.5), 15, 24)
        heave = False
        if t >= self.clock:
            t = self.clock
            heave = t < 3.0 and mode != "putback" and not forced
        self.burn(t)
        now = self.elapsed
        late_clock = t >= 20 and not forced

        # ---- turnover
        handler = putback or wchoice(rng, O, [(g.r("hand") + g.r("pass")) ** 2 * (1.3 if g.pi == 0 else 1)
                                              for g in O])
        if mode != "putback" and not heave and not forced:
            dstl = sum(g.r("stl") for g in D) / 5
            to_p = 0.128 + (dstl - 60) * 0.0016 - ((handler.r("hand") + handler.r("pass")) / 2 - 65) * 0.0019
            to_p += {"aggressive": 0.022, "conservative": -0.014}.get(sd["defense"], 0)
            to_p += (0.02 if late_clock else 0) - (0.02 if mode == "trans" else 0)
            to_p -= (OT.chem - 72) / 40 * 0.01
            to_p += OT.mod("tov", now)
            if rng.random() < clamp(to_p, 0.05, 0.24):
                self.stat(handler, "tov", 1, deltas)
                r = rng.random()
                steal_p = 0.52 + (dstl - 60) * 0.006 + (0.08 if sd["defense"] == "aggressive" else 0)
                if r < steal_p:
                    stealer = wchoice(rng, D, [g.r("stl") ** 3 for g in D])
                    self.stat(stealer, "stl", 1, deltas)
                    self.ev(o, "to", f"{stealer.name} picks off {handler.name}! Steal.", deltas)
                    DT.mo = clamp(DT.mo + 0.06, -1, 1)
                    return d, "trans", None
                if r < steal_p + 0.10:
                    self.personal_foul(OT, handler, deltas)
                    OT.fouls_q -= 1
                    self.ev(o, "to", f"Offensive foul on {handler.name}.", deltas)
                    return d, None, None
                msg = rng.choice(["throws it away", "steps out of bounds", "is called for traveling",
                                  "loses the handle"]) if not late_clock else "— shot clock violation"
                self.ev(o, "to", f"{handler.name} {msg}. Turnover.", deltas)
                return d, None, None

        # ---- non-shooting defensive foul
        fmult = {"aggressive": 1.35, "conservative": 0.75}.get(sd["defense"], 1.0) * (1 + 0.06 * self.rival)
        if self.exhibition:
            fmult *= 0.5
        if mode != "putback" and not heave and not forced and rng.random() < 0.07 * fmult:
            fouler = self.pick_fouler(D)
            self.personal_foul(DT, fouler, deltas)
            if DT.fouls_q >= 5:
                fouled = wchoice(rng, O, [g.t["use"] for g in O])
                _, miss = self.free_throws(o, fouled, 2, deltas)
                self.ev(o, "ft", f"Foul on {fouler.name} (bonus). {fouled.name} shoots two.", deltas)
                return self.after_ft(o, miss)
            self.ev(o, "foul", f"Reach-in foul on {fouler.name}.", deltas)
            deltas = []

        # ---- choose shooter + shot type
        passer = None
        stype = None
        if forced:
            call = forced["call"]
            if call == "iso":
                shooter = max(O, key=lambda g: g.ovr)
                tw = {z: shooter.t[z] for z in ("three", "mid", "rim")}
                stype = max(tw, key=tw.get)
            elif call == "three":
                shooter = max(O, key=lambda g: g.r("three"))
                stype = "three"
            elif call == "pnr":
                shooter = max(O, key=lambda g: g.r("ins") + g.r("ath") * 0.5)
                stype = "rim"
            else:
                shooter = max(O, key=lambda g: g.r("post") + g.r("ins") * 0.3)
                stype = "post"
            if call in ("three", "pnr"):
                mates = [g for g in O if g is not shooter]
                passer = max(mates, key=lambda g: g.r("pass"))
        elif putback:
            shooter = putback
        else:
            star_mult = {"share": 0.8, "normal": 1.0, "heliocentric": 1.45}.get(so["star"], 1.0)
            ws = []
            for g in O:
                w = (max(6, g.t["use"]) / 50.0) ** 0.75 * (g.ovr / 65.0) ** 1.12 * (0.6 + 0.4 * g.fat())
                if g.id == OT.top:
                    w *= star_mult
                elif g.id in OT.stars:
                    w *= (1 + (star_mult - 1) * 0.4)
                if self.crunch() and g.id in OT.stars:
                    w *= 1.25 + (g.p.get("clutch", 50) - 50) / 200
                if g.trait == "Diva":
                    w *= 1.12
                w *= DT.mod_weight("focus_def", now, pid=g.id) * OT.mod_weight("pw", now, pid=g.id)
                ws.append(w)
            shooter = wchoice(rng, O, ws)

        os_ = sorted(O, key=lambda g: (g.pi, g.slot))
        ds_ = sorted(D, key=lambda g: (g.pi, g.slot))
        defender = ds_[os_.index(shooter)]
        rim_prot = max(D, key=lambda g: g.r("blk"))

        if stype is None:
            if putback:
                stype = "rim"
            elif heave:
                stype = "heave"
            else:
                f3 = {"inside": 0.72, "perimeter": 1.32}.get(so["focus"], 1.0)
                fi = {"inside": 1.28, "perimeter": 0.84}.get(so["focus"], 1.0)
                w3 = shooter.t["three"] * f3
                wm = shooter.t["mid"] * (1.4 if late_clock else 1)
                wr = shooter.t["rim"] * fi * (1 + clamp((shooter.a["ins"] - defender.a["intd"]) / 90, -0.3, 0.4))
                wp = shooter.t["post"] * fi * (1 + clamp((shooter.a["post"] - defender.a["intd"]) / 80, -0.4, 0.5))
                if mode == "trans":
                    wr *= 2.2
                    w3 *= 1.15
                    wp *= 0.15
                ws = [w3 + 0.5, wm + 0.5, wr + 0.5, wp + 0.1]
                ws = [w * DT.mod_weight("zone_def", now, zone=z) for w, z in zip(ws, ZONES)]
                stype = wchoice(rng, ZONES, ws)

        # ---- assist
        if not passer and stype != "heave" and not putback and not forced:
            base = {"three": 0.94, "mid": 0.56, "rim": 0.72, "post": 0.36}[stype]
            mates = [g for g in O if g is not shooter]
            team_pass = sum(g.r("pass") for g in mates) / 4
            p_ast = base * (0.78 + (team_pass - 58) / 110) * (1 - (shooter.a["hand"] - 60) / 260)
            p_ast *= 1 + (OT.chem - 72) / 400
            if mode == "trans":
                p_ast *= 1.08
            if rng.random() < clamp(p_ast, 0.05, 0.95):
                passer = wchoice(rng, mates, [g.r("pass") ** 2.4 * (g.t["pass"] / 50) for g in mates])

        # ---- make probability
        S, X = shooter, defender
        if stype == "rim":
            p = 0.565 + (S.r("ins") - 65) * 0.0045 + (S.r("ath") - 65) * 0.0015 \
                - (X.r("intd") - 65) * 0.0020 - (rim_prot.r("blk") - 65) * 0.0012
            if mode == "trans":
                p += 0.07
            if putback:
                p += 0.03
        elif stype == "post":
            p = 0.455 + (S.r("post") - 65) * 0.0045 + (S.r("ins") - 65) * 0.001 - (X.r("intd") - 65) * 0.0035
        elif stype == "mid":
            p = 0.39 + (S.r("mid") - 65) * 0.0045 - (X.r("perd") - 65) * 0.0022
        elif stype == "three":
            p = 0.314 + (S.r("three") - 65) * 0.0042 - (X.r("perd") - 65) * 0.0016
        else:
            p = 0.11
        if stype != "heave":
            p += (S.r("iq") - 65) * 0.0008
            p += 0.028 if passer else 0
            if o == 0:
                p += 0.012 + 0.004 * (OT.lvl("arena") - self.avg_upg.get("arena", 0)) + 0.003 * self.rival
            p -= 0.04 if late_clock else 0
            if sd["defense"] == "aggressive" and stype == "three":
                p += 0.012
            if sd["defense"] == "conservative" and stype == "rim":
                p += 0.015
            if self.crunch():
                p += (S.p.get("clutch", 50) - 50) * 0.0011 + (0.01 if S.trait == "Competitor" else 0)
            p += 0.0035 * (OT.lvl("analytics") - self.avg_upg.get("analytics", 0))
            p += OT.mo * 0.025
            p += (OT.chem - 72) / 40 * 0.012
            p += S.mood * 0.012
            p += OT.mod("make", now) + DT.mod("def", now)
            p += DT.mod("zone_def", now, zone=stype) + DT.mod("focus_def", now, pid=S.id)
            p += OT.mod("pmake", now, pid=S.id)
            if forced:
                p += METER_BONUS.get(forced.get("grade"), 0)
        p = clamp(p, 0.06, 0.9)

        pts = 3 if stype in ("three", "heave") else 2
        dist, loc = self.shot_loc(stype)

        # ---- block
        if stype in ("rim", "post"):
            pb = 0.068 + (rim_prot.r("blk") - 65) * 0.0022 - (S.r("ath") - 65) * 0.0008
        elif stype == "mid":
            pb = 0.018
        else:
            pb = 0.006
        if forced:
            pb *= 0.5
        if rng.random() < clamp(pb, 0.003, 0.2):
            if stype in ("rim", "post"):
                blocker = wchoice(rng, D, [g.r("blk") ** 3 * (2 if g is X else 1) for g in D])
            else:
                blocker = X
            self.stat(S, "fga", 1, deltas)
            if pts == 3:
                self.stat(S, "tpa", 1, deltas)
            self.zone_track(OT, S, stype, 0, 0)
            self.stat(blocker, "blk", 1, deltas)
            DT.mo = clamp(DT.mo + 0.05, -1, 1)
            self.ev(o, "miss", f"{blocker.name} {rng.choice(['sends it back', 'rejects', 'swats', 'erases'])} "
                               f"{S.name}'s {self.shot_word(stype, dist)}!", deltas,
                    shot={"x": loc[0], "y": loc[1], "m": 0, "p": S.id})
            return self.after_miss(o, blocked=True, three=pts == 3)

        # ---- shooting foul
        if stype != "heave":
            pf = {"rim": 0.205, "post": 0.16, "mid": 0.05, "three": 0.016}[stype]
            draw = (S.a["ins"] + S.a["ath"]) / 2 if stype in ("rim", "post") else S.a["hand"]
            pf *= (1 + (draw - 65) / 140) * fmult
            if rng.random() < pf:
                fouler = X if rng.random() < 0.7 else (rim_prot if stype == "rim" else rng.choice(D))
                self.personal_foul(DT, fouler, deltas)
                if rng.random() < p * 0.42:
                    self.stat(S, "fgm", 1, deltas)
                    self.stat(S, "fga", 1, deltas)
                    if pts == 3:
                        self.stat(S, "tpm", 1, deltas)
                        self.stat(S, "tpa", 1, deltas)
                    self.stat(S, "pts", pts, deltas)
                    self.zone_track(OT, S, stype, 1, pts)
                    self.add_points(o, pts)
                    if passer:
                        self.stat(passer, "ast", 1, deltas)
                    _, miss = self.free_throws(o, S, 1, deltas)
                    self.ev(o, "make", f"AND-ONE! {S.name} {self.make_word(stype, dist)} through contact from "
                                       f"{fouler.name}" + (f" (ast {passer.name})" if passer else "") + ".",
                            deltas, shot={"x": loc[0], "y": loc[1], "m": 1, "p": S.id})
                    return self.after_ft(o, miss)
                _, miss = self.free_throws(o, S, pts, deltas)
                self.ev(o, "ft", f"{S.name} fouled by {fouler.name} on the {self.shot_word(stype, dist)} — "
                                 f"{pts} free throws.", deltas)
                return self.after_ft(o, miss)

        # ---- the shot
        self.stat(S, "fga", 1, deltas)
        if pts == 3:
            self.stat(S, "tpa", 1, deltas)
        if rng.random() < p:
            self.stat(S, "fgm", 1, deltas)
            if pts == 3:
                self.stat(S, "tpm", 1, deltas)
            self.stat(S, "pts", pts, deltas)
            self.zone_track(OT, S, stype, 1, pts)
            self.add_points(o, pts)
            if passer:
                self.stat(passer, "ast", 1, deltas)
            txt = f"{S.name} {self.make_word(stype, dist)}" + (f" (ast {passer.name})" if passer else "") + "."
            if stype == "heave":
                txt = f"{S.name} launches from {dist} ft at the buzzer... BANG! It counts!"
            if forced:
                txt = "DRAWN UP PERFECTLY — " + txt
            self.ev(o, "make", txt, deltas, shot={"x": loc[0], "y": loc[1], "m": 1, "p": S.id})
            return d, None, None
        self.zone_track(OT, S, stype, 0, 0)
        self.ev(o, "miss", f"{S.name} misses the {self.shot_word(stype, dist)}.", deltas,
                shot={"x": loc[0], "y": loc[1], "m": 0, "p": S.id})
        return self.after_miss(o, three=pts == 3)

    def zone_track(self, team, g, stype, made, pts):
        if stype not in ZONES:
            return
        team.zfga[stype] += 1
        team.zfgm[stype] += made
        team.zpts[stype] += pts
        g.z[stype][1] += 1
        g.z[stype][0] += made

    def after_miss(self, o, blocked=False, three=False, ftmiss=False):
        if self.clock <= 0:
            return 1 - o, None, None
        side, g, off = self.rebound(o, ftmiss=ftmiss, blocked=blocked, three=three)
        deltas = []
        self.stat(g, "orb" if off else "drb", 1, deltas)
        if off:
            putback = g if (g.pi >= 3 or self.rng.random() < 0.25) and self.rng.random() < 0.55 else None
            self.ev(o, "reb", f"Offensive board, {g.name}!", deltas)
            return o, ("putback" if putback else "reset"), putback
        self.ev(side, "reb", f"{g.name} grabs the rebound.", deltas)
        return side, ("trans" if self.rng.random() < 0.18 else None), None

    def after_ft(self, o, last_miss):
        if last_miss:
            return self.after_miss(o, ftmiss=True)
        return 1 - o, None, None

    # ------------------------------------------------------------------ flavor
    def shot_loc(self, stype):
        rng = self.rng
        if stype == "rim":
            dist = rng.uniform(0, 4)
        elif stype == "post":
            dist = rng.uniform(4, 12)
        elif stype == "mid":
            dist = rng.uniform(11, 22)
        elif stype == "three":
            dist = rng.uniform(23.8, 27.5) if rng.random() > 0.22 else 22.2
        else:
            dist = rng.uniform(32, 60)
        if stype == "three" and dist < 23:
            ang = rng.choice([-1, 1]) * rng.uniform(80, 90)
        else:
            ang = rng.uniform(-88, 88)
        x = clamp(dist * math.sin(math.radians(ang)), -24.3, 24.3)
        y = max(dist * math.cos(math.radians(ang)), -4.5)
        if stype in ("three", "heave") and abs(x) >= 22 and y < 9:
            x = 22.3 if x > 0 else -22.3
        return int(round(dist)), [round(x, 1), round(min(y, 44), 1)]

    def shot_word(self, stype, dist):
        return {"rim": "layup", "post": f"{dist}-ft hook", "mid": f"{dist}-ft jumper",
                "three": f"{dist}-ft three", "heave": "heave"}[stype]

    def make_word(self, stype, dist):
        r = self.rng.choice
        if stype == "rim":
            return r(["finishes at the rim", "throws it down", "lays it in", "slams it home", "scoops it in",
                      "flushes the dunk"])
        if stype == "post":
            return r([f"backs down and hits the {dist}-footer", f"spins baseline for {dist}",
                      f"drops in a {dist}-ft hook"])
        if stype == "mid":
            return r([f"pulls up and buries the {dist}-footer", f"knocks down a {dist}-ft jumper",
                      f"fades away from {dist}... good"])
        return r([f"drains a {dist}-ft three", f"splashes it from {dist}", f"buries the triple from {dist} ft",
                  f"hits from deep ({dist} ft)"])

    # ------------------------------------------------------------------ flow control
    def start(self):
        self.started = True
        self.start_lineups()
        self.ev(0, "start", "Tip-off!")
        self.tip = 0 if self.rng.random() < 0.5 else 1
        self.off = self.tip
        self.begin_period()

    def begin_period(self):
        self.qlen = 720.0 if self.q <= 4 else 300.0
        self.clock = self.qlen
        for t in self.T:
            t.fouls_q = 0
        if self.q > 1:
            self.off = self.tip if self.q == 4 else 1 - self.tip
            if self.q > 4:
                self.off = self.rng.randint(0, 1)
            self.ev(0, "q", f"Start of {'Q' + str(self.q) if self.q <= 4 else 'OT' + str(self.q - 4)}.")
        self.q_start = list(self.score)
        self.mode, self.pb = None, None

    def end_period(self):
        self.qscores.append([self.score[0] - self.q_start[0], self.score[1] - self.q_start[1]])
        label = f"Q{self.q}" if self.q <= 4 else f"OT{self.q - 4}"
        self.ev(0, "endq", f"End of {label}: {self.T[0].t['abbr']} {self.score[0]} – "
                           f"{self.T[1].t['abbr']} {self.score[1]}")
        if self.q == 2:
            self.half_zones = [{z: (t.zpts[z], t.zfgm[z], t.zfga[z]) for z in ZONES} for t in self.T]
        if self.q >= 4 and self.score[0] != self.score[1]:
            self.done = True
            return
        bonus = 30 if self.q == 2 else 12
        for t in self.T:
            for g in t.players:
                g.energy = min(100, g.energy + bonus)
            t.mo *= 0.5
        self.q += 1
        self.begin_period()

    def step(self):
        """One possession. Returns True if a period ended."""
        if self.mode != "putback":
            self.ai_timeouts()
            for t in self.T:
                self.subs(t)
        self.off, self.mode, self.pb = self.possession(self.off, self.mode, self.pb)
        self.check_injuries()
        self.flow.append((round(self.elapsed), self.score[0] - self.score[1]))
        if self.clock <= 0:
            self.end_period()
            return True
        return False

    def play(self):
        self.start()
        while not self.done:
            self.step()
        return self.result()

    # ------------------------------------------------------------------ live coaching
    def pending_decision(self):
        """Checks for a moment that should pause a live game for the human coach."""
        side = self.live_side
        if side is None or self.done:
            return None
        if self.q >= 4 and 2.0 < self.clock <= 30 and self.off == side and self.mode != "putback" \
                and abs(self.margin(side)) <= 4 and f"fp{self.q}" not in self.prompted:
            self.prompted.add(f"fp{self.q}")
            return {"type": "final_play", "margin": self.margin(side), "clock": round(self.clock, 1)}
        if self.run[0] == 1 - side and self.run[1] >= 8 and "run" not in self.prompted:
            self.prompted.add("run")
            return {"type": "run", "run": self.run[1], "read": self.def_read_prompt()}
        return None

    def run_chunk(self, secs=45.0):
        """Advance a live game. Stops at chunk end, a period break, a decision point, or the final."""
        if not self.started:
            self.start()
        target = self.elapsed + secs
        while not self.done:
            dec = self.pending_decision()
            if dec:
                return dec
            ended = self.step()
            if self.done:
                break
            if ended:
                return {"type": "break", "q": self.q - 1, "half": self.q == 3,
                        "halftime": self.halftime_prompt() if self.q == 3 else None}
            if self.elapsed >= target:
                return None
        return {"type": "final"}

    def manual_sub(self, side, out_id, in_id):
        team = self.T[side]
        out, inn = self.by_id(out_id), self.by_id(in_id)
        if not out or not inn or not out.on or inn.on or out.side != side or inn.side != side:
            return "Invalid substitution."
        if not inn.avail():
            return f"{inn.name} can't play."
        self.swap(team, out, inn, manual=True)
        inn.hold_in = self.elapsed + 240
        out.hold_out = self.elapsed + 180
        return None

    def set_strategy(self, side, k, v):
        team = self.T[side]
        if k in DEFAULT_STRAT:
            team.strat[k] = v
            team.depth = DEPTH.get(team.strat["rotation"], 10)

    def add_mod(self, side, kind, v, secs, **kw):
        m = {"k": kind, "v": v, "until": self.elapsed + secs}
        m.update(kw)
        self.T[side].mods.append(m)

    # ---- challenge prompts / resolution (correct answers are derived from the game state)
    def def_read_prompt(self):
        side = self.live_side
        opp = self.T[1 - side]
        hot = max(opp.players, key=lambda g: g.s["pts"] + (3 if g.on else 0))
        z = {k: list(v) for k, v in hot.z.items()}
        return {"pid": hot.id, "name": hot.name, "pts": hot.s["pts"], "zones": z}

    def resolve_def_read(self, pid, choice):
        side = self.live_side
        g = self.by_id(pid)
        if not g:
            return {"ok": False, "txt": "Unknown player."}
        att = {k: v[1] for k, v in g.z.items()}
        if sum(att.values()) >= 3:
            inside = att["rim"] + att["post"]
            key = max((("three", att["three"]), ("paint", inside), ("mid", att["mid"])), key=lambda x: x[1])[0]
        else:
            t = g.t
            key = max((("three", t["three"]), ("paint", t["rim"] + t["post"]), ("mid", t["mid"])),
                      key=lambda x: x[1])[0]
        coach = self.T[side].lvl("coaching")
        ok = choice == key
        if ok:
            self.add_mod(side, "focus_def", -0.07 * (1 + 0.1 * coach), 420, pid=pid, w=0.65)
            txt = f"Perfect read. {g.name} is getting blanketed — his looks just got a lot tougher."
        else:
            self.add_mod(side, "focus_def", 0.04, 300, pid=pid, w=1.1)
            right = {"three": "chase him off the line", "paint": "wall off the paint", "mid": "top-lock his pull-ups"}
            txt = f"Wrong coverage — he's still feasting. (You needed to {right[key]}.)"
        self.challenges.append({"type": "def_read", "ok": ok})
        self.ev(side, "coach", f"COACH: {txt}")
        return {"ok": ok, "txt": txt}

    def film_prompt(self):
        side = self.live_side
        if self.half_zones is None:
            return None
        oz = self.half_zones[1 - side]
        return {"zones": {z: {"pts": v[0], "fgm": v[1], "fga": v[2]} for z, v in oz.items()}}

    def resolve_film(self, zone):
        side = self.live_side
        oz = self.half_zones[1 - side]
        best = max(ZONES, key=lambda z: oz[z][0])
        coach = self.T[side].lvl("coaching")
        ok = zone == best
        if ok:
            self.add_mod(side, "zone_def", -0.055 * (1 + 0.1 * coach), 99999, z=zone, w=0.72)
            txt = f"Film session nailed it. You're taking away their {ZONE_LABEL[zone].lower()} in the second half."
        else:
            self.add_mod(side, "zone_def", -0.015, 99999, z=zone, w=0.95)
            self.add_mod(side, "zone_def", 0.025, 99999, z=best, w=1.1)
            txt = f"You sold out on the wrong thing — their {ZONE_LABEL[best].lower()} game is wide open now."
        self.challenges.append({"type": "film", "ok": ok})
        self.ev(side, "coach", f"COACH: {txt}")
        return {"ok": ok, "txt": txt}

    HUDDLE = {
        "fire": "🔥 Fire them up",
        "calm": "🫁 Catch your breath",
        "focus": "📋 Lock in on the details",
        "protect": "🏀 Value every possession",
        "star": "⭐ Ride our hot hand",
        "push": "⚡ Push the pace, they're gassed",
        "boards": "💪 Win the glass",
    }

    def _huddle_facts(self):
        side = self.live_side
        team, opp = self.T[side], self.T[1 - side]
        avg_e = sum(g.energy for g in team.on) / 5
        opp_e = sum(g.energy for g in opp.on) / 5
        hot = max(team.players, key=lambda g: g.s["pts"])
        hot_fg = hot.s["fgm"] / hot.s["fga"] if hot.s["fga"] else 0
        return {"margin": self.margin(side), "energy": round(avg_e), "opp_energy": round(opp_e),
                "run": max(self.run[1] if self.run[0] == 1 - side else 0, getattr(self, "last_to_run", 0)),
                "tov": sum(g.s["tov"] for g in team.players),
                "opp_oreb": sum(g.s["orb"] for g in opp.players),
                "hot": {"pid": hot.id, "name": hot.name, "pts": hot.s["pts"], "fgm": hot.s["fgm"], "fga": hot.s["fga"]},
                "_hot_ok": hot.s["fga"] >= 6 and hot_fg >= 0.5}

    def _huddle_good(self, f):
        good = set()
        if f["energy"] < 72:
            good.add("calm")
        if f["run"] >= 6 or f["margin"] <= -8:
            good.add("fire")
        if f["margin"] >= 8:
            good.add("focus")
        if f["tov"] >= 8:
            good.add("protect")
        if f["_hot_ok"]:
            good.add("star")
        if f["opp_energy"] <= f["energy"] - 8 and f["opp_energy"] < 78:
            good.add("push")
        if f["opp_oreb"] >= 6:
            good.add("boards")
        if not good:
            good.add("fire" if f["margin"] < 0 else "focus")
        return good

    def huddle_prompt(self):
        f = self._huddle_facts()
        good = self._huddle_good(f)
        keys = list(self.HUDDLE)
        pick = [self.rng.choice(sorted(good))]
        others = [k for k in keys if k not in pick]
        self.rng.shuffle(others)
        opts = pick + others[:3]
        self.rng.shuffle(opts)
        out = {k: v for k, v in f.items() if not k.startswith("_")}
        out["options"] = [{"key": k, "label": self.HUDDLE[k] if k != "star" else f"⭐ Ride {f['hot']['name']}"}
                          for k in opts]
        return out

    def resolve_huddle(self, choice):
        side = self.live_side
        team = self.T[side]
        f = self._huddle_facts()
        good = self._huddle_good(f)
        ok = choice in good
        coach = team.lvl("coaching")
        boost = 1 + 0.1 * coach
        txt = ""
        if choice == "fire" and any(g.trait == "Hothead" for g in team.on) and self.rng.random() < 0.3:
            hh = next(g for g in team.on if g.trait == "Hothead")
            hh.fouls += 1
            hh.s["pf"] += 1
            self.T[1 - side].mo = clamp(self.T[1 - side].mo + 0.25, -1, 1)
            txt = f"{hh.name} came out of the huddle too hot — technical foul! "
            ok = False
        if ok:
            team.mo = clamp(team.mo + 0.3, -1, 1)
            self.add_mod(side, "make", 0.02 * boost, 200)
            if choice == "calm":
                for g in team.on:
                    g.energy = min(100, g.energy + 7)
            elif choice == "protect":
                self.add_mod(side, "tov", -0.035 * boost, 300)
            elif choice == "star":
                self.add_mod(side, "pmake", 0.04 * boost, 300, pid=f["hot"]["pid"])
                self.add_mod(side, "pw", 0, 300, pid=f["hot"]["pid"], w=1.4)
            elif choice == "push":
                self.add_mod(side, "make", 0.015 * boost, 240)
            elif choice == "boards":
                self.add_mod(side, "dreb", 0.05 * boost, 300)
            txt += {"fire": "The bench is on its feet. Your guys come out swinging.",
                    "calm": "Deep breaths. Legs are back under them.",
                    "focus": "Locked in. Crisp sets, no wasted possessions.",
                    "protect": "Ball security drilled home. No more gifts.",
                    "star": f"Everything runs through {f['hot']['name']} now — and he's feeling it.",
                    "push": "Run them off the floor. They can't keep up.",
                    "boards": "Bodies on bodies. Nobody gets a second shot."}.get(choice, "That landed.")
        else:
            self.add_mod(side, "make", -0.016, 200)
            reason = []
            if "calm" in good:
                reason.append("they were gassed")
            if "fire" in good:
                reason.append("they needed a jolt")
            if "protect" in good:
                reason.append("the turnovers were killing you")
            if "boards" in good:
                reason.append("you were getting crushed on the glass")
            if "push" in good:
                reason.append("the other team was exhausted")
            if "star" in good:
                reason.append(f"{f['hot']['name']} had the hot hand")
            txt += "That message missed the moment" + (f" — {', and '.join(reason[:2])}." if reason else ".")
        self.last_to_run = 0
        self.challenges.append({"type": "huddle", "ok": ok})
        self.ev(side, "coach", f"COACH: {txt}")
        return {"ok": ok, "txt": txt}

    # ---- halftime adjustments: one of several challenges, picked at random each game
    def halftime_prompt(self):
        side = self.live_side
        kind = self.rng.choice(["film", "matchup", "mismatch", "tempo"])
        team, opp = self.T[side], self.T[1 - side]
        if kind == "film":
            self.half_ctx = {"kind": "film"}
            return {"kind": "film", **(self.film_prompt() or {"zones": {}})}
        if kind == "matchup":
            star = max(opp.players, key=lambda g: g.s["pts"] + g.ovr * 0.05)
            pool = sorted([g for g in team.players if g.avail()], key=lambda g: -g.ovr)[:8]
            cands = []
            for g in (max(pool, key=lambda g: g.a["perd"]), max(pool, key=lambda g: g.a["intd"]),
                      max(pool, key=lambda g: g.ovr)):
                if g not in cands:
                    cands.append(g)
            for g in pool:
                if len(cands) >= 3:
                    break
                if g not in cands:
                    cands.append(g)
            self.half_ctx = {"kind": kind, "star": star.id, "cands": [g.id for g in cands]}
            return {"kind": kind, "star": {"pid": star.id, "name": star.name, "pts": star.s["pts"],
                                           "zones": {k: list(v) for k, v in star.z.items()}},
                    "options": [{"pid": g.id, "name": g.name, "pos": POS[g.pi], "perd": g.a["perd"],
                                 "intd": g.a["intd"]} for g in cands]}
        if kind == "mismatch":
            os_ = sorted(team.on, key=lambda g: (g.pi, g.slot))
            ds_ = sorted(opp.on, key=lambda g: (g.pi, g.slot))
            opts = []
            for g, x in zip(os_, ds_):
                inside = max(g.a["ins"], g.a["post"])
                outside = max(g.a["three"], g.a["mid"])
                edge = max(inside - x.a["intd"], outside - x.a["perd"])
                opts.append({"pid": g.id, "name": g.name, "pos": POS[g.pi], "inside": inside, "outside": outside,
                             "vs": x.name, "vs_perd": x.a["perd"], "vs_intd": x.a["intd"], "_edge": edge})
            self.rng.shuffle(opts)
            opts = opts[:4]
            self.half_ctx = {"kind": kind, "edges": {o["pid"]: o["_edge"] for o in opts}}
            return {"kind": kind, "options": [{k: v for k, v in o.items() if not k.startswith("_")} for o in opts]}
        # tempo
        bench_e = lambda t: sum(g.energy for g in t.players if not g.on and g.avail()) / max(
            1, sum(1 for g in t.players if not g.on and g.avail()))
        depth = lambda t: sum(sorted((g.ovr for g in t.players), reverse=True)[5:9]) / 4
        info = {"margin": self.margin(side), "our_bench": round(depth(team), 1), "their_bench": round(depth(opp), 1),
                "our_energy": round(bench_e(team)), "their_energy": round(bench_e(opp)),
                "our_tov": sum(g.s["tov"] for g in team.players)}
        self.half_ctx = {"kind": kind, **info}
        return {"kind": kind, **info, "options": ["slow", "normal", "fast"]}

    def resolve_halftime(self, choice):
        side = self.live_side
        ctx = getattr(self, "half_ctx", None) or {"kind": "film"}
        kind = ctx["kind"]
        coach = self.T[side].lvl("coaching")
        boost = 1 + 0.1 * coach
        if kind == "film":
            return self.resolve_film(choice)
        if kind == "matchup":
            star = self.by_id(ctx["star"])
            paint = star.z["rim"][1] + star.z["post"][1]
            outside = star.z["three"][1] + star.z["mid"][1]
            attr = "intd" if paint > outside or (paint == outside and star.pi >= 3) else "perd"
            cands = [self.by_id(i) for i in ctx["cands"]]
            try:
                pick = self.by_id(int(choice))
            except (TypeError, ValueError):
                pick = None
            if pick not in cands:
                pick = None
            ok = pick is not None and pick.a[attr] >= max(g.a[attr] for g in cands)
            pick = pick or cands[-1]
            if ok:
                self.add_mod(side, "focus_def", -0.065 * boost, 99999, pid=star.id, w=0.7)
                txt = f"{pick.name} shadows {star.name} all half. Smart assignment."
            else:
                self.add_mod(side, "focus_def", 0.035, 99999, pid=star.id, w=1.1)
                best = max(cands, key=lambda g: g.a[attr])
                txt = f"{star.name} is cooking {pick.name if pick else 'him'}. {best.name} was the better " \
                      f"{'post' if attr == 'intd' else 'perimeter'} defender for that job."
            res_type = "matchup"
        elif kind == "mismatch":
            edges = ctx["edges"]
            try:
                pid = int(choice)
            except (TypeError, ValueError):
                pid = -1
            if pid not in edges:
                pid = min(edges, key=edges.get)
            ok = edges.get(pid, -99) >= max(edges.values())
            g = self.by_id(pid)
            if ok:
                self.add_mod(side, "pmake", 0.045 * boost, 99999, pid=pid)
                self.add_mod(side, "pw", 0, 99999, pid=pid, w=1.35)
                txt = f"You found the soft spot: feed {g.name} his matchup all half."
            else:
                self.add_mod(side, "pw", 0, 99999, pid=pid, w=1.15)
                self.add_mod(side, "make", -0.01, 99999)
                best = self.by_id(max(edges, key=edges.get))
                txt = f"Forcing it to {g.name} gums up the offense. {best.name} had the real mismatch."
            res_type = "mismatch"
        else:
            m = ctx["margin"]
            if ctx["our_energy"] >= ctx["their_energy"] + 5 and ctx["our_bench"] >= ctx["their_bench"]:
                right = "fast"
            elif m >= 6 or ctx["our_tov"] >= 9:
                right = "slow"
            elif m <= -6 and ctx["our_bench"] >= ctx["their_bench"] - 2:
                right = "fast"
            else:
                right = "normal"
            ok = choice == right
            self.set_strategy(side, "pace", choice if choice in PACE_SECS else "normal")
            if ok:
                self.add_mod(side, "make", 0.016 * boost, 99999)
                txt = {"fast": "Run and gun. Your fresher legs take over.",
                       "slow": "Shorten the game, value every trip. Textbook.",
                       "normal": "Stay the course. Your rhythm holds."}[right]
            else:
                self.add_mod(side, "make", -0.012, 99999)
                txt = f"The tempo plan backfires. The situation called for a {right} pace."
            res_type = "tempo"
        self.challenges.append({"type": res_type, "ok": ok})
        self.ev(side, "coach", f"COACH: {txt}")
        return {"ok": ok, "txt": txt}


    def call_final_play(self, call, acc):
        grade = meter_grade(acc, self.T[self.live_side].lvl("coaching"))
        self.forced = {"call": call, "grade": grade}
        self.challenges.append({"type": "final_play", "ok": grade in ("perfect", "good")})
        label = {"iso": "Isolation for the star", "three": "Spread pick-and-pop for three",
                 "pnr": "High pick-and-roll to the rim", "post": "Post entry"}.get(call, call)
        self.ev(self.live_side, "coach", f"COACH: Final play — {label}. Execution: {grade.upper()}.")
        return {"grade": grade}

    # ------------------------------------------------------------------ live snapshot / result
    def snapshot(self):
        return {
            "score": list(self.score), "q": self.q, "clock": round(self.clock, 1), "el": round(self.elapsed, 1),
            "timeouts": [t.timeouts for t in self.T], "mo": [round(t.mo, 2) for t in self.T],
            "on": [[g.id for g in t.on] for t in self.T],
            "players": {g.id: {"e": round(g.energy), "f": g.fouls, "inj": bool(g.injured), "on": g.on,
                               "hold": g.hold_in > self.elapsed}
                        for t in self.T for g in t.players},
            "strat": [dict(t.strat) for t in self.T], "done": self.done,
            "run": self.run,
        }

    def result(self):
        box = {}
        for t in self.T:
            for g in t.players:
                if g.sec <= 0 and not g.started:
                    continue
                row = dict(g.s)
                row["min"] = round(g.sec / 60, 1)
                row["pm"] = g.pm
                row["gs"] = 1 if g.started else 0
                row["tid"] = t.tid
                box[g.id] = row
        return {
            "score": list(self.score), "q": self.qscores, "ot": max(0, self.q - 4), "box": box,
            "starters": [[g.id for g in t.players if g.started] for t in self.T],
            "events": self.events if self.record else None,
            "injuries": self.injuries,
            "flow": self.flow[::4] if self.record else None,
            "challenges": self.challenges,
        }


def play_game(home_t, home_roster, away_t, away_roster, rng=None, record=False, playoff=False, opts=None):
    return Game(home_t, home_roster, away_t, away_roster, rng=rng, record=record, playoff=playoff,
                opts=opts).play()
