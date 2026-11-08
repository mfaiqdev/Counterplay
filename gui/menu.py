"""
menu.py - Menus and non-gameplay screens.

    ButtonMenu          a title + optional text lines + a list of buttons.
                        Used for the main menu, pause menu and the
                        victory / defeat screens.
    InstructionsScreen  the "How to play" page.

Every handle_event() returns an action string (like "start" or "quit") when
the player picks something, otherwise None.  main.py decides what to do.
"""

import pygame

from environment.vault import Vault, WALL
from gui.renderer import (
    COLORS, WINDOW_WIDTH, WINDOW_HEIGHT, get_font, draw_text,
    draw_thief, draw_guard, draw_camera, draw_key, draw_door, draw_padlock,
    draw_gold, draw_gem, draw_energy_cell, draw_exit,
)
from environment.vault import LOCKED_DOOR


# ---------------------------------------------------------------------------
# Backgrounds
# ---------------------------------------------------------------------------
def draw_menu_background(screen, with_blueprint=False):
    """Dark background with a faint grid. Optionally a mini facility map."""
    screen.fill(COLORS["background"])
    grid_color = (15, 20, 29)
    for x in range(0, WINDOW_WIDTH, 40):
        pygame.draw.line(screen, grid_color, (x, 0), (x, WINDOW_HEIGHT))
    for y in range(0, WINDOW_HEIGHT, 40):
        pygame.draw.line(screen, grid_color, (0, y), (WINDOW_WIDTH, y))
    if with_blueprint:
        _draw_blueprint(screen, 604, 220, 17)


def _draw_blueprint(screen, left, top, tile):
    """A small decorative picture of the facility walls."""
    vault = Vault()
    for y in range(vault.height):
        for x in range(vault.width):
            rect = pygame.Rect(left + x * tile, top + y * tile, tile, tile)
            if vault.tile_at(x, y) == WALL:
                pygame.draw.rect(screen, (30, 40, 58), rect)
            elif vault.is_restricted(x, y):
                pygame.draw.rect(screen, (34, 20, 28), rect)
    # Mark start, vault door and exit
    for position, color in [(vault.start, COLORS["accent"]),
                            (vault.exit_pos, COLORS["green"]),
                            (vault.locked_door_positions()[0], COLORS["red"])]:
        center = (left + position[0] * tile + tile // 2, top + position[1] * tile + tile // 2)
        pygame.draw.circle(screen, color, center, 5)
    outline = pygame.Rect(left - 8, top - 8, vault.width * tile + 16, vault.height * tile + 16)
    pygame.draw.rect(screen, COLORS["border"], outline, 1, border_radius=8)


# ---------------------------------------------------------------------------
# Buttons
# ---------------------------------------------------------------------------
class Button:
    def __init__(self, label, action, rect):
        self.label = label
        self.action = action
        self.rect = rect

    def draw(self, screen, selected, primary):
        font = get_font(19, True)
        if selected:
            fill, border, text = COLORS["accent"], COLORS["accent"], (6, 20, 26)
        elif primary:
            fill, border, text = COLORS["panel_light"], COLORS["accent"], COLORS["text"]
        else:
            fill, border, text = COLORS["panel_light"], COLORS["border"], COLORS["text"]
        pygame.draw.rect(screen, fill, self.rect, border_radius=8)
        pygame.draw.rect(screen, border, self.rect, 1, border_radius=8)
        if selected:                                    # little marker on the left
            marker = pygame.Rect(self.rect.x + 14, self.rect.centery - 8, 4, 16)
            pygame.draw.rect(screen, (6, 20, 26), marker, border_radius=2)
        draw_text(screen, self.label, font, text, self.rect.center, "center")


class ButtonMenu:
    """
    A vertical list of buttons with a title.

    layout="left"   - text on the left (main menu, with the blueprint on the right)
    layout="panel"  - a centred panel (pause / win / lose screens)
    """

    def __init__(self, title, buttons, subtitle="", lines=None,
                 layout="panel", title_color=None):
        self.title = title
        self.subtitle = subtitle
        self.lines = lines or []
        self.layout = layout
        self.title_color = title_color or COLORS["text"]
        self.selected = 0
        self.button_specs = buttons          # list of (label, action)
        self._build_buttons()

    # -- layout --------------------------------------------------------
    def _build_buttons(self):
        width, height, gap = 320, 52, 14
        if self.layout == "left":
            left, top = 90, 330
        else:
            self.panel_rect = self._panel_rect(width, height, gap)
            left = self.panel_rect.centerx - width // 2
            top = self.panel_rect.bottom - 36 - len(self.button_specs) * (height + gap) + gap
        self.buttons = []
        for index, (label, action) in enumerate(self.button_specs):
            rect = pygame.Rect(left, top + index * (height + gap), width, height)
            self.buttons.append(Button(label, action, rect))

    def _panel_rect(self, width, height, gap):
        header = 120 + len(self.lines) * 30
        total = header + len(self.button_specs) * (height + gap) + 50
        rect = pygame.Rect(0, 0, 500, total)
        rect.center = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)
        return rect

    # -- input ---------------------------------------------------------
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.buttons)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.buttons)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                return self.buttons[self.selected].action
        elif event.type == pygame.MOUSEMOTION:
            for index, button in enumerate(self.buttons):
                if button.rect.collidepoint(event.pos):
                    self.selected = index
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for button in self.buttons:
                if button.rect.collidepoint(event.pos):
                    return button.action
        return None

    # -- drawing -------------------------------------------------------
    def draw(self, screen):
        if self.layout == "left":
            self._draw_left(screen)
        else:
            self._draw_panel(screen)

    def _draw_left(self, screen):
        draw_menu_background(screen, with_blueprint=True)
        pygame.draw.rect(screen, COLORS["accent"], (90, 130, 56, 4))
        draw_text(screen, self.title, get_font(60, True), COLORS["text"], (88, 154))
        draw_text(screen, self.subtitle, get_font(22), COLORS["accent"], (90, 232))
        for index, line in enumerate(self.lines):
            draw_text(screen, line, get_font(16), COLORS["muted"], (90, 272 + index * 24))
        self._draw_buttons(screen)
        draw_text(screen, "UP / DOWN to choose   ENTER to confirm   F11 fullscreen",
                  get_font(13), COLORS["muted"], (90, WINDOW_HEIGHT - 66))
        draw_text(screen, "DSA + AI Semester Project  |  Starter version 0.2",
                  get_font(13), COLORS["muted"], (90, WINDOW_HEIGHT - 40))

    def _draw_panel(self, screen):
        # Dim whatever is behind the panel (usually the paused game)
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((6, 8, 12, 190))
        screen.blit(dim, (0, 0))

        pygame.draw.rect(screen, COLORS["panel"], self.panel_rect, border_radius=14)
        pygame.draw.rect(screen, COLORS["border"], self.panel_rect, 1, border_radius=14)
        pygame.draw.rect(screen, self.title_color,
                         (self.panel_rect.x + 30, self.panel_rect.y + 28, 44, 4))

        draw_text(screen, self.title, get_font(38, True), self.title_color,
                  (self.panel_rect.x + 30, self.panel_rect.y + 42))
        draw_text(screen, self.subtitle, get_font(17), COLORS["muted"],
                  (self.panel_rect.x + 30, self.panel_rect.y + 92))
        for index, line in enumerate(self.lines):
            draw_text(screen, line, get_font(17), COLORS["text"],
                      (self.panel_rect.x + 30, self.panel_rect.y + 130 + index * 30))
        self._draw_buttons(screen)

    def _draw_buttons(self, screen):
        for index, button in enumerate(self.buttons):
            button.draw(screen, index == self.selected, primary=(index == 0))


# ---------------------------------------------------------------------------
# Instructions screen
# ---------------------------------------------------------------------------
class InstructionsScreen:
    """The 'How to play' page: objective, controls and a legend of symbols."""

    OBJECTIVE_STEPS = [
        "Find the KEY hidden in the top-left room.",
        "Use it on the locked VAULT DOOR (red, top right).",
        "Steal at least one piece of LOOT inside the vault.",
        "Run to the EXIT in the bottom-right corner.",
    ]

    CONTROLS = [
        ("W A S D / Arrows", "Move the thief"),
        ("Space", "Stand still"),
        ("P or Esc", "Pause"),
        ("R", "Restart the mission"),
        ("F11 / F1", "Fullscreen / show detection tiles"),
    ]

    RULES = [
        "Guards and cameras see in a cone of light. Stay out of the light.",
        "Being seen raises the ALERT. Guards then hunt you.",
        "Every step costs ENERGY (more while carrying loot).",
        "Energy cells restore energy. Run out and you lose.",
    ]

    def __init__(self):
        self.back_button = Button("Back", "back", pygame.Rect(600, WINDOW_HEIGHT - 76, 200, 46))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (
                pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
            return "back"
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.back_button.rect.collidepoint(event.pos):
                return "back"
        return None

    def draw(self, screen):
        draw_menu_background(screen)
        pygame.draw.rect(screen, COLORS["accent"], (60, 40, 56, 4))
        draw_text(screen, "How to play", get_font(40, True), COLORS["text"], (60, 56))

        self._draw_objective(screen, 60, 112)
        self._draw_controls(screen, 60, 312)
        self._draw_legend(screen, 600, 112)
        self._draw_rules(screen, 60, 524)
        self.back_button.draw(screen, selected=True, primary=True)

    def _section_title(self, screen, text, x, y):
        draw_text(screen, text, get_font(14, True), COLORS["accent"], (x, y))

    def _draw_objective(self, screen, x, y):
        self._section_title(screen, "OBJECTIVE", x, y)
        for index, step in enumerate(self.OBJECTIVE_STEPS):
            row_y = y + 30 + index * 40
            badge = pygame.Rect(x, row_y, 28, 28)
            pygame.draw.rect(screen, COLORS["panel_light"], badge, border_radius=14)
            pygame.draw.rect(screen, COLORS["accent"], badge, 1, border_radius=14)
            draw_text(screen, str(index + 1), get_font(15, True), COLORS["accent"],
                      badge.center, "center")
            draw_text(screen, step, get_font(17), COLORS["text"], (x + 42, row_y + 14), "midleft")

    def _draw_controls(self, screen, x, y):
        self._section_title(screen, "CONTROLS", x, y)
        for index, (keys, action) in enumerate(self.CONTROLS):
            row_y = y + 28 + index * 34
            chip = pygame.Rect(x, row_y, 170, 28)
            pygame.draw.rect(screen, COLORS["panel_light"], chip, border_radius=6)
            pygame.draw.rect(screen, COLORS["border"], chip, 1, border_radius=6)
            draw_text(screen, keys, get_font(14, True), COLORS["text"], chip.center, "center")
            draw_text(screen, action, get_font(17), COLORS["muted"], (x + 190, row_y + 14),
                      "midleft")

    def _draw_rules(self, screen, x, y):
        self._section_title(screen, "GOOD TO KNOW", x, y)
        for index, rule in enumerate(self.RULES):
            draw_text(screen, rule, get_font(15), COLORS["muted"], (x, y + 28 + index * 24))

    def _draw_legend(self, screen, x, y):
        self._section_title(screen, "LEGEND", x, y)
        panel = pygame.Rect(x, y + 28, 460, 470)
        pygame.draw.rect(screen, COLORS["panel"], panel, border_radius=10)
        pygame.draw.rect(screen, COLORS["border"], panel, 1, border_radius=10)

        size = 40
        entries = [
            ("Thief (you)", lambda cx, cy: draw_thief(screen, cx, cy, size)),
            ("Guard - patrols and chases", lambda cx, cy: draw_guard(screen, cx, cy, size)),
            ("Security camera", lambda cx, cy: draw_camera(screen, cx, cy, size)),
            ("Key", lambda cx, cy: draw_key(screen, cx, cy, size)),
            ("Locked vault door", lambda cx, cy: self._legend_locked_door(screen, cx, cy)),
            ("Loot (gold and gems)", lambda cx, cy: self._legend_loot(screen, cx, cy)),
            ("Energy cell", lambda cx, cy: draw_energy_cell(screen, cx, cy, size)),
            ("Exit", lambda cx, cy: draw_exit(
                screen, pygame.Rect(cx - 20, cy - 20, 40, 40), True, 0.5)),
        ]
        for index, (label, draw_icon) in enumerate(entries):
            row_y = panel.y + 34 + index * 54
            draw_icon(panel.x + 44, row_y)
            draw_text(screen, label, get_font(17), COLORS["text"], (panel.x + 90, row_y),
                      "midleft")

    def _legend_locked_door(self, screen, cx, cy):
        rect = pygame.Rect(cx - 20, cy - 20, 40, 40)
        draw_door(screen, rect, True, LOCKED_DOOR)
        draw_padlock(screen, cx, cy, 40)

    def _legend_loot(self, screen, cx, cy):
        draw_gold(screen, cx - 11, cy, 34)
        draw_gem(screen, cx + 12, cy, 34)
