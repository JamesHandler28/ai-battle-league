import pygame
import math
import os
import numpy as np
import settings
import roster
import map_config
import physics
import assets_manager
import sound_manager
from entities import Gladiator, Particle
from ui import draw_left_panel, draw_right_panel, draw_debug_panel
try:
    import tkinter as tk
    _tk_available = True
except Exception:
    _tk_available = False

# --- SETUP DISPLAY ---
os.environ['SDL_VIDEO_CENTERED'] = '1'
pygame.init()

info = pygame.display.Info()
MONITOR_W = info.current_w
MONITOR_H = info.current_h

# 1. Scale Game to hit Top/Bottom of screen
SCALE = MONITOR_H / settings.GAME_HEIGHT
DISPLAY_GAME_WIDTH = int(settings.GAME_WIDTH * SCALE)
DISPLAY_GAME_HEIGHT = int(settings.GAME_HEIGHT * SCALE)

# 2. Calculate Margins
REMAINING_WIDTH = MONITOR_W - DISPLAY_GAME_WIDTH
SIDE_PANEL_WIDTH = REMAINING_WIDTH // 2

# 3. Create Window
window = pygame.display.set_mode((MONITOR_W, MONITOR_H), pygame.FULLSCREEN | pygame.SCALED)

pygame.display.set_caption("AI Battle League")

# --- HELPER: Coordinate Converter ---
def to_screen(pos):
    x, y = pos
    screen_x = SIDE_PANEL_WIDTH + (x * SCALE)
    screen_y = y * SCALE
    return (screen_x, screen_y)

def get_bot_by_name(name):
    for bot in roster.ALL_BOTS:
        if bot.name == name: return bot
    return roster.ALL_BOTS[0]

def main():
    clock = pygame.time.Clock()
    
    # Initialize sound effects
    sound_manager.init_sounds()
    
    font_title = pygame.font.SysFont("Arial", 28, bold=True)
    font_text = pygame.font.SysFont("Arial", 20)
    font_win = pygame.font.SysFont("Arial", 64, bold=True)
    font_countdown = pygame.font.SysFont("Arial", 300, bold=True)

    particles = []
    kill_feed = [] 
    
    # --- LOAD ASSETS (HIGH RES) ---
    # We load assets multiplied by SCALE so they look crisp
    player_size = int(70 * SCALE)
    
    weapon_sprite = assets_manager.load_texture("weapon.png", fixed_height=int(55 * SCALE))
    
    # Load Map Background
    bg_path = os.path.join("assets", map_config.MAP_IMAGE_FILE)
    if os.path.exists(bg_path):
        background_img = pygame.image.load(bg_path).convert()
        background_img = pygame.transform.scale(background_img, (DISPLAY_GAME_WIDTH, DISPLAY_GAME_HEIGHT))
    else:
        background_img = None

    # --- CREATE PROCEDURAL DUST ASSET ---
    dust_img = pygame.Surface((60, 60), pygame.SRCALPHA)
    pygame.draw.circle(dust_img, (160, 160, 160, 180), (15, 20), 6)  
    pygame.draw.circle(dust_img, (140, 140, 140, 180), (50, 25), 5)  
    pygame.draw.circle(dust_img, (180, 180, 180, 180), (30, 45), 7) 
    pygame.draw.circle(dust_img, (150, 150, 150, 180), (40, 35), 4)

    # --- SPAWN TEAMS ---
    green_team = []
    for i, name in enumerate(roster.TEAM_GREEN_NAMES):
        stats = get_bot_by_name(name)
        spawn_x = (settings.GAME_WIDTH / (len(roster.TEAM_GREEN_NAMES) + 1)) * (i+1)
        green_team.append(Gladiator(spawn_x, 100, 0, stats))
        # Update sprite to high res
        green_team[-1].base_image = assets_manager.load_texture(stats.image_file, size=(player_size, player_size))
        green_team[-1].angle = math.pi / 2
    
    red_team = []
    for i, name in enumerate(roster.TEAM_RED_NAMES):
        stats = get_bot_by_name(name)
        spawn_x = (settings.GAME_WIDTH / (len(roster.TEAM_RED_NAMES) + 1)) * (i+1)
        red_team.append(Gladiator(spawn_x, settings.GAME_HEIGHT - 100, 1, stats))
        # Update sprite to high res
        red_team[-1].base_image = assets_manager.load_texture(stats.image_file, size=(player_size, player_size))
        red_team[-1].angle = -math.pi / 2
    
    all_players = green_team + red_team

    # --- GAME VARIABLES ---
    show_debug_walls = False
    game_over = False
    winner_text = ""
    winner_color = settings.WHITE
    
    walk_sound_timer = 0  # Global timer for constant footstep rate
    
    game_state = "WAITING" 
    countdown_start_time = 0
    countdown_last_play = None
    countdown_audio_start = None
    countdown_audio_length = None
    # Clipboard HUD
    clipboard_msg = None
    clipboard_msg_time = 0
    
    # Surfaces for UI
    left_ui_surface = pygame.Surface((SIDE_PANEL_WIDTH, MONITOR_H))
    right_ui_surface = pygame.Surface((SIDE_PANEL_WIDTH, MONITOR_H))

    running = True
    while running:
        current_time = pygame.time.get_ticks()

        # --- EVENT LOOP (Checking for Spacebar) ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    main(); return
                if event.key == pygame.K_d:
                    show_debug_walls = not show_debug_walls
                if event.key == pygame.K_ESCAPE:
                    running = False

                if event.key == pygame.K_SPACE:
                    if game_state == "WAITING":
                        game_state = "COUNTDOWN"
                        countdown_start_time = current_time
                        # If a single countdown audio exists, play it. Timing is
                        # controlled manually through settings (see `settings.py`).
                        if sound_manager.has_single_countdown():
                            try:
                                sound_manager.play_countdown_single()
                                countdown_audio_start = current_time
                                # Use manual settings to control visual sync.
                                if settings.COUNTDOWN_SINGLE_LENGTH_MS:
                                    countdown_audio_length = int(settings.COUNTDOWN_SINGLE_LENGTH_MS)
                                else:
                                    countdown_audio_length = None
                            except Exception:
                                countdown_audio_start = None
                                countdown_audio_length = None
                        else:
                            countdown_audio_start = None
                            countdown_audio_length = None
                    elif game_state == "GAME_OVER":
                        main() # Restart
                        return
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Left click only
                if event.button == 1 and show_debug_walls:
                    mx, my = event.pos
                    # Ensure inside the game view (not side panels)
                    if SIDE_PANEL_WIDTH <= mx <= SIDE_PANEL_WIDTH + DISPLAY_GAME_WIDTH and 0 <= my <= DISPLAY_GAME_HEIGHT:
                        gx = int((mx - SIDE_PANEL_WIDTH) / SCALE)
                        gy = int(my / SCALE)
                        # Prepare text for clipboard: coords + template rect
                        rect_w, rect_h = 100, 50
                        copy_text = f"({gx}, {gy})\npygame.Rect({gx}, {gy}, {rect_w}, {rect_h})"
                        # Try tkinter clipboard first, fallback to Windows clip
                        copied = False
                        try:
                            if _tk_available:
                                r = tk.Tk()
                                r.withdraw()
                                r.clipboard_clear()
                                r.clipboard_append(copy_text)
                                r.update()
                                r.destroy()
                                copied = True
                        except Exception:
                            copied = False
                        if not copied:
                            try:
                                import subprocess
                                p = subprocess.Popen('clip', stdin=subprocess.PIPE, shell=True)
                                p.communicate(copy_text.encode('utf-8'))
                                copied = (p.returncode == 0)
                            except Exception:
                                copied = False

                        clipboard_msg = f"Copied: ({gx}, {gy})"
                        clipboard_msg_time = current_time

        # --- GAME LOGIC ---
        if game_state == "PLAYING" and not game_over:
            green_alive = sum(1 for p in green_team if p.alive)
            red_alive = sum(1 for p in red_team if p.alive)
            
            if green_alive == 0:
                game_over = True
                game_state = "GAME_OVER"
                winner_text = f"{roster.TEAM_RED_TITLE} WINS!"
                winner_color = (50, 255, 50)
            elif red_alive == 0:
                game_over = True
                game_state = "GAME_OVER"
                winner_text = f"{roster.TEAM_GREEN_TITLE} WINS!"
                winner_color = (50, 255, 50)

            for p in all_players:
                enemies = [e for e in all_players if e.team_id != p.team_id]
                # Pass polygons-only (map_config.POLYGONS)
                p.logic(enemies, all_players, map_config.POLYGONS, particles, kill_feed)
                p.update_weapon(map_config.POLYGONS, all_players, particles, kill_feed)
            
            # Handle walk sounds at game level - constant rate if any player is moving
            any_player_moving = any(np.linalg.norm(p.vel) > 0.5 for p in all_players if p.alive)
            if any_player_moving:
                walk_sound_timer += 1
                if walk_sound_timer > 10:  # Play every ~10 frames (constant rate)
                    sound_manager.play_walk()
                    walk_sound_timer = 0
            else:
                walk_sound_timer = 0

        # --- DRAWING (DIRECT TO WINDOW) ---
        
        # 1. Background
        if background_img:
            window.blit(background_img, (SIDE_PANEL_WIDTH, 0))
        else:
            game_rect = pygame.Rect(SIDE_PANEL_WIDTH, 0, DISPLAY_GAME_WIDTH, DISPLAY_GAME_HEIGHT)
            pygame.draw.rect(window, settings.FLOOR_COLOR, game_rect)

        # 2. Dead Players (Dust)
        for p in all_players:
            if not p.alive: 
                screen_pos = to_screen(p.pos)
                rect = dust_img.get_rect(center=screen_pos)
                window.blit(dust_img, rect)

        # 3. Living Players
        for p in all_players:
            if p.alive:
                img = pygame.transform.rotate(p.base_image, -math.degrees(p.angle) + 90)
                screen_pos = to_screen(p.pos)
                rect = img.get_rect(center=screen_pos)
                window.blit(img, rect)
                
                # Health Bar
                bar_w = 30 * SCALE
                bar_h = 5 * SCALE
                bar_x = screen_pos[0] - (bar_w / 2)
                bar_y = screen_pos[1] - (player_size / 2) - bar_h - 5
                
                pct = max(0, p.hp / p.max_hp)
                pygame.draw.rect(window, (255, 0, 0), (bar_x, bar_y, bar_w, bar_h))
                pygame.draw.rect(window, (0, 255, 0), (bar_x, bar_y, bar_w * pct, bar_h))

                # Weapon
                if p.has_weapon:
                    base_angle = -math.degrees(p.angle) + 90 
                    render_angle = base_angle + ((p.swing_timer * 8) - 60) if p.swing_timer > 0 else base_angle - 90
                    w_rot = pygame.transform.rotate(weapon_sprite, render_angle)
                    
                    forward_vec = np.array([math.cos(p.angle), math.sin(p.angle)])
                    hand_offset = forward_vec * (20 * SCALE)
                    hand_pos = (screen_pos[0] + hand_offset[0], screen_pos[1] + hand_offset[1])
                    
                    rect = w_rot.get_rect(center=hand_pos)
                    window.blit(w_rot, rect)
                elif p.weapon_flying:
                    w_rot = pygame.transform.rotate(weapon_sprite, -math.degrees(math.atan2(p.weapon_dir[1], p.weapon_dir[0])) + 90)
                    screen_w_pos = to_screen(p.weapon_pos)
                    rect = w_rot.get_rect(center=screen_w_pos)
                    window.blit(w_rot, rect)
                elif p.weapon_pos is not None:
                    ground_angle = math.atan2(p.weapon_dir[1], p.weapon_dir[0])
                    w_rot = pygame.transform.rotate(weapon_sprite, -math.degrees(ground_angle) + 90)
                    screen_w_pos = to_screen(p.weapon_pos)
                    rect = w_rot.get_rect(center=screen_w_pos)
                    window.blit(w_rot, rect)
        
        if show_debug_walls:
            # 4. Polygons
            for poly in map_config.POLYGONS:
                screen_poly = [to_screen(p) for p in poly]
                pygame.draw.lines(window, (0, 255, 0), True, screen_poly, 3)

            # --- NEW: 5. PLAYER & WEAPON HITBOXES ---
            for p in all_players:
                if not p.alive: continue
                
                screen_pos = to_screen(p.pos)
                
                # A. Physical Body (Red Circle)
                # We multiply radius by SCALE so it matches the zoom
                body_rad = int(p.radius * SCALE)
                pygame.draw.circle(window, (255, 0, 0), screen_pos, body_rad, 2)
                
                # B. Melee Range (Yellow Ring)
                # Only drawn if they are holding the weapon
                weapon_pos = None
                angle_deg = 0

                if p.has_weapon:
                    # Weapon in hand → match sprite rotation AND position
                    forward_vec = np.array([math.cos(p.angle), math.sin(p.angle)])
                    
                    # Same hand offset used for rendering
                    hand_offset = forward_vec * (20)
                    weapon_pos = (
                        p.pos[0] + forward_vec[0] * 20,
                        p.pos[1] + forward_vec[1] * 20
                    )

                    # Match sprite rotation exactly:
                    angle_deg = -math.degrees(p.angle) + 90

                elif p.weapon_flying:
                    weapon_pos = p.weapon_pos
                    angle_deg = -math.degrees(math.atan2(p.weapon_dir[1], p.weapon_dir[0]))

                elif p.weapon_pos is not None:
                    weapon_pos = p.weapon_pos
                    angle_deg = -math.degrees(math.atan2(p.weapon_dir[1], p.weapon_dir[0]))

                # Draw if we have a position
                if weapon_pos is not None:
                    g_corners = physics.get_corners(weapon_pos, (50, 16), angle_deg)
                    s_corners = [to_screen(c) for c in g_corners]
                    pygame.draw.lines(window, (255, 255, 0), True, s_corners, 3)

            # --- NEW: Cursor Map Info ---
            # Show game/map coordinates and pixel color under the cursor
            try:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                # Only show when cursor is inside the game area
                if SIDE_PANEL_WIDTH <= mouse_x <= SIDE_PANEL_WIDTH + DISPLAY_GAME_WIDTH and 0 <= mouse_y <= DISPLAY_GAME_HEIGHT:
                    game_x = (mouse_x - SIDE_PANEL_WIDTH) / SCALE
                    game_y = mouse_y / SCALE
                    coord_text = f"Map: ({int(game_x)}, {int(game_y)})"
                    txt_surf = font_text.render(coord_text, True, (255, 255, 255))

                    col_surf = None
                    if background_img:
                        # sample the scaled background image at the cursor local coordinates
                        local_x = int(mouse_x - SIDE_PANEL_WIDTH)
                        local_y = int(mouse_y)
                        if 0 <= local_x < DISPLAY_GAME_WIDTH and 0 <= local_y < DISPLAY_GAME_HEIGHT:
                            try:
                                col = background_img.get_at((local_x, local_y))
                                col_text = f"Pixel: {col[0]}, {col[1]}, {col[2]}"
                                col_surf = font_text.render(col_text, True, (255, 255, 255))
                            except Exception:
                                col_surf = None

                    # Build HUD surface
                    hud_w = txt_surf.get_width() + 8
                    hud_h = txt_surf.get_height() + 8
                    if col_surf:
                        hud_w = max(hud_w, col_surf.get_width() + 8)
                        hud_h += col_surf.get_height()

                    hud = pygame.Surface((hud_w, hud_h), pygame.SRCALPHA)
                    hud.fill((0, 0, 0, 160))
                    hud.blit(txt_surf, (4, 4))
                    if col_surf:
                        hud.blit(col_surf, (4, 4 + txt_surf.get_height()))

                    # Position HUD slightly offset from cursor so it doesn't obscure the pixel
                    hud_x = min(mouse_x + 16, SIDE_PANEL_WIDTH + DISPLAY_GAME_WIDTH - hud_w)
                    hud_y = min(mouse_y + 16, DISPLAY_GAME_HEIGHT - hud_h)
                    window.blit(hud, (hud_x, hud_y))
            except Exception:
                pass


        # 4. Draw UI
        draw_left_panel(left_ui_surface, green_team, font_title, font_text)
        # Draw debug info on left panel (per-player stuck/escape state)
        draw_debug_panel(left_ui_surface, all_players, font_text)
        draw_right_panel(right_ui_surface, red_team, kill_feed, font_title, font_text)
        
        window.blit(left_ui_surface, (0, 0))
        window.blit(right_ui_surface, (SIDE_PANEL_WIDTH + DISPLAY_GAME_WIDTH, 0))
        
        # 5. Overlays
        cx, cy = MONITOR_W // 2, MONITOR_H // 2
        
        if game_state == "WAITING":
            overlay = pygame.Surface((DISPLAY_GAME_WIDTH, DISPLAY_GAME_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 100))
            window.blit(overlay, (SIDE_PANEL_WIDTH, 0))
            text = font_win.render("PRESS SPACE TO START", True, (255, 255, 255))
            window.blit(text, (cx - text.get_width()//2, cy - text.get_height()//2))

        elif game_state == "COUNTDOWN":
            # If a single countdown audio was started, sync visuals using
            # manual settings: either explicit segment end-times
            # (`COUNTDOWN_SINGLE_SEGMENTS_MS`) or a total length
            # (`COUNTDOWN_SINGLE_LENGTH_MS`). If neither is provided we fall
            # back to per-number timing and per-number sounds.
            if countdown_audio_start is not None and (settings.COUNTDOWN_SINGLE_SEGMENTS_MS or countdown_audio_length):
                audio_elapsed = current_time - countdown_audio_start

                # If explicit segment boundaries provided, use them
                if settings.COUNTDOWN_SINGLE_SEGMENTS_MS:
                    seg = settings.COUNTDOWN_SINGLE_SEGMENTS_MS
                    # Expect a list/tuple of two integers: [end_ms_for_3, end_ms_for_2]
                    try:
                        t3_end, t2_end = int(seg[0]), int(seg[1])
                    except Exception:
                        t3_end, t2_end = None, None

                    if t3_end is None or t2_end is None:
                        # Malformed segments → fallback to equal thirds if total length provided
                        if countdown_audio_length:
                            if audio_elapsed >= countdown_audio_length:
                                game_state = "PLAYING"
                                countdown_last_play = None
                                count_text = ""
                                color = (255, 255, 255)
                            else:
                                frac = audio_elapsed / float(countdown_audio_length)
                                if frac < (1.0/3.0):
                                    count_text = "3"; color = (255, 0, 0)
                                elif frac < (2.0/3.0):
                                    count_text = "2"; color = (255, 165, 0)
                                else:
                                    count_text = "1"; color = (255, 255, 0)
                        else:
                            # Nothing sensible provided → fall back to per-number timing
                            audio_elapsed = None
                    else:
                        if audio_elapsed >= t2_end:
                            # Past all segments → countdown complete
                            game_state = "PLAYING"
                            countdown_last_play = None
                            count_text = ""
                            color = (255, 255, 255)
                        elif audio_elapsed >= t3_end:
                            count_text = "2"; color = (255, 165, 0)
                        else:
                            count_text = "3"; color = (255, 0, 0)

                # If no explicit segments but total length provided, split into thirds
                elif countdown_audio_length:
                    if audio_elapsed >= countdown_audio_length:
                        game_state = "PLAYING"
                        countdown_last_play = None
                        count_text = ""
                        color = (255, 255, 255)
                    else:
                        frac = audio_elapsed / float(countdown_audio_length)
                        if frac < (1.0/3.0):
                            count_text = "3"; color = (255, 0, 0)
                        elif frac < (2.0/3.0):
                            count_text = "2"; color = (255, 165, 0)
                        else:
                            count_text = "1"; color = (255, 255, 0)
                else:
                    # Shouldn't reach here; fall back to per-number behavior
                    audio_elapsed = None
            else:
                elapsed = current_time - countdown_start_time
                if elapsed < 1000:
                    count_text = "3"; color = (255, 0, 0)
                elif elapsed < 2000:
                    count_text = "2"; color = (255, 165, 0)
                elif elapsed < 3000:
                    count_text = "1"; color = (255, 255, 0)
                else:
                    game_state = "PLAYING"
                    countdown_last_play = None

                # Play countdown sound once when the visible number changes (per-number files / synth)
                try:
                    count_val = int(count_text)
                except Exception:
                    count_val = None
                if count_val is not None and count_val != countdown_last_play:
                    sound_manager.play_countdown(count_val)
                    countdown_last_play = count_val

            text = font_countdown.render(count_text, True, color)
            outline = font_countdown.render(count_text, True, (0,0,0))
            window.blit(outline, (cx - text.get_width()//2 + 5, cy - text.get_height()//2 + 5))
            window.blit(text, (cx - text.get_width()//2, cy - text.get_height()//2))

        elif game_state == "GAME_OVER":
            text = font_win.render(winner_text, True, winner_color)
            outline = font_win.render(winner_text, True, (0, 0, 0))
            window.blit(outline, (cx - text.get_width()//2 + 4, cy - text.get_height()//2 + 4))
            window.blit(text, (cx - text.get_width()//2, cy - text.get_height()//2))

        pygame.display.flip()
        clock.tick(settings.FPS)
    pygame.quit()

if __name__ == "__main__":
    main()