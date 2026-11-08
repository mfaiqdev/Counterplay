"""
COUNTERPLAY: Where AI Takes on AI
=================================
Run this file to start the game:

    python main.py

main.py is the "glue": it reads the keyboard, asks the Game (environment/)
to advance, and asks the Renderer (gui/) to draw.  It contains no game rules.
"""

import os
import sys

import pygame

from environment.game import (
    Game, ACTION_WAIT, ACTION_UP, ACTION_DOWN, ACTION_LEFT, ACTION_RIGHT,
    STATUS_PLAYING, STATUS_WON, STATUS_CAUGHT,
)
from gui.renderer import Renderer, COLORS, WINDOW_WIDTH, WINDOW_HEIGHT
from gui.menu import ButtonMenu, InstructionsScreen

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
FPS = 60
STEP_INTERVAL = 0.12        # seconds per game tick (one thief step)
END_SCREEN_DELAY = 0.9      # seconds to look at the final moment before the menu
FADE_SPEED = 4.0            # screen fade-in speed (higher = quicker)

# Screens (the "state" of the application)
SCREEN_MENU = "menu"
SCREEN_INSTRUCTIONS = "instructions"
SCREEN_PLAYING = "playing"
SCREEN_PAUSED = "paused"
SCREEN_ENDED = "ended"

# Which keys move the thief
MOVE_KEYS = {
    pygame.K_w: ACTION_UP, pygame.K_UP: ACTION_UP,
    pygame.K_s: ACTION_DOWN, pygame.K_DOWN: ACTION_DOWN,
    pygame.K_a: ACTION_LEFT, pygame.K_LEFT: ACTION_LEFT,
    pygame.K_d: ACTION_RIGHT, pygame.K_RIGHT: ACTION_RIGHT,
}


class App:
    """Owns the window, the current screen, and the game loop."""

    def __init__(self, screen):
        self.screen = screen
        self.fade = 0.0                 # 1.0 = fully black, fades to 0 on screen changes
        self.game = Game()
        self.renderer = Renderer(self.game)

        self._screen_name = SCREEN_MENU
        self.previous_screen = SCREEN_MENU      # where "Back" goes from instructions
        self.running = True

        self.main_menu = self._make_main_menu()
        self.pause_menu = self._make_pause_menu()
        self.end_menu = None
        self.instructions = InstructionsScreen()

        # Input and timing for gameplay
        self.held_actions = []          # movement keys currently held (latest last)
        self.queued_action = None       # a quick tap that has not been used yet
        self.step_timer = 0.0
        self.end_timer = 0.0
        self.waiting_for_input = True   # the mission starts on the first key press

    # The fade plays whenever we switch to a different screen
    # (except pausing and resuming, which should feel instant).
    @property
    def screen_name(self):
        return self._screen_name

    @screen_name.setter
    def screen_name(self, new_name):
        old_name = self._screen_name
        if new_name != old_name and SCREEN_PAUSED not in (new_name, old_name):
            self.fade = 1.0
        self._screen_name = new_name

    # ------------------------------------------------------------------
    # Building menus
    # ------------------------------------------------------------------
    def _make_main_menu(self):
        return ButtonMenu(
            "COUNTERPLAY",
            [("Start Mission", "start"), ("How to Play", "help"), ("Quit", "quit")],
            subtitle="Where AI Takes on AI",
            lines=["Steal the loot. Beat the security. Escape."],
            layout="left",
        )

    def _make_pause_menu(self):
        return ButtonMenu(
            "PAUSED",
            [("Resume", "resume"), ("Restart Mission", "restart"),
             ("How to Play", "help"), ("Main Menu", "menu")],
            subtitle="The facility waits for you.",
        )

    def _make_end_menu(self):
        """Build the victory or defeat screen from the final game status."""
        thief = self.game.thief
        stats = [
            "Steps taken:   " + str(thief.steps_taken),
            "Loot value:    $" + str(thief.loot_value),
            "Energy left:   " + str(int(thief.energy)),
        ]
        if self.game.status == STATUS_WON:
            title, subtitle, color = "MISSION COMPLETE", "You escaped with the loot.", COLORS["green"]
        elif self.game.status == STATUS_CAUGHT:
            title, subtitle, color = "BUSTED", "Security caught the thief.", COLORS["red"]
        else:
            title, subtitle, color = "OUT OF ENERGY", "The thief collapsed before escaping.", COLORS["orange"]
        return ButtonMenu(
            title,
            [("Play Again", "restart"), ("Main Menu", "menu")],
            subtitle=subtitle, lines=stats, title_color=color,
        )

    # ------------------------------------------------------------------
    # Changing screens
    # ------------------------------------------------------------------
    def start_new_game(self):
        self.game.reset()
        self.renderer.set_game(self.game)
        self.held_actions = []
        self.queued_action = None
        self.step_timer = 0.0
        self.waiting_for_input = True
        self.renderer.elapsed_seconds = 0.0
        self.screen_name = SCREEN_PLAYING

    def go_to_menu(self):
        self.main_menu = self._make_main_menu()
        self.screen_name = SCREEN_MENU

    def open_instructions(self):
        self.previous_screen = self.screen_name
        self.screen_name = SCREEN_INSTRUCTIONS

    def pause(self):
        self.pause_menu = self._make_pause_menu()
        self.held_actions = []
        self.screen_name = SCREEN_PAUSED

    # ------------------------------------------------------------------
    # Handling input events
    # ------------------------------------------------------------------
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
            pygame.display.toggle_fullscreen()
            return

        if self.screen_name == SCREEN_MENU:
            self._apply_menu_action(self.main_menu.handle_event(event))
        elif self.screen_name == SCREEN_INSTRUCTIONS:
            if self.instructions.handle_event(event) == "back":
                self.screen_name = self.previous_screen
        elif self.screen_name == SCREEN_PLAYING:
            self._handle_playing_event(event)
        elif self.screen_name == SCREEN_PAUSED:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
                self.screen_name = SCREEN_PLAYING
            else:
                self._apply_menu_action(self.pause_menu.handle_event(event))
        elif self.screen_name == SCREEN_ENDED and self.end_timer >= END_SCREEN_DELAY:
            self._apply_menu_action(self.end_menu.handle_event(event))

    def _handle_playing_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in MOVE_KEYS:
                action = MOVE_KEYS[event.key]
                if action in self.held_actions:
                    self.held_actions.remove(action)
                self.held_actions.append(action)
                self.queued_action = action
                self._react_quickly()
            elif event.key == pygame.K_SPACE:
                self.queued_action = ACTION_WAIT
                self._react_quickly()
            elif event.key == pygame.K_F1:
                self.renderer.show_debug_tiles = not self.renderer.show_debug_tiles
            elif event.key in (pygame.K_ESCAPE, pygame.K_p):
                self.pause()
            elif event.key == pygame.K_r:
                self.start_new_game()
        elif event.type == pygame.KEYUP and event.key in MOVE_KEYS:
            action = MOVE_KEYS[event.key]
            if action in self.held_actions:
                self.held_actions.remove(action)
        elif event.type == pygame.WINDOWFOCUSLOST:
            self.pause()

    def _react_quickly(self):
        """
        Make a key press feel instant: the first press starts the mission, and
        a press that comes after a long enough pause moves right away instead
        of waiting for the next tick.
        """
        if self.waiting_for_input:
            self.waiting_for_input = False
            self.step_timer = STEP_INTERVAL
        elif self.step_timer >= STEP_INTERVAL * 0.5:
            self.step_timer = STEP_INTERVAL

    def _apply_menu_action(self, action):
        """Do what the chosen menu button says."""
        if action is None:
            return
        if action in ("start", "restart"):
            self.start_new_game()
        elif action == "resume":
            self.screen_name = SCREEN_PLAYING
        elif action == "help":
            self.open_instructions()
        elif action == "menu":
            self.go_to_menu()
        elif action == "quit":
            self.running = False

    # ------------------------------------------------------------------
    # Updating
    # ------------------------------------------------------------------
    def update(self, dt):
        self.fade = max(0.0, self.fade - dt * FADE_SPEED)
        if self.screen_name == SCREEN_PLAYING:
            self._update_playing(dt)
        elif self.screen_name == SCREEN_ENDED:
            self.end_timer += dt
        # Animations keep running on the paused and ended screens too
        if self.screen_name in (SCREEN_PLAYING, SCREEN_ENDED):
            self.renderer.update(dt)

    def _update_playing(self, dt):
        if self.waiting_for_input:
            return                          # nothing moves until the player does
        self.renderer.elapsed_seconds += dt
        self.step_timer += dt
        while self.step_timer >= STEP_INTERVAL and self.game.status == STATUS_PLAYING:
            self.step_timer -= STEP_INTERVAL
            self._do_game_step(self._choose_action())
        if self.game.status != STATUS_PLAYING:
            self._finish_game()

    def _choose_action(self):
        """A tapped key wins; otherwise use the latest held key; otherwise wait."""
        if self.queued_action is not None:
            action = self.queued_action
            self.queued_action = None
            return action
        if self.held_actions:
            return self.held_actions[-1]
        return ACTION_WAIT

    def _do_game_step(self, action):
        _state, _reward, _done, info = self.game.step(action)
        self.renderer.handle_events(info["events"])

    def _finish_game(self):
        self.end_menu = self._make_end_menu()
        self.end_timer = 0.0
        self.screen_name = SCREEN_ENDED

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def draw(self):
        if self.screen_name == SCREEN_MENU:
            self.main_menu.draw(self.screen)
        elif self.screen_name == SCREEN_INSTRUCTIONS:
            self.instructions.draw(self.screen)
        else:
            self.renderer.draw(self.screen)
            if self.screen_name == SCREEN_PLAYING and self.waiting_for_input:
                self.renderer.draw_banner(self.screen, "MISSION READY",
                                          "Press W A S D or an arrow key to begin")
            elif self.screen_name == SCREEN_PAUSED:
                self.pause_menu.draw(self.screen)
            elif self.screen_name == SCREEN_ENDED and self.end_timer >= END_SCREEN_DELAY:
                self.end_menu.draw(self.screen)
        self._draw_fade()

    def _draw_fade(self):
        """Black overlay that fades away after a screen change."""
        if self.fade <= 0:
            return
        veil = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        veil.set_alpha(int(255 * self.fade * 0.85))
        self.screen.blit(veil, (0, 0))

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self):
        clock = pygame.time.Clock()
        while self.running:
            dt = min(clock.tick(FPS) / 1000.0, 0.1)    # cap dt after window drags
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.draw()
            pygame.display.flip()


def load_window_icon():
    """Use assets/icon.png as the window icon if it exists."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.png")
    try:
        pygame.display.set_icon(pygame.image.load(path))
    except (pygame.error, FileNotFoundError):
        pass                                    # the icon is optional


def create_window():
    """
    Open the game window.  SCALED lets the window be resized (the picture
    scales to fit) and vsync keeps the motion smooth.  If the computer does not
    support that, fall back to a plain fixed-size window.
    """
    size = (WINDOW_WIDTH, WINDOW_HEIGHT)
    try:
        return pygame.display.set_mode(size, pygame.SCALED | pygame.RESIZABLE, vsync=1)
    except pygame.error:
        return pygame.display.set_mode(size)


def main():
    pygame.init()
    load_window_icon()
    pygame.display.set_caption("COUNTERPLAY - Where AI Takes on AI")
    screen = create_window()
    App(screen).run()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
