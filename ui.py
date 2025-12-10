import pygame
import settings
import roster
import numpy as np

def draw_team_stats(surface, team, y_start, font_text, font_small, color_primary):
    y_off = y_start
    panel_width = surface.get_width()
    bar_width = 160
    
    for p in team:
        # --- PREPARE DATA ---
        kills = getattr(p, 'kills', 0)
        deaths = getattr(p, 'deaths', 0)
        dmg = getattr(p, 'damage_dealt', 0)
        cooldown = getattr(p, 'cooldown', 0)
        max_cooldown = getattr(p, 'max_cooldown', 60)
        
        text_color = (255, 255, 255) if p.alive else (100, 100, 100)
        
        # Row 1: Name and K/D
        name_txt = font_text.render(p.name, True, text_color)
        surface.blit(name_txt, (20, y_off))
        
        kd_txt = font_text.render(f"K:{kills} D:{deaths}", True, (255, 215, 0))
        surface.blit(kd_txt, (panel_width - 20 - kd_txt.get_width(), y_off))
        
        # Row 2: HP Bar + DMG
        y_bar = y_off + 22
        pygame.draw.rect(surface, (50, 0, 0), (20, y_bar, bar_width, 10)) # BG
        
        if p.alive:
            hp_pct = max(0, p.hp / p.max_hp)
            pygame.draw.rect(surface, color_primary, (20, y_bar, bar_width * hp_pct, 10)) # FG
            
            # Tiny HP Text
            hp_txt = font_small.render(f"{int(p.hp)}/{p.max_hp}", True, (255, 255, 255))
            surface.blit(hp_txt, (20 + bar_width/2 - hp_txt.get_width()/2, y_bar - 1))

        dmg_txt = font_small.render(f"DMG: {int(dmg)}", True, (200, 200, 200))
        surface.blit(dmg_txt, (20 + bar_width + 10, y_bar))

        # Row 3: Cooldown Bar
        if p.alive:
            y_cd = y_bar + 14
            if max_cooldown > 0:
                cd_pct = 1.0 - min(1.0, max(0, cooldown / max_cooldown))
            else:
                cd_pct = 1.0
            pygame.draw.rect(surface, (0, 0, 50), (20, y_cd, bar_width, 4))
            cd_color = (0, 255, 255) if cd_pct == 1.0 else (0, 100, 200)
            pygame.draw.rect(surface, cd_color, (20, y_cd, bar_width * cd_pct, 4))

        y_off += 60 # Spacing

# Added font_small to arguments
def draw_left_panel(surface, green_team, font_title, font_text, font_small): 
    surface.fill(settings.UI_BG_COLOR)
    
    # Title
    title = font_title.render(roster.TEAM_GREEN_TITLE, True, settings.GREEN_TEAM_COLOR)
    rect = title.get_rect(center=(surface.get_width()//2, 40))
    surface.blit(title, rect)
    
    # Draw Green Stats (Using new function)
    draw_team_stats(surface, green_team, 80, font_text, font_small, settings.GREEN_TEAM_COLOR)

# Added font_small to arguments
def draw_right_panel(surface, red_team, kill_feed, font_title, font_text, font_small):
    surface.fill(settings.UI_BG_COLOR)
    
    # Title
    title = font_title.render(roster.TEAM_RED_TITLE, True, settings.RED_TEAM_COLOR)
    rect = title.get_rect(center=(surface.get_width()//2, 40))
    surface.blit(title, rect)
    
    # Draw Red Stats (Using new function)
    draw_team_stats(surface, red_team, 80, font_text, font_small, settings.RED_TEAM_COLOR)

    # Draw Kill Feed
    kf_y = surface.get_height() - 250
    pygame.draw.line(surface, (100, 100, 100), (20, kf_y), (surface.get_width()-20, kf_y), 2)
    
    kf_title = font_title.render("KILL FEED", True, (255, 255, 0))
    surface.blit(kf_title, (20, kf_y + 10))
    
    msg_y = kf_y + 40
    for msg in kill_feed[-8:]: 
        # Using font_small for feed
        txt = font_small.render(msg, True, (220, 220, 220))
        surface.blit(txt, (20, msg_y))
        msg_y += 20

def draw_debug_panel(surface, players, font_text):
    # (Kept simple for now)
    pass