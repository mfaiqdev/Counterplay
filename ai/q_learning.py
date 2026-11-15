"""
q_learning.py - Tabular Q-learning (used by the Thief AI and the Security AI)

A Q-table is a notebook: for every situation (state) it keeps a score for
every action. The agent improves the scores from the rewards it gets.
"""

import random
import pickle
class QLearningTable:
    """Stores Q-values, chooses actions and learns from rewards."""

    def __init__(self, actions, alpha=0.1, gamma=0.95, epsilon=0.1, epsilon_min=0.01, epsilon_decay=1.0):
        self.actions = list(actions)   # the moves we can choose from
        self.alpha = alpha             # dial 1: how fast I change my mind
        self.gamma = gamma             # dial 2: how much I care about the future
        self.epsilon = epsilon         # dial 3: how often I try a random move
        self.epsilon_min = epsilon_min      # never explore less than this
        self.epsilon_decay = epsilon_decay  # 1.0 means "don't shrink"
        self.q = {}                    # the notebook (empty at the start)

    
    def _row(self, state):
        """Open the page for this situation (make a new page if it is new)."""
        if state not in self.q:
            self.q[state] = {action: 0.0 for action in self.actions}
        return self.q[state]

    def get_q(self, state, action):
        """Read the score of one action in one situation."""
        return self._row(state)[action]

    
    def best_action(self, state):
        """The move with the highest score (if tied, pick one randomly)."""
        row = self._row(state)
        best_score = max(row.values())
        best_moves = [a for a, score in row.items() if score == best_score]
        return random.choice(best_moves)

    def choose_action(self, state, explore=True):
        """Usually the best move, but sometimes a random one (epsilon)."""
        if explore and random.random() < self.epsilon:
            return random.choice(self.actions)
        return self.best_action(state)

    
    def update(self, state, action, reward, next_state, done):
        """After a move, fix the score using the reward we got."""
        row = self._row(state)
        if done:
            future = 0.0     # the game ended, so there is no "later"
        else:
            future = max(self._row(next_state).values())
        target = reward + self.gamma * future
        row[action] += self.alpha * (target - row[action])


    
    def decay_epsilon(self):
        """Explore a little less after each game."""
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def save(self, path):
        """Save the notebook to a file."""
        with open(path, "wb") as file:
            pickle.dump({"q": self.q, "epsilon": self.epsilon}, file)

    def load(self, path):
        """Load a saved notebook from a file."""
        with open(path, "rb") as file:
            data = pickle.load(file)
        self.q = data["q"]
        self.epsilon = data["epsilon"]