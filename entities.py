import pygame
import numpy as np
import math
import random
import settings
import physics
import vision
import assets_manager
import debug_console
import sound_manager


def is_point_free(pt, walls_check, circles_list=None, rot_walls_list=None, polygons_list=None, radius=25):
    """Module-level safe check whether a point is free of obstacles.
    This function is used to avoid nested-local name issues and will
    fall back to conservative defaults on error.
    """
    try:
        if circles_list is None: circles_list = []
        if rot_walls_list is None: rot_walls_list = []
        if polygons_list is None: polygons_list = []

        r = pygame.Rect(pt[0]-15, pt[1]-15, 30, 30)
        if any(r.colliderect(w) for w in walls_check):
            return False
        for center, rad in circles_list:
            if np.linalg.norm(np.array(pt) - np.array(center)) < rad + radius:
                return False
        for r_wall in rot_walls_list:
            if physics.check_circle_rotated_rect(pt, radius, r_wall)[0]:
                return False
        for poly in polygons_list:
            hit, _ = physics.resolve_circle_polygon(np.array(pt), radius, poly)
            if hit:
                return False
        if not (0 + 10 < pt[0] < settings.GAME_WIDTH - 10 and 0 + 10 < pt[1] < settings.GAME_HEIGHT - 10):
            return False
        return True
    except Exception:
        # Be conservative: if anything goes wrong, treat point as blocked
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
        
        # Keep stats saved (Essential fix)
        self.stats = stats
        
        self.name = stats.name
        self.max_hp = stats.hp
        self.hp = stats.hp
        
        # RESTORED: Acceleration-based speed
        # Multiplied by 1.5 to compensate for the larger screen/hitboxes
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
        
        # Keep Bigger Hitbox (Essential fix)
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
        self.last_pos = np.array(self.pos)
        self.stuck_timer = 0
        self.escape_timer = 0
        self.escape_dir = np.array([0.0, 0.0])
        self.stuck_reported = False
        self.stuck_origin = None  # Track where we got stuck
        self.walk_sound_timer = random.randint(0, 9)  # Stagger walk sounds so not all 8 players walk at once

    def logic(self, enemies, all_players, walls, circles, rot_walls, polygons, particles, kill_feed):
        if not self.alive: return

        

        # --- OPTIMIZATION: Filter Walls (Prevents Lag) ---
        nearby_walls = []
        box_size = 300
        for w in walls:
            if abs(self.pos[0] - w.centerx) < box_size and abs(self.pos[1] - w.centery) < box_size:
                nearby_walls.append(w)
        # -------------------------------------------------

        # --- Stuck detection / escape logic cleaned ---
        dist = np.linalg.norm(self.pos - self.last_pos)
        if dist < 0.5:
            if self.escape_timer <= 0:
                self.stuck_timer += 1
            else:
                self.stuck_timer = min(self.stuck_timer + 0.5, 100)
        else:
            if self.stuck_timer > 0 and self.stuck_origin is not None:
                if np.linalg.norm(self.pos - self.stuck_origin) > 50:
                    self.stuck_timer = 0
                    self.stuck_reported = False
                    self.escape_timer = 0
                    self.stuck_origin = None
            else:
                self.stuck_timer = 0
                self.stuck_reported = False
                self.escape_timer = 0

        self.last_pos = self.pos.copy()

        # Trigger escape push
        if self.stuck_timer > 8 and self.escape_timer <= 0:
            if not self.stuck_reported:
                self.stuck_origin = self.pos.copy()
                self.stuck_reported = True
                try:
                    debug_console.console_log("stuck_detected", {"name": self.name, "pos": self.pos.tolist()})
                except Exception:
                    pass
            # Compute normal away from nearest obstacle (rects/circles only for simplicity)
            normal = np.array([0.0, 0.0])
            best_dist = 9999
            px, py = self.pos
            for w in walls:
                cx = np.clip(px, w.x, w.x + w.width)
                cy = np.clip(py, w.y, w.y + w.height)
                vect = np.array([px - cx, py - cy])
                d = np.linalg.norm(vect)
                if d < best_dist and d > 1e-6:
                    best_dist = d
                    normal = vect / d
            for center, rad in circles:
                vect = self.pos - np.array(center)
                d = np.linalg.norm(vect)
                if d < best_dist and d > 1e-6:
                    best_dist = d
                    normal = vect / d
            if np.linalg.norm(normal) < 1e-6:
                normal = np.array([1.0, 0.0])
            self.escape_dir = normal / (np.linalg.norm(normal) + 1e-6)
            self.escape_timer = 20
            if self.stuck_timer > 50:
                nudge = 3.0 if self.stuck_timer > 80 else 1.5
                self.vel += self.escape_dir * nudge
                self.escape_timer = max(self.escape_timer, 40)

        # 2. FIND TARGET
        closest_visible_enemy = None
        min_vis_dist = 9999
        for e in enemies:
            if not e.alive: continue
            dist = np.linalg.norm(e.pos - self.pos)
            if dist < 800:
                if vision.check_line_of_sight(self.pos, e.pos, nearby_walls, circles, rot_walls, polygons):
                    if dist < min_vis_dist:
                        min_vis_dist = dist
                        closest_visible_enemy = e

        # 3. PICK MOVE TARGET
        move_target = self.pos.copy()

        # If severely stuck, pick a reachable wander position (your existing helper)
        if self.stuck_timer > 30:
            if self.wander_target is None or self.stuck_timer % 30 == 0:
                self.wander_target = self.find_reachable_wander(nearby_walls)
                try:
                    debug_console.console_log("stuck_wander_target", {
                        "name": self.name,
                        "pos": self.pos.tolist(),
                        "wander_target": self.wander_target.tolist(),
                        "escape_dir": self.escape_dir.tolist(),
                        "stuck_timer": int(self.stuck_timer)
                    })
                except Exception:
                    pass
            move_target = self.wander_target

        elif not self.has_weapon and self.weapon_pos is not None:
            move_target = self.weapon_pos

        elif closest_visible_enemy:
            self.patrol_target = None
            desired_dist = self.aggression_dist
            if self.melee_bias > 0.6:
                desired_dist = 0

            if min_vis_dist > desired_dist:
                move_target = closest_visible_enemy.pos
            else:
                # compute strafe target and validate it before committing
                vec = closest_visible_enemy.pos - self.pos
                if np.linalg.norm(vec) == 0:
                    vec = np.array([1.0, 0.0])
                perp = np.array([-vec[1], vec[0]])
                if self.escape_timer > 0:
                    # while escaping, bias away from enemy slightly
                    perp = perp * 0.0 + (-vec) * 0.2

                # random chance to flip strafe direction, but protected by a cooldown
                if self.strafe_cooldown <= 0 and random.random() < self.strafe_rate:
                    self.strafe_dir *= -1
                    self.strafe_cooldown = 14  # lock flipping for a few frames

                # build candidate target
                target_dist = desired_dist
                if not self.has_weapon and closest_visible_enemy.has_weapon:
                    target_dist = 600
                dist_factor = (min_vis_dist - target_dist) * 0.01
                candidate = self.pos + (perp * self.strafe_dir) + (vec * dist_factor)

                # if candidate is blocked, try opposite strafe; if still blocked, try a small outward offset
                if not is_point_free(candidate, nearby_walls, circles, rot_walls, polygons, self.radius):
                    # try opposite
                    candidate2 = self.pos + (perp * -self.strafe_dir) + (vec * dist_factor)
                    if is_point_free(candidate2, nearby_walls, circles, rot_walls, polygons, self.radius):
                        self.strafe_dir *= -1  # commit to opposite
                        candidate = candidate2
                        self.strafe_cooldown = 14
                    else:
                        # try a small offset directly away from the nearest wall (escape push)
                        escape = self.pos - (vec / (np.linalg.norm(vec)+1e-6)) * 30
                        if is_point_free(escape, nearby_walls, circles, rot_walls, polygons, self.radius):
                            candidate = escape
                        else:
                            # fallback: find a nearby reachable point
                            candidate = self.find_reachable_wander(nearby_walls)

                move_target = candidate

        else:
            if self.patrol_target is None or np.linalg.norm(self.pos - self.patrol_target) < 50:
                self.patrol_target = np.array([random.uniform(50, settings.GAME_WIDTH-50), random.uniform(50, settings.GAME_HEIGHT-50)])
            move_target = self.patrol_target

        # 4. FAN SWEEP + sliding + apply acceleration
        diff = move_target - self.pos
        dist = np.linalg.norm(diff)
        if dist > 0:
            desired_dir = diff / dist

            # OVERRIDE: If actively escaping, use escape direction instead of normal pathfinding
            if self.escape_timer > 0:
                desired_dir = self.escape_dir
                # Apply collision handling to escape direction
                step = 10.0
                test = self.pos + desired_dir * step
                test_rect = pygame.Rect(test[0]-15, test[1]-15, 30, 30)
                blocked = any(test_rect.colliderect(w) for w in nearby_walls)
                
                if blocked:
                    # Try sliding on X axis during escape
                    slide_x = np.array([desired_dir[0], 0.0])
                    if np.linalg.norm(slide_x) > 0:
                        test = self.pos + slide_x * step
                        test_rect = pygame.Rect(test[0]-15, test[1]-15, 30, 30)
                        if not any(test_rect.colliderect(w) for w in nearby_walls):
                            desired_dir = slide_x / np.linalg.norm(slide_x)
                        else:
                            # Try sliding on Y axis
                            slide_y = np.array([0.0, desired_dir[1]])
                            if np.linalg.norm(slide_y) > 0:
                                test = self.pos + slide_y * step
                                test_rect = pygame.Rect(test[0]-15, test[1]-15, 30, 30)
                                if not any(test_rect.colliderect(w) for w in nearby_walls):
                                    desired_dir = slide_y / np.linalg.norm(slide_y)
                                else:
                                    # Both axes blocked: try a small perpendicular jitter
                                    # so we can wiggle out of corners instead of
                                    # coming to a full stop and repeating.
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
                # Check straight ahead with raycast
                look_ahead = self.pos + desired_dir * 50
                blocked_ahead = vision.cast_ray(self.pos, look_ahead, nearby_walls, circles, rot_walls, polygons)

                if blocked_ahead:
                    # BLOCKED! Try Fan Sweep to find an actually traversable opening (also validate with point_is_free)
                    found_path = False
                    for angle in [45, -45, 90, -90, 135, -135]:
                        test_dir = physics.rotate_vector(desired_dir, angle)
                        test_look = self.pos + test_dir * 50
                        # require both line-of-sight to that point AND that landing point is free
                        if not vision.cast_ray(self.pos, test_look, nearby_walls, circles, rot_walls, polygons) and is_point_free(self.pos + test_dir*15, nearby_walls, circles, rot_walls, polygons, self.radius):
                            desired_dir = test_dir
                            found_path = True
                            break

                    if not found_path:
                        # reverse or pick short escape if everything is blocked
                        desired_dir = -desired_dir
                        # if still blocked, pick small perpendicular escape to avoid oscillation
                        small_escape = self.pos + np.array([-desired_dir[1], desired_dir[0]]) * 15
                        if is_point_free(small_escape, nearby_walls, circles, rot_walls, polygons, self.radius):
                            desired_dir = (small_escape - self.pos) / (np.linalg.norm(small_escape - self.pos) + 1e-6)

                # Attempt forward movement by testing a small step. If blocked, try sliding.
                step = 10.0
                test = self.pos + desired_dir * step
                test_rect = pygame.Rect(test[0]-15, test[1]-15, 30, 30)
                blocked = any(test_rect.colliderect(w) for w in nearby_walls)

                if blocked:
                    # Try sliding on X axis
                    slide_x = np.array([desired_dir[0], 0.0])
                    test = self.pos + slide_x * step
                    test_rect = pygame.Rect(test[0]-15, test[1]-15, 30, 30)
                    if not any(test_rect.colliderect(w) for w in nearby_walls) and np.linalg.norm(slide_x) > 0:
                        desired_dir = slide_x / (np.linalg.norm(slide_x) + 1e-6)
                    else:
                        # Try sliding on Y axis
                        slide_y = np.array([0.0, desired_dir[1]])
                        test = self.pos + slide_y * step
                        test_rect = pygame.Rect(test[0]-15, test[1]-15, 30, 30)
                        if not any(test_rect.colliderect(w) for w in nearby_walls) and np.linalg.norm(slide_y) > 0:
                            desired_dir = slide_y / (np.linalg.norm(slide_y) + 1e-6)
                        else:
                            # fully blocked: try a tiny perpendicular jitter before giving up
                            perp = np.array([-desired_dir[1], desired_dir[0]])
                            if np.linalg.norm(perp) > 1e-6:
                                desired_dir = (perp / np.linalg.norm(perp)) * 0.5
                            else:
                                desired_dir = np.array([0.0, 0.0])            # ACCELERATION: Add to velocity instead of setting position
            # If desired_dir is nearly zero, damp velocity to help unsticking
            if np.linalg.norm(desired_dir) < 1e-3:
                # damping to prevent jitter against wall
                self.vel *= 0.5
            else:
                self.vel += desired_dir * self.speed

        # 5. AIMING & ATTACK (unchanged)
        if closest_visible_enemy:
            target_vec = closest_visible_enemy.pos - self.pos
            self.angle = math.atan2(target_vec[1], target_vec[0])

            if self.has_weapon and min_vis_dist < 70 and self.cooldown <= 0:
                closest_visible_enemy.hp -= self.melee_dmg
                self.cooldown = 30
                self.swing_timer = 15
                sound_manager.play_swing()
                for _ in range(5):
                    particles.append(Particle(closest_visible_enemy.pos[0], closest_visible_enemy.pos[1], (255, 0, 0), 4))
                # If the hit killed the target, play death sound only; otherwise play collision
                if closest_visible_enemy.hp <= 0:
                    closest_visible_enemy.alive = False
                    try:
                        sound_manager.play_death()
                    except Exception:
                        pass
                    kill_feed.append(f"{self.name} STABBED {closest_visible_enemy.name}")
                else:
                    try:
                        sound_manager.play_collision()
                    except Exception:
                        pass
            else:
                wants_to_throw = random.random() > self.melee_bias
                if self.has_weapon and self.cooldown <= 0 and min_vis_dist < 800 and wants_to_throw:
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
            if np.linalg.norm(self.vel) > 0.1:
                self.angle = math.atan2(self.vel[1], self.vel[0])

        # 6. FRICTION & MOVEMENT
        self.vel *= 0.9  # Friction prevents infinite speed
        self.pos += self.vel

        # decrement small timers
        if self.strafe_cooldown > 0:
            self.strafe_cooldown -= 1
        if self.escape_timer > 0:
            self.escape_timer -= 1

        # 7. PHYSICS RESOLUTION (Collisions) - unchanged
        for _ in range(4):
            hit_something = False

            # Player vs Player (Soft Push)
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

            # Walls
            player_rect = pygame.Rect(self.pos[0]-15, self.pos[1]-15, 30, 30)
            for w in nearby_walls:
                if player_rect.colliderect(w):
                    d_left = abs(player_rect.right - w.left); d_right = abs(w.right - player_rect.left)
                    d_top = abs(player_rect.bottom - w.top); d_bottom = abs(w.bottom - player_rect.top)
                    min_d = min(d_left, d_right, d_top, d_bottom)
                    if min_d == d_left:
                        self.pos[0] -= d_left; self.vel[0] = min(0, self.vel[0])
                    elif min_d == d_right:
                        self.pos[0] += d_right; self.vel[0] = max(0, self.vel[0])
                    elif min_d == d_top:
                        self.pos[1] -= d_top; self.vel[1] = min(0, self.vel[1])
                    elif min_d == d_bottom:
                        self.pos[1] += d_bottom; self.vel[1] = max(0, self.vel[1])
                    hit_something = True
                    player_rect = pygame.Rect(self.pos[0]-15, self.pos[1]-15, 30, 30)

            # Circles
            for center, radius in circles:
                c_pos = np.array(center); dist_vec = self.pos - c_pos
                dist = np.linalg.norm(dist_vec); min_dist = radius + self.radius
                if dist < min_dist:
                    if dist == 0: push_dir = np.array([1.0, 0.0])
                    else: push_dir = dist_vec / dist
                    overlap = min_dist - dist
                    self.pos += push_dir * overlap; hit_something = True

            # Polygons
            for poly in polygons:
                hit, push = physics.resolve_circle_polygon(self.pos, self.radius, poly)
                if hit:
                    self.pos += push
                    # Reflect velocity (Bounce off walls slightly)
                    normal = push / np.linalg.norm(push)
                    dot = np.dot(self.vel, normal)
                    if dot < 0: self.vel -= normal * dot
                    hit_something = True

            # Rotated Walls
            for r_wall in rot_walls:
                hit, normal, overlap = physics.check_circle_rotated_rect(self.pos, self.radius, r_wall)
                if hit:
                    self.pos += normal * overlap
                    dot = np.dot(self.vel, normal)
                    if dot < 0: self.vel -= normal * dot
                    hit_something = True

            self.pos[0] = np.clip(self.pos[0], 0, settings.GAME_WIDTH)
            self.pos[1] = np.clip(self.pos[1], 0, settings.GAME_HEIGHT)

            if not hit_something: break

        if self.cooldown > 0: self.cooldown -= 1
        if self.swing_timer > 0: self.swing_timer -= 1

    
    def find_reachable_wander(self, walls):
        for _ in range(20):
            p = np.array([
                random.uniform(50, settings.GAME_WIDTH-50),
                random.uniform(50, settings.GAME_HEIGHT-50)
            ])
            r = pygame.Rect(p[0]-20, p[1]-20, 40, 40)
            if not any(r.colliderect(w) for w in walls):
                return p
        return self.pos.copy()


    def update_weapon(self, walls, circles, rot_walls, polygons, enemies, particles, kill_feed):
        if self.weapon_flying:
            # FIX: Slower speed (10)
            speed = 10 
            self.weapon_pos += self.weapon_dir * speed
            angle_deg = -math.degrees(math.atan2(self.weapon_dir[1], self.weapon_dir[0]))
            
            # FIX: Bigger hitbox (80x30)
            weapon_hitbox = (self.weapon_pos, (50, 16), angle_deg)
            w_rect = pygame.Rect(self.weapon_pos[0]-25, self.weapon_pos[1]-8, 50, 16)

            hit_wall = False
            for w in walls:
                if w_rect.colliderect(w): hit_wall = True; break
            if not hit_wall:
                for center, radius in circles:
                    if np.linalg.norm(self.weapon_pos - np.array(center)) < radius: hit_wall = True; break
            if not hit_wall:
                for r_wall in rot_walls:
                    if physics.check_circle_rotated_rect(self.weapon_pos, 5, r_wall)[0]: hit_wall = True; break
            if not hit_wall:
                for poly in polygons:
                    prev_pos = self.weapon_pos - self.weapon_dir * speed
                    if physics.line_intersects_polygon(prev_pos, self.weapon_pos, poly): hit_wall = True; break
            
            if hit_wall: 
                self.weapon_pos -= self.weapon_dir * speed 
                self.weapon_flying = False
                hit_pos = self.weapon_pos + self.weapon_dir * speed
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
                            self.weapon_flying = False
                            # If the projectile killed the player, play death sound only; otherwise play collision
                            if e.hp <= 0:
                                e.alive = False
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
        
        # --- Weapon pickup simplified ---
        if not self.has_weapon and not self.weapon_flying and self.weapon_pos is not None:
            if np.linalg.norm(self.pos - self.weapon_pos) < 60:  # larger pickup radius
                self.has_weapon = True
                self.weapon_pos = None
