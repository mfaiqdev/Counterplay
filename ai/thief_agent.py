"""
thief_agent.py - Thief AI   *** PLACEHOLDER - NOT IMPLEMENTED YET ***

The Thief AI should play the heist: collect the key, open the door, steal the
loot and escape, while avoiding guards and cameras.

Planned interface
-----------------
    agent = ThiefAgent()
    action = agent.choose_action(state)       # state from game.get_state()
    agent.learn(state, action, reward, next_state, done)

'action' is one of the ACTION_* numbers in environment/game.py.
Combine q_learning.py (learning) with algorithms/ (path planning).
"""


class ThiefAgent:
    """TODO: choose actions for the thief and learn from experience."""

    def choose_action(self, state):
        raise NotImplementedError("Thief AI has not been implemented yet.")

    def learn(self, state, action, reward, next_state, done):
        raise NotImplementedError("Thief AI has not been implemented yet.")
