"""
Tests for the game rules (no window, no Pygame needed).

Run from the project folder with:
    python -m unittest discover -s tests -v

Most tests use Game(with_security=False): an empty facility with no guards or
cameras, so only the rule being tested can affect the result.
"""

import os
import sys
import unittest
from collections import deque

# Make "environment" importable no matter where the tests are started from.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from environment.game import (
    Game, ACTION_WAIT, ACTION_UP, ACTION_DOWN, ACTION_LEFT, ACTION_RIGHT,
    STATUS_PLAYING, STATUS_WON, STATUS_CAUGHT, STATUS_EXHAUSTED,
    ALERT_CALM, ALERT_SUSPICIOUS, ALERT_ALARM,
    MOVE_ENERGY_COST, ENERGY_CELL_AMOUNT,
    EVENT_KEY_COLLECTED, EVENT_DOOR_UNLOCKED, EVENT_DOOR_LOCKED,
    EVENT_LOOT_COLLECTED, EVENT_SPOTTED_BY_CAMERA,
)
from environment.vault import (
    Vault, ITEM_KEY, ITEM_GOLD, ITEM_ENERGY, LOOT_VALUES, OPEN_DOOR, DIRECTIONS,
)
from environment.player import MAX_ENERGY
from environment.security import Camera, Guard, build_route, compute_visible_tiles


def make_game():
    """A game with no guards or cameras."""
    return Game(with_security=False)


def place_thief(game, x, y):
    """Teleport the thief (tests only)."""
    game.thief.x = x
    game.thief.y = y


def find_item(game, kind):
    """Return the position of the first item of the given kind."""
    for position, item in game.vault.items.items():
        if item == kind:
            return position
    return None


class TestSetup(unittest.TestCase):
    def test_reset_gives_a_fresh_game(self):
        game = make_game()
        game.step(ACTION_UP)
        game.reset()
        self.assertEqual(game.thief.position, game.vault.start)
        self.assertEqual(game.thief.energy, MAX_ENERGY)
        self.assertEqual(game.status, STATUS_PLAYING)
        self.assertEqual(game.tick, 0)

    def test_state_has_expected_information(self):
        state = Game().get_state()
        for key in ("thief", "guards", "cameras", "alert_level", "status",
                    "locked_doors", "items", "exit"):
            self.assertIn(key, state)

    def test_step_returns_state_reward_done_info(self):
        result = make_game().step(ACTION_WAIT)
        self.assertEqual(len(result), 4)
        state, reward, done, info = result
        self.assertIsInstance(state, dict)
        self.assertIsInstance(reward, float)
        self.assertFalse(done)
        self.assertIn("events", info)

    def test_level_has_required_features(self):
        vault = Vault()
        self.assertGreaterEqual(len(vault.locked_door_positions()), 1)
        self.assertIsNotNone(find_item_in_vault(vault, ITEM_KEY))
        self.assertIsNotNone(find_item_in_vault(vault, ITEM_GOLD))
        self.assertNotEqual(vault.start, vault.exit_pos)
        self.assertGreaterEqual(len(vault.guard_routes), 1)
        self.assertGreaterEqual(len(vault.camera_setups), 1)

    def test_game_can_have_guards_and_cameras(self):
        game = Game()
        self.assertGreaterEqual(len(game.security.guards), 1)
        self.assertGreaterEqual(len(game.security.cameras), 1)


def find_item_in_vault(vault, kind):
    for position, item in vault.items.items():
        if item == kind:
            return position
    return None


class TestMovement(unittest.TestCase):
    def test_thief_moves_in_all_four_directions(self):
        game = make_game()
        place_thief(game, 3, 8)                     # open hallway tile
        game.step(ACTION_RIGHT)
        self.assertEqual(game.thief.position, (4, 8))
        game.step(ACTION_LEFT)
        self.assertEqual(game.thief.position, (3, 8))
        game.step(ACTION_UP)
        self.assertEqual(game.thief.position, (3, 7))
        game.step(ACTION_DOWN)
        self.assertEqual(game.thief.position, (3, 8))

    def test_walls_block_movement(self):
        game = make_game()
        place_thief(game, 1, 8)                     # next to the left outer wall
        game.step(ACTION_LEFT)
        self.assertEqual(game.thief.position, (1, 8))

    def test_wait_does_not_move(self):
        game = make_game()
        start = game.thief.position
        game.step(ACTION_WAIT)
        self.assertEqual(game.thief.position, start)

    def test_moving_costs_energy(self):
        game = make_game()
        place_thief(game, 3, 8)
        game.step(ACTION_RIGHT)
        self.assertAlmostEqual(game.thief.energy, MAX_ENERGY - MOVE_ENERGY_COST)

    def test_normal_doors_can_be_walked_through(self):
        game = make_game()
        place_thief(game, 4, 8)
        game.step(ACTION_DOWN)                      # onto the door at (4, 9)
        self.assertEqual(game.thief.position, (4, 9))


class TestKeyAndDoor(unittest.TestCase):
    def test_collecting_the_key(self):
        game = make_game()
        key_x, key_y = find_item(game, ITEM_KEY)
        place_thief(game, key_x + 1, key_y)
        _, _, _, info = game.step(ACTION_LEFT)
        self.assertTrue(game.thief.has_key)
        self.assertIn(EVENT_KEY_COLLECTED, info["events"])
        self.assertIsNone(find_item(game, ITEM_KEY))

    def test_locked_door_blocks_without_key(self):
        game = make_game()
        door_x, door_y = game.vault.locked_door_positions()[0]
        place_thief(game, door_x, door_y + 1)       # in the hallway below the door
        _, _, _, info = game.step(ACTION_UP)
        self.assertEqual(game.thief.position, (door_x, door_y + 1))
        self.assertIn(EVENT_DOOR_LOCKED, info["events"])
        self.assertTrue(game.vault.is_locked_door(door_x, door_y))

    def test_key_unlocks_the_door(self):
        game = make_game()
        door_x, door_y = game.vault.locked_door_positions()[0]
        place_thief(game, door_x, door_y + 1)
        game.thief.has_key = True
        _, _, _, info = game.step(ACTION_UP)
        self.assertIn(EVENT_DOOR_UNLOCKED, info["events"])
        self.assertEqual(game.vault.tile_at(door_x, door_y), OPEN_DOOR)
        self.assertFalse(game.thief.has_key)        # key is used up
        game.step(ACTION_UP)                        # now we can walk through
        self.assertEqual(game.thief.position, (door_x, door_y))


class TestVaultDoors(unittest.TestCase):
    def test_unlocking_updates_the_locked_door_list(self):
        vault = Vault()
        door = vault.locked_door_positions()[0]
        vault.unlock_door(*door)
        self.assertEqual(vault.locked_door_positions(), [])
        self.assertTrue(vault.is_walkable(*door))

    def test_reset_locks_the_door_again(self):
        game = make_game()
        game.vault.unlock_door(*game.vault.locked_door_positions()[0])
        game.reset()
        self.assertEqual(len(game.vault.locked_door_positions()), 1)


class TestLootAndEnergy(unittest.TestCase):
    def test_collecting_loot(self):
        game = make_game()
        loot_x, loot_y = find_item(game, ITEM_GOLD)
        place_thief(game, loot_x + 1, loot_y)
        _, _, _, info = game.step(ACTION_LEFT)
        self.assertEqual(game.thief.loot_count, 1)
        self.assertEqual(game.thief.loot_value, LOOT_VALUES[ITEM_GOLD])
        self.assertIn(EVENT_LOOT_COLLECTED, info["events"])
        self.assertIsNone(game.vault.items.get((loot_x, loot_y)))

    def test_carrying_loot_costs_more_energy(self):
        free = make_game()
        loaded = make_game()
        for game in (free, loaded):
            place_thief(game, 3, 8)
        loaded.thief.add_loot(100)
        free.step(ACTION_RIGHT)
        loaded.step(ACTION_RIGHT)
        self.assertLess(loaded.thief.energy, free.thief.energy)

    def test_energy_cell_restores_energy(self):
        game = make_game()
        cell_x, cell_y = find_item(game, ITEM_ENERGY)
        place_thief(game, cell_x + 1, cell_y)
        game.thief.energy = 30.0
        game.step(ACTION_LEFT)
        self.assertGreater(game.thief.energy, 30.0 + ENERGY_CELL_AMOUNT - 1)

    def test_energy_never_goes_above_maximum(self):
        game = make_game()
        game.thief.restore_energy(500)
        self.assertEqual(game.thief.energy, MAX_ENERGY)


class TestWinAndLose(unittest.TestCase):
    def test_escaping_with_loot_wins(self):
        game = make_game()
        exit_x, exit_y = game.vault.exit_pos
        place_thief(game, exit_x - 1, exit_y)
        game.thief.add_loot(100)
        _, reward, done, _ = game.step(ACTION_RIGHT)
        self.assertEqual(game.status, STATUS_WON)
        self.assertTrue(done)
        self.assertGreater(reward, 0)

    def test_exit_without_loot_does_not_win(self):
        game = make_game()
        exit_x, exit_y = game.vault.exit_pos
        place_thief(game, exit_x - 1, exit_y)
        game.step(ACTION_RIGHT)
        self.assertEqual(game.status, STATUS_PLAYING)

    def test_running_out_of_energy_loses(self):
        game = make_game()
        place_thief(game, 3, 8)
        game.thief.energy = 0.1
        _, reward, done, _ = game.step(ACTION_RIGHT)
        self.assertEqual(game.status, STATUS_EXHAUSTED)
        self.assertTrue(done)
        self.assertLess(reward, 0)

    def test_guard_next_to_thief_catches_it(self):
        game = Game()
        guard = game.security.guards[0]
        place_thief(game, 8, 8)
        guard.x, guard.y = 9, 8
        _, reward, done, _ = game.step(ACTION_WAIT)
        self.assertEqual(game.status, STATUS_CAUGHT)
        self.assertTrue(done)
        self.assertLess(reward, 0)

    def test_nothing_changes_after_game_over(self):
        game = make_game()
        game.status = STATUS_CAUGHT
        position = game.thief.position
        _, _, done, _ = game.step(ACTION_UP)
        self.assertTrue(done)
        self.assertEqual(game.thief.position, position)


class TestSecurity(unittest.TestCase):
    def test_camera_spotting_the_thief_raises_the_alarm(self):
        game = Game()
        game.security.guards.clear()
        camera = game.security.cameras[0]
        # Stand two tiles in front of the camera.
        fx, fy = camera.facing
        place_thief(game, camera.x + fx * 2, camera.y + fy * 2)
        _, _, _, info = game.step(ACTION_WAIT)
        self.assertEqual(game.alert_level, ALERT_ALARM)
        self.assertIn(EVENT_SPOTTED_BY_CAMERA, info["events"])

    def test_restricted_area_makes_system_suspicious(self):
        game = make_game()
        door_x, door_y = 13, 6                       # door into the security office
        place_thief(game, door_x, door_y)
        game.step(ACTION_UP)                         # step into the office (13, 5)
        self.assertEqual(game.alert_level, ALERT_SUSPICIOUS)

    def test_alert_calms_down_over_time(self):
        game = make_game()
        game.alert_level = ALERT_ALARM
        game.alert_timer = 3
        place_thief(game, 3, 8)
        for _ in range(200):
            game.step(ACTION_WAIT)
            game.thief.energy = MAX_ENERGY           # keep the thief alive
        self.assertEqual(game.alert_level, ALERT_CALM)

    def test_walls_block_vision(self):
        vault = Vault()
        # Looking right along row 2, the solid wall at x=9 hides the room beyond it.
        tiles = compute_visible_tiles(vault, (6, 2), (1, 0), 5)
        self.assertNotIn((10, 2), tiles)
        self.assertIn((7, 2), tiles)
        # Row 3 has an open doorway at x=9, so the view passes through it.
        tiles = compute_visible_tiles(vault, (6, 3), (1, 0), 5)
        self.assertIn((10, 3), tiles)

    def test_guard_patrols_along_its_route(self):
        vault = Vault()
        guard = Guard(build_route(vault.guard_routes[0]))
        start = guard.position
        for _ in range(60):
            guard.update(vault, (-5, -5), ALERT_CALM, None)
        self.assertNotEqual(guard.position, start)
        for tile in [guard.position]:
            self.assertTrue(vault.is_walkable(*tile))

    def test_guard_chases_a_visible_thief(self):
        vault = Vault()
        guard = Guard(build_route(vault.guard_routes[0]))
        guard.x, guard.y = 5, 7
        guard.facing = (1, 0)
        guard.update(vault, (8, 7), ALERT_CALM, None)
        self.assertEqual(guard.mode, "chase")

    def test_camera_turns_between_directions(self):
        vault = Vault()
        camera = Camera(26, 1, ["left", "down"])
        first = camera.facing
        for _ in range(20):
            camera.update(vault)
        self.assertNotEqual(camera.facing, first)


class TestLevelCanBeCompleted(unittest.TestCase):
    """Ignoring guards, is there a path start -> key -> door -> loot -> exit?"""

    def reachable(self, vault, start, goal, can_pass_locked_doors):
        queue = deque([start])
        seen = {start}
        while queue:
            x, y = queue.popleft()
            if (x, y) == goal:
                return True
            for dx, dy in DIRECTIONS.values():
                nxt = (x + dx, y + dy)
                if nxt in seen or vault.is_wall(*nxt):
                    continue
                if vault.is_locked_door(*nxt) and not can_pass_locked_doors:
                    continue
                seen.add(nxt)
                queue.append(nxt)
        return False

    def test_key_is_reachable_without_unlocking(self):
        vault = Vault()
        key = find_item_in_vault(vault, ITEM_KEY)
        self.assertTrue(self.reachable(vault, vault.start, key, False))

    def test_loot_needs_the_locked_door(self):
        vault = Vault()
        loot_tiles = [p for p, k in vault.items.items() if k in LOOT_VALUES]
        for loot in loot_tiles:
            self.assertFalse(self.reachable(vault, vault.start, loot, False))
            self.assertTrue(self.reachable(vault, vault.start, loot, True))

    def test_exit_is_reachable_from_the_vault(self):
        vault = Vault()
        loot = find_item_in_vault(vault, ITEM_GOLD)
        self.assertTrue(self.reachable(vault, loot, vault.exit_pos, True))

    def test_every_guard_route_is_walkable(self):
        vault = Vault()
        for corners in vault.guard_routes:
            for x, y in build_route(corners):
                self.assertTrue(vault.is_walkable(x, y), (x, y))


if __name__ == "__main__":
    unittest.main()
