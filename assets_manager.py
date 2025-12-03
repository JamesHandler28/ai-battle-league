import pygame
import os

TEXTURE_CACHE = {}

def load_texture(filename, size=None, fixed_height=None):
    # CHANGED: We now include the size in the key!
    # This prevents the "Small Image" cache from blocking the "Big Image" request.
    key = (filename, size, fixed_height)
    
    if key in TEXTURE_CACHE: return TEXTURE_CACHE[key]
    
    try:
        path = os.path.join("assets", filename)
        img = pygame.image.load(path).convert_alpha()
        
        if size: 
            img = pygame.transform.smoothscale(img, size)
        elif fixed_height:
            aspect = img.get_width() / img.get_height()
            new_w = int(fixed_height * aspect)
            img = pygame.transform.smoothscale(img, (new_w, fixed_height))
            
        TEXTURE_CACHE[key] = img
        return img
    except Exception as e:
        print(f"Warning: Could not load {filename}. Using fallback. ({e})")
        s = size if size else (40, 40)
        surf = pygame.Surface(s, pygame.SRCALPHA)
        pygame.draw.circle(surf, (255, 0, 255), (s[0]//2, s[1]//2), s[0]//2)
        TEXTURE_CACHE[key] = surf
        return surf