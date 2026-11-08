"""
environment package - the game rules, with no graphics.

Quick tour:
    vault.py     the map, doors and items
    player.py    the thief
    security.py  guards, cameras and the security system
    game.py      the rules and the reset / get_state / step interface
"""

from environment.game import Game

__all__ = ["Game"]
