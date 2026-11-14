# Nine & Done

A basketball dynasty sim that runs in the browser. You're the owner, GM and coach. Each league has 20 teams and a 9-game season. The top 8 make the playoffs: best-of-three quarterfinals and semifinals, then a best-of-five Finals.

## Run

```
python server.py        # or double-click run.bat
```

The game opens at http://127.0.0.1:8777. It needs Python 3.10+ and uses only the standard library. Saves go to `data/ninedone.db` (SQLite).

## Systems

- **League**: 20 teams. Rosters start either pre-built or from a fantasy draft. The top 8 by record make the playoffs (1v8, 4v5, 2v7, 3v6); ties go to head-to-head, then point differential.
- **Offseason**: a lottery day (the 12 non-playoff teams; four picks drawn) sets the draft order before free agency and the draft. Every drafted player's rookie deal carries a +1 year team option, at 115% of the rookie salary.
- **Aging**: each player has his own decline age (30, 31 or 32). Before it, players follow the normal age curve. From it on, each year is a constant -0.12★, plus a random ±0.15★, plus up to ±0.15★ for how he performed last season, so a great year can still bring a small gain.
- **Ratings**: players and teams are shown only as 1.0–5.0 stars, to the nearest tenth. A player's rating measures impact: attributes roll up into seven skill groups (scoring from his best zones, playmaking, perimeter D, interior D, rebounding, athleticism, IQ), each position weighs them differently, and strengths count for more than weaknesses. A 5.0 is a generational superstar who is elite at what matters for him, not maxed out everywhere. Players are generated with real strengths and weaknesses (not every PG is a playmaker), and every position has the same chance at 5.0. Individual attributes are still shown.
- **Front office**: daily trade calls, one untouchable per season (AI teams sometimes name one too), contract negotiation with agent patience and counteroffers, and prospect scouting with fog of war (hidden attributes plus star ranges narrowed with scouting points; each report only narrows the last one, never goes outside it, and always contains the true rating, and prospects don't change before the draft). Auto-picks, both yours and the AI teams', draft from what each team has scouted, not from true ratings. Each of these is helped by an upgrade track.
- **Award race**: live ladders and finalists during the season. Voters add variance, and winners are revealed when the regular season ends.

- **Live coaching** (🎙 Coach live on the Hub): the game is simulated in 45-second chunks while you coach. You can call timeouts, make subs, and change strategy from the clipboard. The game also pauses at quarter breaks, momentum runs, and close final possessions.
- **Coaching challenges**: these can help your team or hurt it, depending on how you do.
  - **Huddle speech**: read the situation and pick the right message.
  - **Defensive read**: study the hot scorer's shot chart and choose the coverage.
  - **Halftime film session**: take away the zone that hurt you most in the first half.
  - **Final-play call**: draw up the play, then time your release on the shot meter.
- **Personalities and morale**: every player has one of 9 traits. Morale reacts to wins, minutes, rivalry games and conversations with you. It feeds team chemistry, on-court performance, development, contract asks and trade requests.
- **Rivalries**: heat builds from close games, overtime and playoff series, and cools 20% each offseason. Five named rivalries are seeded at league creation.
- **All-Star break** (after game 5): 14 players are selected, and there's a playable 3-Point Contest, a Dunk Contest, and an All-Star Game you can watch.
- **Franchise upgrades**: you earn franchise points (FP) throughout the season and spend them on 9 tracks with 5 levels each. AI teams buy upgrades too. The Arena, Analytics and Development edges are measured against the league average.

## How it's built

| Path | What |
|---|---|
| `nd/sim.py` | Possession-by-possession game engine. Handles usage, shot selection, matchups, fatigue, subs, fouls, injuries, clutch play and the play-by-play event stream. |
| `nd/players.py` | Attributes, position ceilings, archetypes, tendencies, development and aging, contracts |
| `nd/league.py` | Season state machine: schedule, standings, playoffs, lottery, draft, awards, offseason, free agency |
| `nd/franchise.py` | Upgrades + franchise points, morale/chemistry/talks, rivalries, All-Star weekend |
| `nd/trade.py` | Trade valuation (contender, rebuild or neutral), cap rules, AI acceptance, trade-block offers |
| `nd/store.py` | SQLite persistence. One row per league, one per game box score. |
| `server.py` | JSON API and static file server |
| `static/` | Vanilla JS single-page app with no build step |

## Tests

```
python test/simtest.py 3 classic   # headless seasons + realism stats
python test/configtest.py          # schedules, 8-team playoffs, lottery day, team options, aging
node test/mobiletest.mjs <saveId> <owner>   # phone emulation: overflow check + screenshots
python test/apitest.py             # full API loop (server must be running)
python test/livetest.py            # live coaching, upgrades, talks and All-Star weekend over HTTP
node test/uitest.mjs <saveId>      # clicks through a live-coached game in headless Edge (DevTools protocol)
node test/metertest.mjs            # shot-meter component check
python test/shots.py <saveId> hub roster draft   # headless Edge screenshots
```
