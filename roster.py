import random

class BotStats:
    def __init__(self, name, image_file, hp, speed, melee_dmg, throw_dmg, cooldown, aggression, strafe_rate, accuracy, melee_bias):
        self.name = name
        self.image_file = image_file

        self.hp = hp
        self.speed = speed
        self.melee_dmg = melee_dmg 
        self.throw_dmg = throw_dmg 
        self.cooldown = cooldown 
        self.aggression = aggression 
        self.strafe_rate = strafe_rate 
        self.accuracy = accuracy 
        self.melee_bias = melee_bias 

ALL_BOTS = [
    # TEAM BIKINI BOTTOM (PINK)
    BotStats("SpongeBob", "BBSpongebob.png", hp=9, speed=0.5, melee_dmg=3, throw_dmg=6, cooldown=60, aggression=100, strafe_rate=0.5, accuracy=0.7, melee_bias=0.4),
    BotStats("Patrick",   "BBPatrick.png",   hp=9, speed=0.4, melee_dmg=3, throw_dmg=6, cooldown=60, aggression=100, strafe_rate=0.1, accuracy=0.4, melee_bias=0.4),
    BotStats("Squidward", "BBSquidward.png", hp=9, speed=0.4, melee_dmg=3, throw_dmg=6, cooldown=60, aggression=600, strafe_rate=0.1, accuracy=0.8, melee_bias=0.4),
    BotStats("Mr. Krabs", "BBKrabs.png",     hp=9, speed=0.5, melee_dmg=3, throw_dmg=6, cooldown=60, aggression=150, strafe_rate=0.2, accuracy=0.7, melee_bias=0.3),

    # TEAM QUAHOG (BLUE)
    BotStats("Peter",     "QPeter.png",      hp=9, speed=0.4, melee_dmg=3, throw_dmg=6, cooldown=60, aggression=100, strafe_rate=0.0, accuracy=0.5, melee_bias=0.4),
    BotStats("Stewie",    "QStewie.png",     hp=9, speed=0.2, melee_dmg=2, throw_dmg=6, cooldown=30, aggression=700, strafe_rate=0.3, accuracy=0.9, melee_bias=0.3),
    BotStats("Brian",     "QBrian.png",      hp=9, speed=0.7, melee_dmg=2, throw_dmg=6, cooldown=30, aggression=400, strafe_rate=0.1, accuracy=0.8, melee_bias=0.6),
    BotStats("Lois",      "QLois.png",       hp=9, speed=0.5, melee_dmg=3, throw_dmg=6, cooldown=60, aggression=200, strafe_rate=0.2, accuracy=0.7, melee_bias=0.5),

    # TEAM MUSHROOM KINGDOM (RED)
    BotStats("Mario",     "MKMario.png",     hp=9, speed=0.6, melee_dmg=3, throw_dmg=6, cooldown=60, aggression=300, strafe_rate=0.2, accuracy=0.8, melee_bias=0.7),
    BotStats("Luigi",     "MKLuigi.png",     hp=9, speed=0.5, melee_dmg=3, throw_dmg=6, cooldown=60, aggression=500, strafe_rate=0.6, accuracy=0.7, melee_bias=0.6),
    BotStats("Bowser",    "MKBowser.png",    hp=9, speed=0.3, melee_dmg=5, throw_dmg=6, cooldown=120, aggression=100, strafe_rate=0.0, accuracy=0.6, melee_bias=0.2),
    BotStats("Peach",     "MKPeach.png",     hp=9, speed=0.6, melee_dmg=2, throw_dmg=6, cooldown=30, aggression=600, strafe_rate=0.2, accuracy=0.9, melee_bias=0.5),

    # TEAM SPRINGFIELD (YELLOW)
    BotStats("Homer",     "SHomer.png",      hp=9, speed=0.4, melee_dmg=3, throw_dmg=6, cooldown=60, aggression=150, strafe_rate=0.1, accuracy=0.5, melee_bias=0.5),
    BotStats("Bart",      "SBart.png",       hp=9, speed=0.6, melee_dmg=3, throw_dmg=6, cooldown=60, aggression=300, strafe_rate=0.7, accuracy=0.8, melee_bias=0.4),
    BotStats("Lisa",      "SLisa.png",       hp=9, speed=0.5, melee_dmg=2, throw_dmg=6, cooldown=30, aggression=800, strafe_rate=0.1, accuracy=1.0, melee_bias=0.6),
    BotStats("Marge",     "SMarge.png",      hp=9, speed=0.3, melee_dmg=3, throw_dmg=6, cooldown=60, aggression=400, strafe_rate=0.2, accuracy=0.7, melee_bias=0.6),
    
    # TEAM RING (GREEN)
    BotStats("Sonic",     "RSonic.png",      hp=9, speed=1.0, melee_dmg=3, throw_dmg=6, cooldown=60, aggression=100, strafe_rate=0.8, accuracy=0.6, melee_bias=0.3),
    BotStats("Knuckles",  "RKnuckles.png",   hp=9, speed=0.8, melee_dmg=3, throw_dmg=6, cooldown=60, aggression=100, strafe_rate=0.8, accuracy=0.5, melee_bias=0.8),
    BotStats("Tails",     "RTails.png",      hp=9, speed=0.7, melee_dmg=3, throw_dmg=6, cooldown=60, aggression=500, strafe_rate=0.8, accuracy=0.7, melee_bias=0.2),
    BotStats("Shadow",    "RShadow.png",     hp=9, speed=0.9, melee_dmg=3, throw_dmg=6, cooldown=60, aggression=600, strafe_rate=0.9, accuracy=0.8, melee_bias=0.8),

    # TEAM DC (BLACK)
    BotStats("Superman",  "DCSuperman.png",  hp=9, speed=0.8, melee_dmg=3, throw_dmg=6, cooldown=60, aggression=100, strafe_rate=0.1, accuracy=0.8, melee_bias=0.5),
    BotStats("Batman",    "DCBatman.png",    hp=9, speed=0.5, melee_dmg=3, throw_dmg=6, cooldown=60, aggression=300, strafe_rate=0.5, accuracy=0.9, melee_bias=0.5),
    BotStats("Flash",     "DCFlash.png",     hp=9, speed=1.0, melee_dmg=2, throw_dmg=6, cooldown=30, aggression=100, strafe_rate=0.9, accuracy=0.6, melee_bias=0.3),
    BotStats("Wonder",    "DCWonder.png",    hp=9, speed=0.5, melee_dmg=2, throw_dmg=6, cooldown=30, aggression=100, strafe_rate=0.0, accuracy=0.5, melee_bias=0.3),

    # TEAM SOUTH PARK (WHITE)
    BotStats("Cartman",   "SPCartman.png",   hp=9, speed=0.2, melee_dmg=5, throw_dmg=6, cooldown=120, aggression=150, strafe_rate=0.1, accuracy=0.7, melee_bias=0.4),
    BotStats("Kenny",     "SPKenny.png",     hp=9, speed=0.7, melee_dmg=3, throw_dmg=6, cooldown=60, aggression=200, strafe_rate=0.5, accuracy=0.5, melee_bias=0.5),
    BotStats("Kyle",      "SPKyle.png",      hp=9, speed=0.4, melee_dmg=3, throw_dmg=6, cooldown=60, aggression=500, strafe_rate=0.2, accuracy=0.8, melee_bias=0.5),
    BotStats("Stan",      "SPStan.png",      hp=9, speed=0.5, melee_dmg=3, throw_dmg=6, cooldown=60, aggression=300, strafe_rate=0.2, accuracy=0.7, melee_bias=0.4),

    # TEAM PEANUTS (ORANGE)
    BotStats("Charlie B", "PCharlieB.png",   hp=9, speed=0.4, melee_dmg=3, throw_dmg=6, cooldown=60, aggression=200, strafe_rate=0.1, accuracy=0.4, melee_bias=0.4),
    BotStats("Snoopy",    "PSnoopy.png",     hp=9, speed=0.7, melee_dmg=2, throw_dmg=6, cooldown=30, aggression=100, strafe_rate=0.6, accuracy=0.8, melee_bias=0.7),
    BotStats("Lucy",      "PLucy.png",       hp=9, speed=0.3, melee_dmg=2, throw_dmg=6, cooldown=30, aggression=150, strafe_rate=0.2, accuracy=0.6, melee_bias=0.8),
    BotStats("Woodstock", "PWoodstock.png",  hp=9, speed=0.6, melee_dmg=5, throw_dmg=6, cooldown=120, aggression=500, strafe_rate=0.3, accuracy=0.7, melee_bias=0.3),
    
    # OTHERS
    BotStats("67",        "67kid.png",       hp=30, speed=1.0, melee_dmg=5, throw_dmg=9, cooldown=0, aggression=800, strafe_rate=1.0, accuracy=1.0, melee_bias=0.1),
]

# --- MATCHUP CONFIG ---

# 1. Custom Team Names (Displayed in UI)
TEAM_GREEN_TITLE = "Fat"
TEAM_RED_TITLE   = "Fast"

# 2. Who is fighting?
TEAM_GREEN_NAMES = ["Cartman", "Peter", "Homer", "Patrick"]
TEAM_RED_NAMES   = ["Flash", "Sonic", "Snoopy", "Kenny"]