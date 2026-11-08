"""
renderer.py - Everything that is DRAWN while playing.

The renderer only reads the game; it never changes game rules.  It also
holds the colour palette and fonts so every screen looks consistent.

Layout of the window:
    +-------------------------------------------+
    |  HUD bar (HUD_HEIGHT pixels)              |
    +-------------------------------------------+
    |                                           |
    |  Map (TILE_SIZE pixels per tile)          |
    |                                           |
    +-------------------------------------------+
"""

import math
import pygame

from environment.security import GUARD_VIEW_RANGE, CAMERA_VIEW_RANGE

from environment.vault import (
    DOOR, LOCKED_DOOR, OPEN_DOOR,
    ITEM_KEY, ITEM_GOLD, ITEM_GEM, ITEM_ENERGY,
)
from environment.player import MAX_ENERGY
from environment.game import (
    ALERT_NAMES, ALERT_CALM, ALERT_ALARM, REQUIRED_LOOT,
    EVENT_KEY_COLLECTED, EVENT_DOOR_UNLOCKED, EVENT_DOOR_LOCKED,
    EVENT_LOOT_COLLECTED, EVENT_ENERGY_COLLECTED, EVENT_ENTERED_RESTRICTED,
    EVENT_SPOTTED_BY_CAMERA, EVENT_SPOTTED_BY_GUARD, EVENT_NEED_LOOT,
    EVENT_ESCAPED, EVENT_CAUGHT, EVENT_EXHAUSTED,
)

# ---------------------------------------------------------------------------
# Sizes
# ---------------------------------------------------------------------------
TILE_SIZE = 40
HUD_HEIGHT = 80
MAP_COLUMNS = 28
MAP_ROWS = 16
WINDOW_WIDTH = MAP_COLUMNS * TILE_SIZE            # 1120
WINDOW_HEIGHT = HUD_HEIGHT + MAP_ROWS * TILE_SIZE  # 720

# ---------------------------------------------------------------------------
# Colour palette (dark theme with a cyan accent)
# ---------------------------------------------------------------------------
COLORS = {
    "background": (10, 13, 19),
    "panel": (18, 23, 33),
    "panel_light": (27, 34, 48),
    "border": (45, 56, 76),
    "text": (226, 232, 240),
    "muted": (132, 145, 165),
    "accent": (34, 211, 238),       # cyan  - the thief and main highlights
    "gold": (250, 204, 21),         # loot and keys
    "red": (248, 81, 73),           # danger, guards
    "orange": (251, 146, 60),       # warnings
    "green": (52, 211, 153),        # success, exit
    "purple": (167, 139, 250),      # gems
    "floor_a": (17, 22, 32),
    "floor_b": (20, 26, 38),
    "restricted": (44, 21, 30),
    "restricted_line": (70, 31, 44),
    "wall": (36, 44, 61),
    "wall_top": (58, 70, 94),
    "door": (73, 89, 122),
    "locked": (150, 46, 56),
}

# Light settings (the glowing view cones of guards and cameras)
LIGHT_RAY_COUNT = 64            # more rays = smoother cone edge
LIGHT_RAY_STEP = 4              # pixels per step while tracing a ray
LIGHT_SOFTNESS = 4              # edge blur (the cone mask is drawn 1/4 size)
GUARD_LIGHT_COLOR = (255, 228, 150)
CAMERA_LIGHT_COLOR = (120, 225, 255)
DANGER_LIGHT_COLOR = (255, 72, 62)

_font_cache = {}


def get_font(size, bold=False):
    """Create (and remember) a font. Uses a clean system font if available."""
    key = (size, bold)
    if key not in _font_cache:
        names = "segoeui,calibri,helveticaneue,arial,dejavusans"
        _font_cache[key] = pygame.font.SysFont(names, size, bold=bold)
    return _font_cache[key]


def mix_colors(color_a, color_b, amount):
    """Blend two colours. amount=0 gives color_a, amount=1 gives color_b."""
    return tuple(int(a + (b - a) * amount) for a, b in zip(color_a, color_b))


def facing_to_angle(facing):
    """Turn a direction like (1, 0) into an angle in radians."""
    return math.atan2(facing[1], facing[0])


def draw_text(surface, text, font, color, position, anchor="topleft"):
    """Draw text. 'anchor' says which point of the text 'position' refers to."""
    image = font.render(text, True, color)
    rect = image.get_rect()
    setattr(rect, anchor, position)
    surface.blit(image, rect)
    return rect


# ===========================================================================
# Icon drawing functions
# Each draws one object centred on (cx, cy) with the given tile 'size'.
# They are also used by the "How to play" legend in menu.py.
# ===========================================================================
def draw_thief(surface, cx, cy, size, facing=(0, 1), carrying=False):
    radius = int(size * 0.34)
    pygame.draw.circle(surface, (4, 6, 10), (cx, cy + 3), radius)            # shadow
    pygame.draw.circle(surface, COLORS["accent"], (cx, cy), radius)
    pygame.draw.circle(surface, (14, 116, 144), (cx, cy), radius, 2)         # rim
    # Eye shows which way the thief is facing
    eye = (int(cx + facing[0] * radius * 0.45), int(cy + facing[1] * radius * 0.45))
    pygame.draw.circle(surface, (10, 13, 19), eye, max(2, radius // 3))
    pygame.draw.circle(surface, (255, 255, 255), eye, max(1, radius // 6))
    if carrying:                                                             # loot bag
        bag = pygame.Rect(0, 0, int(size * 0.2), int(size * 0.2))
        bag.center = (cx + radius, cy - radius)
        pygame.draw.rect(surface, COLORS["gold"], bag, border_radius=3)
        pygame.draw.rect(surface, (120, 90, 0), bag, 1, border_radius=3)


def draw_guard(surface, cx, cy, size, facing=(1, 0), chasing=False):
    radius = int(size * 0.34)
    color = COLORS["red"] if chasing else COLORS["orange"]
    pygame.draw.circle(surface, (4, 6, 10), (cx, cy + 3), radius)
    pygame.draw.circle(surface, color, (cx, cy), radius)
    pygame.draw.circle(surface, (110, 28, 28), (cx, cy), radius, 2)
    pygame.draw.circle(surface, (60, 20, 20), (cx, cy), int(radius * 0.5))   # cap
    # A small pointer shows where the guard is looking
    fx, fy = facing
    tip = (cx + fx * (radius + 5), cy + fy * (radius + 5))
    side_a = (cx + fx * (radius - 2) - fy * 5, cy + fy * (radius - 2) + fx * 5)
    side_b = (cx + fx * (radius - 2) + fy * 5, cy + fy * (radius - 2) - fx * 5)
    pygame.draw.polygon(surface, (255, 235, 210), [tip, side_a, side_b])


def draw_camera(surface, cx, cy, size, facing=(0, 1), alert=False, blink=True):
    radius = int(size * 0.27)
    pygame.draw.circle(surface, (4, 6, 10), (cx, cy + 2), radius + 1)
    pygame.draw.circle(surface, (52, 62, 84), (cx, cy), radius)
    pygame.draw.circle(surface, (130, 145, 170), (cx, cy), radius, 2)
    lens = (int(cx + facing[0] * radius * 0.9), int(cy + facing[1] * radius * 0.9))
    pygame.draw.circle(surface, (10, 13, 19), lens, max(3, radius // 2))
    pygame.draw.circle(surface, COLORS["red"] if alert else COLORS["accent"], lens,
                       max(1, radius // 4))
    if blink:                                                                # LED
        pygame.draw.circle(surface, COLORS["red"], (cx - radius + 2, cy - radius + 2), 2)


def draw_key(surface, cx, cy, size):
    unit = size / 40.0
    gold = COLORS["gold"]
    ring = (int(cx - 8 * unit), int(cy))
    pygame.draw.circle(surface, gold, ring, int(7 * unit), max(2, int(3 * unit)))
    pygame.draw.line(surface, gold, (int(cx - 2 * unit), int(cy)),
                     (int(cx + 11 * unit), int(cy)), max(2, int(3 * unit)))
    pygame.draw.line(surface, gold, (int(cx + 8 * unit), int(cy)),
                     (int(cx + 8 * unit), int(cy + 5 * unit)), max(2, int(3 * unit)))
    pygame.draw.line(surface, gold, (int(cx + 11 * unit), int(cy)),
                     (int(cx + 11 * unit), int(cy + 4 * unit)), max(2, int(3 * unit)))


def draw_gold(surface, cx, cy, size):
    unit = size / 40.0
    bar = pygame.Rect(0, 0, int(22 * unit), int(12 * unit))
    bar.center = (cx, cy + int(2 * unit))
    pygame.draw.rect(surface, (202, 138, 4), bar, border_radius=3)
    top = pygame.Rect(bar.x + int(3 * unit), bar.y - int(3 * unit),
                      bar.width - int(6 * unit), int(6 * unit))
    pygame.draw.rect(surface, COLORS["gold"], top, border_radius=3)
    pygame.draw.rect(surface, (120, 80, 0), bar, 1, border_radius=3)


def draw_gem(surface, cx, cy, size):
    unit = size / 40.0
    points = [(cx, cy - 11 * unit), (cx + 10 * unit, cy - 2 * unit),
              (cx, cy + 11 * unit), (cx - 10 * unit, cy - 2 * unit)]
    pygame.draw.polygon(surface, COLORS["purple"], points)
    pygame.draw.polygon(surface, (237, 233, 254), points, max(1, int(2 * unit)))
    pygame.draw.line(surface, (237, 233, 254), (cx - 10 * unit, cy - 2 * unit),
                     (cx + 10 * unit, cy - 2 * unit), 1)


def draw_energy_cell(surface, cx, cy, size):
    unit = size / 40.0
    body = pygame.Rect(0, 0, int(14 * unit), int(20 * unit))
    body.center = (cx, cy + int(1 * unit))
    pygame.draw.rect(surface, COLORS["green"], body, border_radius=3)
    cap = pygame.Rect(0, 0, int(6 * unit), int(3 * unit))
    cap.midbottom = (cx, body.top)
    pygame.draw.rect(surface, COLORS["green"], cap)
    bolt = [(cx + 2 * unit, cy - 6 * unit), (cx - 3 * unit, cy + 2 * unit),
            (cx, cy + 2 * unit), (cx - 2 * unit, cy + 8 * unit),
            (cx + 3 * unit, cy - 1 * unit), (cx, cy - 1 * unit)]
    pygame.draw.polygon(surface, (6, 40, 30), bolt)


def draw_padlock(surface, cx, cy, size):
    unit = size / 40.0
    body = pygame.Rect(0, 0, int(14 * unit), int(11 * unit))
    body.center = (cx, cy + int(3 * unit))
    shackle = pygame.Rect(0, 0, int(9 * unit), int(10 * unit))
    shackle.midbottom = (cx, body.top + 2)
    pygame.draw.rect(surface, (255, 220, 220), shackle, max(1, int(2 * unit)),
                     border_radius=4)
    pygame.draw.rect(surface, (255, 220, 220), body, border_radius=2)
    pygame.draw.circle(surface, COLORS["locked"], body.center, max(1, int(2 * unit)))


def draw_door(surface, rect, horizontal_bar, state):
    """
    Draw a door filling a wall gap.
    horizontal_bar=True means the door sits in a horizontal wall.
    state is DOOR, LOCKED_DOOR or OPEN_DOOR.
    """
    if state == OPEN_DOOR:
        color, edge = (30, 90, 70), COLORS["green"]
    elif state == LOCKED_DOOR:
        color, edge = COLORS["locked"], (255, 120, 120)
    else:
        color, edge = COLORS["door"], (130, 150, 190)

    if horizontal_bar:
        bar = pygame.Rect(rect.x + 1, rect.centery - 6, rect.width - 2, 12)
    else:
        bar = pygame.Rect(rect.centerx - 6, rect.y + 1, 12, rect.height - 2)

    if state == OPEN_DOOR:
        # An unlocked door is shown as just its two side posts.
        if horizontal_bar:
            pygame.draw.rect(surface, color, (bar.x, bar.y, 8, bar.height))
            pygame.draw.rect(surface, color, (bar.right - 8, bar.y, 8, bar.height))
        else:
            pygame.draw.rect(surface, color, (bar.x, bar.y, bar.width, 8))
            pygame.draw.rect(surface, color, (bar.x, bar.bottom - 8, bar.width, 8))
        return

    pygame.draw.rect(surface, color, bar, border_radius=3)
    pygame.draw.rect(surface, edge, bar, 2, border_radius=3)


def draw_exit(surface, rect, active, pulse):
    base = COLORS["green"] if active else (60, 90, 80)
    fill = pygame.Surface(rect.size, pygame.SRCALPHA)
    strength = 70 + int(40 * pulse) if active else 40
    fill.fill((base[0], base[1], base[2], strength))
    surface.blit(fill, rect.topleft)
    pygame.draw.rect(surface, base, rect.inflate(-4, -4), 2, border_radius=4)
    # Arrow pointing out of the building
    cx, cy = rect.center
    pygame.draw.polygon(surface, base, [(cx - 8, cy - 8), (cx + 8, cy), (cx - 8, cy + 8)])
    font = get_font(10, True)
    draw_text(surface, "EXIT", font, base, (rect.centerx, rect.top + 5), "midtop")


# ===========================================================================
# The Renderer
# ===========================================================================
class Renderer:
    """Draws the game world and the HUD."""

    def __init__(self, game):
        self.map_surface = pygame.Surface((MAP_COLUMNS * TILE_SIZE, MAP_ROWS * TILE_SIZE))
        self.overlay = pygame.Surface(self.map_surface.get_size(), pygame.SRCALPHA)
        self.time = 0.0
        self.elapsed_seconds = 0.0
        self._gradient_cache = {}
        self._light_cache = {}          # last drawn cone for each light
        self.set_game(game)

    def set_game(self, game):
        """Point the renderer at a (new) game, e.g. after a restart."""
        self.game = game
        self.static_layer = self._build_static_layer()
        self.toasts = []            # [text, color, age]
        self.pulses = []            # expanding rings [x, y, color, age]
        self.flash_alpha = 0.0
        self.flash_color = COLORS["red"]
        self.visual_positions = {}
        self.visual_angles = {}
        self.light_tones = {}       # 0 = calm colour, 1 = danger colour
        self.show_debug_tiles = False
        self._light_cache = {}
        self._sight_grid_doors = None
        self.snap_visuals()

    # ------------------------------------------------------------------
    # Static background (floor, restricted zones, walls) is drawn once
    # ------------------------------------------------------------------
    def _build_static_layer(self):
        vault = self.game.vault
        layer = pygame.Surface(self.map_surface.get_size())
        for y in range(vault.height):
            for x in range(vault.width):
                rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                if vault.is_wall(x, y):
                    self._draw_wall_tile(layer, rect, vault, x, y)
                else:
                    self._draw_floor_tile(layer, rect, x, y, vault.is_restricted(x, y))
        self._add_wall_shadows(layer, vault)
        return layer

    def _add_wall_shadows(self, layer, vault):
        """Soft shadows on the floor next to walls give the map some depth."""
        shade_down = pygame.Surface((TILE_SIZE, 12), pygame.SRCALPHA)
        for row in range(12):
            pygame.draw.line(shade_down, (0, 0, 0, int(110 * (1 - row / 12) ** 2)),
                             (0, row), (TILE_SIZE, row))
        shade_right = pygame.transform.rotate(shade_down, 90)      # 12 wide, tile tall
        for y in range(vault.height):
            for x in range(vault.width):
                if vault.is_wall(x, y):
                    continue
                if vault.is_wall(x, y - 1):
                    layer.blit(shade_down, (x * TILE_SIZE, y * TILE_SIZE))
                if vault.is_wall(x - 1, y):
                    layer.blit(pygame.transform.flip(shade_right, True, False),
                               (x * TILE_SIZE, y * TILE_SIZE))

    def _draw_floor_tile(self, layer, rect, x, y, restricted):
        if restricted:
            pygame.draw.rect(layer, COLORS["restricted"], rect)
            # Diagonal hatch lines mark restricted areas
            for offset in range(0, TILE_SIZE * 2, 10):
                start = (rect.x + offset, rect.y)
                end = (rect.x, rect.y + offset)
                self._draw_clipped_line(layer, COLORS["restricted_line"], start, end, rect)
        else:
            color = COLORS["floor_a"] if (x + y) % 2 == 0 else COLORS["floor_b"]
            pygame.draw.rect(layer, color, rect)
        pygame.draw.rect(layer, (13, 17, 25), rect, 1)

    @staticmethod
    def _draw_clipped_line(layer, color, start, end, clip_rect):
        old_clip = layer.get_clip()
        layer.set_clip(clip_rect)
        pygame.draw.line(layer, color, start, end, 1)
        layer.set_clip(old_clip)

    def _draw_wall_tile(self, layer, rect, vault, x, y):
        pygame.draw.rect(layer, COLORS["wall"], rect)
        pygame.draw.rect(layer, (30, 37, 52), rect, 1)
        if not vault.is_wall(x, y - 1):              # lit top edge
            pygame.draw.rect(layer, COLORS["wall_top"], (rect.x, rect.y, rect.width, 3))
        if not vault.is_wall(x, y + 1):              # darker front face of the wall
            face = pygame.Rect(rect.x, rect.bottom - 9, rect.width, 9)
            pygame.draw.rect(layer, (22, 28, 40), face)
            pygame.draw.line(layer, (50, 62, 84), face.topleft, face.topright)

    # ------------------------------------------------------------------
    # Smooth movement: sprites glide toward their real tile position
    # ------------------------------------------------------------------
    def snap_visuals(self):
        """Put every sprite and light exactly where it belongs (no gliding)."""
        self.visual_positions = {}
        self.visual_angles = {}
        self.light_tones = {}
        self.visual_positions["thief"] = self._as_float(self.game.thief.position)
        for index, guard in enumerate(self.game.security.guards):
            self.visual_positions[("guard", index)] = self._as_float(guard.position)
            self.visual_angles[("guard", index)] = facing_to_angle(guard.facing)
            self.light_tones[("guard", index)] = 0.0
        for index, camera in enumerate(self.game.security.cameras):
            self.visual_angles[("camera", index)] = facing_to_angle(camera.facing)
            self.light_tones[("camera", index)] = 0.0

    @staticmethod
    def _as_float(tile):
        return [float(tile[0]), float(tile[1])]

    def _glide(self, name, tile, sharpness, dt):
        """
        Move a sprite smoothly toward its tile.  Each frame it covers a share
        of the remaining distance, so it speeds up and settles gently.
        A higher 'sharpness' makes it follow more tightly.
        """
        position = self.visual_positions.setdefault(name, self._as_float(tile))
        dx = tile[0] - position[0]
        dy = tile[1] - position[1]
        if math.hypot(dx, dy) > 3:               # too far (e.g. restart): snap
            position[0], position[1] = float(tile[0]), float(tile[1])
            return
        blend = 1 - math.exp(-sharpness * dt)
        position[0] += dx * blend
        position[1] += dy * blend

    def _turn(self, name, facing, sharpness, dt):
        """Rotate a drawn angle smoothly toward the real facing direction."""
        target = facing_to_angle(facing)
        current = self.visual_angles.setdefault(name, target)
        difference = (target - current + math.pi) % (2 * math.pi) - math.pi
        self.visual_angles[name] = current + difference * (1 - math.exp(-sharpness * dt))

    def _fade_tone(self, name, target, dt):
        """Slowly shift a light between its calm colour (0) and danger colour (1)."""
        current = self.light_tones.get(name, 0.0)
        self.light_tones[name] = current + (target - current) * (1 - math.exp(-9 * dt))

    def update(self, dt):
        """Advance animations. Call once per frame with the frame time."""
        self.time += dt
        game = self.game
        self._glide("thief", game.thief.position, 26.0, dt)

        thief_tile = game.thief.position
        for index, guard in enumerate(game.security.guards):
            name = ("guard", index)
            self._glide(name, guard.position, 13.0, dt)
            self._turn(name, guard.facing, 9.0, dt)
            danger = 1.0 if (guard.mode == "chase" or thief_tile in guard.visible_tiles) else 0.0
            self._fade_tone(name, danger, dt)
        for index, camera in enumerate(game.security.cameras):
            name = ("camera", index)
            self._turn(name, camera.facing, 7.0, dt)
            self._fade_tone(name, 1.0 if thief_tile in camera.visible_tiles else 0.0, dt)

        for toast in self.toasts:
            toast[2] += dt
        self.toasts = [t for t in self.toasts if t[2] < 2.6]

        for pulse in self.pulses:
            pulse[3] += dt
        self.pulses = [p for p in self.pulses if p[3] < 0.6]

        self.flash_alpha = max(0.0, self.flash_alpha - dt * 220)

    # ------------------------------------------------------------------
    # Reacting to game events (messages and effects)
    # ------------------------------------------------------------------
    def handle_events(self, events):
        thief_tile = self.game.thief.position
        for event in events:
            if event == EVENT_KEY_COLLECTED:
                self._toast("Key collected", COLORS["gold"])
                self._pulse(thief_tile, COLORS["gold"])
            elif event == EVENT_DOOR_UNLOCKED:
                self._toast("Vault door unlocked", COLORS["green"])
                door = self._find_open_door()
                self._pulse(door or thief_tile, COLORS["green"])
            elif event == EVENT_DOOR_LOCKED:
                self._toast("Locked - you need the key", COLORS["orange"])
            elif event == EVENT_LOOT_COLLECTED:
                self._toast("Loot secured! Now escape", COLORS["gold"])
                self._pulse(thief_tile, COLORS["gold"])
            elif event == EVENT_ENERGY_COLLECTED:
                self._toast("Energy restored", COLORS["green"])
                self._pulse(thief_tile, COLORS["green"])
            elif event == EVENT_ENTERED_RESTRICTED:
                self._toast("Restricted area", COLORS["orange"])
            elif event == EVENT_SPOTTED_BY_CAMERA:
                self._toast("Spotted by camera!", COLORS["red"])
                self._flash(COLORS["red"])
            elif event == EVENT_SPOTTED_BY_GUARD:
                self._toast("A guard has seen you!", COLORS["red"])
                self._flash(COLORS["red"])
            elif event == EVENT_NEED_LOOT:
                self._toast("Steal the loot before leaving", COLORS["orange"])
            elif event in (EVENT_ESCAPED, EVENT_CAUGHT, EVENT_EXHAUSTED):
                self._flash(COLORS["green"] if event == EVENT_ESCAPED else COLORS["red"])

    def _find_open_door(self):
        vault = self.game.vault
        for y in range(vault.height):
            for x in range(vault.width):
                if vault.tile_at(x, y) == OPEN_DOOR:
                    return (x, y)
        return None

    def _toast(self, text, color):
        for toast in self.toasts:
            if toast[0] == text and toast[2] < 1.5:
                return                          # already showing this message
        self.toasts.append([text, color, 0.0])
        self.toasts = self.toasts[-3:]          # keep at most 3 messages

    def _pulse(self, tile, color):
        self.pulses.append([tile[0], tile[1], color, 0.0])

    def _flash(self, color):
        self.flash_color = color
        self.flash_alpha = 120.0

    # ------------------------------------------------------------------
    # Drawing a whole frame
    # ------------------------------------------------------------------
    def draw(self, screen):
        screen.fill(COLORS["background"])
        self._draw_map()
        screen.blit(self.map_surface, (0, HUD_HEIGHT))
        self._draw_alert_frame(screen)
        self._draw_flash(screen)
        self._draw_toasts(screen)
        self._draw_hud(screen)

    def _draw_map(self):
        surface = self.map_surface
        surface.blit(self.static_layer, (0, 0))
        self._draw_doors(surface)
        self._draw_exit(surface)
        self._draw_items(surface)
        self._draw_lights(surface)
        self._draw_cameras(surface)
        self._draw_thief_glow(surface)
        self._draw_guards(surface)
        self._draw_thief(surface)
        self._draw_alert_bubbles(surface)
        self._draw_pulses(surface)

    def _tile_rect(self, x, y):
        return pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)

    def _pixel_center(self, x, y):
        return (int(x * TILE_SIZE + TILE_SIZE / 2), int(y * TILE_SIZE + TILE_SIZE / 2))

    def _draw_doors(self, surface):
        vault = self.game.vault
        for y in range(vault.height):
            for x in range(vault.width):
                tile = vault.tile_at(x, y)
                if tile not in (DOOR, LOCKED_DOOR, OPEN_DOOR):
                    continue
                rect = self._tile_rect(x, y)
                # A door in a horizontal wall has walls to its left and right.
                horizontal = vault.is_wall(x - 1, y) and vault.is_wall(x + 1, y)
                pygame.draw.rect(surface, COLORS["floor_a"], rect)
                draw_door(surface, rect, horizontal, tile)
                if tile == LOCKED_DOOR:
                    draw_padlock(surface, rect.centerx, rect.centery, TILE_SIZE)

    def _draw_exit(self, surface):
        exit_x, exit_y = self.game.vault.exit_pos
        active = self.game.thief.loot_count >= REQUIRED_LOOT
        pulse = (math.sin(self.time * 3.0) + 1) / 2
        draw_exit(surface, self._tile_rect(exit_x, exit_y), active, pulse)

    def _draw_items(self, surface):
        bob = int(math.sin(self.time * 3.0) * 2)           # gentle floating
        for (x, y), kind in self.game.vault.items.items():
            cx, cy = self._pixel_center(x, y)
            cy += bob
            if kind == ITEM_KEY:
                draw_key(surface, cx, cy, TILE_SIZE)
            elif kind == ITEM_GOLD:
                draw_gold(surface, cx, cy, TILE_SIZE)
            elif kind == ITEM_GEM:
                draw_gem(surface, cx, cy, TILE_SIZE)
            elif kind == ITEM_ENERGY:
                draw_energy_cell(surface, cx, cy, TILE_SIZE)

    # ------------------------------------------------------------------
    # Lights: soft glowing cones traced with rays so walls cast real edges
    # ------------------------------------------------------------------
    def _draw_lights(self, surface):
        self.overlay.fill((0, 0, 0, 0))

        for index, camera in enumerate(self.game.security.cameras):
            name = ("camera", index)
            origin = self._pixel_center(camera.x, camera.y)
            color = mix_colors(CAMERA_LIGHT_COLOR, DANGER_LIGHT_COLOR, self.light_tones[name])
            self._draw_light_cone(name, origin, self.visual_angles[name], CAMERA_VIEW_RANGE,
                                  color, 80)

        for index, guard in enumerate(self.game.security.guards):
            name = ("guard", index)
            vx, vy = self.visual_positions[name]
            origin = self._pixel_center(vx, vy)
            color = mix_colors(GUARD_LIGHT_COLOR, DANGER_LIGHT_COLOR, self.light_tones[name])
            self._draw_light_cone(name, origin, self.visual_angles[name], GUARD_VIEW_RANGE,
                                  color, 104)
            self._draw_glow(origin, 34, color, 90)        # the torch itself

        surface.blit(self.overlay, (0, 0))
        if self.show_debug_tiles:
            self._draw_debug_tiles(surface)

    def _draw_light_cone(self, name, origin, angle, view_range, color, strength):
        """
        Draw one cone of light (90 degrees wide) onto the overlay.

        Building a cone is the most expensive part of drawing, so the result
        is remembered and reused until the light moves, turns or changes colour.
        """
        radius = int(view_range * TILE_SIZE + TILE_SIZE // 2)
        radius -= radius % LIGHT_SOFTNESS
        corner = (origin[0] - radius, origin[1] - radius)

        cache_key = (origin[0] // 2, origin[1] // 2, round(angle, 1),
                     tuple(c // 8 for c in color),
                     len(self.game.vault.locked_door_positions()))
        cached = self._light_cache.get(name)
        if cached is None or cached[0] != cache_key:
            cached = (cache_key, self._build_light_cone(origin, angle, radius, color, strength))
            self._light_cache[name] = cached
        self.overlay.blit(cached[1], corner)

    def _build_light_cone(self, origin, angle, radius, color, strength):
        """Create the picture of a light cone (see _draw_light_cone)."""
        size = radius * 2
        corner = (origin[0] - radius, origin[1] - radius)

        # 1. Trace rays to find how far the light reaches in each direction.
        half_angle = math.pi / 4
        points = [(radius, radius)]
        for i in range(LIGHT_RAY_COUNT + 1):
            ray_angle = angle - half_angle + (2 * half_angle) * i / LIGHT_RAY_COUNT
            hit = self._trace_ray(origin, ray_angle, radius)
            points.append((hit[0] - corner[0], hit[1] - corner[1]))

        # 2. Draw the cone shape small, then scale it up: this blurs the edges.
        small = size // LIGHT_SOFTNESS
        mask = pygame.Surface((small, small), pygame.SRCALPHA)
        mask.fill((255, 255, 255, 0))
        small_points = [(x / LIGHT_SOFTNESS, y / LIGHT_SOFTNESS) for x, y in points]
        pygame.draw.polygon(mask, (255, 255, 255, 255), small_points)
        mask = pygame.transform.smoothscale(mask, (size, size))

        # 3. Cut a radial gradient (bright in the middle, fading out) to the cone.
        light = self._gradient(radius, color, strength).copy()
        light.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return light

    def _trace_ray(self, origin, angle, max_distance):
        """Walk along a ray until it hits a wall. Returns the end point in pixels."""
        dx = math.cos(angle)
        dy = math.sin(angle)
        blocked = self._sight_grid()
        columns = len(blocked[0])
        rows = len(blocked)
        distance = 0
        while distance < max_distance:
            distance += LIGHT_RAY_STEP
            tile_x = int((origin[0] + dx * distance) // TILE_SIZE)
            tile_y = int((origin[1] + dy * distance) // TILE_SIZE)
            if (tile_x < 0 or tile_y < 0 or tile_x >= columns or tile_y >= rows
                    or blocked[tile_y][tile_x]):
                distance -= LIGHT_RAY_STEP * 0.5
                break
        distance = min(distance, max_distance)
        return (origin[0] + dx * distance, origin[1] + dy * distance)

    def _sight_grid(self):
        """
        A plain list-of-lists saying which tiles block light.  Looking this up
        is much faster than asking the vault thousands of times per frame.
        It is rebuilt only when a door gets unlocked.
        """
        vault = self.game.vault
        door_count = len(vault.locked_door_positions())
        if getattr(self, "_sight_grid_doors", None) != door_count:
            self._sight_grid_data = [
                [vault.blocks_sight(x, y) for x in range(vault.width)]
                for y in range(vault.height)
            ]
            self._sight_grid_doors = door_count
        return self._sight_grid_data

    def _gradient(self, radius, color, strength):
        """A round glow: 'strength' (0-255) in the centre, fading to nothing."""
        key = (radius, tuple(c // 8 for c in color), strength // 4)
        if key not in self._gradient_cache:
            surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            steps = 36
            for step in range(steps):
                ring_radius = radius * (1 - step / steps)
                fade = (step / steps) ** 1.4
                alpha = int(strength * fade)
                pygame.draw.circle(surface, (color[0], color[1], color[2], alpha),
                                   (radius, radius), max(1, int(ring_radius)))
            self._gradient_cache[key] = surface
            if len(self._gradient_cache) > 300:          # keep memory small
                self._gradient_cache.pop(next(iter(self._gradient_cache)))
        return self._gradient_cache[key]

    def _draw_glow(self, origin, radius, color, strength):
        glow = self._gradient(radius, color, strength)
        self.overlay.blit(glow, (origin[0] - radius, origin[1] - radius))

    def _draw_thief_glow(self, surface):
        """A faint cool glow around the thief so they stand out in the dark."""
        vx, vy = self.visual_positions["thief"]
        cx, cy = self._pixel_center(vx, vy)
        glow = self._gradient(30, COLORS["accent"], 55)
        surface.blit(glow, (cx - 30, cy - 30))

    def _draw_debug_tiles(self, surface):
        """Press F1 to see the exact tiles the game uses for detection."""
        debug = pygame.Surface(self.map_surface.get_size(), pygame.SRCALPHA)
        for camera in self.game.security.cameras:
            for x, y in camera.visible_tiles:
                pygame.draw.rect(debug, (34, 211, 238, 60), self._tile_rect(x, y), 1)
        for guard in self.game.security.guards:
            for x, y in guard.visible_tiles:
                pygame.draw.rect(debug, (250, 204, 21, 80), self._tile_rect(x, y), 1)
        surface.blit(debug, (0, 0))

    def _draw_cameras(self, surface):
        alarm = self.game.alert_level == ALERT_ALARM
        blink = int(self.time * 2) % 2 == 0
        for index, camera in enumerate(self.game.security.cameras):
            cx, cy = self._pixel_center(camera.x, camera.y)
            angle = self.visual_angles[("camera", index)]
            facing = (math.cos(angle), math.sin(angle))
            draw_camera(surface, cx, cy, TILE_SIZE, facing, alarm, blink)

    def _draw_guards(self, surface):
        for index, guard in enumerate(self.game.security.guards):
            vx, vy = self.visual_positions[("guard", index)]
            cx, cy = self._pixel_center(vx, vy)
            angle = self.visual_angles[("guard", index)]
            facing = (math.cos(angle), math.sin(angle))
            draw_guard(surface, cx, cy, TILE_SIZE, facing, guard.mode == "chase")

    def _draw_thief(self, surface):
        vx, vy = self.visual_positions["thief"]
        cx, cy = self._pixel_center(vx, vy)
        thief = self.game.thief
        draw_thief(surface, cx, cy, TILE_SIZE, thief.facing, thief.has_loot)

    def _draw_alert_bubbles(self, surface):
        """A red '!' above any guard that is chasing the thief."""
        font = get_font(16, True)
        for index, guard in enumerate(self.game.security.guards):
            if guard.mode != "chase":
                continue
            vx, vy = self.visual_positions[("guard", index)]
            cx, cy = self._pixel_center(vx, vy)
            bob = int(math.sin(self.time * 10) * 2)
            bubble = pygame.Rect(0, 0, 18, 22)
            bubble.midbottom = (cx, cy - 18 + bob)
            pygame.draw.rect(surface, COLORS["red"], bubble, border_radius=6)
            draw_text(surface, "!", font, (255, 255, 255), bubble.center, "center")

    def _draw_pulses(self, surface):
        for x, y, color, age in self.pulses:
            progress = age / 0.6
            radius = int(10 + 22 * progress)
            alpha = int(200 * (1 - progress))
            ring = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(ring, (color[0], color[1], color[2], alpha),
                               (radius + 2, radius + 2), radius, 3)
            cx, cy = self._pixel_center(x, y)
            surface.blit(ring, (cx - radius - 2, cy - radius - 2))

    # ------------------------------------------------------------------
    # Screen-wide feedback
    # ------------------------------------------------------------------
    def _draw_alert_frame(self, screen):
        """A thin coloured border around the map while the alert is raised."""
        level = self.game.alert_level
        if level == ALERT_CALM:
            return
        color = COLORS["red"] if level == ALERT_ALARM else COLORS["orange"]
        frame = pygame.Rect(0, HUD_HEIGHT, WINDOW_WIDTH, WINDOW_HEIGHT - HUD_HEIGHT)
        pygame.draw.rect(screen, color, frame, 3)

    def _draw_flash(self, screen):
        if self.flash_alpha <= 0:
            return
        flash = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT - HUD_HEIGHT), pygame.SRCALPHA)
        color = self.flash_color
        pygame.draw.rect(flash, (color[0], color[1], color[2], int(self.flash_alpha)),
                         flash.get_rect(), 14)
        screen.blit(flash, (0, HUD_HEIGHT))

    def _draw_toasts(self, screen):
        font = get_font(17, True)
        y = HUD_HEIGHT + 14
        for text, color, age in self.toasts:
            fade = 1.0 if age < 2.0 else max(0.0, (2.6 - age) / 0.6)
            image = font.render(text, True, color)
            box = pygame.Rect(0, 0, image.get_width() + 32, 34)
            box.midtop = (WINDOW_WIDTH // 2, y)
            panel = pygame.Surface(box.size, pygame.SRCALPHA)
            pygame.draw.rect(panel, (10, 13, 19, int(220 * fade)), panel.get_rect(),
                             border_radius=8)
            pygame.draw.rect(panel, (color[0], color[1], color[2], int(255 * fade)),
                             panel.get_rect(), 1, border_radius=8)
            image.set_alpha(int(255 * fade))
            panel.blit(image, image.get_rect(center=panel.get_rect().center))
            screen.blit(panel, box.topleft)
            y += 40

    # ------------------------------------------------------------------
    # HUD
    # ------------------------------------------------------------------
    def _draw_hud(self, screen):
        pygame.draw.rect(screen, COLORS["panel"], (0, 0, WINDOW_WIDTH, HUD_HEIGHT))
        pygame.draw.line(screen, COLORS["border"], (0, HUD_HEIGHT - 1),
                         (WINDOW_WIDTH, HUD_HEIGHT - 1))

        self._draw_hud_brand(screen, 20)
        self._draw_hud_energy(screen, 232)
        self._draw_hud_alert(screen, 462)
        self._draw_hud_inventory(screen, 646)
        self._draw_hud_objective(screen, 830)
        self._draw_hud_time(screen, WINDOW_WIDTH - 24)

    def _hud_label(self, screen, text, x):
        draw_text(screen, text, get_font(12, True), COLORS["muted"], (x, 16))

    def _draw_hud_brand(self, screen, x):
        draw_text(screen, "COUNTERPLAY", get_font(22, True), COLORS["text"], (x, 16))
        draw_text(screen, "SECURITY BREACH IN PROGRESS", get_font(11, True),
                  COLORS["accent"], (x, 46))

    def _draw_hud_energy(self, screen, x):
        self._hud_label(screen, "ENERGY", x)
        energy = self.game.thief.energy
        ratio = energy / MAX_ENERGY
        color = COLORS["green"] if ratio > 0.5 else COLORS["orange"] if ratio > 0.25 else COLORS["red"]
        bar = pygame.Rect(x, 38, 190, 14)
        pygame.draw.rect(screen, COLORS["panel_light"], bar, border_radius=7)
        fill = bar.copy()
        fill.width = max(0, int(bar.width * ratio))
        if fill.width > 0:
            pygame.draw.rect(screen, color, fill, border_radius=7)
        pygame.draw.rect(screen, COLORS["border"], bar, 1, border_radius=7)
        number_color = COLORS["text"]
        if ratio <= 0.25 and int(self.time * 3) % 2 == 0:      # blink when low
            number_color = COLORS["red"]
        draw_text(screen, str(int(math.ceil(energy))), get_font(14, True), number_color,
                  (bar.right + 10, bar.centery), "midleft")

    def _draw_hud_alert(self, screen, x):
        self._hud_label(screen, "ALERT LEVEL", x)
        level = self.game.alert_level
        colors = [COLORS["green"], COLORS["orange"], COLORS["red"]]
        for index in range(3):
            segment = pygame.Rect(x + index * 26, 40, 22, 10)
            filled = index <= level
            color = colors[level] if filled else COLORS["panel_light"]
            pygame.draw.rect(screen, color, segment, border_radius=3)
        draw_text(screen, ALERT_NAMES[level], get_font(14, True), colors[level],
                  (x + 86, 45), "midleft")

    def _draw_hud_inventory(self, screen, x):
        self._hud_label(screen, "INVENTORY", x)
        thief = self.game.thief
        # Key slot
        key_box = pygame.Rect(x, 36, 34, 30)
        self._draw_slot(screen, key_box, thief.has_key)
        if thief.has_key:
            draw_key(screen, key_box.centerx, key_box.centery, 30)
        # Loot
        loot_box = pygame.Rect(x + 44, 36, 34, 30)
        self._draw_slot(screen, loot_box, thief.has_loot)
        if thief.has_loot:
            draw_gold(screen, loot_box.centerx, loot_box.centery, 30)
        value_color = COLORS["gold"] if thief.has_loot else COLORS["muted"]
        draw_text(screen, "$" + str(thief.loot_value), get_font(18, True), value_color,
                  (loot_box.right + 10, loot_box.centery), "midleft")

    def _draw_slot(self, screen, rect, filled):
        pygame.draw.rect(screen, COLORS["panel_light"], rect, border_radius=6)
        border = COLORS["gold"] if filled else COLORS["border"]
        pygame.draw.rect(screen, border, rect, 1, border_radius=6)

    def _draw_hud_objective(self, screen, x):
        self._hud_label(screen, "OBJECTIVE", x)
        draw_text(screen, self._current_objective(), get_font(15, True), COLORS["text"],
                  (x, 36))
        # Four small bars show progress: key, door, loot, escape
        done_count = self._objective_progress()
        for index in range(4):
            bar = pygame.Rect(x + index * 40, 62, 34, 5)
            color = COLORS["accent"] if index < done_count else COLORS["panel_light"]
            pygame.draw.rect(screen, color, bar, border_radius=2)

    def _objective_progress(self):
        """How many of the four objectives are finished (0 to 3)."""
        thief = self.game.thief
        door_open = len(self.game.vault.locked_door_positions()) == 0
        count = 0
        if thief.has_key or door_open or thief.has_loot:
            count = 1
        if door_open:
            count = 2
        if thief.has_loot:
            count = 3
        return count

    def _draw_hud_time(self, screen, right):
        draw_text(screen, "TIME", get_font(12, True), COLORS["muted"], (right, 16), "topright")
        total = int(self.elapsed_seconds)
        text = "%d:%02d" % (total // 60, total % 60)
        draw_text(screen, text, get_font(20, True), COLORS["text"], (right, 34), "topright")

    def draw_banner(self, screen, title, subtitle):
        """A centred message over the map (used before the mission starts)."""
        box = pygame.Rect(0, 0, 520, 96)
        box.center = (WINDOW_WIDTH // 2, HUD_HEIGHT + (WINDOW_HEIGHT - HUD_HEIGHT) // 2 + 170)
        panel = pygame.Surface(box.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (10, 13, 19, 225), panel.get_rect(), border_radius=12)
        pygame.draw.rect(panel, COLORS["accent"], panel.get_rect(), 1, border_radius=12)
        screen.blit(panel, box.topleft)
        draw_text(screen, title, get_font(24, True), COLORS["text"],
                  (box.centerx, box.y + 32), "center")
        pulse = 0.6 + 0.4 * math.sin(self.time * 4)
        draw_text(screen, subtitle, get_font(16), mix_colors(COLORS["muted"], COLORS["accent"], pulse),
                  (box.centerx, box.y + 66), "center")

    def _current_objective(self):
        """Tell the player what to do next, based on game progress."""
        thief = self.game.thief
        door_locked = len(self.game.vault.locked_door_positions()) > 0
        if thief.has_loot:
            return "Reach the EXIT"
        if door_locked and not thief.has_key:
            return "Find the key"
        if door_locked:
            return "Unlock the vault door"
        return "Steal the loot"
