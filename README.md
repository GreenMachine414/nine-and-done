# Nine & Done

A basketball dynasty sim that runs in the browser. You're the owner, GM and coach. Each season is 9 games, the top 4 make the playoffs, and both rounds are best-of-five.

## Run

```
python server.py        # or double-click run.bat
```

The game opens at http://127.0.0.1:8777. It needs Python 3.10+ and uses only the standard library. Saves go to `data/ninedone.db` (SQLite).

## Systems

- **Custom leagues**: 10–20 teams (even numbers), optional conferences (Atlas and Horizon), and an optional CFP-style selection committee. Rosters start either pre-built or from a fantasy draft. Playoffs are 4 teams (2 rounds) or 8 teams (3 rounds), every series best-of-five. Schedules are published a year in advance.
- **Selection committee**: weekly rankings built from record, strength of schedule (opponents and opponents' opponents), quality wins, bad losses, capped margin, recent form, an early-season eye test, conference standing and head-to-head. With conferences on, each conference's top-ranked team gets an automatic bid.
- **Ratings**: the engine runs on internal ratings, and the UI shows a 2K-style scale (99 max, a handful of players in the 90-club).
- **Front office**: daily trade calls, one untouchable per season (AI teams sometimes name one too), contract negotiation with agent patience and counteroffers, and prospect scouting with fog of war (hidden attributes plus OVR/POT ranges narrowed with scouting points). Each of these is helped by an upgrade track.
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
python test/configtest.py          # every league configuration: schedules, playoffs, committee, negotiation, scouting
python test/apitest.py             # full API loop (server must be running)
python test/livetest.py            # live coaching, upgrades, talks and All-Star weekend over HTTP
node test/uitest.mjs <saveId>      # clicks through a live-coached game in headless Edge (DevTools protocol)
node test/metertest.mjs            # shot-meter component check
python test/shots.py <saveId> hub roster draft   # headless Edge screenshots
```
