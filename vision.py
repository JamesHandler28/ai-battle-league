import numpy as np
import physics

def cast_ray(start, end, polygons):
    """Raycast against polygons only. Returns True if the segment intersects any polygon."""
    for poly in polygons:
        if physics.line_intersects_polygon(start, end, poly):
            return True
    return False


def check_line_of_sight(start_pos, end_pos, polygons):
    """Check LoS using polygon-only geometry. Uses two offset rays for thickness."""
    # Primary ray
    if cast_ray(start_pos, end_pos, polygons):
        return False

    # Thickness check (shoot 2 rays side by side)
    vec = end_pos - start_pos
    dist = np.linalg.norm(vec)
    if dist == 0:
        return True
    perp = np.array([-vec[1], vec[0]]) / dist * 12.0

    if cast_ray(start_pos + perp, end_pos + perp, polygons):
        return False
    if cast_ray(start_pos - perp, end_pos - perp, polygons):
        return False

    return True