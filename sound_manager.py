import pygame
import os
import time
import numpy as np

SOUND_CACHE = {}
DEATH_CHANNEL = None  # Dedicated channel for death sounds
LAST_WALK_TIME = 0  # Track last walk sound play time

def load_sound(filename, volume=1.0):
    """Load a sound effect with caching"""
    if filename in SOUND_CACHE:
        return SOUND_CACHE[filename]
    
    try:
        path = os.path.join("assets", filename)
        # If the file doesn't exist, silently return None (avoid noisy warnings)
        if not os.path.exists(path):
            return None
        sound = pygame.mixer.Sound(path)
        sound.set_volume(min(1.0, volume))
        SOUND_CACHE[filename] = sound
        return sound
    except Exception as e:
        print(f"Warning: Could not load sound {filename}. ({e})")
        return None

def play_sound(filename, volume=1.0):
    """Load and play a sound effect immediately"""
    sound = load_sound(filename, volume)
    if sound:
        sound.play()

# Preload common sounds
SWING_SOUND = None
THROW_SOUND = None
WALK_SOUND = None
DEATH_SOUND = None
COLLISION_SOUND = None
COUNTDOWN_SOUNDS = {}  # map int -> Sound
LAST_COUNTDOWN_TIME = 0
COUNTDOWN_SINGLE = None

def init_sounds():
    """Initialize all sound effects (call once at game start)"""
    global SWING_SOUND, THROW_SOUND, WALK_SOUND, DEATH_SOUND, DEATH_CHANNEL, COLLISION_SOUND
    
    SWING_SOUND = load_sound("swing.wav", volume=0.7)
    THROW_SOUND = load_sound("throw.wav", volume=0.7)
    WALK_SOUND = load_sound("walk.wav", volume=0.2)
    DEATH_SOUND = load_sound("death.wav", volume=1.0)
    COLLISION_SOUND = load_sound("collision.wav", volume=0.5)
    # Try to preload countdown clips (3,2,1). If missing, we'll synthesize a beep on demand.
    for n in (3, 2, 1):
        snd = load_sound(f"countdown_{n}.wav", volume=0.9)
        if snd:
            COUNTDOWN_SOUNDS[n] = snd
    # Also try a single countdown track (e.g. a 3-second file)
    global COUNTDOWN_SINGLE
    COUNTDOWN_SINGLE = load_sound("countdown.wav", volume=0.95)
    
    # Create a dedicated channel for death sounds (prevents overlapping)
    DEATH_CHANNEL = pygame.mixer.Channel(0)
    
    # Silent in normal runs: avoid terminal output about loaded sounds

def play_swing():
    """Play swing sound effect"""
    if SWING_SOUND:
        SWING_SOUND.play()

def play_throw():
    """Play throw sound effect"""
    if THROW_SOUND:
        THROW_SOUND.play()

def play_walk():
    """Play walking sound effect (quiet) with slight delay between plays"""
    global LAST_WALK_TIME
    current_time = time.time()
    if WALK_SOUND and (current_time - LAST_WALK_TIME) > 0.2:  # 100ms delay between plays
        WALK_SOUND.play()
        LAST_WALK_TIME = current_time

def play_death():
    """Play death sound effect - uses dedicated channel to ensure it plays"""
    if DEATH_SOUND and DEATH_CHANNEL:
        DEATH_CHANNEL.play(DEATH_SOUND)
    else:
        # Do not print warnings to terminal; silently ignore missing channel/sound
        pass

def play_collision():
    """Play weapon collision sound effect"""
    if COLLISION_SOUND:
        COLLISION_SOUND.play()


def _synthesize_beep(frequency=880.0, duration=0.12, volume=0.5, sample_rate=44100):
    """Synthesize a short sine-wave beep and return a pygame Sound."""
    length = int(sample_rate * duration)
    t = np.linspace(0, duration, length, False)
    wave = 0.5 * np.sin(2 * np.pi * frequency * t)
    # convert to 16-bit signed
    audio = np.int16(wave * (2**15 - 1) * volume)
    try:
        sound = pygame.sndarray.make_sound(audio)
        return sound
    except Exception as e:
        # If sndarray not available or failure, fallback to None (silent)
        return None


def play_countdown(n: int):
    """Play countdown sound for number `n` (3/2/1).

    Looks for `assets/countdown_3.wav`, etc. If not found, synthesizes a short beep.
    """
    if n in COUNTDOWN_SOUNDS:
        COUNTDOWN_SOUNDS[n].play()
        return

    # fallback: synthesize different frequency per number
    freq_map = {3: 720.0, 2: 880.0, 1: 1000.0}
    freq = freq_map.get(n, 800.0)
    snd = _synthesize_beep(frequency=freq, duration=0.12, volume=0.6)
    if snd:
        snd.play()


def has_single_countdown():
    return COUNTDOWN_SINGLE is not None


def play_countdown_single():
    """Play the single countdown track (if available) and return its length in seconds.

    Returns None if no single track is available.
    """
    if COUNTDOWN_SINGLE:
        try:
            COUNTDOWN_SINGLE.play()
            # NOTE: We intentionally do NOT return the audio length here.
            # Timing / segmentation for a single countdown audio is controlled
            # manually via `settings.py` (COUNTDOWN_SINGLE_LENGTH_MS or
            # COUNTDOWN_SINGLE_SEGMENTS_MS). This avoids automatic length
            # measurement and gives the user explicit control.
            return None
        except Exception as e:
            # Silent on playback error
            return None
    return None


def get_countdown_single_length():
    if COUNTDOWN_SINGLE:
        try:
            return COUNTDOWN_SINGLE.get_length()
        except Exception:
            return None
    return None
