import pygame
import numpy as np
import math
import random
import settings
import physics
import vision
import assets_manager
import sound_manager


def is_point_free(pt, polygons_list, radius=25):
    """Return True if a circle at `pt` with `radius` does not intersect any polygon.
    Conservative: any exception returns False.
    """
    try:
        if polygons_list is None:
            polygons_list = []
        for poly in polygons_list:
            hit, _ = physics.resolve_circle_polygon(np.array(pt), radius, poly)
            if hit:
                return False
        if not (0 + 10 < pt[0] < settings.GAME_WIDTH - 10 and 0 + 10 < pt[1] < settings.GAME_HEIGHT - 10):
            return False
        return True
    except Exception:
        return False

class Particle:
    def __init__(self, x, y, color, speed, size=5):
        self.x, self.y = x, y
        angle = random.uniform(0, 6.28)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = 1.0
        self.decay = 0.05 + random.uniform(0, 0.05)
        self.color = color
        self.size = size
        
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= self.decay
        self.size *= 0.9
        
    def draw(self, surface):
        if self.life > 0:
            s = pygame.Surface((int(self.size*2), int(self.size*2)), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, int(self.life*255)), (int(self.size), int(self.size)), int(self.size))
            surface.blit(s, (self.x - self.size, self.y - self.size))

class Gladiator:
    def __init__(self, x, y, team_id, stats):
        self.pos = np.array([float(x), float(y)])
        self.vel = np.array([0.0, 0.0])
        self.team_id = team_id
        
        self.stats = stats
        self.name = stats.name
        self.max_hp = stats.hp
        self.hp = stats.hp
        
        self.kills = 0
        self.deaths = 0
        self.damage_dealt = 0
        
        self.speed = stats.speed * 0.6
        
        self.melee_dmg = stats.melee_dmg
        self.throw_dmg = stats.throw_dmg
        self.max_cooldown = stats.cooldown
        self.aggression_dist = stats.aggression
        self.strafe_rate = stats.strafe_rate
        self.accuracy = stats.accuracy
        self.melee_bias = stats.melee_bias
        
        self.base_image = assets_manager.load_texture(stats.image_file, size=(60, 60))
        self.image = self.base_image
        
        self.radius = 25
        
        self.alive = True
        self.has_weapon = True
        self.weapon_pos = None
        self.weapon_flying = False
        self.weapon_dir = np.array([0.0, 0.0])
        
        self.cooldown = 0
        self.angle = 0.0
        self.strafe_dir = 1
        self.last_pos = self.pos.copy()
        self.stuck_timer = 0
        self.wander_target = None
        self.patrol_target = None
        self.swing_timer = 0
        self.strafe_cooldown = 0
        self.escape_timer = 0
        self.escape_dir = np.array([0.0, 0.0])
        self.stuck_reported = False
        self.stuck_origin = None 
        self.walk_sound_timer = random.randint(0, 9)
        self.move_target = None 
        self.avoid_bias = 1
        
        self.warmup_timer = 100

        # --- PERFORMANCE OPTIMIZATION VARS ---
        # Random start so bots don't all "think" on the exact same frame
        self.scan_timer = random.randint(0, 10) 
        self.cached_polygons = []
        self.last_poly_update_pos = np.array([-999.0, -999.0])
        self.current_target = None # Memorize target to avoid re-scanning
        # -------------------------------------

    def logic(self, enemies, all_players, polygons, particles, kill_feed):
        if not self.alive: return

        if self.warmup_timer > 0:
            self.warmup_timer -= 1

        # --- OPTIMIZATION 1: Cache Nearby Polygons ---
        # Only recalculate 'nearby' walls if we have moved > 100px from last check
        # This reduces list iterations significantly.
        dist_since_update = np.linalg.norm(self.pos - self.last_poly_update_pos)
        if dist_since_update > 100:
            self.cached_polygons = []
            box_size = 400 # Slightly larger box to account for caching
            px, py = self.pos
            for poly in polygons:
                xs = [p[0] for p in poly]
                ys = [p[1] for p in poly]
                cx = (min(xs) + max(xs)) / 2.0
                cy = (min(ys) + max(ys)) / 2.0
                if abs(px - cx) < box_size and abs(py - cy) < box_size:
                    self.cached_polygons.append(poly)
            self.last_poly_update_pos = self.pos.copy()
        
        nearby_polygons = self.cached_polygons
        # ----------------------------------------------

        # --- Stuck detection ---
        dist = np.linalg.norm(self.pos - self.last_pos)
        if dist < 0.5:
            if self.escape_timer <= 0:
                self.stuck_timer += 1
            else:
                self.stuck_timer = min(self.stuck_timer + 0.5, 100)
        else:
            self.stuck_timer = max(0, self.stuck_timer - 2)
            if self.stuck_origin is not None and np.linalg.norm(self.pos - self.stuck_origin) > 50:
                self.stuck_timer = 0
                self.stuck_reported = False
                self.escape_timer = 0
                self.stuck_origin = None

        self.last_pos = self.pos.copy()

        # Trigger escape push
        if self.stuck_timer > 8 and self.escape_timer <= 0:
            if not self.stuck_reported:
                self.stuck_origin = self.pos.copy()
                self.stuck_reported = True
            
            normal = np.array([1.0, 0.0]) # Default fallback
            best_dist = 9999
            
            # Use cached polygons for escape logic too
            for poly in nearby_polygons:
                for i in range(len(poly)):
                    p1 = np.array(poly[i])
                    p2 = np.array(poly[(i+1) % len(poly)])
                    edge = p2 - p1
                    elen2 = np.dot(edge, edge)
                    if elen2 == 0: continue
                    t = max(0, min(1, np.dot(self.pos - p1, edge) / elen2))
                    closest = p1 + t * edge
                    vect = self.pos - closest
                    d = np.linalg.norm(vect)
                    if d < best_dist and d > 1e-6:
                        best_dist = d
                        normal = vect / d
            
            self.escape_dir = normal / (np.linalg.norm(normal) + 1e-6)
            self.escape_timer = 20
            if self.stuck_timer > 50:
                nudge = 3.0 if self.stuck_timer > 80 else 1.5
                self.vel += self.escape_dir * nudge
                self.escape_timer = max(self.escape_timer, 40)

        # --- OPTIMIZATION 2: Throttled Target Finding ---
        # 1. Decrement timer
        if self.scan_timer > 0:
            self.scan_timer -= 1
        
        # 2. If we have a target, check if it's still valid (fast check)
        closest_visible_enemy = self.current_target
        target_is_valid = False
        
        if closest_visible_enemy and closest_visible_enemy.alive:
             dist_to_target = np.linalg.norm(closest_visible_enemy.pos - self.pos)
             if dist_to_target < 800:
                 # Only do the expensive raycast if the timer is 0 OR every few frames
                 if self.scan_timer == 0:
                     if vision.check_line_of_sight(self.pos, closest_visible_enemy.pos, nearby_polygons):
                         target_is_valid = True
                 else:
                     # Assume validity between scans to save FPS
                     target_is_valid = True

        if not target_is_valid:
            closest_visible_enemy = None
            self.current_target = None

        # 3. Only search for a NEW target if we don't have one and timer is up
        min_vis_dist = 9999
        if closest_visible_enemy:
            min_vis_dist = np.linalg.norm(closest_visible_enemy.pos - self.pos)
            
        if self.scan_timer == 0 and closest_visible_enemy is None:
            # Reset timer (randomized slightly to prevent all bots scanning frame 10, 20, 30...)
            self.scan_timer = 6 + random.randint(0, 3) 
            
            for e in enemies:
                if not e.alive: continue
                dist = np.linalg.norm(e.pos - self.pos)
                if dist < 800 and dist < min_vis_dist:
                    # Expensive Check
                    if vision.check_line_of_sight(self.pos, e.pos, nearby_polygons):
                        min_vis_dist = dist
                        closest_visible_enemy = e
            
            self.current_target = closest_visible_enemy
        # ------------------------------------------------

        # 3. PICK MOVE TARGET
        move_target = self.pos.copy()
        self.move_target = move_target 

        if self.stuck_timer > 30:
            if self.wander_target is None or self.stuck_timer % 30 == 0:
                self.wander_target = self.find_reachable_wander(nearby_polygons) 
            move_target = self.wander_target

        elif not self.has_weapon and self.weapon_pos is not None:
            # Check LOS to weapon less frequently? No, this is rare state, keep it accurate
            if vision.check_line_of_sight(self.pos, self.weapon_pos, nearby_polygons):
                move_target = self.weapon_pos
            else:
                # Flanking Logic (kept same)
                to_weapon = self.weapon_pos - self.pos
                dist = np.linalg.norm(to_weapon)
                if dist > 0:
                    dir_to = to_weapon / dist
                    perp = np.array([-dir_to[1], dir_to[0]]) 
                    flank_left = self.pos + (perp * 60) + (dir_to * 20)
                    flank_right = self.pos - (perp * 60) + (dir_to * 20)
                    left_free = is_point_free(flank_left, nearby_polygons, self.radius)
                    right_free = is_point_free(flank_right, nearby_polygons, self.radius)
                    
                    if left_free and not right_free: move_target = flank_left
                    elif right_free and not left_free: move_target = flank_right
                    elif left_free and right_free:
                        if np.linalg.norm(flank_left - self.weapon_pos) < np.linalg.norm(flank_right - self.weapon_pos):
                            move_target = flank_left
                        else:
                            move_target = flank_right
                    else:
                        move_target = self.weapon_pos
                else:
                    move_target = self.weapon_pos

        elif closest_visible_enemy:
            self.patrol_target = None
            desired_dist = self.aggression_dist
            if self.melee_bias > 0.6:
                desired_dist = 0

            if min_vis_dist > desired_dist:
                move_target = closest_visible_enemy.pos
            else:
                vec = closest_visible_enemy.pos - self.pos
                if np.linalg.norm(vec) == 0: vec = np.array([1.0, 0.0])
                perp = np.array([-vec[1], vec[0]])
                if self.escape_timer > 0: perp = perp * 0.0 + (-vec) * 0.2

                if self.strafe_cooldown <= 0 and random.random() < self.strafe_rate:
                    self.strafe_dir *= -1
                    self.strafe_cooldown = 14 

                target_dist = desired_dist
                if not self.has_weapon and closest_visible_enemy.has_weapon:
                    target_dist = 600
                dist_factor = (min_vis_dist - target_dist) * 0.01
                candidate = self.pos + (perp * self.strafe_dir) + (vec * dist_factor)

                if not is_point_free(candidate, nearby_polygons, self.radius):
                    candidate2 = self.pos + (perp * -self.strafe_dir) + (vec * dist_factor)
                    if is_point_free(candidate2, nearby_polygons, self.radius):
                        self.strafe_dir *= -1 
                        candidate = candidate2
                        self.strafe_cooldown = 14
                    else:
                        escape = self.pos - (vec / (np.linalg.norm(vec)+1e-6)) * 30
                        if is_point_free(escape, nearby_polygons, self.radius):
                            candidate = escape
                        else:
                            candidate = self.find_reachable_wander(nearby_polygons)

                move_target = candidate

        else:
            if self.patrol_target is None or np.linalg.norm(self.pos - self.patrol_target) < 50:
                self.patrol_target = np.array([random.uniform(50, settings.GAME_WIDTH-50), random.uniform(50, settings.GAME_HEIGHT-50)])
            move_target = self.patrol_target

        self.move_target = move_target

        # 4. FAN SWEEP + sliding + apply acceleration
        diff = move_target - self.pos
        dist = np.linalg.norm(diff)
        if dist > 0:
            desired_dir = diff / dist

            if self.escape_timer > 0:
                desired_dir = self.escape_dir
                step = 10.0
                test = self.pos + desired_dir * step
                blocked = not is_point_free(test, nearby_polygons, self.radius)

                if blocked:
                    slide_x = np.array([desired_dir[0], 0.0])
                    if np.linalg.norm(slide_x) > 0:
                        test = self.pos + slide_x * step
                        if is_point_free(test, nearby_polygons, self.radius):
                            desired_dir = slide_x / np.linalg.norm(slide_x)
                        else:
                            slide_y = np.array([0.0, desired_dir[1]])
                            if np.linalg.norm(slide_y) > 0:
                                test = self.pos + slide_y * step
                                if is_point_free(test, nearby_polygons, self.radius):
                                    desired_dir = slide_y / np.linalg.norm(slide_y)
                                else:
                                    perp = np.array([-desired_dir[1], desired_dir[0]])
                                    if np.linalg.norm(perp) > 1e-6:
                                        desired_dir = perp / np.linalg.norm(perp)
                                    else:
                                        desired_dir = np.array([0.0, 0.0])
                            else:
                                desired_dir = np.array([0.0, 0.0])
                    else:
                        desired_dir = np.array([0.0, 0.0])
            else:
                look_ahead = self.pos + desired_dir * 50
                # Use cached polygons for raycast
                blocked_ahead = vision.cast_ray(self.pos, look_ahead, nearby_polygons) 

                if blocked_ahead:
                    if self.avoid_bias == 1:
                        check_angles = [45, 90, 135, -45, -90, -135]
                    else:
                        check_angles = [-45, -90, -135, 45, 90, 135]

                    found_path = False
                    for angle in check_angles:
                        test_dir = physics.rotate_vector(desired_dir, angle)
                        test_look = self.pos + test_dir * 50
                        
                        if not vision.cast_ray(self.pos, test_look, nearby_polygons) and is_point_free(self.pos + test_dir*15, nearby_polygons, self.radius):
                            desired_dir = test_dir
                            found_path = True
                            if angle > 0: self.avoid_bias = 1
                            elif angle < 0: self.avoid_bias = -1
                            break

                    if not found_path:
                        desired_dir = -desired_dir
                        small_escape = self.pos + np.array([-desired_dir[1], desired_dir[0]]) * 15
                        if is_point_free(small_escape, nearby_polygons, self.radius):
                            desired_dir = (small_escape - self.pos) / (np.linalg.norm(small_escape - self.pos) + 1e-6)

                step = 10.0
                test = self.pos + desired_dir * step
                blocked = not is_point_free(test, nearby_polygons, self.radius)

                if blocked:
                    slide_x = np.array([desired_dir[0], 0.0])
                    test = self.pos + slide_x * step
                    if is_point_free(test, nearby_polygons, self.radius) and np.linalg.norm(slide_x) > 0:
                        desired_dir = slide_x / (np.linalg.norm(slide_x) + 1e-6)
                    else:
                        slide_y = np.array([0.0, desired_dir[1]])
                        test = self.pos + slide_y * step
                        if is_point_free(test, nearby_polygons, self.radius) and np.linalg.norm(slide_y) > 0:
                            desired_dir = slide_y / (np.linalg.norm(slide_y) + 1e-6)
                        else:
                            perp = np.array([-desired_dir[1], desired_dir[0]])
                            if np.linalg.norm(perp) > 1e-6:
                                desired_dir = (perp / np.linalg.norm(perp)) * 0.5
                            else:
                                desired_dir = np.array([0.0, 0.0])            
            
            if np.linalg.norm(desired_dir) < 1e-3:
                self.vel *= 0.5
            else:
                self.vel += desired_dir * self.speed

        # 5. AIMING & ATTACK
        if closest_visible_enemy:
            target_vec = closest_visible_enemy.pos - self.pos
            self.angle = math.atan2(target_vec[1], target_vec[0])

            # A. MELEE ATTACK
            if self.has_weapon and min_vis_dist < 70 and self.cooldown <= 0:
                closest_visible_enemy.hp -= self.melee_dmg
                self.damage_dealt += self.melee_dmg
                self.cooldown = 30
                self.swing_timer = 15
                sound_manager.play_swing()
                
                for _ in range(5):
                    particles.append(Particle(closest_visible_enemy.pos[0], closest_visible_enemy.pos[1], (255, 0, 0), 4))
                
                if closest_visible_enemy.hp <= 0:
                    closest_visible_enemy.alive = False
                    self.kills += 1
                    try: sound_manager.play_death()
                    except: pass
                    kill_feed.append(f"{self.name} STABBED {closest_visible_enemy.name}")
                else:
                    try: sound_manager.play_collision()
                    except: pass

            # B. RANGED ATTACK
            else:
                can_throw_time = self.warmup_timer <= 0
                wants_to_throw = random.random() > self.melee_bias

                if self.has_weapon and wants_to_throw and self.cooldown <= 0 and min_vis_dist < 800 and wants_to_throw:
                    lead_pos = closest_visible_enemy.pos + (closest_visible_enemy.vel * 15)
                    aim_vec = lead_pos - self.pos
                    base_angle = math.atan2(aim_vec[1], aim_vec[0])
                    
                    jitter = (1.0 - self.accuracy) * 0.5
                    final_angle = base_angle + random.uniform(-jitter, jitter)
                    
                    self.has_weapon = False
                    self.weapon_flying = True
                    self.weapon_pos = self.pos.copy()
                    self.weapon_dir = np.array([math.cos(final_angle), math.sin(final_angle)])
                    
                    sound_manager.play_throw()
                    self.cooldown = self.max_cooldown

        else:
            if np.linalg.norm(self.vel) > 0.5:
                target_angle = math.atan2(self.vel[1], self.vel[0])
                diff = target_angle - self.angle
                while diff > math.pi: diff -= 2 * math.pi
                while diff < -math.pi: diff += 2 * math.pi
                self.angle += diff * 0.2

        # 6. FRICTION & MOVEMENT
        self.vel *= 0.9
        self.pos += self.vel

        if self.strafe_cooldown > 0: self.strafe_cooldown -= 1
        if self.escape_timer > 0: self.escape_timer -= 1

        # 7. PHYSICS RESOLUTION (Collisions)
        for _ in range(4):
            hit_something = False
            for other in all_players:
                if other is self or not other.alive: continue
                diff = self.pos - other.pos
                dist = np.linalg.norm(diff)
                min_dist = self.radius + other.radius
                if dist < min_dist:
                    if dist == 0: push = np.array([1.0, 0.0])
                    else: push = diff / dist
                    overlap = min_dist - dist
                    self.pos += push * (overlap * 0.5)
                    hit_something = True

            # Use cached polygons for collision resolution too
            for poly in nearby_polygons:
                hit, push = physics.resolve_circle_polygon(self.pos, self.radius, poly)
                if hit:
                    self.pos += push
                    normal = push / np.linalg.norm(push)
                    dot = np.dot(self.vel, normal)
                    if dot < 0: 
                        self.vel = self.vel - 1.0 * dot * normal
                    hit_something = True

            self.pos[0] = np.clip(self.pos[0], 0, settings.GAME_WIDTH)
            self.pos[1] = np.clip(self.pos[1], 0, settings.GAME_HEIGHT)

            if not hit_something: break

        if self.cooldown > 0: self.cooldown -= 1
        if self.swing_timer > 0: self.swing_timer -= 1

    def find_reachable_wander(self, polygons):
        for _ in range(20):
            p = np.array([
                random.uniform(50, settings.GAME_WIDTH-50),
                random.uniform(50, settings.GAME_HEIGHT-50)
            ])
            if is_point_free(p, polygons, radius=20):
                return p
        return self.pos.copy()

    def update_weapon(self, polygons, enemies, particles, kill_feed):
        if not self.alive:
            self.weapon_flying = False
            self.weapon_pos = None
            return
        
        if self.weapon_flying:
            speed = 10 
            self.weapon_pos += self.weapon_dir * speed
            angle_deg = -math.degrees(math.atan2(self.weapon_dir[1], self.weapon_dir[0]))
            
            weapon_hitbox = (self.weapon_pos, (50, 16), angle_deg)
            w_rect = pygame.Rect(self.weapon_pos[0]-25, self.weapon_pos[1]-8, 50, 16)

            hit_wall = False
            # Check against full polygon list for weapon accuracy
            for poly in polygons:
                prev_pos = self.weapon_pos - self.weapon_dir * speed
                if physics.line_intersects_polygon(prev_pos, self.weapon_pos, poly):
                    hit_wall = True
                    break
            
            if hit_wall: 
                self.weapon_pos -= self.weapon_dir * speed 
                sword_half_length = 25
                self.weapon_pos -= self.weapon_dir * sword_half_length
                self.weapon_flying = False
                hit_pos = self.weapon_pos + self.weapon_dir * (sword_half_length + 5)
                sound_manager.play_collision()
                for _ in range(5): particles.append(Particle(hit_pos[0], hit_pos[1], (255, 255, 0), 3))
            elif not (0 < self.weapon_pos[0] < settings.GAME_WIDTH) or not (0 < self.weapon_pos[1] < settings.GAME_HEIGHT):
                 self.weapon_flying = False
                 self.weapon_pos[0] = np.clip(self.weapon_pos[0], 20, settings.GAME_WIDTH-20)
                 self.weapon_pos[1] = np.clip(self.weapon_pos[1], 20, settings.GAME_HEIGHT-20)
            else:
                for e in enemies:
                    if e.team_id != self.team_id and e.alive:
                        hit, _, _ = physics.check_circle_rotated_rect(e.pos, e.radius, weapon_hitbox)
                        if hit:
                            e.hp -= self.throw_dmg
                            self.damage_dealt += self.throw_dmg
                            self.weapon_flying = False
                            if e.hp <= 0:
                                e.alive = False
                                self.kills += 1
                                try:
                                    sound_manager.play_death()
                                except Exception:
                                    pass
                                kill_feed.append(f"{self.name} SNIPED {e.name}")
                            else:
                                try:
                                    sound_manager.play_collision()
                                except Exception:
                                    pass
                            for _ in range(10):
                                particles.append(Particle(e.pos[0], e.pos[1], (200, 0, 0), 5))
                            break
        
        if not self.has_weapon and not self.weapon_flying and self.weapon_pos is not None:
            if np.linalg.norm(self.pos - self.weapon_pos) < 60: 
                self.has_weapon = True
                self.weapon_pos = None