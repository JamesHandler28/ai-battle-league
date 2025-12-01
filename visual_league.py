import pygame
import numpy as np
import math
import random
import roster
import map_config
import os

# --- CONFIGURATION ---
EDIT_MODE = False
FULLSCREEN = False

GAME_WIDTH = 900
GAME_HEIGHT = 1200
UI_WIDTH = 400 

FPS = 60
FLOOR_COLOR = (20, 20, 25)
UI_BG_COLOR = (30, 30, 35)

# --- SETUP DISPLAY ---
os.environ['SDL_VIDEO_CENTERED'] = '1'
pygame.init()
info = pygame.display.Info()
monitor_h = info.current_h

SCALE = 1.0
if GAME_HEIGHT > monitor_h - 100:
    SCALE = (monitor_h - 100) / GAME_HEIGHT
    print(f"Map too big for screen! Scaling by {SCALE:.2f}")

DISPLAY_GAME_WIDTH = int(GAME_WIDTH * SCALE)
DISPLAY_GAME_HEIGHT = int(GAME_HEIGHT * SCALE)
TOTAL_WIDTH = DISPLAY_GAME_WIDTH + UI_WIDTH
TOTAL_HEIGHT = DISPLAY_GAME_HEIGHT

window = pygame.display.set_mode((TOTAL_WIDTH, TOTAL_HEIGHT))
canvas = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
ui_surface = pygame.Surface((UI_WIDTH, TOTAL_HEIGHT))

pygame.display.set_caption("AI Battle League")

# --- MATH HELPERS ---
def rotate_vector(vec, angle_degrees):
    theta = math.radians(angle_degrees)
    cs = math.cos(theta); sn = math.sin(theta)
    return np.array([vec[0]*cs - vec[1]*sn, vec[0]*sn + vec[1]*cs])

def line_intersects_circle(start_pos, end_pos, circle_center, radius):
    d = end_pos - start_pos; f = start_pos - circle_center
    a = np.dot(d, d); b = 2 * np.dot(f, d); c = np.dot(f, f) - radius**2
    discriminant = b**2 - 4*a*c
    if discriminant < 0: return False 
    discriminant = math.sqrt(discriminant)
    t1 = (-b - discriminant) / (2*a); t2 = (-b + discriminant) / (2*a)
    if 0 <= t1 <= 1 or 0 <= t2 <= 1: return True
    return False

def get_corners(center, size, angle):
    cx, cy = center; w, h = size[0]/2, size[1]/2
    rad = math.radians(-angle); cos_a, sin_a = math.cos(rad), math.sin(rad)
    corners = []
    for dx, dy in [(-w, -h), (w, -h), (w, h), (-w, h)]:
        rx = dx * cos_a - dy * sin_a; ry = dx * sin_a + dy * cos_a
        corners.append((cx + rx, cy + ry))
    return corners

def check_circle_rotated_rect(circle_pos, radius, rect_data):
    (cx, cy), (w, h), angle = rect_data
    tx = circle_pos[0] - cx; ty = circle_pos[1] - cy
    rad = math.radians(angle); cos_a, sin_a = math.cos(rad), math.sin(rad)
    local_x = tx * cos_a - ty * sin_a; local_y = tx * sin_a + ty * cos_a
    closest_x = max(-w/2, min(w/2, local_x)); closest_y = max(-h/2, min(h/2, local_y))
    dist_x = local_x - closest_x; dist_y = local_y - closest_y
    distance_sq = dist_x**2 + dist_y**2
    if distance_sq < radius**2:
        dist = math.sqrt(distance_sq)
        if dist == 0: overlap = radius; normal = np.array([1.0, 0.0])
        else: overlap = radius - dist; normal = np.array([dist_x/dist, dist_y/dist])
        world_nx = normal[0] * cos_a + normal[1] * sin_a
        world_ny = -normal[0] * sin_a + normal[1] * cos_a 
        return True, np.array([world_nx, world_ny]), overlap
    return False, None, 0

def line_intersects_rotated_rect(p1, p2, rect_data):
    corners = get_corners(*rect_data)
    for i in range(4):
        p3 = corners[i]; p4 = corners[(i+1)%4]
        d = (p2[0]-p1[0])*(p4[1]-p3[1]) - (p2[1]-p1[1])*(p4[0]-p3[0])
        if d != 0:
            u = ((p3[0]-p1[0])*(p4[1]-p3[1]) - (p3[1]-p1[1])*(p4[0]-p3[0])) / d
            v = ((p3[0]-p1[0])*(p2[1]-p1[1]) - (p3[1]-p1[1])*(p2[0]-p1[0])) / d
            if 0 <= u <= 1 and 0 <= v <= 1: return True
    return False

def resolve_circle_polygon(pos, radius, points):
    hit = False; best_push = np.array([0.0, 0.0]); max_overlap = -9999
    for i in range(len(points)):
        p1 = np.array(points[i]); p2 = np.array(points[(i + 1) % len(points)])
        edge = p2 - p1; edge_len_sq = np.dot(edge, edge)
        if edge_len_sq == 0: continue
        t = max(0, min(1, np.dot(pos - p1, edge) / edge_len_sq))
        closest_point = p1 + t * edge
        diff = pos - closest_point; dist_sq = np.dot(diff, diff)
        if dist_sq < radius * radius:
            dist = math.sqrt(dist_sq)
            if dist == 0: normal = np.array([-edge[1], edge[0]]); normal = normal / np.linalg.norm(normal); overlap = radius
            else: normal = diff / dist; overlap = radius - dist
            if overlap > max_overlap: max_overlap = overlap; best_push = normal * overlap; hit = True
    return hit, best_push

def line_intersects_polygon(p1, p2, points):
    for i in range(len(points)):
        p3 = np.array(points[i]); p4 = np.array(points[(i + 1) % len(points)])
        d = (p2[0]-p1[0])*(p4[1]-p3[1]) - (p2[1]-p1[1])*(p4[0]-p3[0])
        if d != 0:
            u = ((p3[0]-p1[0])*(p4[1]-p3[1]) - (p3[1]-p1[1])*(p4[0]-p3[0])) / d
            v = ((p3[0]-p1[0])*(p2[1]-p1[1]) - (p3[1]-p1[1])*(p2[0]-p1[0])) / d
            if 0 <= u <= 1 and 0 <= v <= 1: return True
    return False

# --- VISION SYSTEM ---
def cast_ray(start, end, walls, circles, rot_walls, polygons):
    for w in walls:
        if w.clipline(start, end): return True
    for r_wall in rot_walls:
        if line_intersects_rotated_rect(start, end, r_wall): return True
    for poly in polygons:
        if line_intersects_polygon(start, end, poly): return True
    for center, radius in circles:
        if line_intersects_circle(start, end, np.array(center), radius + 5): return True
    return False 

def check_line_of_sight(start_pos, end_pos, walls, circles, rot_walls, polygons):
    inflated_walls = [w.inflate(20, 20) for w in walls]
    if cast_ray(start_pos, end_pos, inflated_walls, circles, rot_walls, polygons): return False
    vec = end_pos - start_pos
    dist = np.linalg.norm(vec)
    if dist == 0: return True
    perp = np.array([-vec[1], vec[0]]) / dist * 12.0 
    if cast_ray(start_pos + perp, end_pos + perp, inflated_walls, circles, rot_walls, polygons): return False
    if cast_ray(start_pos - perp, end_pos - perp, inflated_walls, circles, rot_walls, polygons): return False
    return True

# --- ASSETS ---
TEXTURE_CACHE = {}
def load_texture(filename, size=None, fixed_height=None):
    if filename in TEXTURE_CACHE: return TEXTURE_CACHE[filename]
    try:
        path = os.path.join("assets", filename)
        img = pygame.image.load(path).convert_alpha()
        if size: img = pygame.transform.smoothscale(img, size)
        elif fixed_height:
            aspect = img.get_width() / img.get_height()
            new_w = int(fixed_height * aspect)
            img = pygame.transform.smoothscale(img, (new_w, fixed_height))
        TEXTURE_CACHE[filename] = img
        return img
    except Exception as e:
        print(f"Error loading {filename}: {e}. Using fallback.")
        s = size if size else (40, 40)
        surf = pygame.Surface(s, pygame.SRCALPHA)
        pygame.draw.circle(surf, (255, 0, 255), (s[0]//2, s[1]//2), s[0]//2)
        TEXTURE_CACHE[filename] = surf
        return surf

class Particle:
    def __init__(self, x, y, color, speed, size=5):
        self.x, self.y = x, y; angle = random.uniform(0, 6.28)
        self.vx = math.cos(angle) * speed; self.vy = math.sin(angle) * speed
        self.life = 1.0; self.decay = 0.05 + random.uniform(0, 0.05); self.color = color; self.size = size
    def update(self): self.x += self.vx; self.y += self.vy; self.life -= self.decay; self.size *= 0.9
    def draw(self, surface):
        if self.life > 0:
            s = pygame.Surface((int(self.size*2), int(self.size*2)), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, int(self.life*255)), (int(self.size), int(self.size)), int(self.size))
            surface.blit(s, (self.x - self.size, self.y - self.size))

# --- GLADIATOR LOGIC ---
class Gladiator:
    def __init__(self, x, y, team_id, stats):
        self.pos = np.array([float(x), float(y)])
        self.vel = np.array([0.0, 0.0])
        self.team_id = team_id
        self.stats = stats
        
        self.name = stats.name
        self.max_hp = stats.hp; self.hp = stats.hp
        self.speed = stats.speed
        self.melee_dmg = stats.melee_dmg
        self.throw_dmg = stats.throw_dmg
        self.max_cooldown = stats.cooldown
        self.aggression_dist = stats.aggression
        self.strafe_rate = stats.strafe_rate
        self.accuracy = stats.accuracy
        self.melee_bias = stats.melee_bias 
        
        self.base_image = load_texture(stats.image_file, size=(60, 60))
        self.image = self.base_image
        self.radius = 30
        
        self.alive = True
        self.has_weapon = True
        self.weapon_pos = None; self.weapon_flying = False; self.weapon_dir = np.array([0.0, 0.0])
        self.cooldown = 0; self.angle = 0.0; self.radius = 15; self.strafe_dir = 1
        
        self.last_pos = self.pos.copy(); self.stuck_timer = 0; self.wander_target = None
        self.patrol_target = None
        self.swing_timer = 0 

    def logic(self, enemies, walls, circles, rot_walls, polygons, particles, kill_feed):
        if not self.alive: return

        # STUCK CHECK: Slightly more sensitive (2.0 px)
        if np.linalg.norm(self.pos - self.last_pos) < 2.0: self.stuck_timer += 1
        else: self.stuck_timer = 0; self.last_pos = self.pos.copy()

        closest_visible_enemy = None
        min_vis_dist = 9999
        for e in enemies:
            if not e.alive: continue
            dist = np.linalg.norm(e.pos - self.pos)
            if dist < 800:
                if check_line_of_sight(self.pos, e.pos, walls, circles, rot_walls, polygons):
                    if dist < min_vis_dist: min_vis_dist = dist; closest_visible_enemy = e

        move_target = self.pos.copy()
        
        if self.stuck_timer > 30:
            if self.wander_target is None or self.stuck_timer % 30 == 0:
                self.wander_target = np.array([random.uniform(100, GAME_WIDTH-100), random.uniform(100, GAME_HEIGHT-100)])
            move_target = self.wander_target
        elif not self.has_weapon and self.weapon_pos is not None: move_target = self.weapon_pos
        elif closest_visible_enemy:
            self.patrol_target = None
            desired_dist = self.aggression_dist
            if self.melee_bias > 0.6: desired_dist = 0
            if min_vis_dist > desired_dist: move_target = closest_visible_enemy.pos
            else:
                vec = closest_visible_enemy.pos - self.pos
                perp = np.array([-vec[1], vec[0]])
                if random.random() < self.strafe_rate: self.strafe_dir *= -1
                target_dist = desired_dist
                if not self.has_weapon and closest_visible_enemy.has_weapon: target_dist = 600
                dist_factor = (min_vis_dist - target_dist) * 0.01 
                move_target = self.pos + (perp * self.strafe_dir) + (vec * dist_factor)
        else:
            if self.patrol_target is None or np.linalg.norm(self.pos - self.patrol_target) < 50:
                self.patrol_target = np.array([random.uniform(50, GAME_WIDTH-50), random.uniform(50, GAME_HEIGHT-50)])
            move_target = self.patrol_target

        # --- SMART MOVEMENT (FAN SWEEP) ---
        diff = move_target - self.pos
        dist = np.linalg.norm(diff)
        if dist > 0:
            desired_dir = diff / dist
            
            # Check straight ahead
            look_ahead = self.pos + desired_dir * 50
            if cast_ray(self.pos, look_ahead, walls, circles, rot_walls, polygons):
                
                # BLOCKED! Try Fan Sweep to find opening
                found_path = False
                # Try 45, then 90, then 135 degrees (Left and Right)
                for angle in [45, -45, 90, -90, 135, -135]:
                    test_dir = rotate_vector(desired_dir, angle)
                    test_look = self.pos + test_dir * 50
                    if not cast_ray(self.pos, test_look, walls, circles, rot_walls, polygons):
                        desired_dir = test_dir
                        found_path = True
                        break
                
                # If completely boxed in, reverse
                if not found_path:
                    desired_dir = -desired_dir

            self.vel += desired_dir * self.speed

        if closest_visible_enemy:
            target_vec = closest_visible_enemy.pos - self.pos
            self.angle = math.atan2(target_vec[1], target_vec[0])
            
            if self.has_weapon and min_vis_dist < 70 and self.cooldown <= 0:
                closest_visible_enemy.hp -= self.melee_dmg 
                self.cooldown = 30; self.swing_timer = 15 
                for _ in range(5): particles.append(Particle(closest_visible_enemy.pos[0], closest_visible_enemy.pos[1], (255, 0, 0), 4))
                if closest_visible_enemy.hp <= 0: 
                    closest_visible_enemy.alive = False
                    kill_feed.append(f"{self.name} STABBED {closest_visible_enemy.name}")
            else:
                wants_to_throw = random.random() > self.melee_bias
                if self.has_weapon and self.cooldown <= 0 and min_vis_dist < 800 and wants_to_throw:
                    lead_pos = closest_visible_enemy.pos + (closest_visible_enemy.vel * 15) 
                    aim_vec = lead_pos - self.pos
                    base_angle = math.atan2(aim_vec[1], aim_vec[0])
                    jitter = (1.0 - self.accuracy) * 0.5 
                    final_angle = base_angle + random.uniform(-jitter, jitter)
                    self.has_weapon = False; self.weapon_flying = True; self.weapon_pos = self.pos.copy()
                    self.weapon_dir = np.array([math.cos(final_angle), math.sin(final_angle)])
                    self.cooldown = self.max_cooldown
        else:
            if np.linalg.norm(self.vel) > 0.1: self.angle = math.atan2(self.vel[1], self.vel[0])

        self.vel *= 0.9 
        self.pos += self.vel
        
        for _ in range(4): 
            hit_something = False
            player_rect = pygame.Rect(self.pos[0]-15, self.pos[1]-15, 30, 30)
            for w in walls:
                if player_rect.colliderect(w):
                    d_left = abs(player_rect.right - w.left); d_right = abs(w.right - player_rect.left)
                    d_top = abs(player_rect.bottom - w.top); d_bottom = abs(w.bottom - player_rect.top)
                    min_d = min(d_left, d_right, d_top, d_bottom)
                    if min_d == d_left: self.pos[0] -= d_left; self.vel[0] = min(0, self.vel[0])
                    elif min_d == d_right: self.pos[0] += d_right; self.vel[0] = max(0, self.vel[0])
                    elif min_d == d_top: self.pos[1] -= d_top; self.vel[1] = min(0, self.vel[1])
                    elif min_d == d_bottom: self.pos[1] += d_bottom; self.vel[1] = max(0, self.vel[1])
                    hit_something = True; player_rect = pygame.Rect(self.pos[0]-15, self.pos[1]-15, 30, 30)
            for center, radius in circles:
                c_pos = np.array(center); dist_vec = self.pos - c_pos
                dist = np.linalg.norm(dist_vec); min_dist = radius + 15
                if dist < min_dist:
                    if dist == 0: push_dir = np.array([1.0, 0.0])
                    else: push_dir = dist_vec / dist
                    overlap = min_dist - dist
                    self.pos += push_dir * overlap; hit_something = True
            for poly in polygons:
                hit, push = resolve_circle_polygon(self.pos, self.radius, poly)
                if hit:
                    self.pos += push; normal = push / np.linalg.norm(push); dot = np.dot(self.vel, normal)
                    if dot < 0: self.vel -= normal * dot
                    hit_something = True
            for r_wall in rot_walls:
                hit, normal, overlap = check_circle_rotated_rect(self.pos, self.radius, r_wall)
                if hit: 
                    self.pos += normal * overlap; dot = np.dot(self.vel, normal)
                    if dot < 0: self.vel -= normal * dot
                    hit_something = True
            self.pos[0] = np.clip(self.pos[0], 0, GAME_WIDTH)
            self.pos[1] = np.clip(self.pos[1], 0, GAME_HEIGHT)
            if not hit_something: break 

        if self.cooldown > 0: self.cooldown -= 1
        if self.swing_timer > 0: self.swing_timer -= 1

    def update_weapon(self, walls, circles, rot_walls, polygons, enemies, particles, kill_feed):
        if self.weapon_flying:
            self.weapon_pos += self.weapon_dir * 20
            angle_deg = -math.degrees(math.atan2(self.weapon_dir[1], self.weapon_dir[0]))
            weapon_hitbox = (self.weapon_pos, (50, 20), angle_deg)
            w_rect = pygame.Rect(self.weapon_pos[0]-20, self.weapon_pos[1]-20, 40, 40)

            hit_wall = False
            for w in walls:
                if w_rect.colliderect(w): hit_wall = True; break
            if not hit_wall:
                for center, radius in circles:
                    if np.linalg.norm(self.weapon_pos - np.array(center)) < radius: hit_wall = True; break
            if not hit_wall:
                for r_wall in rot_walls:
                    if check_circle_rotated_rect(self.weapon_pos, 5, r_wall)[0]: hit_wall = True; break
            if not hit_wall:
                for poly in polygons:
                    prev_pos = self.weapon_pos - self.weapon_dir * 20
                    if line_intersects_polygon(prev_pos, self.weapon_pos, poly): hit_wall = True; break
            
            if hit_wall: 
                self.weapon_pos -= self.weapon_dir * 20 
                self.weapon_flying = False
                hit_pos = self.weapon_pos + self.weapon_dir * 20
                for _ in range(5): particles.append(Particle(hit_pos[0], hit_pos[1], (255, 255, 0), 3))
            elif not (0 < self.weapon_pos[0] < GAME_WIDTH) or not (0 < self.weapon_pos[1] < GAME_HEIGHT):
                 self.weapon_flying = False; self.weapon_pos[0] = np.clip(self.weapon_pos[0], 20, GAME_WIDTH-20); self.weapon_pos[1] = np.clip(self.weapon_pos[1], 20, GAME_HEIGHT-20)
            else:
                for e in enemies:
                    if e.team_id != self.team_id and e.alive:
                        hit, _, _ = check_circle_rotated_rect(e.pos, e.radius, weapon_hitbox)
                        if hit:
                            e.hp -= self.throw_dmg 
                            self.weapon_flying = False
                            for _ in range(10): particles.append(Particle(e.pos[0], e.pos[1], (200, 0, 0), 5))
                            if e.hp <= 0: 
                                e.alive = False
                                kill_feed.append(f"{self.name} SNIPED {e.name}")
                            break
        
        if not self.has_weapon and not self.weapon_flying and self.weapon_pos is not None:
            if np.linalg.norm(self.pos - self.weapon_pos) < 35:
                self.has_weapon = True; self.weapon_pos = None

def get_bot_by_name(name):
    for bot in roster.ALL_BOTS:
        if bot.name == name: return bot
    return roster.ALL_BOTS[0]

# --- UI DRAWING ---
def draw_ui(surface, green_team, red_team, kill_feed, font_title, font_text):
    surface.fill(UI_BG_COLOR)
    y_off = 20
    
    title = font_title.render(roster.TEAM_GREEN_TITLE, True, (50, 255, 50))
    surface.blit(title, (20, y_off)); y_off += 40
    for p in green_team:
        color = (255, 255, 255) if p.alive else (100, 100, 100)
        name_txt = font_text.render(f"{p.name} ({max(0, p.hp)}/{p.max_hp})", True, color)
        surface.blit(name_txt, (20, y_off))
        if p.alive:
            pct = max(0, p.hp / p.max_hp)
            pygame.draw.rect(surface, (100, 0, 0), (220, y_off+5, 100, 10))
            pygame.draw.rect(surface, (0, 200, 0), (220, y_off+5, 100 * pct, 10))
        y_off += 30
        
    y_off += 30
    title = font_title.render(roster.TEAM_RED_TITLE, True, (255, 50, 50))
    surface.blit(title, (20, y_off)); y_off += 40
    for p in red_team:
        color = (255, 255, 255) if p.alive else (100, 100, 100)
        name_txt = font_text.render(f"{p.name} ({max(0, p.hp)}/{p.max_hp})", True, color)
        surface.blit(name_txt, (20, y_off))
        if p.alive:
            pct = max(0, p.hp / p.max_hp)
            pygame.draw.rect(surface, (100, 0, 0), (220, y_off+5, 100, 10))
            pygame.draw.rect(surface, (0, 200, 0), (220, y_off+5, 100 * pct, 10))
        y_off += 30

    y_off = TOTAL_HEIGHT - 300
    pygame.draw.line(surface, (100, 100, 100), (20, y_off), (UI_WIDTH-20, y_off), 2)
    y_off += 20
    title = font_title.render("KILL FEED", True, (255, 255, 0))
    surface.blit(title, (20, y_off)); y_off += 40
    for msg in kill_feed[-8:]:
        txt = font_text.render(msg, True, (200, 200, 200))
        surface.blit(txt, (20, y_off)); y_off += 25

def main():
    clock = pygame.time.Clock()
    weapon_sprite = load_texture("weapon.png", fixed_height=50) # Smaller weapon
    
    try: 
        font_title = pygame.font.SysFont("Arial", 28, bold=True)
        font_text = pygame.font.SysFont("Arial", 20)
        font_win = pygame.font.SysFont("Arial", 64, bold=True)
    except: 
        font_title = pygame.font.Font(None, 36)
        font_text = pygame.font.Font(None, 24)
        font_win = pygame.font.Font(None, 80)
        
    particles = []
    kill_feed = [] 
    
    try:
        background_img = pygame.image.load(map_config.MAP_IMAGE_FILE)
        background_img = pygame.transform.scale(background_img, (GAME_WIDTH, GAME_HEIGHT))
    except: background_img = None

    if not EDIT_MODE:
        green_team = []
        for i, name in enumerate(roster.TEAM_GREEN_NAMES):
            stats = get_bot_by_name(name)
            spawn_x = (GAME_WIDTH / (len(roster.TEAM_GREEN_NAMES) + 1)) * (i+1)
            green_team.append(Gladiator(spawn_x, 150, 0, stats))
        
        red_team = []
        for i, name in enumerate(roster.TEAM_RED_NAMES):
            stats = get_bot_by_name(name)
            spawn_x = (GAME_WIDTH / (len(roster.TEAM_RED_NAMES) + 1)) * (i+1)
            red_team.append(Gladiator(spawn_x, GAME_HEIGHT - 150, 1, stats))
        all_players = green_team + red_team
    else: all_players = []

    show_debug_walls = EDIT_MODE 
    rot_walls_data = getattr(map_config, 'ROTATED_WALLS', [])
    polygons_data = getattr(map_config, 'POLYGONS', [])

    game_over = False
    winner_text = ""
    winner_color = (255, 255, 255)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r: main(); return
                if event.key == pygame.K_d: show_debug_walls = not show_debug_walls
                if event.key == pygame.K_ESCAPE: running = False

        if not EDIT_MODE and not game_over:
            green_alive = sum(1 for p in green_team if p.alive)
            red_alive = sum(1 for p in red_team if p.alive)
            if green_alive == 0:
                game_over = True
                winner_text = f"{roster.TEAM_RED_TITLE} WINS!"
                winner_color = (255, 50, 50)
            elif red_alive == 0:
                game_over = True
                winner_text = f"{roster.TEAM_GREEN_TITLE} WINS!"
                winner_color = (50, 255, 50)

            for p in all_players:
                enemies = [e for e in all_players if e.team_id != p.team_id]
                p.logic(enemies, map_config.WALLS, getattr(map_config, 'CIRCLES', []), rot_walls_data, polygons_data, particles, kill_feed)
                p.update_weapon(map_config.WALLS, getattr(map_config, 'CIRCLES', []), rot_walls_data, polygons_data, all_players, particles, kill_feed)

        if background_img: canvas.blit(background_img, (0, 0))
        else: canvas.fill(FLOOR_COLOR)

        if show_debug_walls:
            for w in map_config.WALLS: pygame.draw.rect(canvas, (0, 255, 255), w, 2)
            for center, radius in getattr(map_config, 'CIRCLES', []): pygame.draw.circle(canvas, (0, 255, 255), center, radius, 2)
            for data in rot_walls_data:
                corners = get_corners(*data)
                pygame.draw.lines(canvas, (255, 0, 255), True, corners, 2)
            for poly in polygons_data:
                pygame.draw.lines(canvas, (0, 255, 0), True, poly, 3)

        if not EDIT_MODE:
            for p in all_players:
                if not p.alive: 
                    dead_img = p.base_image.copy()
                    dead_img.fill((50, 50, 50, 255), special_flags=pygame.BLEND_RGBA_MULT)
                    img = pygame.transform.rotate(dead_img, -math.degrees(p.angle) + 90)
                    rect = img.get_rect(center=p.pos)
                    canvas.blit(img, rect)

            for p in particles[:]:
                p.update(); p.draw(canvas)
                if p.life <= 0: particles.remove(p)

            for p in all_players:
                if p.alive:
                    img = pygame.transform.rotate(p.base_image, -math.degrees(p.angle) + 90)
                    rect = img.get_rect(center=p.pos)
                    canvas.blit(img, rect)
                    
                    bar_width = 30; pct = max(0, p.hp / p.max_hp)
                    pygame.draw.rect(canvas, (255, 0, 0), (p.pos[0]-15, p.pos[1]-30, bar_width, 5))
                    pygame.draw.rect(canvas, (0, 255, 0), (p.pos[0]-15, p.pos[1]-30, bar_width * pct, 5))

                    if p.has_weapon:
                        base_angle = -math.degrees(p.angle) + 90 
                        if p.swing_timer > 0:
                            swing_offset = (p.swing_timer * 8) - 60 
                            render_angle = base_angle + swing_offset
                        else:
                            render_angle = base_angle - 90
                        w_rot = pygame.transform.rotate(weapon_sprite, render_angle)
                        
                        forward_vec = np.array([math.cos(p.angle), math.sin(p.angle)])
                        hand_pos = p.pos + forward_vec * 20
                        rect = w_rot.get_rect(center=hand_pos)
                        canvas.blit(w_rot, rect)
                        
                    elif p.weapon_flying:
                        w_rot = pygame.transform.rotate(weapon_sprite, -math.degrees(math.atan2(p.weapon_dir[1], p.weapon_dir[0])) + 90)
                        rect = w_rot.get_rect(center=p.weapon_pos); canvas.blit(w_rot, rect)
                    elif p.weapon_pos is not None: 
                        ground_angle = math.atan2(p.weapon_dir[1], p.weapon_dir[0])
                        w_rot = pygame.transform.rotate(weapon_sprite, -math.degrees(ground_angle) + 90)
                        rect = w_rot.get_rect(center=p.weapon_pos)
                        canvas.blit(w_rot, rect)

        if game_over:
            text = font_win.render(winner_text, True, winner_color)
            outline = font_win.render(winner_text, True, (0, 0, 0))
            cx, cy = GAME_WIDTH // 2, GAME_HEIGHT // 2
            canvas.blit(outline, (cx - text.get_width()//2 + 4, cy - text.get_height()//2 + 4))
            canvas.blit(text, (cx - text.get_width()//2, cy - text.get_height()//2))

        draw_ui(ui_surface, green_team, red_team, kill_feed, font_title, font_text)

        pygame.transform.smoothscale(canvas, (DISPLAY_GAME_WIDTH, DISPLAY_GAME_HEIGHT), window.subsurface((0, 0, DISPLAY_GAME_WIDTH, DISPLAY_GAME_HEIGHT)))
        window.blit(ui_surface, (DISPLAY_GAME_WIDTH, 0))

        if show_debug_walls:
            mx, my = pygame.mouse.get_pos()
            if mx < DISPLAY_GAME_WIDTH:
                game_mx = int(mx / SCALE)
                game_my = int(my / SCALE)
                debug_str = f"GAME: {game_mx}, {game_my}"
                try: text_surf = pygame.font.SysFont("Arial", 20, bold=True).render(debug_str, True, (255, 255, 255))
                except: text_surf = pygame.font.Font(None, 24).render(debug_str, True, (255, 255, 255))
                bg_rect = text_surf.get_rect(topleft=(mx + 15, my + 15)); bg_rect.inflate_ip(10, 10)
                pygame.draw.rect(window, (0, 0, 0), bg_rect); window.blit(text_surf, (mx + 15, my + 15))

        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()

if __name__ == "__main__":
    main()