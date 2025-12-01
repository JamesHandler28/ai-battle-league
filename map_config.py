import pygame

# --- MAP SETTINGS ---
MAP_IMAGE_FILE = "Warehouse.png" 

# --- COLLISION WALLS ---
# TIP: In Edit Mode, hover your mouse over a spot to see the (X, Y) coordinates!
# Format: pygame.Rect(x, y, width, height)

WALLS = [
    
    # 1. TOP WALL
    pygame.Rect(0, -50, 3000, 50),       

    # 2. BOTTOM WALL
    pygame.Rect(0, 1200, 3000, 50),      

    # 3. RIGHT WALL
    pygame.Rect(900, 0, 50, 3000),      

    # 4. LEFT WALL
    pygame.Rect(-50, 0, 50, 3000),
    
    # Boxes
    pygame.Rect(230, 260, 112, 52),
    pygame.Rect(555, 885, 112, 52),

    pygame.Rect(0, 555, 180, 85),
    pygame.Rect(720, 555, 180, 85),

]

# --- CIRCLES ---
CIRCLES = []

# --- ROTATED WALLS ---
# Format: ((Center_X, Center_Y), (Width, Height), Angle)
ROTATED_WALLS = [
    ((180, 425), (70, 70), 18), 
    ((715, 775), (70, 70), 18),
]

# --- POLYGONS ---
POLYGONS = [
    # Example: An "L" shaped wall (No seams!)
    [
        (615, 255),
        (733, 255),
        (733, 374),
        (675, 374),
        (675, 313),
        (615, 313),
    ],

    [
        (167, 821),
        (226, 821),
        (226, 881),
        (285, 881),
        (285, 939),
        (170, 939),
    ],

    [
        (407, 420),
        (565, 420),
        (565, 565),
        (540, 565),
        (540, 615),
        (494, 615),
        (494, 773),
        (331, 773),
        (331, 629),
        (358, 629),
        (360, 582),
        (404, 582),
    ],
]