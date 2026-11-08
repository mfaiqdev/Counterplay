"""
player.py - The thief (the character the player controls).

The Thief only stores facts about itself (position, energy, what it carries).
The rules for moving, picking things up and unlocking doors live in game.py.
"""

MAX_ENERGY = 100.0


class Thief:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.facing = (0, 1)        # direction the thief last moved in
        self.energy = MAX_ENERGY
        self.has_key = False
        self.loot_count = 0         # how many loot items are carried
        self.loot_value = 0         # total money value of the carried loot
        self.steps_taken = 0        # number of real moves made

    @property
    def position(self):
        return (self.x, self.y)

    @property
    def has_loot(self):
        return self.loot_count > 0

    def move_to(self, x, y):
        """Change position and remember which way we are facing."""
        self.facing = (x - self.x, y - self.y)
        self.x = x
        self.y = y
        self.steps_taken += 1

    def spend_energy(self, amount):
        self.energy = max(0.0, self.energy - amount)

    def restore_energy(self, amount):
        self.energy = min(MAX_ENERGY, self.energy + amount)

    def is_exhausted(self):
        return self.energy <= 0.0

    def add_loot(self, value):
        self.loot_count += 1
        self.loot_value += value
