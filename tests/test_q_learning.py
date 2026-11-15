import random
import unittest

from ai.q_learning import QLearningTable

LEFT, RIGHT = 0, 1
GOAL = 4        # a corridor with squares 0 1 2 3 4


def corridor_step(position, action):
    """Move in the tiny corridor. Returns (new_position, reward, done)."""
    if action == LEFT:
        position = max(0, position - 1)
    else:
        position = position + 1
    if position == GOAL:
        return position, 10.0, True
    return position, -0.1, False


class TestQLearning(unittest.TestCase):
    def test_update_moves_score_toward_reward(self):
        table = QLearningTable([LEFT, RIGHT], alpha=0.5, gamma=0.9)
        table.update("A", RIGHT, 10.0, "B", True)
        self.assertEqual(table.get_q("A", RIGHT), 5.0)

    def test_learns_to_go_right(self):
        random.seed(1)
        table = QLearningTable([LEFT, RIGHT], alpha=0.5, gamma=0.9, epsilon=0.3)
        for _ in range(300):
            position = 0
            for _ in range(50):
                action = table.choose_action(position)
                new_position, reward, done = corridor_step(position, action)
                table.update(position, action, reward, new_position, done)
                position = new_position
                if done:
                    break
        for square in range(GOAL):
            self.assertEqual(table.best_action(square), RIGHT)


if __name__ == "__main__":
    unittest.main()