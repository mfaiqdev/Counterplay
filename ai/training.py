"""
training.py - Training and evaluation   *** PLACEHOLDER - NOT IMPLEMENTED YET ***

Planned jobs
------------
* train(episodes)     play many games, letting the agents learn.
* evaluate(episodes)  play with learning switched off and measure results.
* Metrics to report:  escape rate, catch rate, loot collected, average steps.
* Compare scripted behaviour with learned behaviour.

Skeleton of one training episode (using the environment API):

    game = Game()
    state = game.reset()
    done = False
    while not done:
        action = thief_agent.choose_action(state)
        next_state, reward, done, info = game.step(action)
        thief_agent.learn(state, action, reward, next_state, done)
        state = next_state

Tip: training does not need Pygame. Never import gui/ from this file.
"""


def train(episodes):
    raise NotImplementedError("Training has not been implemented yet.")


def evaluate(episodes):
    raise NotImplementedError("Evaluation has not been implemented yet.")
