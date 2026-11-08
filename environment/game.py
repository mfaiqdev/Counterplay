"""
game.py - The game rules and the public "environment" interface.

The GUI (or, later, an AI agent) talks to the game through four things:

    game.reset()          start a new game, returns the first state
    game.get_state()      look at the current state (a plain dictionary)
    game.step(action)     do one action, returns (state, reward, done, info)
    game.get_legal_actions()

This file never draws anything and never reads the keyboard.
"""

from environment.vault import (
    Vault, ITEM_KEY, ITEM_GOLD, ITEM_GEM, ITEM_ENERGY, LOOT_VALUES,
)
from environment.player import Thief
from environment.security import SecuritySystem

# ---------------------------------------------------------------------------
# Actions the thief can take
# ---------------------------------------------------------------------------
ACTION_WAIT = 0
ACTION_UP = 1
ACTION_DOWN = 2
ACTION_LEFT = 3
ACTION_RIGHT = 4

ACTION_NAMES = ["WAIT", "UP", "DOWN", "LEFT", "RIGHT"]
ACTION_VECTORS = {
    ACTION_WAIT: (0, 0),
    ACTION_UP: (0, -1),
    ACTION_DOWN: (0, 1),
    ACTION_LEFT: (-1, 0),
    ACTION_RIGHT: (1, 0),
}

# ---------------------------------------------------------------------------
# Game status
# ---------------------------------------------------------------------------
STATUS_PLAYING = "playing"
STATUS_WON = "won"
STATUS_CAUGHT = "caught"
STATUS_EXHAUSTED = "exhausted"

# Alert levels
ALERT_CALM = 0
ALERT_SUSPICIOUS = 1
ALERT_ALARM = 2
ALERT_NAMES = ["CALM", "SUSPICIOUS", "ALARM"]

# ---------------------------------------------------------------------------
# Game settings (easy to tweak)
# ---------------------------------------------------------------------------
MOVE_ENERGY_COST = 0.4           # energy used by one step
CARRYING_ENERGY_COST = 0.55      # energy used by one step while carrying loot
WAIT_ENERGY_COST = 0.05          # energy used by standing still / bumping a wall
ENERGY_CELL_AMOUNT = 25.0        # energy restored by an energy cell
REQUIRED_LOOT = 1                # loot items needed before the exit works

ALARM_HOLD_TICKS = 40            # how long ALARM lasts after the thief is last seen
SUSPICIOUS_HOLD_TICKS = 30       # how long SUSPICIOUS lasts

# Rewards (not used by the GUI; they are for future AI training)
REWARD_STEP = -0.1
REWARD_KEY = 10.0
REWARD_UNLOCK = 10.0
REWARD_LOOT = 50.0
REWARD_ENERGY = 2.0
REWARD_SPOTTED = -5.0
REWARD_WIN = 100.0
REWARD_CAUGHT = -100.0
REWARD_EXHAUSTED = -50.0

# Event names.  step() lists the events that happened, so the GUI can show
# messages and effects without having to guess what changed.
EVENT_KEY_COLLECTED = "key_collected"
EVENT_DOOR_UNLOCKED = "door_unlocked"
EVENT_DOOR_LOCKED = "door_locked"
EVENT_LOOT_COLLECTED = "loot_collected"
EVENT_ENERGY_COLLECTED = "energy_collected"
EVENT_ENTERED_RESTRICTED = "entered_restricted"
EVENT_SPOTTED_BY_CAMERA = "spotted_by_camera"
EVENT_SPOTTED_BY_GUARD = "spotted_by_guard"
EVENT_NEED_LOOT = "need_loot"
EVENT_ESCAPED = "escaped"
EVENT_CAUGHT = "caught"
EVENT_EXHAUSTED = "exhausted"


class Game:
    """One heist. Create it, then call step() again and again."""

    def __init__(self, with_security=True):
        # with_security=False gives an empty facility (handy for unit tests)
        self.with_security = with_security
        self.reset()

    # ------------------------------------------------------------------
    # Starting over
    # ------------------------------------------------------------------
    def reset(self):
        """Build a fresh level and return the starting state."""
        self.vault = Vault()
        self.thief = Thief(*self.vault.start)
        self.security = SecuritySystem(self.vault, enabled=self.with_security)

        self.status = STATUS_PLAYING
        self.tick = 0
        self.alert_level = ALERT_CALM
        self.alert_timer = 0
        self.last_known_pos = None       # where the thief was last spotted
        self.events = []                 # events from the most recent step
        self.total_reward = 0.0

        self._seen_by_camera_before = False
        self._seen_by_guard_before = False
        return self.get_state()

    # ------------------------------------------------------------------
    # Observing the game
    # ------------------------------------------------------------------
    def get_state(self):
        """Return everything an agent could want to know, as plain data."""
        return {
            "tick": self.tick,
            "status": self.status,
            "alert_level": self.alert_level,
            "thief": {
                "x": self.thief.x,
                "y": self.thief.y,
                "energy": self.thief.energy,
                "has_key": self.thief.has_key,
                "loot_count": self.thief.loot_count,
                "loot_value": self.thief.loot_value,
            },
            "guards": [
                {"x": g.x, "y": g.y, "facing": g.facing, "mode": g.mode}
                for g in self.security.guards
            ],
            "cameras": [
                {"x": c.x, "y": c.y, "facing": c.facing}
                for c in self.security.cameras
            ],
            "locked_doors": self.vault.locked_door_positions(),
            "items": dict(self.vault.items),
            "exit": self.vault.exit_pos,
        }

    def get_legal_actions(self):
        """All action numbers the thief may choose from."""
        return [ACTION_WAIT, ACTION_UP, ACTION_DOWN, ACTION_LEFT, ACTION_RIGHT]

    def is_over(self):
        return self.status != STATUS_PLAYING

    # ------------------------------------------------------------------
    # Doing one step
    # ------------------------------------------------------------------
    def step(self, action):
        """
        Advance the game by one tick.

        Returns (state, reward, done, info)
            state  - dictionary from get_state()
            reward - a number describing how good this step was
            done   - True when the game has ended
            info   - {"events": [...], "status": "..."}
        """
        if self.is_over():
            return self.get_state(), 0.0, True, {"events": [], "status": self.status}

        self.events = []
        self.tick += 1
        reward = REWARD_STEP

        reward += self._move_thief(action)
        reward += self._check_win()
        if self.status == STATUS_PLAYING:
            reward += self._check_exhausted()
        if self.status == STATUS_PLAYING:
            reward += self._update_security()
        if self.status == STATUS_PLAYING:
            reward += self._check_caught()

        self.total_reward += reward
        info = {"events": list(self.events), "status": self.status}
        return self.get_state(), reward, self.is_over(), info

    # ------------------------------------------------------------------
    # The thief's action
    # ------------------------------------------------------------------
    def _move_thief(self, action):
        """Handle one thief action. Returns the reward earned."""
        dx, dy = ACTION_VECTORS.get(action, (0, 0))
        if (dx, dy) == (0, 0):
            self.thief.spend_energy(WAIT_ENERGY_COST)
            return 0.0

        target_x = self.thief.x + dx
        target_y = self.thief.y + dy
        self.thief.facing = (dx, dy)

        # Walking into a locked door
        if self.vault.is_locked_door(target_x, target_y):
            return self._try_unlock(target_x, target_y)

        # Walking into a wall
        if not self.vault.is_walkable(target_x, target_y):
            self.thief.spend_energy(WAIT_ENERGY_COST)
            return 0.0

        # A normal move
        was_restricted = self.vault.is_restricted(self.thief.x, self.thief.y)
        self.thief.move_to(target_x, target_y)
        if self.thief.has_loot:
            self.thief.spend_energy(CARRYING_ENERGY_COST)
        else:
            self.thief.spend_energy(MOVE_ENERGY_COST)

        if self.vault.is_restricted(target_x, target_y) and not was_restricted:
            self.events.append(EVENT_ENTERED_RESTRICTED)
        return self._pick_up_item()

    def _try_unlock(self, door_x, door_y):
        """The thief walked into a locked door."""
        self.thief.spend_energy(WAIT_ENERGY_COST)
        if self.thief.has_key:
            self.vault.unlock_door(door_x, door_y)
            self.thief.has_key = False          # the key is used up
            self.events.append(EVENT_DOOR_UNLOCKED)
            return REWARD_UNLOCK
        self.events.append(EVENT_DOOR_LOCKED)
        return 0.0

    def _pick_up_item(self):
        """Collect whatever lies on the thief's tile. Returns the reward."""
        item = self.vault.take_item(self.thief.x, self.thief.y)
        if item == ITEM_KEY:
            self.thief.has_key = True
            self.events.append(EVENT_KEY_COLLECTED)
            return REWARD_KEY
        if item in (ITEM_GOLD, ITEM_GEM):
            self.thief.add_loot(LOOT_VALUES[item])
            self.events.append(EVENT_LOOT_COLLECTED)
            return REWARD_LOOT
        if item == ITEM_ENERGY:
            self.thief.restore_energy(ENERGY_CELL_AMOUNT)
            self.events.append(EVENT_ENERGY_COLLECTED)
            return REWARD_ENERGY
        return 0.0

    # ------------------------------------------------------------------
    # End conditions
    # ------------------------------------------------------------------
    def _check_win(self):
        """The thief wins by standing on the exit while carrying enough loot."""
        if self.thief.position != self.vault.exit_pos:
            return 0.0
        if self.thief.loot_count >= REQUIRED_LOOT:
            self.status = STATUS_WON
            self.events.append(EVENT_ESCAPED)
            return REWARD_WIN
        self.events.append(EVENT_NEED_LOOT)      # a hint for the GUI
        return 0.0

    def _check_exhausted(self):
        if self.thief.is_exhausted():
            self.status = STATUS_EXHAUSTED
            self.events.append(EVENT_EXHAUSTED)
            return REWARD_EXHAUSTED
        return 0.0

    def _check_caught(self):
        if self.security.guard_is_touching(self.thief.position):
            self.status = STATUS_CAUGHT
            self.events.append(EVENT_CAUGHT)
            return REWARD_CAUGHT
        return 0.0

    # ------------------------------------------------------------------
    # Security and alert level
    # ------------------------------------------------------------------
    def _update_security(self):
        """Move guards and cameras, then work out the new alert level."""
        seen_by_camera, seen_by_guard = self.security.update(
            self.vault, self.thief.position, self.alert_level, self.last_known_pos)

        reward = 0.0
        if seen_by_camera and not self._seen_by_camera_before:
            self.events.append(EVENT_SPOTTED_BY_CAMERA)
            reward += REWARD_SPOTTED
        if seen_by_guard and not self._seen_by_guard_before:
            self.events.append(EVENT_SPOTTED_BY_GUARD)
            reward += REWARD_SPOTTED
        self._seen_by_camera_before = seen_by_camera
        self._seen_by_guard_before = seen_by_guard

        self._update_alert(seen_by_camera or seen_by_guard)
        return reward

    def _update_alert(self, thief_is_seen):
        """
        Alert rules:
          * Being seen sets ALARM and remembers where the thief was.
          * Standing in a restricted area makes the system SUSPICIOUS.
          * With nothing new, the alert slowly drops one level at a time.
        """
        if thief_is_seen:
            self.alert_level = ALERT_ALARM
            self.alert_timer = ALARM_HOLD_TICKS
            self.last_known_pos = self.thief.position
            return

        in_restricted = self.vault.is_restricted(self.thief.x, self.thief.y)
        if in_restricted and self.alert_level <= ALERT_SUSPICIOUS:
            self.alert_level = ALERT_SUSPICIOUS
            self.alert_timer = SUSPICIOUS_HOLD_TICKS
            return

        if self.alert_level > ALERT_CALM:
            self.alert_timer -= 1
            if self.alert_timer <= 0:
                self.alert_level -= 1
                self.alert_timer = SUSPICIOUS_HOLD_TICKS
                if self.alert_level == ALERT_CALM:
                    self.last_known_pos = None
