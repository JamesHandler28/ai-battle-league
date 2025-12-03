import numpy as np
import physics

def cast_ray(start, end, walls, circles, rot_walls, polygons):
    # Standard Rect Walls
    for w in walls:
        if w.clipline(start, end): return True
    # Rotated Walls
    for r_wall in rot_walls:
        if physics.line_intersects_rotated_rect(start, end, r_wall): return True
    # Polygons
    for poly in polygons:
        if physics.line_intersects_polygon(start, end, poly): return True
    # Circles (Pillars)
    for center, radius in circles:
        if physics.line_intersects_circle(start, end, np.array(center), radius + 5): return True
    return False 

def check_line_of_sight(start_pos, end_pos, walls, circles, rot_walls, polygons):
    # Optimization: Inflate walls slightly for LoS so bots don't shoot scraping edges
    inflated_walls = [w.inflate(20, 20) for w in walls]
    
    if cast_ray(start_pos, end_pos, inflated_walls, circles, rot_walls, polygons): return False
    
    # Thickness check (shoot 2 rays side by side)
    vec = end_pos - start_pos
    dist = np.linalg.norm(vec)
    if dist == 0: return True
    perp = np.array([-vec[1], vec[0]]) / dist * 12.0 
    
    if cast_ray(start_pos + perp, end_pos + perp, inflated_walls, circles, rot_walls, polygons): return False
    if cast_ray(start_pos - perp, end_pos - perp, inflated_walls, circles, rot_walls, polygons): return False
    
    return True