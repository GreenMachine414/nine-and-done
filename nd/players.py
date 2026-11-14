"""Player model: positions, attributes, ceilings, tendencies, generation, development, contracts."""
import random

from .data import FIRST_NAMES, LAST_NAMES, FIRST_NAMES_US, LAST_NAMES_US, SCHOOLS, MIN_SALARY, MAX_SALARY

POS = ["PG", "SG", "SF", "PF", "C"]

ATTRS = ["ins", "mid", "three", "ft", "post", "pass", "hand", "iq",
         "perd", "intd", "stl", "blk", "reb", "ath", "sta"]

ATTR_LABEL = {
    "ins": "Finishing", "mid": "Mid-Range", "three": "Three-Point", "ft": "Free Throw", "post": "Post Game",
    "pass": "Passing", "hand": "Ball Handling", "iq": "Basketball IQ", "perd": "Perimeter D",
    "intd": "Interior D", "stl": "Steal", "blk": "Block", "reb": "Rebounding", "ath": "Athleticism",
    "sta": "Stamina",
}

# Position attribute ceilings: no player at that position can exceed these.
CEIL = {
    "PG": dict(ins=90, mid=99, three=99, ft=99, post=55, **{"pass": 99}, hand=99, iq=99, perd=99, intd=60, stl=99,
               blk=50, reb=66, ath=99, sta=99),
    "SG": dict(ins=98, mid=99, three=99, ft=99, post=70, **{"pass": 97}, hand=99, iq=99, perd=99, intd=75, stl=99,
               blk=64, reb=82, ath=99, sta=99),
    "SF": dict(ins=99, mid=99, three=99, ft=98, post=88, **{"pass": 98}, hand=98, iq=99, perd=99, intd=92, stl=98,
               blk=86, reb=94, ath=99, sta=99),
    "PF": dict(ins=99, mid=97, three=95, ft=94, post=99, **{"pass": 93}, hand=89, iq=99, perd=95, intd=99, stl=90,
               blk=98, reb=99, ath=99, sta=99),
    "C": dict(ins=99, mid=93, three=90, ft=90, post=99, **{"pass": 92}, hand=80, iq=99, perd=84, intd=99, stl=84,
              blk=99, reb=99, ath=98, sta=98),
}


# Offsets from the player's quality level that define the "shape" of each position.
BASE = {
    "PG": dict(ins=-3, mid=1, three=3, ft=5, post=-26, **{"pass": 9}, hand=10, iq=3, perd=2, intd=-22, stl=3, blk=-30,
               reb=-20, ath=3, sta=5),
    "SG": dict(ins=-1, mid=3, three=5, ft=5, post=-18, **{"pass": 0}, hand=4, iq=0, perd=3, intd=-15, stl=2, blk=-22,
               reb=-14, ath=3, sta=4),
    "SF": dict(ins=2, mid=2, three=1, ft=0, post=-6, **{"pass": -4}, hand=-3, iq=0, perd=4, intd=-4, stl=0, blk=-8,
               reb=-4, ath=4, sta=3),
    "PF": dict(ins=5, mid=-2, three=-6, ft=-6, post=5, **{"pass": -8}, hand=-12, iq=0, perd=-6, intd=6, stl=-8, blk=4,
               reb=8, ath=0, sta=0),
    "C": dict(ins=8, mid=-8, three=-16, ft=-12, post=9, **{"pass": -10}, hand=-20, iq=0, perd=-14, intd=10, stl=-12,
              blk=12, reb=12, ath=-2, sta=-3),
}

ARCH = {
    "PG": {"Floor General": {"pass": 9, "iq": 8, "hand": 4, "ins": -4, "ath": -3},
           "Scoring Guard": {"three": 6, "mid": 6, "ins": 3, "pass": -6},
           "Slasher": {"ins": 10, "ath": 8, "three": -8, "mid": -3},
           "Two-Way Guard": {"perd": 10, "stl": 8, "three": -3, "pass": -3}},
    "SG": {"Sharpshooter": {"three": 12, "ft": 8, "mid": 4, "ins": -6, "hand": -3},
           "Slasher": {"ins": 10, "ath": 8, "three": -8},
           "3&D Wing": {"three": 6, "perd": 10, "stl": 4, "hand": -6, "pass": -6, "mid": -4},
           "Shot Creator": {"mid": 10, "hand": 8, "three": 3, "perd": -6}},
    "SF": {"Two-Way Wing": {"perd": 8, "intd": 4, "stl": 4, "three": 2},
           "Point Forward": {"pass": 12, "hand": 8, "iq": 5, "three": -4},
           "Athletic Finisher": {"ins": 10, "ath": 10, "three": -8, "ft": -6},
           "Stretch Wing": {"three": 10, "mid": 4, "intd": -6, "reb": -6}},
    "PF": {"Stretch Four": {"three": 14, "mid": 6, "post": -6, "intd": -6, "reb": -6},
           "Bruiser": {"post": 10, "ins": 8, "reb": 6, "three": -10},
           "Rim Runner": {"ath": 10, "ins": 8, "blk": 6, "mid": -8, "three": -10},
           "Glue Guy": {"iq": 8, "pass": 6, "perd": 6, "ins": -2}},
    "C": {"Rim Protector": {"blk": 14, "intd": 10, "reb": 6, "post": -4, "mid": -6},
          "Post Scorer": {"post": 14, "ins": 6, "ft": 4, "blk": -6, "ath": -4},
          "Stretch Big": {"three": 18, "mid": 8, "post": -6, "blk": -6, "reb": -6},
          "Glass Cleaner": {"reb": 14, "ath": 4, "ins": 4, "mid": -6}},
}

_W_RAW = {
    "PG": dict(ins=6, mid=8, three=12, ft=3, post=0, **{"pass": 15}, hand=14, iq=10, perd=9, intd=1, stl=5, blk=0,
               reb=2, ath=9, sta=3),
    "SG": dict(ins=8, mid=10, three=15, ft=4, post=1, **{"pass": 7}, hand=9, iq=8, perd=11, intd=1, stl=5, blk=1,
               reb=3, ath=10, sta=3),
    "SF": dict(ins=10, mid=8, three=10, ft=3, post=4, **{"pass": 6}, hand=6, iq=8, perd=11, intd=5, stl=5, blk=3,
               reb=6, ath=10, sta=3),
    "PF": dict(ins=13, mid=5, three=6, ft=2, post=9, **{"pass": 4}, hand=3, iq=8, perd=6, intd=12, stl=2, blk=8,
               reb=13, ath=9, sta=3),
    "C": dict(ins=14, mid=3, three=3, ft=2, post=11, **{"pass": 4}, hand=1, iq=8, perd=3, intd=15, stl=1, blk=14,
              reb=15, ath=7, sta=2),
}
WEIGHTS = {p: {k: v / sum(w.values()) for k, v in w.items()} for p, w in _W_RAW.items()}
_GROW_W = {k: sum(WEIGHTS[p][k] for p in WEIGHTS) / len(WEIGHTS) for k in WEIGHTS["PG"]}   # position-neutral

TRAITS = {
    "Leader": "Lifts the locker room. Boosts team chemistry and steadies teammates' morale.",
    "Mentor": "Young teammates (23 and under) develop faster each offseason.",
    "Competitor": "Lives to win. Big morale swings with results, and a little extra in crunch time.",
    "Diva": "Wants touches and minutes. Gets unhappy fast when buried on the bench.",
    "Loyal": "Gives a hometown discount when re-signing and rarely sulks.",
    "Mercenary": "Follows the money. Asks for more and doesn't care much about winning.",
    "Professional": "Steady as they come. Morale barely moves, for better or worse.",
    "Hothead": "Plays with fire: more fouls, bigger momentum swings, may lose it in huddles.",
    "Gym Rat": "Lives in the gym. Extra offseason development.",
}
TRAIT_W = {"Leader": 8, "Mentor": 7, "Competitor": 12, "Diva": 8, "Loyal": 10, "Mercenary": 10,
           "Professional": 18, "Hothead": 9, "Gym Rat": 10}


def roll_trait(rng):
    return rng.choices(list(TRAIT_W), weights=list(TRAIT_W.values()))[0]


HEIGHTS = {"PG": (73, 77), "SG": (75, 78), "SF": (78, 81), "PF": (80, 83), "C": (82, 87)}


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


# ---- Overall rating = impact. Attributes roll up into seven skill groups. Scoring counts a player's best
# zones (a slasher, a shooter and a post scorer can all be elite), and each position weighs the groups by how
# much they matter there. A power mean lets strengths count for more than weaknesses, so a superstar needs to
# be elite at what matters for him, not maxed out everywhere (and not every PG has to be a playmaker).
GROUP_W = {
    "PG": dict(score=.30, play=.24, perd=.14, intd=.02, reb=.04, ath=.12, iq=.14),
    "SG": dict(score=.36, play=.12, perd=.17, intd=.03, reb=.06, ath=.13, iq=.13),
    "SF": dict(score=.32, play=.09, perd=.15, intd=.09, reb=.10, ath=.13, iq=.12),
    "PF": dict(score=.28, play=.05, perd=.07, intd=.19, reb=.18, ath=.11, iq=.12),
    "C": dict(score=.25, play=.04, perd=.03, intd=.25, reb=.21, ath=.09, iq=.13),
}
GROUP_ATTRS = {"score": ["ins", "mid", "three", "post", "ft"], "play": ["pass", "hand"], "perd": ["perd", "stl"],
               "intd": ["intd", "blk"], "reb": ["reb"], "ath": ["ath", "sta"], "iq": ["iq"]}
GROUP_NAMES = {"score": "Scoring", "play": "Playmaking", "perd": "Perimeter D", "intd": "Interior D",
               "reb": "Rebounding", "ath": "Athleticism", "iq": "IQ"}
_IMPACT_POW = 3.0
# per position: maps impact onto the rating scale so typically-built players keep the rating they always had
_CAL = {"PG": (-1.4, 1.015), "SG": (-2.0, 1.014), "SF": (-2.0, 1.010), "PF": (-2.9, 1.012), "C": (-4.4, 1.034)}
_SHARE = {"ins": .23, "mid": .23, "three": .23, "post": .23, "ft": .08, "pass": .5, "hand": .5, "perd": .7,
          "stl": .3, "intd": .6, "blk": .4, "reb": 1.0, "ath": .8, "sta": .2, "iq": 1.0}
_GROUP_OF = {k: g for g, ks in GROUP_ATTRS.items() for k in ks}
# how much each attribute matters at each position (used to shape growth and decline)
ATTR_IMP = {pos: {k: GROUP_W[pos][_GROUP_OF[k]] * _SHARE[k] for k in ATTRS} for pos in GROUP_W}


def skill_groups(a):
    z = sorted((a["ins"], a["mid"], a["three"], a["post"]), reverse=True)
    return {"score": (0.55 * z[0] + 0.30 * z[1] + 0.15 * z[2]) * 0.92 + 0.08 * a["ft"],
            "play": 0.5 * a["pass"] + 0.5 * a["hand"],
            "perd": 0.7 * a["perd"] + 0.3 * a["stl"],
            "intd": 0.6 * a["intd"] + 0.4 * a["blk"],
            "reb": a["reb"], "ath": 0.8 * a["ath"] + 0.2 * a["sta"], "iq": a["iq"]}


def impact(pos, a):
    g = skill_groups(a)
    w = GROUP_W[pos]
    return sum(w[k] * max(1.0, g[k]) ** _IMPACT_POW for k in w) ** (1 / _IMPACT_POW)


def calc_ovr(p):
    A, B = _CAL[p["pos"]]
    return int(round(A + B * impact(p["pos"], p["a"])))


# Internal ratings ("raw") drive the engine and economy. Everything shown to players uses a 2K-style display
# scale: a few stars in the 90-club, 99 max, rotation guys in the 70s.
_DISP = [(0, 25), (30, 45), (40, 55), (50, 64), (60, 72), (70, 79), (78, 84), (84, 88), (88, 91), (93, 95),
         (98, 99), (200, 99)]


def disp(raw):
    raw = float(raw)
    for (x0, y0), (x1, y1) in zip(_DISP, _DISP[1:]):
        if raw <= x1:
            return int(round(y0 + (y1 - y0) * (raw - x0) / (x1 - x0)))
    return 99


def undisp(d):
    """Inverse of disp(): the raw rating that displays as d."""
    for (x0, y0), (x1, y1) in zip(_DISP, _DISP[1:]):
        if d <= y1 and y1 > y0:
            return x0 + (x1 - x0) * (d - y0) / (y1 - y0)
    return 100.0


# Players are shown only as 1.0-5.0 stars, to the nearest tenth. Linear up to the knee (about 4.1 stars), then
# steeper, so 5.0 is a generational superstar: elite at everything that matters for him, average elsewhere.
STAR_KNEE = 84
STAR_TOP = 91      # raw rating of a 5.0 (a Jordan-type profile)
ELITE_RAW = 87     # above this (about 4.5 stars), upward moves are smaller: the last steps to greatness are hardest
ELITE_DAMP = 0.4
POT_MAX = 97       # highest potential a prospect can have
_SK = 1 + (STAR_KNEE - 45) * 0.08


def star_value(ovr):
    """Unrounded, unclamped star value of a raw rating."""
    if ovr <= STAR_KNEE:
        return 1 + (ovr - 45) * 0.08
    return _SK + (ovr - STAR_KNEE) * (5 - _SK) / (STAR_TOP - STAR_KNEE)


def raw_for_stars(sv):
    """Inverse of star_value()."""
    if sv <= _SK:
        return 45 + (sv - 1) / 0.08
    return STAR_KNEE + (sv - _SK) * (STAR_TOP - STAR_KNEE) / (5 - _SK)


def stars_for(ovr):
    return round(min(5.0, max(1.0, star_value(ovr))), 1)


def market_salary(ovr, age):
    """What a player 'should' earn per year, $M."""
    x = clamp((ovr - 48) / 44.0, 0, 1.15)
    s = MIN_SALARY + (MAX_SALARY - MIN_SALARY) * x ** 2.3
    if age >= 32:
        s *= max(0.55, 1 - (age - 31) * 0.09)
    elif age <= 23:
        s *= 0.92
    return round(clamp(s, MIN_SALARY, MAX_SALARY), 1)


TAGS = [
    ("Sniper", lambda a, p: a["three"] >= 86),
    ("Microwave", lambda a, p: a["mid"] >= 86),
    ("Rim Wrecker", lambda a, p: a["ins"] >= 86 and a["ath"] >= 82),
    ("Post Maestro", lambda a, p: a["post"] >= 86),
    ("Maestro", lambda a, p: a["pass"] >= 86),
    ("Handles", lambda a, p: a["hand"] >= 88),
    ("Lockdown", lambda a, p: a["perd"] >= 86),
    ("Anchor", lambda a, p: a["intd"] >= 86),
    ("Pickpocket", lambda a, p: a["stl"] >= 86),
    ("Swat Team", lambda a, p: a["blk"] >= 86),
    ("Glass Eater", lambda a, p: a["reb"] >= 88),
    ("Freak Athlete", lambda a, p: a["ath"] >= 90),
    ("Iron Lungs", lambda a, p: a["sta"] >= 92),
    ("Floor Brain", lambda a, p: a["iq"] >= 88),
    ("Clutch Gene", lambda a, p: p.get("clutch", 50) >= 82),
    ("Charity Stripe", lambda a, p: a["ft"] >= 90),
]


def refresh(p):
    """Recompute derived fields after any attribute change."""
    c = CEIL[p["pos"]]
    for k in ATTRS:
        p["a"][k] = int(clamp(round(p["a"][k]), 20, c[k]))
    p["ovr"] = calc_ovr(p)
    p["pot"] = max(p.get("pot", p["ovr"]), p["ovr"])
    p["stars"] = stars_for(p["ovr"])
    p["pstars"] = stars_for(p["pot"])
    p["tags"] = [n for n, f in TAGS if f(p["a"], p)][:4]
    p["t"] = gen_tendencies(p, p.get("t"))
    return p


def gen_tendencies(p, prev=None, rng=random):
    a = p["a"]
    seed = (prev or {}).get("_n")
    if seed is None:
        seed = [rng.gauss(0, 1) for _ in range(6)]
    n = seed
    w3 = max(2, a["three"] - 38) ** 1.65 * (1 + n[0] * 0.12)
    wm = max(2, a["mid"] - 42) ** 1.35 * (1 + n[1] * 0.12)
    wr = max(2, (a["ins"] * 0.7 + a["ath"] * 0.3) - 38) ** 1.5 * (1 + n[2] * 0.12)
    wp = max(1, a["post"] - 48) ** 1.6 * (1 + n[3] * 0.12)
    tot = w3 + wm + wr + wp
    scoring = max(a["ins"] * 0.9, a["mid"], a["three"], a["post"] * 0.95)
    use = clamp(32 + (scoring - 60) * 1.15 + n[4] * 7, 8, 99)
    pas = clamp(a["pass"] * 0.75 + a["iq"] * 0.15 + n[5] * 6, 10, 99)
    return {
        "three": round(w3 / tot * 100), "mid": round(wm / tot * 100),
        "rim": round(wr / tot * 100), "post": round(wp / tot * 100),
        "use": round(use), "pass": round(pas), "_n": n,
    }


def _name(rng, used):
    for _ in range(50):
        r = rng.random()
        if r < 0.62:      # mostly American names
            n = (rng.choice(FIRST_NAMES_US), rng.choice(LAST_NAMES_US))
        elif r < 0.8:     # mixed
            n = (rng.choice(FIRST_NAMES_US), rng.choice(LAST_NAMES))
        else:             # international
            n = (rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES))
        if n not in used:
            used.add(n)
            return n
    return (rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES) + "-" + rng.choice(LAST_NAMES))


def generate(rng, pid, target_ovr, age, pos=None, used_names=None, season=0):
    pos = pos or rng.choice(POS)
    arch_name = rng.choice(list(ARCH[pos]))
    arch = ARCH[pos][arch_name]
    # signature strengths and a weakness among the groups that matter at his position
    rel = sorted(GROUP_W[pos], key=lambda g: -GROUP_W[pos][g])[:5]
    strong = rng.sample(rel, rng.choice([1, 2]))
    weak = rng.choice([g for g in rel if g not in strong])
    shape = dict.fromkeys(ATTRS, 0.0)
    for g in strong:
        bump = rng.uniform(4, 11)
        for k in GROUP_ATTRS[g]:
            shape[k] += bump
    for k in GROUP_ATTRS[weak]:
        shape[k] -= rng.uniform(4, 10)
    a = {}
    for k in ATTRS:
        a[k] = target_ovr + BASE[pos][k] + arch.get(k, 0) + shape[k] + rng.gauss(0, 4.5)
    p = {"id": pid, "pos": pos, "a": a, "arch": arch_name}
    c = CEIL[pos]
    for _ in range(8):
        for k in ATTRS:
            a[k] = clamp(a[k], 20, c[k])
        diff = target_ovr - calc_ovr(p)
        if abs(diff) < 0.6:
            break
        for k in ATTRS:
            a[k] += diff
    fn, ln = _name(rng, used_names if used_names is not None else set())
    lo, hi = HEIGHTS[pos]
    ht = rng.randint(lo, hi)
    p.update({
        "fn": fn, "ln": ln, "age": age, "ht": ht,
        "wt": int(150 + (ht - 70) * 6.5 + rng.gauss(0, 10)),
        "num": rng.choice([0, 1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17, 20, 21, 22, 23, 24, 25, 30, 31,
                           32, 33, 34, 35, 41, 44, 50, 55, 77]),
        "school": rng.choice(SCHOOLS),
        "clutch": int(clamp(rng.gauss(55, 15), 15, 99)),
        "dur": int(clamp(rng.gauss(75, 12), 30, 99)),
        "tid": -1, "stats": {}, "hist": [], "inj": None,
        "contract": None, "draft": None, "awards": [],
        "trait": roll_trait(rng), "morale": int(clamp(rng.gauss(68, 8), 45, 90)), "mlog": [],
        "decline_age": rng.choice([30, 31, 32]),
    })
    ovr = calc_ovr(p)
    if age <= 20:
        g = rng.uniform(8, 26)
    elif age <= 22:
        g = rng.uniform(4, 18)
    elif age <= 24:
        g = rng.uniform(0, 10)
    elif age <= 26:
        g = rng.uniform(0, 4)
    else:
        g = 0
    p["pot"] = int(clamp(ovr + g, ovr, POT_MAX))
    refresh(p)
    p["hist"].append({"s": season, "ovr": p["ovr"], "age": age})
    return p


SCOUT_MAX_STEP = 4


def scout_report(p, step, scouting=0, salt=0):
    """Fog-of-war view of a prospect for a team with `step` scouting visits and the given scouting upgrade.
    Returns display-scale ranges for OVR/POT and only the attributes uncovered so far."""
    r = random.Random(p["id"] * 7919 + 17)
    order = list(ATTRS)
    r.shuffle(order)            # which attributes get uncovered first (fixed per player)
    step = max(0, min(SCOUT_MAX_STEP, step))
    # Where the true value sits inside each range is uniformly random, edges included, and re-drawn at every
    # scouting step, so successive reports can't be compared to back out the exact rating.
    rs = random.Random(p["id"] * 104729 + step * 7907 + salt * 15485863 + 3)   # each team's scouts differ
    f_o, f_p = rs.random(), rs.random()
    n_known = min(len(ATTRS), 4 + scouting + 3 * step)
    known = {k: p["a"][k] for k in order[:n_known]}
    shrink = 1 - 0.1 * scouting
    wo = [7.0, 5.0, 3.0, 1.5, 0.0][step] * shrink
    wp = [10.0, 8.0, 6.0, 4.0, 2.0][step] * shrink
    lo_o = p["ovr"] - f_o * 2 * wo
    lo_p = p["pot"] - f_p * 2 * wp
    ovr = [stars_for(lo_o), stars_for(lo_o + 2 * wo)]
    pot = [max(ovr[0], stars_for(lo_p)), max(ovr[1], stars_for(lo_p + 2 * wp))]
    return {"step": step, "max": SCOUT_MAX_STEP, "known": known, "ovr": ovr, "pot": pot,
            "tags": p["tags"] if step >= 2 else []}


def fuzz_pot(p, scouting=0):
    """Scouting-report range for a prospect's potential (deterministic per player)."""
    r = random.Random(p["id"] * 7919)
    spread = max(1, (4 if p["age"] >= 22 else 6) - scouting)
    center = p["pot"] + round(r.randint(-3, 3) * spread / 6)
    return [max(p["ovr"], center - spread), min(99, center + spread)]




def _land(p, want, rng):
    """Nudge whole-number attributes until the overall equals `want`. Growth goes into what matters most for
    his position, with some randomness, so the player's shape (strengths and weaknesses) is kept."""
    refresh(p)
    a = p["a"]
    imp = ATTR_IMP[p["pos"]]
    ceil = CEIL[p["pos"]]
    for _ in range(300):
        if p["ovr"] == want:
            break
        d = 1 if p["ovr"] < want else -1
        ok = [k for k in ATTRS if (a[k] < ceil[k] if d > 0 else a[k] > 20)]
        if not ok:
            break
        k = max(ok, key=lambda k: imp[k] * (0.4 + rng.random()))
        a[k] += d
        p["ovr"] = calc_ovr(p)


DECLINE_STARS = 0.12   # constant yearly drop once a player reaches his decline age


def develop(p, rng, bonus=0.0, decline_cut=0.0, perf=0.0):
    """Offseason progression / regression. Mutates p. Returns ovr delta.
    bonus: extra growth points for young players (dev upgrade, mentors, gym rats, morale).
    decline_cut: -0.3..0.3 fraction of the age decline removed (dev upgrade vs league average).
    perf: -1..1, last season's performance vs players of the same rating (from league.performance_scores).
    Before his decline age (30, 31 or 32) a player follows the normal age curve with its usual random swing.
    From his decline age on, each year is exactly: a constant decline (DECLINE_STARS) + a random +/-0.15 stars
    + up to +/-0.15 stars for last season's performance. A great year can still mean a tiny gain."""
    before = p["ovr"]
    age = p["age"]
    dage = p.get("decline_age") or 31
    a = p["a"]
    if age >= dage:
        d = -DECLINE_STARS * (1 - decline_cut) + rng.uniform(-0.15, 0.15) + max(-1.0, min(1.0, perf)) * 0.15
        target = raw_for_stars(star_value(before) + d)          # the change is in stars, at his level
        m = target - before
        for k in ATTRS:   # bodies go first: athleticism and stamina carry more of the change, IQ less
            w = 1.6 if k in ("ath", "sta") else 0.4 if k == "iq" else 1.0
            a[k] += m * w + rng.gauss(0, 0.4)
    else:
        if age <= 20:
            m = 4.0
        elif age <= 22:
            m = 3.0
        elif age <= 24:
            m = 1.7
        elif age <= 26:
            m = 0.5
        elif age <= 28:
            m = -0.4
        elif age <= 30:
            m = -1.4
        else:
            m = -2.8
        gap = p["pot"] - p["ovr"]
        if m > 0:
            m *= 0.3 + min(1.15, max(0, gap) / 8)
        if m > 0 and p["ovr"] >= 80:          # harder to keep climbing near the top of the league
            m *= 0.6
        if m < 0:
            m *= (1 - decline_cut)
        m += bonus if age <= 25 else bonus * 0.4
        m += rng.gauss(0, 1.8)
        if m > 0 and gap <= 0:
            m *= 0.25
        if m > 0 and p["ovr"] >= ELITE_RAW:   # the last steps to greatness are the hardest
            m *= ELITE_DAMP
        target = before
        for k in ATTRS:
            w = 1.0
            ch = 0.0
            if k in ("ath", "sta"):
                w = 0.5 if m > 0 else 1.7
                if age >= 29:
                    ch -= rng.uniform(0.5, 2.0)
            elif k == "iq":
                w = 0.7 if m > 0 else 0.0
                if age >= 25:
                    ch += rng.uniform(0, 1.5)
            ch += m * w + rng.gauss(0, 1.1)
            a[k] += ch
            target += ch * _GROW_W[k]   # the yearly change: same formula at every position
    _land(p, int(target + rng.random()), rng)    # randomized rounding keeps the average change exact
    refresh(p)
    if p["age"] >= 26:
        p["pot"] = max(p["ovr"], min(p["pot"], p["ovr"] + max(0, 29 - p["age"])))
    else:
        p["pot"] = int(clamp(p["pot"] + rng.gauss(-1.0, 2.5), p["ovr"], POT_MAX))
    refresh(p)
    return p["ovr"] - before


def contract_ask(p, mood=1.0, resign=False):
    sal = market_salary(p["ovr"], p["age"])
    tr = p.get("trait")
    if tr == "Mercenary":
        mood *= 1.12
    elif tr == "Loyal" and resign:
        mood *= 0.88
    if resign:
        m = p.get("morale", 65)
        mood *= 1 + max(0, 50 - m) / 120 - max(0, m - 75) / 250
    if p["age"] <= 25 and p["pot"] > p["ovr"] + 4:
        sal = max(sal, market_salary((p["ovr"] + p["pot"]) / 2, p["age"]) * 0.9)
    sal = round(clamp(sal * mood, MIN_SALARY, MAX_SALARY), 1)
    yrs = 4 if p["age"] <= 26 else 3 if p["age"] <= 30 else 2 if p["age"] <= 33 else 1
    return {"sal": sal, "yrs": yrs}


def full_name(p):
    return f'{p["fn"]} {p["ln"]}'


def short_name(p):
    return f'{p["fn"][0]}. {p["ln"]}'
