"""
guard_pathfinding_demo.py - Play the real game with guards that chase using
OUR search algorithm, and SEE the path they plan.

Run from the project folder:

    python tools/guard_pathfinding_demo.py                         normal game, BFS guards
    python tools/guard_pathfinding_demo.py --scenario              the "hide behind a wall" test
    python tools/guard_pathfinding_demo.py --scenario --original   the same test, built-in guards

What is different from the normal game (python main.py)?
--------------------------------------------------------
    built-in guards   A chasing guard only steps to a neighbouring tile that
                      is closer to its target.  When a wall is in the way, no
                      neighbour is closer, so the guard gets stuck.
    BFS guards        A chasing guard asks BFS for the shortest path to its
                      target and takes the first step, so it walks AROUND walls
                      through the doorways.  The planned path is drawn on the
                      map as orange dots.

The --scenario test
-------------------
Every mission starts with the thief hiding in the start room at (7, 12) and
the hallway guard at (10, 8), already chasing the thief.  A wall is between
them.  Press SPACE once to start, then just watch:
    * built-in guard: walks left, gets stuck against the wall at (7, 8)
    * BFS guard:      walks around through the doorways and catches you
In this test both kinds of guard are made more patient (they give up after
80 ticks instead of 10) so there is time to watch them try.

How it works without touching anyone else's code
------------------------------------------------
Python lets us replace a method of a class while a program runs (this is
called "monkey patching").  Before the game starts, this script swaps in its
own versions of a few methods.  No project file is edited, and the swaps only
exist while this script is running.  The real integration of path planning
into the guards belongs to the Security AI part of the project.
"""

import argparse
import os
import sys

# Make the project folder importable (this file lives in tools/).
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import pygame

from algorithms import bfs
from environment import security
from environment.game import Game
from environment.security import Guard, MODE_CHASE
from gui.renderer import Renderer, get_font, draw_text, TILE_SIZE

SEARCH = bfs                                # the algorithm the guards will use

SCENARIO_THIEF = (7, 12)                    # hiding in the start room
SCENARIO_GUARD = (10, 8)                    # in the hallway, wall in between
SCENARIO_GIVE_UP_TICKS = 80                 # more patient guards for the test

PATH_COLOR = (251, 146, 60)                 # orange dots for the planned path
LABEL_COLOR = (226, 232, 240)


# ---------------------------------------------------------------------------
# 1. Guards that plan with our search
# ---------------------------------------------------------------------------
def chase_step_with_search(guard, vault):
    """Replacement for Guard._chase_step: follow the path our search finds."""
    guard.demo_path = None
    if guard.target is None or guard.target == guard.position:
        return
    path = SEARCH.find_path(vault, guard.position, guard.target)
    if path and len(path) > 1:
        guard.trail.append(guard.position)    # the guard's own "way back" stack
        guard._move_to(path[1])               # path[0] is where the guard stands
        guard.demo_path = path[1:]            # remember the rest, for drawing


# ---------------------------------------------------------------------------
# 2. The "hide behind a wall" scenario
# ---------------------------------------------------------------------------
def add_scenario_to(original_reset):
    """Wrap Game.reset so every new mission starts in the test situation."""

    def reset_with_scenario(game):
        original_reset(game)
        game.thief.x, game.thief.y = SCENARIO_THIEF
        if game.security.guards:
            guard = game.security.guards[0]
            guard.x, guard.y = SCENARIO_GUARD
            guard.facing = (-1, 0)
            guard.mode = MODE_CHASE
            guard.target = SCENARIO_THIEF     # it just saw the thief go this way
            if SCENARIO_GUARD in guard.route:  # so it can patrol on normally later
                guard.route_index = guard.route.index(SCENARIO_GUARD)
        return game.get_state()

    return reset_with_scenario


# ---------------------------------------------------------------------------
# 3. Drawing the planned path and a label
# ---------------------------------------------------------------------------
def add_path_drawing_to(original_draw_guards):
    """Wrap Renderer._draw_guards so the planned path is drawn under the guards."""

    def draw_guards_with_paths(renderer, surface):
        radius = max(3, TILE_SIZE // 8)
        for guard in renderer.game.security.guards:
            path = getattr(guard, "demo_path", None)
            if guard.mode == MODE_CHASE and path:
                for x, y in path:
                    pygame.draw.circle(surface, PATH_COLOR,
                                       renderer._pixel_center(x, y), radius)
        original_draw_guards(renderer, surface)

    return draw_guards_with_paths


def add_label_to(original_draw, text):
    """Wrap Renderer.draw so a small label says which guards are running."""

    def draw_with_label(renderer, screen):
        original_draw(renderer, screen)
        draw_text(screen, text, get_font(16, True), LABEL_COLOR,
                  (12, screen.get_height() - 10), anchor="bottomleft")

    return draw_with_label


# ---------------------------------------------------------------------------
# Start the game with the swaps in place
# ---------------------------------------------------------------------------
def install(scenario=False, original=False):
    """Swap in the demo behaviour.  Returns the label shown on screen."""
    if original:
        label = "Guards: built-in 'step closer' rule"
    else:
        Guard._chase_step = chase_step_with_search
        Renderer._draw_guards = add_path_drawing_to(Renderer._draw_guards)
        label = "Guards: " + SEARCH.NAME + " path planning (orange dots = planned path)"

    if scenario:
        Game.reset = add_scenario_to(Game.reset)
        security.GUARD_GIVE_UP_TICKS = SCENARIO_GIVE_UP_TICKS
        label += "   |   scenario: press SPACE once, then watch"

    Renderer.draw = add_label_to(Renderer.draw, label)
    return label


def main():
    parser = argparse.ArgumentParser(description="Guards that chase with our search.")
    parser.add_argument("--scenario", action="store_true",
                        help="start every mission in the 'hide behind a wall' test")
    parser.add_argument("--original", action="store_true",
                        help="keep the built-in guards (to compare)")
    options = parser.parse_args()
    label = install(scenario=options.scenario, original=options.original)

    import main as game                     # the normal game, started as usual
    original_create_window = game.create_window

    def create_window_with_caption():
        screen = original_create_window()
        pygame.display.set_caption("COUNTERPLAY - demo (" + label.split("   |")[0] + ")")
        return screen

    game.create_window = create_window_with_caption
    game.main()


if __name__ == "__main__":
    main()
