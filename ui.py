import pygame
import settings
import roster
import numpy as np

def draw_health_bars(surface, team, y_start, font_text, color_bar):
    y_off = y_start
    for p in team:
        # Name
        color_text = (255, 255, 255) if p.alive else (100, 100, 100)
        name_txt = font_text.render(f"{p.name} ({max(0, int(p.hp))}/{p.max_hp})", True, color_text)
        surface.blit(name_txt, (20, y_off))
        
        # Bar
        if p.alive:
            pct = max(0, p.hp / p.max_hp)
            # Draw bar below name
            pygame.draw.rect(surface, (50, 0, 0), (20, y_off + 25, 200, 10))
            pygame.draw.rect(surface, color_bar, (20, y_off + 25, 200 * pct, 10))
        
        y_off += 50 # Spacing

def draw_left_panel(surface, green_team, font_title, font_text):
    surface.fill(settings.UI_BG_COLOR)
    
    # Title
    title = font_title.render(roster.TEAM_GREEN_TITLE, True, settings.GREEN_TEAM_COLOR)
    # Center title horizontally
    rect = title.get_rect(center=(surface.get_width()//2, 40))
    surface.blit(title, rect)
    
    # Draw Green Stats
    draw_health_bars(surface, green_team, 80, font_text, settings.GREEN_TEAM_COLOR)


def draw_debug_panel(surface, players, font_text):
    """Draw per-player debug info on the provided UI surface (left side).
    Shows name, stuck timer, escape direction and stuck origin distance.
    """
    x = 20
    # Start a bit lower to avoid overlapping team list
    y = 80 + (len(players[:8]) * 50) + 10
    # Draw a titled box
    pygame.draw.rect(surface, (30, 30, 30), (10, y - 10, surface.get_width() - 20, min(400, surface.get_height() - y - 20)))
    title = font_text.render("DEBUG (Players)", True, (200, 200, 200))
    surface.blit(title, (x, y))
    y += 24

    for p in players:
        try:
            name = p.name
            stuck = int(p.stuck_timer) if hasattr(p, 'stuck_timer') else 0
            esc = p.escape_dir if hasattr(p, 'escape_dir') else None
            esc_str = "(0.00,0.00)"
            if esc is not None:
                esc_str = f"({esc[0]:.2f},{esc[1]:.2f})"
            origin_dist = "N/A"
            if hasattr(p, 'stuck_origin') and p.stuck_origin is not None:
                try:
                    origin_dist = f"{np.linalg.norm(p.pos - p.stuck_origin):.1f}"
                except Exception:
                    origin_dist = "N/A"

            # Colorize name when actively stuck
            color = (255, 100, 100) if stuck > 0 else (200, 200, 200)
            txt = font_text.render(f"{name}: STK={stuck} ESC={esc_str} OR_DIST={origin_dist}", True, color)
            surface.blit(txt, (x, y))
            y += 20
            if y > surface.get_height() - 30:
                break
        except Exception:
            continue

def draw_right_panel(surface, red_team, kill_feed, font_title, font_text):
    surface.fill(settings.UI_BG_COLOR)
    
    # Title
    title = font_title.render(roster.TEAM_RED_TITLE, True, settings.RED_TEAM_COLOR)
    rect = title.get_rect(center=(surface.get_width()//2, 40))
    surface.blit(title, rect)
    
    # Draw Red Stats
    draw_health_bars(surface, red_team, 80, font_text, settings.RED_TEAM_COLOR)

    # Draw Kill Feed at Bottom
    kf_y = surface.get_height() - 250
    pygame.draw.line(surface, (100, 100, 100), (20, kf_y), (surface.get_width()-20, kf_y), 2)
    
    kf_title = font_title.render("KILL FEED", True, (255, 255, 0))
    surface.blit(kf_title, (20, kf_y + 10))
    
    msg_y = kf_y + 50
    for msg in kill_feed[-6:]: # Show last 6 kills
        txt = font_text.render(msg, True, (200, 200, 200))
        surface.blit(txt, (20, msg_y))
        msg_y += 25

def draw_debug_panel(surface, players, font):
    """Draws a debug panel on the left UI surface."""
    y_offset = 300  # Start below the team list
    for i, p in enumerate(players):
        state = "IDLE"
        if p.escape_timer > 0:
            state = f"ESCAPE ({p.escape_timer})"
        elif p.stuck_timer > 0:
            state = f"STUCK ({p.stuck_timer})"
        elif p.wander_target is not None:
            state = "WANDER"
        elif p.patrol_target is not None:
            state = "PATROL"
        
        color = (255, 255, 0) # Yellow for debug info
        
        debug_text = f"{p.name}: {state}"
        text_surf = font.render(debug_text, True, color)
        surface.blit(text_surf, (10, y_offset))
        y_offset += 20
        
        if p.move_target is not None:
            target_text = f"  Target: ({int(p.move_target[0])}, {int(p.move_target[1])})"
            text_surf = font.render(target_text, True, color)
            surface.blit(text_surf, (10, y_offset))
            y_offset += 25 # Extra space between players