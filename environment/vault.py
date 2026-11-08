"""
vault.py - The facility map (the "vault" building).

This file answers the question: "What does the level look like and what is
standing on each tile?"  It does NOT contain game rules (see game.py) and it
does NOT draw anything (see gui/renderer.py).

The map is a grid.  Every tile has an (x, y) position:
    x = column (0 is the left edge)
    y = row    (0 is the top edge)

The level is a fixed hand-designed map (no random generation) so that it is
always possible to finish.
"""

# ---------------------------------------------------------------------------
# Tile symbols used in the layout below
# ---------------------------------------------------------------------------
WALL = "#"          # solid wall - nobody can walk here
FLOOR = "."         # normal floor
DOOR = "d"          # normal door - always open, just a doorway
LOCKED_DOOR = "D"   # locked door - needs the key
OPEN_DOOR = "o"     # a locked door after it has been unlocked
EXIT = "E"          # the escape point

# These symbols appear in the layout text but are really "things on the floor".
# The Vault removes them from the grid and stores them in self.items instead.
START_SYMBOL = "S"
KEY_SYMBOL = "K"
GOLD_SYMBOL = "L"
GEM_SYMBOL = "G"
ENERGY_SYMBOL = "+"

# Item names (used as values in Vault.items)
ITEM_KEY = "key"
ITEM_GOLD = "gold"
ITEM_GEM = "gem"
ITEM_ENERGY = "energy"

# How much each kind of loot is worth
LOOT_VALUES = {
    ITEM_GOLD: 100,
    ITEM_GEM: 250,
}

# Movement directions as (dx, dy).  Shared by thief, guards and cameras.
DIRECTIONS = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}

# ---------------------------------------------------------------------------
# The level layout (28 columns x 16 rows)
#
#   S = thief start      K = key         + = energy cell
#   L = gold bar         G = gem         E = exit
#   D = LOCKED door      d = normal door
#
#   Top-left  : key room          Top-middle : security office (restricted)
#   Top-right : the vault (locked door at the bottom, restricted)
#   Middle    : long hallway (patrolled by a guard)
#   Bottom    : start room, storage room, exit room
# ---------------------------------------------------------------------------
LEVEL_LAYOUT = [
    "############################",   # row 0
    "#........#........#......G.#",   # row 1
    "#.K......#........#........#",   # row 2
    "#........d........#.L......#",   # row 3
    "#........#......+.#........#",   # row 4
    "#........#........#.....L..#",   # row 5
    "####d########d########D#####",   # row 6  (doors into the hallway)
    "#..........................#",   # row 7  (hallway)
    "#..........................#",   # row 8  (hallway)
    "####d########d########d#####",   # row 9  (doors out of the hallway)
    "#........#........#........#",   # row 10
    "#........#........#........#",   # row 11
    "#........d...+....d........#",   # row 12
    "#.S......#........#........#",   # row 13
    "#........#........#.......E#",   # row 14
    "############################",   # row 15
]

# Rectangles (x1, y1, x2, y2) that count as "restricted areas".
# Being inside one makes the security system suspicious.
RESTRICTED_ZONES = [
    (10, 1, 17, 5),    # security office
    (19, 1, 26, 5),    # the vault
]

# Guard patrol routes.  Each route is a list of corner points; the guard
# walks in straight lines from corner to corner and then repeats.
# Consecutive corners must share a row or a column.
GUARD_ROUTES = [
    [(2, 7), (20, 7), (20, 8), (2, 8)],        # guard 1: the hallway loop
    [(20, 11), (24, 11), (24, 13), (20, 13)],  # guard 2: inside the exit room
]

# Security cameras.  "directions" is the list of directions the camera
# turns through, one after another.
CAMERA_SETUPS = [
    {"x": 17, "y": 1, "directions": ["down", "left"]},   # security office
    {"x": 26, "y": 8, "directions": ["left", "down"]},   # east end of hallway
    {"x": 26, "y": 1, "directions": ["left", "down"]},   # inside the vault
]


class Vault:
    """Holds the grid, the doors, the items and the restricted zones."""

    def __init__(self, layout=None):
        if layout is None:
            layout = LEVEL_LAYOUT

        self.height = len(layout)
        self.width = len(layout[0])

        # grid[y][x] is the terrain symbol for that tile
        self.grid = []
        # items maps (x, y) -> item name, e.g. {(2, 2): "key"}
        self.items = {}
        self.start = (1, 1)
        self.exit_pos = (1, 1)
        self.locked_doors = set()     # positions of doors that are still locked

        self._parse_layout(layout)

        # Level data that other modules read
        self.restricted_zones = list(RESTRICTED_ZONES)
        self.guard_routes = [list(route) for route in GUARD_ROUTES]
        self.camera_setups = [dict(setup) for setup in CAMERA_SETUPS]

    # ------------------------------------------------------------------
    # Building the map
    # ------------------------------------------------------------------
    def _parse_layout(self, layout):
        """Turn the text layout into the grid and the items dictionary."""
        for y, row in enumerate(layout):
            grid_row = []
            for x, symbol in enumerate(row):
                grid_row.append(self._read_symbol(x, y, symbol))
            self.grid.append(grid_row)

    def _read_symbol(self, x, y, symbol):
        """Handle one layout character and return the terrain for the tile."""
        if symbol == START_SYMBOL:
            self.start = (x, y)
            return FLOOR
        if symbol == KEY_SYMBOL:
            self.items[(x, y)] = ITEM_KEY
            return FLOOR
        if symbol == GOLD_SYMBOL:
            self.items[(x, y)] = ITEM_GOLD
            return FLOOR
        if symbol == GEM_SYMBOL:
            self.items[(x, y)] = ITEM_GEM
            return FLOOR
        if symbol == ENERGY_SYMBOL:
            self.items[(x, y)] = ITEM_ENERGY
            return FLOOR
        if symbol == EXIT:
            self.exit_pos = (x, y)
        if symbol == LOCKED_DOOR:
            self.locked_doors.add((x, y))
        return symbol

    # ------------------------------------------------------------------
    # Questions about tiles
    # ------------------------------------------------------------------
    def in_bounds(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    def tile_at(self, x, y):
        """Return the terrain symbol at (x, y). Outside the map counts as wall."""
        if not self.in_bounds(x, y):
            return WALL
        return self.grid[y][x]

    def is_wall(self, x, y):
        return self.tile_at(x, y) == WALL

    def is_locked_door(self, x, y):
        return self.tile_at(x, y) == LOCKED_DOOR

    def is_walkable(self, x, y):
        """True if a person can stand on this tile right now."""
        tile = self.tile_at(x, y)
        return tile != WALL and tile != LOCKED_DOOR

    def blocks_sight(self, x, y):
        """Walls and locked doors block the view of guards and cameras."""
        tile = self.tile_at(x, y)
        return tile == WALL or tile == LOCKED_DOOR

    def is_restricted(self, x, y):
        for x1, y1, x2, y2 in self.restricted_zones:
            if x1 <= x <= x2 and y1 <= y <= y2:
                return True
        return False

    def locked_door_positions(self):
        """List of every door that is still locked."""
        return sorted(self.locked_doors)

    # ------------------------------------------------------------------
    # Changing the map
    # ------------------------------------------------------------------
    def unlock_door(self, x, y):
        """Turn a locked door into an open door."""
        if self.is_locked_door(x, y):
            self.grid[y][x] = OPEN_DOOR
            self.locked_doors.discard((x, y))

    def take_item(self, x, y):
        """Remove and return the item at (x, y), or None if there is none."""
        return self.items.pop((x, y), None)

    # ------------------------------------------------------------------
    # Line of sight
    # ------------------------------------------------------------------
    def has_line_of_sight(self, x0, y0, x1, y1):
        """
        True if nothing blocks the view between two tiles.

        Uses Bresenham's line algorithm: it lists the tiles that a straight
        line from (x0, y0) to (x1, y1) passes through, and we check each one.
        """
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        step_x = 1 if x0 < x1 else -1
        step_y = 1 if y0 < y1 else -1
        error = dx - dy
        x, y = x0, y0

        while (x, y) != (x1, y1):
            double_error = 2 * error
            if double_error > -dy:
                error -= dy
                x += step_x
            if double_error < dx:
                error += dx
                y += step_y
            # The last tile is the target itself, so we do not test it.
            if (x, y) != (x1, y1) and self.blocks_sight(x, y):
                return False
        return True
