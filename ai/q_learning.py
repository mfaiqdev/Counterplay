"""
q_learning.py - Tabular Q-learning   *** PLACEHOLDER - NOT IMPLEMENTED YET ***

Planned design
--------------
A Q-table maps (state, action) -> expected future reward.  The update rule:

    Q(s, a) <- Q(s, a) + alpha * (reward + gamma * max_a' Q(s', a') - Q(s, a))

* alpha   learning rate
* gamma   discount factor
* epsilon exploration rate (try random actions sometimes)

Things to decide as a team
--------------------------
* How to turn game.get_state() (a dictionary) into a small, hashable
  "state key" so the table stays small. For example a tuple such as
  (thief_x, thief_y, has_key, has_loot, nearest_guard_distance).
* How to store the table (a Python dict is fine).
"""


class QLearningTable:
    """TODO: store Q-values, choose actions (epsilon-greedy), update values."""

    def __init__(self, actions, alpha=0.1, gamma=0.95, epsilon=0.1):
        raise NotImplementedError("Q-learning has not been implemented yet.")
