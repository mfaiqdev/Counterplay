# COUNTERPLAY: Where AI Takes on AI

A 2D top-down heist game built with Python and Pygame. It is the **starter
foundation** for our Semester 3 *Data Structures & Algorithms* + *Artificial
Intelligence* project.

A thief breaks into a secured facility, steals the loot and escapes, while
guards and cameras try to stop them. In the finished project two AIs will
compete: a **Thief AI** that learns to steal and escape, and a **Security AI**
that learns to detect and catch the thief, with BFS / DFS / Greedy / A* planning
paths along the way.

> **This version is the playable game only.** No search algorithms and no
> Q-learning are implemented yet. Guards follow simple scripted rules. The
> `algorithms/` and `ai/` folders contain clearly marked placeholders.

---

## Quick start (Windows)

You need **Python 3.10 or newer** (https://www.python.org/downloads/).
Tick "Add Python to PATH" during installation.

Open PowerShell or Command Prompt in the project folder (the one containing
`main.py`) and run:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Next time, only these two lines are needed:

```powershell
venv\Scripts\activate
python main.py
```

(macOS / Linux: use `python3 -m venv venv`, `source venv/bin/activate`, then
the same `pip` and `python` commands.)

### Run the tests

```powershell
python -m unittest discover -s tests -v
```

The tests need no window and no graphics.

---

## How to play

**Objective**

1. Find the **key** (top-left room).
2. Use it on the **locked vault door** (red door, top right).
3. Steal at least one piece of **loot** inside the vault.
4. Run to the **exit** (bottom-right corner).

**Controls**

| Key | Action |
|---|---|
| `W A S D` or arrow keys | Move the thief |
| `Space` | Stand still |
| `P` or `Esc` | Pause (resume, restart, how to play, main menu) |
| `R` | Restart the mission |
| `F11` | Toggle fullscreen (the window can also be resized) |
| `F1` | Show the exact tiles used for detection (debug view) |
| Mouse or `Up` / `Down` + `Enter` | Navigate menus |

**Rules**

* The game starts when you press your first movement key.
* Guards and cameras see in a **cone of light**. The glow on the map shows what
  they can see right now. Walls and locked doors block their view. The light
  turns red when it has found you.
* Being seen raises the **alert level**: `CALM` -> `SUSPICIOUS` -> `ALARM`.
  Standing in a restricted (hatched red) area makes the system suspicious.
  During an alarm, guards hunt you.
* A guard on or next to your tile **catches** you: game over.
* Every step costs **energy** (more while carrying loot). Energy cells restore
  it. If energy reaches zero you lose.
* The exit only works once you carry loot.

---

## Project structure

```
counterplay/
├── main.py                  Starts the game; game loop and screen switching
│
├── environment/             GAME LOGIC  (no graphics, no Pygame)
│   ├── vault.py             The map: tiles, doors, items, restricted zones, patrol routes
│   ├── player.py            The thief: position, energy, key, loot
│   ├── security.py          Guards, cameras, vision cones, SecuritySystem
│   └── game.py              Rules + reset() / get_state() / step() interface
│
├── gui/                     WHAT THE PLAYER SEES
│   ├── renderer.py          Draws map, light cones, characters, HUD, effects (+ colours, fonts)
│   └── menu.py              Main menu, pause / win / lose panels, "How to play"
│
├── algorithms/              PLACEHOLDERS for DSA work
│   ├── bfs.py  dfs.py  greedy.py  astar.py
│
├── ai/                      PLACEHOLDERS for AI work
│   ├── q_learning.py  thief_agent.py  security_agent.py  training.py
│
├── tests/test_environment.py   Unit tests for the rules
├── assets/                  Window icon
├── requirements.txt  .gitignore  LICENSE  README.md
```

### The most important design rule

```
 keyboard --> main.py --> Game (environment/) --> state --> Renderer (gui/) --> screen
```

* `environment/` knows the rules and **never** draws or reads the keyboard.
* `gui/` and `main.py` only **display** the game and pass key presses to it.

Because of this, an AI agent can play the game without a window, by calling
the same functions the keyboard uses.

### The environment interface

```python
from environment.game import Game, ACTION_UP

game = Game()
state = game.reset()                              # start a new game
actions = game.get_legal_actions()                # [0, 1, 2, 3, 4]
state, reward, done, info = game.step(ACTION_UP)  # do one action
```

* `state` is a dictionary: thief position/energy/key/loot, guards, cameras,
  alert level, locked doors, remaining items, exit position, status.
* `reward` is a number (see the `REWARD_*` constants in `game.py`).
* `done` is `True` when the thief escaped, was caught, or ran out of energy.
* `info["events"]` lists what happened, e.g. `"key_collected"`, `"spotted_by_camera"`.

Actions: `0 WAIT, 1 UP, 2 DOWN, 3 LEFT, 4 RIGHT`.

---

## Where future work plugs in

| Task | Where to start |
|---|---|
| BFS / DFS / Greedy / A* | `algorithms/*.py` (same `find_path(vault, start, goal)` interface) |
| Graph of rooms and passages | new helper next to the algorithms, built from `Vault` |
| Priority queue / heap | `heapq` inside Greedy and A* |
| Guards use path planning | `Guard._chase_step()` and `Guard.update()` in `environment/security.py` |
| Thief uses path planning | `ai/thief_agent.py` |
| Q-learning (Thief and Security) | `ai/q_learning.py`, `thief_agent.py`, `security_agent.py` |
| Training, metrics, comparisons | `ai/training.py` (no Pygame needed) |
| State key for the Q-table | build it from `game.get_state()` |
| Replanning when things change | check `state["locked_doors"]`, guard positions and alert level each step |

Suggested split for three people: (1) algorithms, (2) Q-learning + thief agent,
(3) security agent + training/metrics. Agree on the `find_path` interface and
the `Game` API first, then work in separate files to avoid merge conflicts.

Tips:

* Change gameplay numbers (energy cost, guard speed, vision range, alert
  durations) at the top of `game.py` and `security.py`.
* The level lives in `LEVEL_LAYOUT` in `environment/vault.py`. After editing it,
  run the tests: they check that the key, vault and exit are still reachable.
* Run `python -m unittest discover -s tests -v` before every commit.

---

## Known limitations

* **Guard chasing is greedy.** Guards step toward the thief without planning, so
  a guard can get stuck behind a wall. This is intentional: it is the behaviour
  A* will replace.
* The Security AI cannot control guards yet: `Game.step()` accepts only the
  thief's action, and guards run on built-in scripts.
* One fixed level. There is no level selection or random generation.
* There is no sound.
* The rules are deliberately simple placeholders and meant to be changed.
* The game advances in real time (about 8 steps per second). Standing still
  also passes time, so guards keep moving.
* The soft light cones are drawn with ray tracing, but the game itself decides
  detection with a simple tile-based cone. They match closely; press `F1` to
  see the real detection tiles.

---
