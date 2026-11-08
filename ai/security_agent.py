"""
security_agent.py - Security AI   *** PLACEHOLDER - NOT IMPLEMENTED YET ***

The Security AI should decide how guards move so they detect, intercept and
stop the thief.  Today the guards follow fixed scripts in
environment/security.py (see Guard.update). The Security AI will replace that
decision.

Planned interface
-----------------
    agent = SecurityAgent()
    guard_actions = agent.choose_actions(state)
    agent.learn(state, guard_actions, reward, next_state, done)

Note: the environment currently only accepts the THIEF's action in
Game.step(). Extending it to accept guard actions is part of this task.
"""


class SecurityAgent:
    """TODO: choose guard actions and learn from experience."""

    def choose_actions(self, state):
        raise NotImplementedError("Security AI has not been implemented yet.")

    def learn(self, state, actions, reward, next_state, done):
        raise NotImplementedError("Security AI has not been implemented yet.")
