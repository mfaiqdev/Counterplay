"""
thief_agent.py - Thief AI

The thief uses a Q-table (q_learning.py) to choose moves. The game's state is
big, so first we shrink it into a short "state key" with only the details
that matter. Similar situations then share one page of the notebook.
"""

from ai.q_learning import QLearningTable
from environment.game import (
    ACTION_WAIT, ACTION_UP, ACTION_DOWN, ACTION_LEFT, ACTION_RIGHT,)

ENERGY_LOW = 25
ENERGY_HIGH = 60

GUARD_NEAR = 3
GUARD_MEDIUM = 7


def energy_level(energy):
    """Turn the exact energy number into 0 = low, 1 = medium, 2 = high."""
    if energy < ENERGY_LOW:
        return 0
    if energy < ENERGY_HIGH:
        return 1
    return 2


def guard_distance_level(thief, guards):
    """How close is the nearest guard? 0 = near, 1 = medium, 2 = far."""
    if not guards:
        return 2
    nearest = min(abs(g["x"] - thief["x"]) + abs(g["y"] - thief["y"]) for g in guards)
    if nearest <= GUARD_NEAR:
        return 0
    if nearest <= GUARD_MEDIUM:
        return 1
    return 2


def make_state_key(state):
    """
    Shrink the big game state (a dictionary) into a short tuple.
    A tuple can be used as a dictionary key, so it fits the Q-table.
    """
    thief = state["thief"]
    return (
        thief["x"],
        thief["y"],
        thief["has_key"],
        len(state["locked_doors"]) == 0,     # True when the door is open
        thief["loot_count"] > 0,             # True when carrying loot
        energy_level(thief["energy"]),
        state["alert_level"],
        guard_distance_level(thief, state["guards"]),
    )

class ThiefAgent:
    """The thief's brain: shrinks the state, chooses a move, learns."""

    def __init__(self, alpha=0.1, gamma=0.95, epsilon=1.0,
                 epsilon_min=0.05, epsilon_decay=0.995):
        actions = [ACTION_WAIT, ACTION_UP, ACTION_DOWN, ACTION_LEFT, ACTION_RIGHT]
        self.table = QLearningTable(actions, alpha=alpha, gamma=gamma, epsilon=epsilon,
            epsilon_min=epsilon_min, epsilon_decay=epsilon_decay,)

    def choose_action(self, state, explore=True):
        """Pick a move for the current game state."""
        return self.table.choose_action(make_state_key(state), explore=explore)

    def learn(self, state, action, reward, next_state, done):
        """Fix the notebook after seeing what the move did."""
        self.table.update(
            make_state_key(state), action, reward,
            make_state_key(next_state), done,
        )

    def end_episode(self):
        """Call this after every finished game: explore a little less."""
        self.table.decay_epsilon()

    def save(self, path):
        self.table.save(path)

    def load(self, path):
        self.table.load(path)