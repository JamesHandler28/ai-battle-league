import pygame

# --- DISPLAY SETTINGS ---
GAME_WIDTH = 900
GAME_HEIGHT = 1200
UI_WIDTH = 400 
FPS = 60

# --- CALCULATED DIMENSIONS ---
# (We will set the scale dynamically in main.py, but these are defaults)
TOTAL_WIDTH = GAME_WIDTH + UI_WIDTH
TOTAL_HEIGHT = GAME_HEIGHT

# --- COLORS ---
FLOOR_COLOR = (20, 20, 25)
UI_BG_COLOR = (30, 30, 35)
GREEN_TEAM_COLOR = (50, 255, 50)
RED_TEAM_COLOR = (255, 50, 50)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# --- COUNTDOWN AUDIO TIMING (MANUAL) ---
# If you provide a single countdown audio file (`assets/countdown.wav`),
# you can control how the on-screen numbers map to that audio by setting
# one of the following values.
#
# - `COUNTDOWN_SINGLE_LENGTH_MS` (int): total length of the single countdown
#    audio in milliseconds. When provided, visuals will be split into three
#    equal thirds across this length.
#
# - `COUNTDOWN_SINGLE_SEGMENTS_MS` (list of two ints): precise segment
#    end-times (in ms from audio start) for the transitions between numbers.
#    Example: `[1200, 2500]` means 0..1200ms => '3', 1200..2500ms => '2',
#    2500ms..end => '1'. If this is provided it overrides
#    `COUNTDOWN_SINGLE_LENGTH_MS` segmentation.
COUNTDOWN_SINGLE_LENGTH_MS = 1200
COUNTDOWN_SINGLE_SEGMENTS_MS = None