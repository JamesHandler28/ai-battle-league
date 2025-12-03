import math
import numpy as np

def rotate_vector(vec, angle_degrees):
    theta = math.radians(angle_degrees)
    cs = math.cos(theta)
    sn = math.sin(theta)
    return np.array([vec[0]*cs - vec[1]*sn, vec[0]*sn + vec[1]*cs])

def line_intersects_circle(start_pos, end_pos, circle_center, radius):
    d = end_pos - start_pos
    f = start_pos - circle_center
    a = np.dot(d, d)
    b = 2 * np.dot(f, d)
    c = np.dot(f, f) - radius**2
    discriminant = b**2 - 4*a*c
    if discriminant < 0: return False 
    discriminant = math.sqrt(discriminant)
    t1 = (-b - discriminant) / (2*a)
    t2 = (-b + discriminant) / (2*a)
    if 0 <= t1 <= 1 or 0 <= t2 <= 1: return True
    return False

def get_corners(center, size, angle):
    cx, cy = center
    w, h = size[0]/2, size[1]/2
    rad = math.radians(-angle)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    corners = []
    for dx, dy in [(-w, -h), (w, -h), (w, h), (-w, h)]:
        rx = dx * cos_a - dy * sin_a
        ry = dx * sin_a + dy * cos_a
        corners.append((cx + rx, cy + ry))
    return corners

def check_circle_rotated_rect(circle_pos, radius, rect_data):
    (cx, cy), (w, h), angle = rect_data
    tx = circle_pos[0] - cx
    ty = circle_pos[1] - cy
    rad = math.radians(angle)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    local_x = tx * cos_a - ty * sin_a
    local_y = tx * sin_a + ty * cos_a
    closest_x = max(-w/2, min(w/2, local_x))
    closest_y = max(-h/2, min(h/2, local_y))
    dist_x = local_x - closest_x
    dist_y = local_y - closest_y
    distance_sq = dist_x**2 + dist_y**2
    if distance_sq < radius**2:
        dist = math.sqrt(distance_sq)
        if dist == 0: 
            overlap = radius
            normal = np.array([1.0, 0.0])
        else: 
            overlap = radius - dist
            normal = np.array([dist_x/dist, dist_y/dist])
        world_nx = normal[0] * cos_a + normal[1] * sin_a
        world_ny = -normal[0] * sin_a + normal[1] * cos_a 
        return True, np.array([world_nx, world_ny]), overlap
    return False, None, 0

def line_intersects_rotated_rect(p1, p2, rect_data):
    corners = get_corners(*rect_data)
    for i in range(4):
        p3 = corners[i]
        p4 = corners[(i+1)%4]
        d = (p2[0]-p1[0])*(p4[1]-p3[1]) - (p2[1]-p1[1])*(p4[0]-p3[0])
        if d != 0:
            u = ((p3[0]-p1[0])*(p4[1]-p3[1]) - (p3[1]-p1[1])*(p4[0]-p3[0])) / d
            v = ((p3[0]-p1[0])*(p2[1]-p1[1]) - (p3[1]-p1[1])*(p2[0]-p1[0])) / d
            if 0 <= u <= 1 and 0 <= v <= 1: return True
    return False

def resolve_circle_polygon(pos, radius, points):
    hit = False
    best_push = np.array([0.0, 0.0])
    max_overlap = -9999
    
    # Check edges
    for i in range(len(points)):
        p1 = np.array(points[i])
        p2 = np.array(points[(i + 1) % len(points)])
        edge = p2 - p1
        edge_len_sq = np.dot(edge, edge)
        if edge_len_sq == 0: continue
        t = max(0, min(1, np.dot(pos - p1, edge) / edge_len_sq))
        closest_point = p1 + t * edge
        diff = pos - closest_point
        dist_sq = np.dot(diff, diff)
        
        if dist_sq < radius * radius:
            dist = math.sqrt(dist_sq)
            if dist == 0: 
                # Should not happen often, push perpendicular to edge
                normal = np.array([-edge[1], edge[0]])
                normal = normal / np.linalg.norm(normal)
                overlap = radius
            else: 
                normal = diff / dist
                overlap = radius - dist
            
            if overlap > max_overlap:
                max_overlap = overlap
                best_push = normal * overlap
                hit = True
                
    # Basic containment check (simplified)
    # If the center is strictly inside, the edge logic above usually handles the push out
    # provided the radius is large enough relative to speed.
    return hit, best_push

def line_intersects_polygon(p1, p2, points):
    for i in range(len(points)):
        p3 = np.array(points[i])
        p4 = np.array(points[(i + 1) % len(points)])
        d = (p2[0]-p1[0])*(p4[1]-p3[1]) - (p2[1]-p1[1])*(p4[0]-p3[0])
        if d != 0:
            u = ((p3[0]-p1[0])*(p4[1]-p3[1]) - (p3[1]-p1[1])*(p4[0]-p3[0])) / d
            v = ((p3[0]-p1[0])*(p2[1]-p1[1]) - (p3[1]-p1[1])*(p2[0]-p1[0])) / d
            if 0 <= u <= 1 and 0 <= v <= 1: return True
    return False