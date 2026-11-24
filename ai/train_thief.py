"""
train_thief.py - Lets the thief play many games by itself and learn.
No window and no keyboard: the agent plays through game.step().
"""

from environment.game import Game, STATUS_WON, STATUS_CAUGHT, STATUS_EXHAUSTED
from ai.thief_agent import ThiefAgent

MAX_STEPS = 600      # a game is stopped after this many moves


def play_one_game(game, agent, learn=True):
    """Play one full game. Returns (total reward, how it ended)."""
    state = game.reset()
    total_reward = 0.0
    for _ in range(MAX_STEPS):
        action = agent.choose_action(state, explore=learn)
        next_state, reward, done, info = game.step(action)
        if learn:
            agent.learn(state, action, reward, next_state, done)
        total_reward += reward
        state = next_state
        if done:
            break
    return total_reward, game.status


def train(episodes=2000, report_every=100):
    """Play many games in a row and print a progress line every few games."""
    game = Game()
    agent = ThiefAgent()

    block_reward = 0.0
    counts = {STATUS_WON: 0, STATUS_CAUGHT: 0, STATUS_EXHAUSTED: 0}

    for episode in range(1, episodes + 1):
        total, status = play_one_game(game, agent)
        agent.end_episode()

        block_reward += total
        if status in counts:
            counts[status] += 1

        if episode % report_every == 0:
            print(
                f"Games {episode - report_every + 1:>4}-{episode:<4} | "
                f"avg reward {block_reward / report_every:7.1f} | "
                f"escaped {counts[STATUS_WON]:>3} | "
                f"caught {counts[STATUS_CAUGHT]:>3} | "
                f"out of energy {counts[STATUS_EXHAUSTED]:>3} | "
                f"epsilon {agent.table.epsilon:.2f}"
            )
            block_reward = 0.0
            counts = {STATUS_WON: 0, STATUS_CAUGHT: 0, STATUS_EXHAUSTED: 0}
    return agent


if __name__ == "__main__":
    trained_agent = train()
    trained_agent.save("thief_q_table.pkl")
    print("Saved the notebook to thief_q_table.pkl")