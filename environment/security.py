"""
security.py - Guards, cameras and the SecuritySystem that manages them.

Everything here is a simple scripted placeholder.  Later, the Security AI
(ai/security_agent.py) can replace the decisions the guards make.  The place
to look is Guard.update(): it decides what the guard does each game tick.

Key ideas
---------
* A game "tick" is one step of the game.  Guards and cameras move on ticks.
* Guards and cameras both "see" a set of tiles (a cone in front of them).
  The thief is detected when the thief's tile is inside that set.
"""

from environment.vault import DIRECTIONS

# ---------------------------------------------------------------------------
# Settings (easy to tweak)
# ---------------------------------------------------------------------------
GUARD_VIEW_RANGE = 5          # how many tiles a guard can see
CAMERA_VIEW_RANGE = 5         # how many tiles a camera can see
CAMERA_TURN_TICKS = 14        # ticks a camera stares in one direction

GUARD_PATROL_INTERVAL = 3     # guard walks one tile every N ticks (calm)
GUARD_ALERT_PATROL_INTERVAL = 2   # patrols faster when the alert is raised
GUARD_CHASE_INTERVAL = 2      # guard moves one tile every N ticks when chasing
GUARD_GIVE_UP_TICKS = 10      # stop chasing after this many ticks without sight
GUARD_RESPONSE_RADIUS = 12    # guards react to an alert only if this close

# Guard modes
MODE_PATROL = "patrol"
MODE_CHASE = "chase"
MODE_RETURN = "return"


def manhattan_distance(a, b):
    """Distance in tiles if you can only move up/down/left/right."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def compute_visible_tiles(vault, origin, facing, view_range):
    """
    Return the set of tiles that something at 'origin' can see.

    The view is a 90-degree cone in the 'facing' direction, limited by
    'view_range', and blocked by walls and locked doors.
    """
    ox, oy = origin
    fx, fy = facing
    visible = set()

    for y in range(oy - view_range, oy + view_range + 1):
        for x in range(ox - view_range, ox + view_range + 1):
            if not vault.in_bounds(x, y) or vault.is_wall(x, y):
                continue
            dx = x - ox
            dy = y - oy
            if dx * dx + dy * dy > view_range * view_range:
                continue
            if (dx, dy) != (0, 0):
                # "forward" is how far the tile is in front of us,
                # "sideways" is how far it is to the left or right.
                forward = dx * fx + dy * fy
                sideways = abs(dx * fy - dy * fx)
                if forward <= 0 or sideways > forward:
                    continue        # outside the 90-degree cone
            if vault.has_line_of_sight(ox, oy, x, y):
                visible.add((x, y))
    return visible


def build_route(corners):
    """
    Turn a list of corner points into a full list of tiles to walk through.
    Example: [(0, 0), (3, 0), (3, 1)] -> (0,0) (1,0) (2,0) (3,0) (3,1) ...
    The route loops: after the last tile the guard goes to the first one.
    """
    route = []
    for i in range(len(corners)):
        start = corners[i]
        end = corners[(i + 1) % len(corners)]
        step_x = (end[0] > start[0]) - (end[0] < start[0])   # -1, 0 or 1
        step_y = (end[1] > start[1]) - (end[1] < start[1])
        x, y = start
        while (x, y) != end:
            route.append((x, y))
            x += step_x
            y += step_y
    return route


# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------
class Camera:
    """A fixed camera that slowly turns between a few directions."""

    def __init__(self, x, y, direction_names):
        self.x = x
        self.y = y
        self.direction_names = direction_names
        self.direction_index = 0
        self.turn_timer = 0
        self.visible_tiles = set()

    @property
    def position(self):
        return (self.x, self.y)

    @property
    def facing(self):
        return DIRECTIONS[self.direction_names[self.direction_index]]

    def update(self, vault):
        """Count ticks, turn when it is time, then refresh what it can see."""
        self.turn_timer += 1
        if self.turn_timer >= CAMERA_TURN_TICKS:
            self.turn_timer = 0
            self.direction_index = (self.direction_index + 1) % len(self.direction_names)
        self.refresh_view(vault)

    def refresh_view(self, vault):
        self.visible_tiles = compute_visible_tiles(
            vault, self.position, self.facing, CAMERA_VIEW_RANGE)


# ---------------------------------------------------------------------------
# Guard
# ---------------------------------------------------------------------------
class Guard:
    """
    A guard with three simple modes:

      patrol - walk around the patrol route
      chase  - walk toward the thief (or toward where the thief was last seen)
      return - walk back to the patrol route along the path we came from
    """

    def __init__(self, route):
        self.route = route
        self.route_index = 0
        self.x, self.y = route[0]
        self.facing = (1, 0)
        self.mode = MODE_PATROL
        self.target = None            # tile we are chasing toward
        self.trail = []               # tiles walked while chasing (a stack)
        self.lost_ticks = 0           # ticks since we last saw the thief
        self.tick_count = 0
        self.visible_tiles = set()

    @property
    def position(self):
        return (self.x, self.y)

    # ------------------------------------------------------------------
    # Main entry point - called once per game tick
    # ------------------------------------------------------------------
    def update(self, vault, thief_pos, alert_level, last_known_pos):
        """
        Move (if it is this guard's turn) and then look for the thief.
        Returns True if the guard can see the thief after moving.

        FUTURE WORK: the Security AI can replace this decision logic.
        """
        self.tick_count += 1
        if self.tick_count % self._move_interval(alert_level) == 0:
            self._take_one_step(vault)

        self.visible_tiles = compute_visible_tiles(
            vault, self.position, self.facing, GUARD_VIEW_RANGE)
        sees_thief = thief_pos in self.visible_tiles

        self._update_mode(sees_thief, thief_pos, alert_level, last_known_pos)
        return sees_thief

    # ------------------------------------------------------------------
    # Deciding what to do
    # ------------------------------------------------------------------
    def _move_interval(self, alert_level):
        """How many ticks the guard waits between steps."""
        if self.mode == MODE_CHASE or self.mode == MODE_RETURN:
            return GUARD_CHASE_INTERVAL
        if alert_level > 0:
            return GUARD_ALERT_PATROL_INTERVAL
        return GUARD_PATROL_INTERVAL

    def _update_mode(self, sees_thief, thief_pos, alert_level, last_known_pos):
        """Switch between patrol / chase / return."""
        if sees_thief:
            self.mode = MODE_CHASE
            self.target = thief_pos
            self.lost_ticks = 0
        elif self.mode == MODE_CHASE:
            self.lost_ticks += 1
            if self.lost_ticks >= GUARD_GIVE_UP_TICKS:
                self.mode = MODE_RETURN
                self.target = None
        elif self.mode == MODE_PATROL and alert_level >= 2 and last_known_pos:
            # A camera spotted the thief: go and investigate that spot.
            if manhattan_distance(self.position, last_known_pos) <= GUARD_RESPONSE_RADIUS:
                self.mode = MODE_CHASE
                self.target = last_known_pos
                self.lost_ticks = 0

    # ------------------------------------------------------------------
    # Moving
    # ------------------------------------------------------------------
    def _take_one_step(self, vault):
        if self.mode == MODE_PATROL:
            self._patrol_step()
        elif self.mode == MODE_CHASE:
            self._chase_step(vault)
        elif self.mode == MODE_RETURN:
            self._return_step()

    def _patrol_step(self):
        """Walk to the next tile on the route."""
        self.route_index = (self.route_index + 1) % len(self.route)
        self._move_to(self.route[self.route_index])

    def _chase_step(self, vault):
        """
        Take one greedy step toward the target.  This is deliberately simple
        (no path planning), so guards can get stuck behind walls.
        A* or BFS can replace this later.
        """
        if self.target is None or self.target == self.position:
            return
        best_tile = self._best_neighbour_toward(vault, self.target)
        if best_tile is not None:
            self.trail.append(self.position)     # remember how to get back
            self._move_to(best_tile)

    def _return_step(self):
        """Walk back along the trail we left while chasing."""
        if self.trail:
            self._move_to(self.trail.pop())
        else:
            self.mode = MODE_PATROL

    def _best_neighbour_toward(self, vault, target):
        """Pick the neighbouring tile that gets closest to the target."""
        best_tile = None
        best_distance = manhattan_distance(self.position, target)
        for dx, dy in DIRECTIONS.values():
            tile = (self.x + dx, self.y + dy)
            if not vault.is_walkable(tile[0], tile[1]):
                continue
            distance = manhattan_distance(tile, target)
            if distance < best_distance:          # strictly closer only
                best_distance = distance
                best_tile = tile
        return best_tile

    def _move_to(self, tile):
        self.facing = (tile[0] - self.x, tile[1] - self.y)
        self.x, self.y = tile


# ---------------------------------------------------------------------------
# SecuritySystem
# ---------------------------------------------------------------------------
class SecuritySystem:
    """Owns all guards and cameras and updates them together."""

    def __init__(self, vault, enabled=True):
        self.guards = []
        self.cameras = []
        if enabled:
            for corners in vault.guard_routes:
                self.guards.append(Guard(build_route(corners)))
            for setup in vault.camera_setups:
                self.cameras.append(Camera(setup["x"], setup["y"], setup["directions"]))
        self.refresh_views(vault)

    def refresh_views(self, vault):
        """Recalculate what every guard and camera can see right now."""
        for camera in self.cameras:
            camera.refresh_view(vault)
        for guard in self.guards:
            guard.visible_tiles = compute_visible_tiles(
                vault, guard.position, guard.facing, GUARD_VIEW_RANGE)

    def update(self, vault, thief_pos, alert_level, last_known_pos):
        """
        Advance cameras and guards by one tick.
        Returns (seen_by_camera, seen_by_guard).
        """
        seen_by_camera = False
        for camera in self.cameras:
            camera.update(vault)
            if thief_pos in camera.visible_tiles:
                seen_by_camera = True

        seen_by_guard = False
        for guard in self.guards:
            if guard.update(vault, thief_pos, alert_level, last_known_pos):
                seen_by_guard = True

        return seen_by_camera, seen_by_guard

    def guard_is_touching(self, thief_pos):
        """True if any guard is on, or right next to, the thief's tile."""
        for guard in self.guards:
            if manhattan_distance(guard.position, thief_pos) <= 1:
                return True
        return False
