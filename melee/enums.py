"""Enum values for various Melee objects """

from enum import Enum

class Stage(Enum):
    """A VS-mode stage """
    NO_STAGE = 0
    FINAL_DESTINATION = 0x19
    BATTLEFIELD = 0x18
    POKEMON_STADIUM = 0x12
    DREAMLAND = 0x1A
    FOUNTAIN_OF_DREAMS = 0x8
    YOSHIS_STORY = 0x6
    RANDOM_STAGE = 0x1D # not technically a stage, but it's useful to call it one

def to_internal_stage(stage_id):
    if stage_id == 0x03:
        return Stage.POKEMON_STADIUM
    if stage_id == 0x08:
        return Stage.YOSHIS_STORY
    if stage_id == 0x02:
        return Stage.FOUNTAIN_OF_DREAMS
    if stage_id == 0x1F:
        return Stage.BATTLEFIELD
    if stage_id == 0x20:
        return Stage.FINAL_DESTINATION
    if stage_id == 0x1C:
        return Stage.DREAMLAND
    return Stage.NO_STAGE

class Menu(Enum):
    """A primary menu scene the game can be in """
    CHARACTER_SELECT = 0
    STAGE_SELECT = 1
    IN_GAME = 2
    SUDDEN_DEATH = 3
    POSTGAME_SCORES = 4
    MAIN_MENU = 5
    SLIPPI_ONLINE_CSS = 6
    PRESS_START = 7
    UNKNOWN_MENU = 0xff

class GameMode(Enum):
    """Melee game mode kind.

    These values mirror doldecomp's ``GameModeKind`` enum and are the low byte
    of the Extract Menu Info scene halfword.
    """
    TITLE = 0x00
    MENU = 0x01
    VS = 0x02
    CLASSIC = 0x03
    ADVENTURE = 0x04
    ALLSTAR = 0x05
    DEBUG = 0x06
    DEBUG_SOUND_TEST = 0x07
    HANYU_CSS = 0x08
    HANYU_SSS = 0x09
    CAMERA_MODE = 0x0A
    TOY_GALLERY = 0x0B
    TOY_LOTTERY = 0x0C
    TOY_COLLECTION = 0x0D
    DEBUG_VS = 0x0E
    TARGET_TEST = 0x0F
    SUPER_SUDDEN_DEATH_VS = 0x10
    INVISIBLE_VS = 0x11
    SLOMO_VS = 0x12
    LIGHTNING_VS = 0x13
    CHALLENGER_APPROACH = 0x14
    CLASSIC_GAME_OVER = 0x15
    ADVENTURE_GAME_OVER = 0x16
    ALLSTAR_GAME_OVER = 0x17
    OPENING_MOVIE = 0x18
    DEBUG_CUTSCENE = 0x19
    DEBUG_GAME_OVER = 0x1A
    TOURNAMENT = 0x1B
    TRAINING = 0x1C
    TINY_VS = 0x1D
    GIANT_VS = 0x1E
    STAMINA_VS = 0x1F
    HOME_RUN_CONTEST = 0x20
    TEN_MAN_VS = 0x21
    HUNDRED_MAN_VS = 0x22
    THREE_MIN_VS = 0x23
    FIFTEEN_MIN_VS = 0x24
    ENDLESS_VS = 0x25
    CRUEL_VS = 0x26
    PROGRESSIVE_SCAN = 0x27
    BOOT = 0x28
    MEMCARD = 0x29
    FIXED_CAMERA_VS = 0x2A
    EVENT = 0x2B
    SINGLE_BUTTON_VS = 0x2C
    COUNT = 0x2D
    UNKNOWN_GAME_MODE = 0xFF

class GameScene(Enum):
    """Melee game scene kind from doldecomp's ``GameSceneKind`` enum."""
    TITLE = 0x00
    MENU = 0x01
    VS = 0x02
    SUDDEN_DEATH = 0x03
    TRAINING_MODE = 0x04
    RESULTS = 0x05
    UNUSED_0X6 = 0x06
    DEBUG_MENU = 0x07
    CSS = 0x08
    SSS = 0x09
    UNUSED_0XA = 0x0A
    TOY_GALLERY = 0x0B
    TOY_LOTTERY = 0x0C
    TOY_COLLECTION = 0x0D
    INTRO_NORMAL = 0x0E
    REGEND_TOYFALL = 0x0F
    REGEND_CONGRATS = 0x10
    CUTSCENE_LUIGI = 0x11
    CUTSCENE_BRINSTAR = 0x12
    CUTSCENE_EXPLOSION = 0x13
    CUTSCENE_THREE_KIRBYS = 0x14
    CUTSCENE_GIANT_KIRBY = 0x15
    CUTSCENE_STARFOX = 0x16
    CUTSCENE_FZERO = 0x17
    CUTSCENE_METAL = 0x18
    CUTSCENE_BOWSER_TOY = 0x19
    CUTSCENE_GIGA_TRANSFORM = 0x1A
    CUTSCENE_GIGA_DEFEATED = 0x1B
    MOVIE_OPENING = 0x1C
    MOVIE_END = 0x1D
    MOVIE_HOWTO = 0x1E
    MOVIE_OMAKE15 = 0x1F
    INTRO_EASY = 0x20
    INTRO_ALLSTAR = 0x21
    GAMEOVER = 0x22
    COMING_SOON = 0x23
    TOURNAMENT_SETUP = 0x24
    TOURNAMENT_BRACKET = 0x25
    TOURNAMENT_ALT = 0x26
    PRIZE_INTERFACE = 0x27
    PROGRESSIVE_SCAN = 0x28
    APPROACH = 0x29
    MEMCARD = 0x2A
    STAFFROLL = 0x2B
    CAMERA_VS = 0x2C
    COUNT = 0x2D
    UNKNOWN_GAME_SCENE = 0xFF

class MatchOutcome(Enum):
    """Melee match outcome kind from doldecomp's ``MatchOutcome`` enum."""
    NONE = 0x00
    TIMEOUT = 0x01
    ELIMINATION = 0x02
    UNKNOWN_0X3 = 0x03
    UNKNOWN_0X4 = 0x04
    UNKNOWN_0X5 = 0x05
    UNKNOWN_0X6 = 0x06
    LRASTART = 0x07
    RETRY = 0x08
    UNKNOWN_0X9 = 0x09
    UNKNOWN_MATCH_OUTCOME = 0xFF

class SubMenu(Enum):
    """Sub-menu of a primary menu"""
    MAIN_MENU_SUBMENU = 0
    ONEP_MODE_SUBMENU = 1
    VS_MODE_SUBMENU = 2
    TROPHIES_SUBMENU = 3
    OPTION_SUBMENU = 4
    DATA_SUBMENU = 5
    REGULAR_MATCH_SUBMENU = 6
    EVENT_MATCH_SUBMENU = 7
    ONLINE_PLAY_SUBMENU = 8
    STADIUM_SUBMENU = 9
    SPECIAL_MELEE_SUBMENU = 12
    CUSTOM_RULES_SUBMENU = 13
    NAME_ENTRY_SUBMENU = 18
    RUMBLE_SUBMENU = 19
    SOUND_SUBMENU = 20
    SCREEN_DISPLAY_SUBMENU = 21
    LANGUAGE_SELECT_SUBMENU = 23
    ERASE_DATA_SUBMENU = 24
    MULTIMAN_MELEE_SUBMENU = 33
    ONLINE_CSS = 0xfe
    UNKNOWN_SUBMENU = 0xff

class ControllerStatus(Enum):
    """One of three states a controller can be in during character select """
    CONTROLLER_HUMAN = 0
    CONTROLLER_CPU = 1
    CONTROLLER_UNPLUGGED = 3

class ControllerType(Enum):
    """Types a controller can be in the Dolphin config

    Named pipe input is considered 'standard' input by Dolphin.
    """
    STANDARD = "6"
    GCN_ADAPTER = "12"
    UNPLUGGED = "0"

class AttackState(Enum):
    """The phases an attack can be in """
    WINDUP = 0
    ATTACKING = 1
    COOLDOWN = 2
    NOT_ATTACKING = 3

class Character(Enum):
    """A Melee character ID.

    Note:
        Numeric values are 'internal' IDs."""
    MARIO = 0x00
    FOX = 0x01
    CPTFALCON = 0x02
    DK = 0x03
    KIRBY = 0x04
    BOWSER = 0x05
    LINK = 0x06
    SHEIK = 0x07
    NESS = 0x08
    PEACH = 0x09
    POPO = 0x0a
    NANA = 0x0b
    PIKACHU = 0x0c
    SAMUS = 0x0d
    YOSHI = 0x0e
    JIGGLYPUFF = 0x0f
    MEWTWO = 0x10
    LUIGI = 0x11
    MARTH = 0x12
    ZELDA = 0x13
    YLINK = 0x14
    DOC = 0x15
    FALCO = 0x16
    PICHU = 0x17
    GAMEANDWATCH = 0x18
    GANONDORF = 0x19
    ROY = 0x1a
    WIREFRAME_MALE = 0x1d
    WIREFRAME_FEMALE = 0x1e
    GIGA_BOWSER = 0x1f
    SANDBAG = 0x20
    UNKNOWN_CHARACTER = 0xff

def to_internal(char_id):
    """Converts a character select-screen ID to an 'internal ID' enum

    Mostly used at the Character Select Screen
    """
    if char_id == 0x00:
        return Character.DOC
    if char_id == 0x01:
        return Character.MARIO
    if char_id == 0x02:
        return Character.LUIGI
    if char_id == 0x03:
        return Character.BOWSER
    if char_id == 0x04:
        return Character.PEACH
    if char_id == 0x05:
        return Character.YOSHI
    if char_id == 0x06:
        return Character.DK
    if char_id == 0x07:
        return Character.CPTFALCON
    if char_id == 0x08:
        return Character.GANONDORF
    if char_id == 0x09:
        return Character.FALCO
    if char_id == 0x0a:
        return Character.FOX
    if char_id == 0x0b:
        return Character.NESS
    if char_id == 0x0c:
        return Character.POPO
    if char_id == 0x0d:
        return Character.KIRBY
    if char_id == 0x0e:
        return Character.SAMUS
    if char_id == 0x0f:
        return Character.ZELDA
    if char_id == 0x10:
        return Character.LINK
    if char_id == 0x11:
        return Character.YLINK
    if char_id == 0x12:
        return Character.PICHU
    if char_id == 0x13:
        return Character.PIKACHU
    if char_id == 0x14:
        return Character.JIGGLYPUFF
    if char_id == 0x15:
        return Character.MEWTWO
    if char_id == 0x16:
        return Character.GAMEANDWATCH
    if char_id == 0x17:
        return Character.MARTH
    if char_id == 0x18:
        return Character.ROY
    return Character.UNKNOWN_CHARACTER

def from_internal(character):
    """Converts a character enum to an "external" ID.

    Mostly used at the Character Select Screen
    """
    if character == Character.DOC:
        return 0x00
    if character == Character.MARIO:
        return 0x01
    if character == Character.LUIGI:
        return 0x02
    if character == Character.BOWSER:
        return 0x03
    if character == Character.PEACH:
        return 0x04
    if character == Character.YOSHI:
        return 0x05
    if character == Character.DK:
        return 0x06
    if character == Character.CPTFALCON:
        return 0x07
    if character == Character.GANONDORF:
        return 0x08
    if character == Character.FALCO:
        return 0x09
    if character == Character.FOX:
        return 0x0A
    if character == Character.NESS:
        return 0x0B
    if character == Character.POPO:
        return 0x0C
    if character == Character.KIRBY:
        return 0x0D
    if character == Character.SAMUS:
        return 0x0E
    if character == Character.ZELDA:
        return 0x0F
    if character == Character.LINK:
        return 0x10
    if character == Character.YLINK:
        return 0x11
    if character == Character.PICHU:
        return 0x12
    if character == Character.PIKACHU:
        return 0x13
    if character == Character.JIGGLYPUFF:
        return 0x14
    if character == Character.MEWTWO:
        return 0x15
    if character == Character.GAMEANDWATCH:
        return 0x16
    if character == Character.MARTH:
        return 0x17
    if character == Character.ROY:
        return 0x18
    return 0xFF

class Button(Enum):
    """A single button on a GCN controller

    Note:
        String values represent the Dolphin input string for that button"""
    BUTTON_A = "A"
    BUTTON_B = "B"
    BUTTON_X = "X"
    BUTTON_Y = "Y"
    BUTTON_Z = "Z"
    BUTTON_L = "L"
    BUTTON_R = "R"
    BUTTON_START = "START"
    BUTTON_D_UP = "D_UP"
    BUTTON_D_DOWN = "D_DOWN"
    BUTTON_D_LEFT = "D_LEFT"
    BUTTON_D_RIGHT = "D_RIGHT"
    #Control sticks considered "buttons" here
    BUTTON_MAIN = "MAIN"
    BUTTON_C = "C"

class Action(Enum):
    """ The in-game action (or animation) a character can be in

    Note:
        Numeric values (mostly) represent their in-game values"""
    # --- Death / KO states ---
    DEAD_DOWN = 0x0
    """These are end-of-stock animations; the character is off-screen or being
removed from play. Bots never need to dispatch on these directly since
death is better detected via ``PlayerState.stock`` changes."""
    DEAD_LEFT = 0x1
    """Fell off the bottom blast zone."""
    DEAD_RIGHT = 0x2
    """Fell off the left blast zone."""
    DEAD_UP = 0x3
    """Fell off the right blast zone."""
    DEAD_FLY_STAR = 0x4
    """Hit upwards off the top blast zone (star KO)."""
    DEAD_FLY_STAR_ICE = 0x5
    """Star KO while encased in ice (Icies' freeze effect persists into death)."""
    DEAD_FLY = 0x6
    """Star KO fly-up animation (character is still on-screen moving upward but
past the blast zone; will fade out)."""
    DEAD_FLY_SPLATTER = 0x7
    """Hit into the screen-camera "splatter" KO (upwards, splat on camera)."""
    DEAD_FLY_SPLATTER_FLAT = 0x8
    """Splatter KO, flat variant (different camera angle pose)."""
    DEAD_FLY_SPLATTER_ICE = 0x9
    """Splatter KO while encased in ice."""
    DEAD_FLY_SPLATTER_FLAT_ICE = 0xa
    """Flat splatter KO while encased in ice."""
    NOTHING_STATE = 0xb
    """Inactive character: Sheik/Zelda off-screen counterpart, or Nana when Sopo
is the active climber. The character is present in memory but not rendered
and cannot be acted upon."""
    # --- Match entry (halo descent) ---
    ON_HALO_DESCENT = 0xc
    """Character descending onto the stage at match start; cannot act."""
    ON_HALO_WAIT = 0x0d
    """Character waiting on the halo platform before dropping to the stage."""
    # --- Grounded locomotion ---
    STANDING = 0x0e
    """Actionable grounded neutral state.for idle/neutral states;
the walking state / the running state for those families; all considered actionable
ground states (the actionable-ground set) suitable for starting ground
attacks / smashes / grabs."""
    WALK_SLOW = 0x0f
    """Idle neutral stance. Default grounded actionable state.
Slow walk speed tier (stick barely tilted)."""
    WALK_MIDDLE = 0x10
    """Medium walk speed tier."""
    WALK_FAST = 0x11
    """Fast walk speed tier (stick near full tilt but not dashing)."""
    TURNING = 0x12
    """Turning around on the ground (from walk/stand). Walking state."""
    TURNING_RUN = 0x13
    """Pivot during a run (the "run-brake -> turn" transition). Running state."""
    DASHING = 0x14
    """Initial dash startup (the foxtrot/dash-dance window). Running state.Required for the dash-attack input type."""
    RUNNING = 0x15
    """Sustained run after the dash transition completes. Running state."""
    RUN_DIRECT = 0x16
    """Mid-run continuation frame. Running state."""
    RUN_BRAKE = 0x17
    """Skid to stop after a run. Running state."""
    KNEE_BEND = 0x18
    """Pre-jump knee bend animation. Actionable grounded state.(actionable; can be
interrupted for smash attacks / grab).
pre-jump animation."""
    # --- Aerial locomotion ---
    JUMPING_FORWARD = 0x19
    """First jump, moving forward. Airborne state."""
    JUMPING_BACKWARD = 0x1A
    """First jump, moving backward."""
    JUMPING_ARIAL_FORWARD = 0x1b
    """Aerial (second) jump, moving forward."""
    JUMPING_ARIAL_BACKWARD = 0x1c
    """Aerial (second) jump, moving backward."""
    FALLING = 0x1D
    """Neutral air fall - the "wait" state of the air."""
    FALLING_FORWARD = 0x1e
    """Falling with forward DI.
falling with forward DI"""
    FALLING_BACKWARD = 0x1f
    """Falling with backward DI.
falling with backward DI"""
    FALLING_AERIAL = 0x20
    """Falling after double-jump (aerial fall)."""
    FALLING_AERIAL_FORWARD = 0x21
    """After double-jump, forward DI.
After double-jump forward DI"""
    FALLING_AERIAL_BACKWARD = 0x22
    """After double-jump, backward DI.
After double-jump backward DI"""
    DEAD_FALL = 0x23
    """Falling after anUp-B - the helpless "dead fall" state post-recovery.
Falling after up-b"""
    SPECIAL_FALL_FORWARD = 0x24
    """Special-fall forward (post-Up-B with forward momentum, e.g. Firefox)."""
    SPECIAL_FALL_BACK = 0x25
    """Special-fall backward."""
    TUMBLING = 0x26
    """Tumbling hitstun (spinning knockback). Slippi may keep stale
``hitstun_frames_left`` here; the real-hitstun check filters it. The tumble
animation itself continues after hitstun ends until the character
touches ground or cancels via jump/attack."""
    # --- Crouch ---
    CROUCH_START = 0x27
    """Transitioning stand -> crouch. Actionable grounded state.Going from stand to crouch"""
    CROUCHING = 0x28
    """Full crouch. Actionable grounded state."""
    CROUCH_END = 0x29
    """Standing up from crouch. Actionable grounded state.Standing up from crouch"""
    # --- Landings ---
    LANDING = 0x2a
    """Normal landing from a fall/jump. Can be cancelled; not stunned. Actionable grounded state.Can be canceled. Not stunned"""
    LANDING_SPECIAL = 0x2b
    """Special landing from wavedash / airdodge. Stunned for a few frames. Actionable grounded state.Landing special like from wavedash. Stunned."""
    # --- Ground attacks (all Classifies as the attacking state) ---
    NEUTRAL_ATTACK_1 = 0x2c
    """Jab 1 (first hit of the neutral combo)."""
    NEUTRAL_ATTACK_2 = 0x2d
    """Jab 2 (second hit)."""
    NEUTRAL_ATTACK_3 = 0x2e
    """Jab 3 (third hit / finisher)."""
    LOOPING_ATTACK_START = 0x2f
    """Rapid-jab startup (the "100" series - infinitely looping jab)."""
    LOOPING_ATTACK_MIDDLE = 0x30
    """Rapid-jab loop (held A)."""
    LOOPING_ATTACK_END = 0x31
    """Rapid-jab ending (release of A)."""
    DASH_ATTACK = 0x32
    """Dash attack (requires ``DASHING`` state)."""
    FTILT_HIGH = 0x33
    """Forward tilt, high angle."""
    FTILT_HIGH_MID = 0x34
    """Forward tilt, high-mid angle."""
    FTILT_MID = 0x35
    """Forward tilt, mid angle."""
    FTILT_LOW_MID = 0x36
    """Forward tilt, low-mid angle."""
    FTILT_LOW = 0x37
    """Forward tilt, low angle."""
    UPTILT = 0x38
    """Up tilt."""
    DOWNTILT = 0x39
    """Down tilt."""
    FSMASH_HIGH = 0x3a
    """Forward smash, high angle (smashes are holdable for charge)."""
    FSMASH_MID_HIGH = 0x3b
    """Forward smash, mid-high angle."""
    FSMASH_MID = 0x3c
    """Forward smash, mid angle."""
    FSMASH_MID_LOW = 0x3d
    """Forward smash, mid-low angle."""
    FSMASH_LOW = 0x3e
    """Forward smash, low angle."""
    UPSMASH = 0x3f
    """Up smash."""
    DOWNSMASH = 0x40
    """Down smash."""
    NAIR = 0x41
    """--- Aerials (Classifies as the attacking state; landing variants Actionable grounded state.per the false-hitstun-neutral set) ---
Neutral aerial."""
    FAIR = 0x42
    """Forward aerial."""
    BAIR = 0x43
    """Back aerial."""
    UAIR = 0x44
    """Up aerial."""
    DAIR = 0x45
    """Down aerial."""
    NAIR_LANDING = 0x46
    """NAIR landing lag (post-aerial IASA-locked frames)."""
    FAIR_LANDING = 0x47
    """FAIR landing lag."""
    BAIR_LANDING = 0x48
    """BAIR landing lag."""
    UAIR_LANDING = 0x49
    """UAIR landing lag."""
    DAIR_LANDING = 0x4a
    """DAIR landing lag."""
    # --- Damage animations (knockback states) ---
    DAMAGE_HIGH_1 = 0x4b
    """These are non-launching damage reactions while grounded or airborne.
the stale-hitstun filter treats them as actionable since some
combos allow interrupting them. the high-level status classifier classifies them as
hitstun only when ``hitstun_frames_left > 0`` is genuine.
Hit upward while grounded (high knockback slot 1)."""
    DAMAGE_HIGH_2 = 0x4c
    """Hit upward while grounded (slot 2)."""
    DAMAGE_HIGH_3 = 0x4d
    """Hit upward while grounded (slot 3)."""
    DAMAGE_NEUTRAL_1 = 0x4e
    """Hit neutrally (mid knockback), slot 1."""
    DAMAGE_NEUTRAL_2 = 0x4f
    """Hit neutrally, slot 2."""
    DAMAGE_NEUTRAL_3 = 0x50
    """Hit neutrally, slot 3."""
    DAMAGE_LOW_1 = 0x51
    """Hit low, slot 1."""
    DAMAGE_LOW_2 = 0x52
    """Hit low, slot 2."""
    DAMAGE_LOW_3 = 0x53
    """Hit low, slot 3."""
    DAMAGE_AIR_1 = 0x54
    """Hit while airborne, slot 1."""
    DAMAGE_AIR_2 = 0x55
    """Hit while airborne, slot 2."""
    DAMAGE_AIR_3 = 0x56
    """Hit while airborne, slot 3."""
    DAMAGE_FLY_HIGH = 0x57
    """Launched upward (high knockback fly). Distinct from DAMAGE_*: the
character is being carried by knockback (e.g. up smash kill). Bots use
this for juggle/launch detection (see mewthree.py / westballz.py)."""
    DAMAGE_FLY_NEUTRAL = 0x58
    """Launched neutrally (up/fly)."""
    DAMAGE_FLY_LOW = 0x59
    """Launched low (scooping knockback)."""
    DAMAGE_FLY_TOP = 0x5a
    """Launched straight up (e.g. rest death, Luigi up-B kill)."""
    DAMAGE_FLY_ROLL = 0x5b
    """Rolling knockback spin (rare ceiling/floor hit)."""
    # --- Item pickup/throw/swing (most Classifies as Attacking when swinging) ---
    ITEM_PICKUP_LIGHT = 0x5C
    """Light item pickup (A press while lightly tilting toward item)."""
    ITEM_PICKUP_HEAVY = 0x5D
    """Heavy item pickup (e.g. barrel/crate)."""
    ITEM_THROW_LIGHT_FORWARD = 0x5E
    """Throw light item forward."""
    ITEM_THROW_LIGHT_BACK = 0x5F
    """Throw light item back."""
    ITEM_THROW_LIGHT_HIGH = 0x60
    """Throw light item up."""
    ITEM_THROW_LIGHT_LOW = 0x61
    """Throw light item down."""
    ITEM_THROW_LIGHT_DASH = 0x62
    """Dash-throw light item (forward momentum throw)."""
    ITEM_THROW_LIGHT_DROP = 0x63
    """Drop light item (Z-drop, no momentum)."""
    ITEM_THROW_LIGHT_AIR_FORWARD = 0x64
    """Aerial drop light item forward."""
    ITEM_THROW_LIGHT_AIR_BACK = 0x65
    """Aerial drop light item back."""
    ITEM_THROW_LIGHT_AIR_HIGH = 0x66
    """Aerial drop light item up."""
    ITEM_THROW_LIGHT_AIR_LOW = 0x67
    """Aerial drop light item down."""
    ITEM_THROW_HEAVY_FORWARD = 0x68
    """Throw heavy item forward."""
    ITEM_THROW_HEAVY_BACK = 0x69
    """Throw heavy item back."""
    ITEM_THROW_HEAVY_HIGH = 0x6A
    """Throw heavy item up."""
    ITEM_THROW_HEAVY_LOW = 0x6B
    """Throw heavy item down."""
    ITEM_THROW_LIGHT_SMASH_FORWARD = 0x6C
    """Smash-throw light item forward (C-stick/smash input adds momentum)."""
    ITEM_THROW_LIGHT_SMASH_BACK = 0x6D
    """Smash-throw light item back."""
    ITEM_THROW_LIGHT_SMASH_UP = 0x6e
    """Smash-throw light item up."""
    ITEM_THROW_LIGHT_SMASH_DOWN = 0x6F
    """Smash-throw light item down."""
    ITEM_THROW_LIGHT_AIR_SMASH_FORWARD = 0x70
    """Aerial smash-throw light item forward."""
    ITEM_THROW_LIGHT_AIR_SMASH_BACK = 0x71
    """Aerial smash-throw light item back."""
    ITEM_THROW_LIGHT_AIR_SMASH_HIGH = 0x72
    """Aerial smash-throw light item up."""
    ITEM_THROW_LIGHT_AIR_SMASH_LOW = 0x73
    """Aerial smash-throw light item down."""
    ITEM_THROW_HEAVY_AIR_SMASH_FORWARD = 0x74
    """Aerial smash-throw heavy item forward."""
    ITEM_THROW_HEAVY_AIR_SMASH_BACK = 0x75
    """Aerial smash-throw heavy item back."""
    ITEM_THROW_HEAVY_AIR_SMASH_HIGH = 0x76
    """Aerial smash-throw heavy item up."""
    ITEM_THROW_HEAVY_AIR_SMASH_LOW = 0x77
    """Aerial smash-throw heavy item down."""
    # --- Item swing animations (4-frame swing sequence for each weapon) ---
    BEAM_SWORD_SWING_1 = 0x78
    """Beam Sword swing sequence (1 of 4)."""
    BEAM_SWORD_SWING_2 = 0x79
    """Beam Sword swing (2 of 4)."""
    BEAM_SWORD_SWING_3 = 0x7A
    """Beam Sword swing (3 of 4)."""
    BEAM_SWORD_SWING_4 = 0x7B
    """Beam Sword swing (4 of 4)."""
    BAT_SWING_1 = 0x7C
    """Home-Run Bat swing (1 of 4)."""
    BAT_SWING_2 = 0x7D
    """Bat swing (2 of 4)."""
    BAT_SWING_3 = 0x7E
    """Bat swing (3 of 4)."""
    BAT_SWING_4 = 0x7F
    """Bat swing (4 of 4)."""
    PARASOL_SWING_1 = 0x80
    """Parasol swing (1 of 4)."""
    PARASOL_SWING_2 = 0x81
    """Parasol swing (2 of 4)."""
    PARASOL_SWING_3 = 0x82
    """Parasol swing (3 of 4)."""
    PARASOL_SWING_4 = 0x83
    """Parasol swing (4 of 4)."""
    FAN_SWING_1 = 0x84
    """Fan swing (1 of 4)."""
    FAN_SWING_2 = 0x85
    """Fan swing (2 of 4)."""
    FAN_SWING_3 = 0x86
    """Fan swing (3 of 4)."""
    FAN_SWING_4 = 0x87
    """Fan swing (4 of 4)."""
    STAR_ROD_SWING_1 = 0x88
    """Star Rod swing (1 of 4). Star Rod also fires a projectile on smash input."""
    STAR_ROD_SWING_2 = 0x89
    """Star Rod swing (2 of 4)."""
    STAR_ROD_SWING_3 = 0x8a
    """Star Rod swing (3 of 4)."""
    STAR_ROD_SWING_4 = 0x8b
    """Star Rod swing (4 of 4)."""
    LIP_STICK_SWING_1 = 0x8c
    """Lip's Stick (Pansy) swing (1 of 4). Plants a damage-over-time flower."""
    LIP_STICK_SWING_2 = 0x8d
    """Lip's Stick swing (2 of 4)."""
    LIP_STICK_SWING_3 = 0x8e
    """Lip's Stick swing (3 of 4)."""
    LIP_STICK_SWING_4 = 0x8f
    """Lip's Stick swing (4 of 4)."""
    # --- Parasol item states ---
    ITEM_PARASOL_OPEN = 0x90
    """Open parasol (after grabbing it)."""
    ITEM_PARASOL_FALL = 0x91
    """Float down with parasol open."""
    ITEM_PARASOL_FALL_SPECIAL = 0x92
    """Special parasol fall (e.g. after special move landing)."""
    ITEM_PARASOL_DAMAGE_FALL = 0x93
    """Parasol close during damage fall."""
    # --- Ray gun / Fire flower / Scope (item shooting) ---
    GUN_SHOOT = 0x94
    """Ray gun shoot (grounded, with ammo)."""
    GUN_SHOOT_AIR = 0x95
    """Ray gun shoot (airborne)."""
    GUN_SHOOT_EMPTY = 0x96
    """Ray gun shoot (grounded, empty - click animation)."""
    GUN_SHOOT_AIR_EMPTY = 0x97
    """Ray gun shoot (airborne, empty)."""
    FIRE_FLOWER_SHOOT = 0x98
    """Fire Flower shoot (grounded)."""
    FIRE_FLOWER_SHOOT_AIR = 0x99
    """Fire Flower shoot (airborne)."""
    ITEM_SCREW = 0x9a
    """Screw Attack item usage (grounded). Launches the user upward."""
    ITEM_SCREW_AIR = 0x9b
    """Screw Attack item usage (airborne)."""
    DAMAGE_SCREW = 0x9c
    """Damage while in Screw Attack animation (grounded)."""
    DAMAGE_SCREW_AIR = 0x9d
    """Damage while in Screw Attack animation (airborne)."""
    ITEM_SCOPE_START = 0x9e
    """Super Scope (item) - start firing (grounded)."""
    ITEM_SCOPE_RAPID = 0x9f
    """Super Scope - rapid fire mode (grounded)."""
    ITEM_SCOPE_FIRE = 0xa0
    """Super Scope - single shot (grounded)."""
    ITEM_SCOPE_END = 0xa1
    """Super Scope - end firing (grounded)."""
    ITEM_SCOPE_AIR_START = 0xa2
    """Super Scope - start firing (airborne)."""
    ITEM_SCOPE_AIR_RAPID = 0xa3
    """Super Scope - rapid fire (airborne)."""
    ITEM_SCOPE_AIR_FIRE = 0xa4
    """Super Scope - single shot (airborne)."""
    ITEM_SCOPE_AIR_END = 0xa5
    """Super Scope - end firing (airborne)."""
    ITEM_SCOPE_START_EMPTY = 0xa6
    """Super Scope (empty) - start (grounded)."""
    ITEM_SCOPE_RAPID_EMPTY = 0xa7
    """Super Scope (empty) - rapid (grounded)."""
    ITEM_SCOPE_FIRE_EMPTY = 0xa8
    """Super Scope (empty) - shot (grounded)."""
    ITEM_SCOPE_END_EMPTY = 0xa9
    """Super Scope (empty) - end (grounded)."""
    ITEM_SCOPE_AIR_START_EMPTY = 0xaa
    """Super Scope (empty) - start (airborne)."""
    ITEM_SCOPE_AIR_RAPID_EMPTY = 0xab
    """Super Scope (empty) - rapid (airborne)."""
    ITEM_SCOPE_AIR_FIRE_EMPTY = 0xac
    """Super Scope (empty) - shot (airborne)."""
    ITEM_SCOPE_AIR_END_EMPTY = 0xad
    """Super Scope (empty) - end (airborne)."""
    # --- Lifting (heavy items) ---
    LIFT_WAIT = 0xae
    """Idle while holding a heavy item (crate/barrel)."""
    LIFT_WALK_1 = 0xaf
    """Walking slowly with heavy item (tier 1)."""
    LIFT_WALK_2 = 0xb0
    """Walking with heavy item (tier 2)."""
    LIFT_TURN = 0xb1
    """Turning while holding a heavy item."""
    # --- Shield states (Classifies as the shielding state) ---
    SHIELD_START = 0xb2
    """Shield-startup press (L/R trigger)."""
    SHIELD = 0xb3
    """Sustained shield hold."""
    SHIELD_RELEASE = 0xb4
    """Shield release (let go of trigger)."""
    SHIELD_STUN = 0xb5
    """Shield stun (after blocking a hit; locked out of all but small shield
actions)."""
    SHIELD_REFLECT = 0xb6
    """Powershield reflect (frame-perfect shield that reflects projectiles)."""
    # --- Knockdown / getup family ---
    TECH_MISS_UP = 0xb7
    """These animations cover the "missed tech -> lying -> getup choice" flow
that the knockdown state covers. Slippi often leaves a stale
``hitstun_frames_left=1`` through these; the
the stale-hitstun filter filter treats ``hitstun_frames_left <= 1``
as actionable here (so Not in hitstun.) but real hitstun
(>1) still Classifies as hitstun.
Missed-tech bounce, lying face-up. The character failed to tech a
knockdown and is bouncing on the ground. Classifies as the knockdown state."""
    LYING_GROUND_UP = 0xb8
    """Lying on the ground, face-up, idle (waiting for getup input).
Classifies as the knockdown state."""
    LYING_GROUND_UP_HIT = 0xb9
    """Lying on the ground, face-up, being hit (additional damage while down).
Classifies as the knockdown state."""
    GROUND_GETUP = 0xba
    """Standing-up getup from the face-up lying state.
Committed getup animation (invulnerable). (committed getup animation)."""
    GROUND_ATTACK_UP = 0xbb
    """Getup attack from face-up (A press while lying down; has a hitbox).
Committed getup animation (invulnerable)."""
    GROUND_ROLL_FORWARD_UP = 0xbc
    """Getup roll forward from face-up. Committed getup animation (invulnerable)."""
    GROUND_ROLL_BACKWARD_UP = 0xbd
    """Getup roll backward from face-up. Committed getup animation (invulnerable)."""
    GROUND_SPOT_UP = 0xbe
    """Spot getup (in-place) from face-up. Committed getup animation (invulnerable)."""
    TECH_MISS_DOWN = 0xbf
    """Missed-tech bounce, lying face-down. Classifies as the knockdown state."""
    LYING_GROUND_DOWN = 0xc0
    """Lying on the ground, face-down, idle. Classifies as the knockdown state."""
    DAMAGE_GROUND = 0xc1
    """Taking damage while lying face-down. Classifies as the knockdown state."""
    NEUTRAL_GETUP = 0xc2
    """Standing-up getup from face-down. Committed getup animation (invulnerable)."""
    GETUP_ATTACK = 0xc3
    """Getup attack from face-down (A press while lying). Committed getup animation (invulnerable). Has a hitbox."""
    GROUND_ROLL_FORWARD_DOWN = 0xc4
    """Getup roll forward from face-down. Committed getup animation (invulnerable)."""
    GROUND_ROLL_BACKWARD_DOWN = 0xc5
    """Getup roll backward from face-down. Committed getup animation (invulnerable)."""
    GROUND_ROLL_SPOT_DOWN = 0xc6
    """Spot getup (in-place) from face-down. Committed getup animation (invulnerable)."""
    # --- Successful techs (Classifies as the dodging state) ---
    NEUTRAL_TECH = 0xc7
    """In-place neutral tech (L/R press within 20 frames of knockdown).
libmelee ``FrameData.is_roll`` includes this; the dodging state."""
    FORWARD_TECH = 0xc8
    """Tech-roll forward. Classifies as the dodging state."""
    BACKWARD_TECH = 0xc9
    """Tech-roll backward. Classifies as the dodging state."""
    WALL_TECH = 0xca
    """Wall tech (L/R press against a wall while in knockback)."""
    WALL_TECH_JUMP = 0xcb
    """Wall tech jump (tech-jump off a wall; can be canceled into aerial)."""
    CEILING_TECH = 0xcc
    """Ceiling tech (tech against the underside of a platform)."""
    # --- Shield break (Classifies as shield-break stun) ---
    SHIELD_BREAK_FLY = 0xcd
    """Initial upward launch when shield breaks (the dazed stun-locked fly)."""
    SHIELD_BREAK_FALL = 0xce
    """Falling after shield-break fly."""
    SHIELD_BREAK_DOWN_U = 0xcf
    """Lying face-up after shield break."""
    SHIELD_BREAK_DOWN_D = 0xd0
    """Lying face-down after shield break."""
    SHIELD_BREAK_STAND_U = 0xd1
    """Standing up from shield break (face-up)."""
    SHIELD_BREAK_STAND_D = 0xd2
    """Standing up from shield break (face-down)."""
    SHIELD_BREAK_TEETER = 0xd3
    """Teetering on the edge while dazed from shield break."""
    # --- Grab (attacker side; Classifies as actively holding a grab) ---
    GRAB = 0xd4
    """Initial grab reach (Z or L+A). Has a brief grab hitbox. Classifies as
actively holding a grab and also as Attacking by the action-set check."""
    GRAB_PULLING = 0xd5
    """Pulling the grabbed opponent inward (post-grab success)."""
    GRAB_RUNNING = 0xd6
    """Running grab (dash-grab, Z while dashing). Extended reach; longer
recovery if whiffed."""
    GRAB_RUNNING_PULLING = 0xd7
    """Pulling an opponent in from a running grab."""
    GRAB_WAIT = 0xd8
    """Grab hold (sustained grab on a victim). Pummels / throw-choices begin
here; throw inputs (FTHROW/BTHROW/UTHROW/DTHROW) are gated on this
state by the throw-input action set."""
    GRAB_PUMMEL = 0xd9
    """Pummel (A press while holding a grab). Throw inputs still valid."""
    GRAB_BREAK = 0xda
    """Grab break (victim's mash-out succeeded; both characters released)."""
    THROW_FORWARD = 0xdb
    """Forward throw animation (attacker side)."""
    THROW_BACK = 0xdc
    """Back throw animation (attacker side)."""
    THROW_UP = 0xdd
    """Up throw animation (attacker side)."""
    THROW_DOWN = 0xde
    """Down throw animation (attacker side)."""
    GRAB_PULLING_HIGH = 0xdf
    """High-variant grab pulling (different animation, same semantics)."""
    GRABBED_WAIT_HIGH = 0xe0
    """Grabbed victim waiting (high variant, e.g. heavy characters).
Classifies as being held in a grab."""
    PUMMELED_HIGH = 0xe1
    """Pummeled (high variant) - victim being pummeled by attacker."""
    GRAB_PULL = 0xe2
    """Being pulled inward from a grab (victim side)."""
    GRABBED = 0xe3
    """Grabbed (victim side, base state). Classifies as being held in a grab."""
    GRAB_PUMMELED = 0xe4
    """Being pummeled (victim side)."""
    GRAB_ESCAPE = 0xe5
    """Mash-out; victim escaping the grab."""
    GRAB_JUMP = 0xe6
    """GRAB_JUMP (DK cargo-carry jump; attacker side). Classifies as
cargo-carrying the opponent (cargo carry state) per
the cargo-carry action set."""
    GRAB_NECK = 0xe7
    """GRAB_NECK (grabbed victim variant - back-grab). Classifies as
being held in a grab."""
    GRAB_FOOT = 0xe8
    """GRAB_FOOT (grabbed victim variant - low grab). Classifies as
being held in a grab."""
    # --- Dodges (Classifies as the dodging state) ---
    ROLL_FORWARD = 0xe9
    """Forward roll (grounded dodge with directional momentum). libmelee
``FrameData.is_roll`` includes this."""
    ROLL_BACKWARD = 0xea
    """Backward roll (grounded)."""
    SPOTDODGE = 0xEB
    """Spot dodge (grounded, in-place dodge)."""
    AIRDODGE = 0xEC
    """Air dodge (L/R in air, then free-fall)."""
    REBOUND_STOP = 0xED
    """Hit-rebound stop (freeze frame after landing a hit with knockback).
Attacker-side pause."""
    REBOUND = 0xEE
    """Hit-rebound continuation (a few frames of attacker momentum shudder)."""
    # --- Thrown by enemy (victim side; Classifies as being held in a grab) ---
    THROWN_FORWARD = 0xEF
    """Being thrown forward (in the throw animation, attacker-controlled)."""
    THROWN_BACK = 0xF0
    """Being thrown back."""
    THROWN_UP = 0xF1
    """Being thrown up."""
    THROWN_DOWN = 0xF2
    """Being thrown down (slam)."""
    THROWN_DOWN_2 = 0xf3
    """Alternate down-throw variant (some characters)."""
    # --- Platform / edge ---
    PLATFORM_DROP = 0xf4
    """Dropping through a platform (down-input on a pass-through platform)."""
    EDGE_TEETERING_START = 0xF5
    """Starting the edge-teeter animation (about to fall off the stage edge)."""
    EDGE_TEETERING = 0xF6
    """Sustained edge teeter (balancing at the stage edge)."""
    BOUNCE_WALL = 0xf7
    """Wall bounce (hit into a wall and rebounding)."""
    BOUNCE_CEILING = 0xf8
    """Ceiling bounce."""
    BUMP_WALL = 0xf9
    """Wall bump (hit into a wall without bounce)."""
    BUMP_CIELING = 0xfa
    """Ceiling bump."""
    SLIDING_OFF_EDGE = 0xfb
    """Sliding off an edge after being hit (knockback carries off-stage)."""
    EDGE_CATCHING = 0xFC
    """Initial ledge catch (the frame the character grabs the edge; brief
intangibility). Classifies as hanging from a ledge."""
    EDGE_HANGING = 0xFD
    """Sustained ledge hang. Classifies as hanging from a ledge."""
    EDGE_GETUP_SLOW = 0xFE
    """Ledge getup (neutral climb on), slow variant (>= 100% damage).
libmelee's FrameData.is_roll -> the dodging state."""
    EDGE_GETUP_QUICK = 0xFF
    """Ledge getup (neutral), quick variant (< 100% damage)."""
    EDGE_ATTACK_SLOW = 0x100
    """Ledge attack (A press on ledge), slow variant (>= 100%). Classifies as
the attacking state (has hitbox)."""
    EDGE_ATTACK_QUICK = 0x101
    """Ledge attack, quick (< 100%)."""
    EDGE_ROLL_SLOW = 0x102
    """Ledge roll getup (roll onto stage), slow (>= 100%). Classifies as
the dodging state (intangible during roll)."""
    EDGE_ROLL_QUICK = 0x103
    """Ledge roll, quick (< 100%)."""
    EDGE_JUMP_1_SLOW = 0x104
    """Ledge jump variant 1, slow."""
    EDGE_JUMP_2_SLOW = 0x105
    """Ledge jump variant 2, slow."""
    EDGE_JUMP_1_QUICK = 0x106
    """Ledge jump variant 1, quick."""
    EDGE_JUMP_2_QUICK = 0x107
    """Ledge jump variant 2, quick."""
    # --- Taunts (Classifies as the taunting state) ---
    TAUNT_RIGHT = 0x108
    """Right taunt (D-pad right)."""
    TAUNT_LEFT = 0x109
    """Left taunt (D-pad left)."""
    # --- Captures (DK cargo, Yoshi, Kirby, etc.) ---
    SHOULDERED_WAIT = 0x10A
    """Being shouldered (DK cargo-walk carry, victim). Victim side."""
    SHOULDERED_WALK_SLOW = 0x10B
    """DK cargo walk slow with victim."""
    SHOULDERED_WALK_MIDDLE = 0x10C
    """DK cargo walk medium."""
    SHOULDERED_WALK_FAST = 0x10D
    """DK cargo walk fast."""
    SHOULDERED_TURN = 0x10E
    """DK cargo turn."""
    THROWN_FF = 0x10F
    """Thrown forward by DK cargo (victim side)."""
    THROWN_FB = 0x110
    """Thrown back by DK cargo."""
    THROWN_F_HIGH = 0x111
    """Thrown by DK cargo, high trajectory."""
    THROWN_F_LOW = 0x112
    """Thrown by DK cargo, low trajectory."""
    CAPTURE_CAPTAIN = 0x113
    """Caught by Captain Falcon's grab animation (Up-B / specific grab)."""
    CAPTURE_YOSHI = 0x114
    """Caught by Yoshi (tongue swallow)."""
    YOSHI_EGG = 0x115
    """Inside a Yoshi egg (after Yoshi swallow)."""
    CAPTURE_KOOPA = 0x116
    """Caught by Bowser (Koopa) grab."""
    CAPTURE_DAMAGE_KOOPA = 0x117
    """Taking damage while in Bowser's grab."""
    CAPTURE_WAIT_KOOPA = 0x118
    """Waiting in Bowser's grab hold."""
    THROWN_KOOPA_F = 0x119
    """Thrown forward by Bowser."""
    THROWN_KOOPA_B = 0x11A
    """Thrown back by Bowser."""
    CAPTURE_KOOPA_AIR = 0x11B
    """Caught by Bowser in the air (aerial Koopa grab)."""
    CAPTURE_DAMAGE_KOOPA_AIR = 0x11C
    """Taking damage while in Bowser's aerial grab."""
    CAPTURE_WAIT_KOOPA_AIR = 0x11D
    """Waiting in Bowser's aerial grab hold."""
    THROWN_KOOPA_AIR_F = 0x11E
    """Thrown forward by Bowser aerial grab."""
    THROWN_KOOPA_AIR_B = 0x11F
    """Thrown back by Bowser aerial grab."""
    CAPTURE_KIRBY = 0x120
    """Caught by Kirby (inhale)."""
    CAPTURE_WAIT_KIRBY = 0x121
    """Waiting in Kirby's mouth."""
    THROWN_KIRBY_STAR = 0x122
    """Star-throw by Kirby (spit out as a star projectile)."""
    THROWN_COPY_STAR = 0x123
    """Copy-ability star (Kirby steals the opponent's neutral-B)."""
    THROWN_KIRBY = 0x124
    """Plain throw from Kirby (without swallow)."""
    BARREL_WAIT = 0x125
    """Inside a barrel (barrel cannon, item)."""
    # --- Special capture / status effects ---
    BURY = 0x126
    """Buried (e.g. DK's headbutt down-B). Victim is stuck in the ground."""
    BURY_WAIT = 0x127
    """Waiting while buried."""
    BURY_JUMP = 0x128
    """Jump-out from being buried."""
    DAMAGE_SONG = 0x129
    """Damage from Jigglypuff's Sing (sleep). Victim put to sleep."""
    DAMAGE_SONG_WAIT = 0x12A
    """Sleeping animation (after Sing)."""
    DAMAGE_SONG_RV = 0x12B
    """Waking up from sleep (the "RV" recover animation)."""
    DAMAGE_BIND = 0x12C
    """Bound (Mewtwo's Disable - victim stunned briefly)."""
    CAPTURE_MEWTWO = 0x12D
    """Caught by Mewtwo (Disable / grab)."""
    CAPTURE_MEWTWO_AIR = 0x12E
    """Caught by Mewtwo in air."""
    THROWN_MEWTWO = 0x12F
    """Thrown by Mewtwo."""
    THROWN_MEWTWO_AIR = 0x130
    """Thrown by Mewtwo (airborne variant)."""
    # --- Items / stage hazards (cinematic states) ---
    WARP_STAR_JUMP = 0x131
    """Warping in via Warp Star item."""
    WARP_STAP_FALL = 0x132
    """Falling from Warp Star apex."""
    # --- Hammer item ---
    HAMMER_WAIT = 0x133
    """Idle while holding the Hammer item."""
    HAMMER_WALK = 0x134
    """Walking with Hammer."""
    HAMMER_TURN = 0x135
    """Turning with Hammer."""
    HAMMER_KNEE_BEND = 0x136
    """Jump startup with Hammer."""
    HAMMER_FALL = 0x137
    """Falling with Hammer."""
    HAMMER_JUMP = 0x138
    """Jumping with Hammer."""
    HAMMER_LANDING = 0x139
    """Landing with Hammer."""
    # --- Mushroom (Super/Poison) size change states ---
    KINOKO_GIANT_START = 0x13A
    """Super mushroom grow start (grounded)."""
    KINOKO_GIANT_START_AIR = 0x13B
    """Super mushroom grow start (airborne)."""
    KINOKO_GIANT_END = 0x13C
    """Super mushroom shrink back to normal size."""
    KINOKO_GIANT_END_AIR = 0x13D
    """Super mushroom shrink (airborne)."""
    KINOKO_SMALL_START = 0x13E
    """Poison mushroom shrink start (grounded)."""
    KINOKO_SMALL_START_AIR = 0x13F
    """Poison mushroom shrink start (airborne)."""
    KINOKO_SMALL_END = 0x140
    """Poison mushroom grow back to normal."""
    KINOKO_SMALL_END_AIR = 0x141
    """Poison mushroom grow back (airborne)."""
    # --- Match start entry ---
    ENTRY = 0x142
    """Character spawn entry (can't act)."""
    ENTRY_START = 0x143
    """Entry start animation."""
    ENTRY_END = 0x144
    """Entry end (drops into STANDING)."""
    # --- Ice / freeze ---
    DAMAGE_ICE = 0x145
    """Frozen (encased in ice). Victim can't act until thaw."""
    DAMAGE_ICE_JUMP = 0x146
    """Jumping out of ice (rare; character thaws while airborne)."""
    # --- Master Hand / Crazy Hand captures (single-player mode) ---
    CAPTURE_MASTERHAND = 0x147
    """Caught by Master Hand."""
    CAPTURE_DAMAGE_MASTERHAND = 0x148
    """Taking damage while in Master Hand's grab."""
    CAPTURE_WAIT_MASTERHAND = 0x149
    """Waiting in Master Hand grab."""
    THROWN_MASTERHAND = 0x14A
    """Thrown by Master Hand."""
    CAPTURE_KIRBY_YOSHI = 0x14B
    """Caught by Kirby or Yoshi (joint variant)."""
    KIRBY_YOSHI_EGG = 0x14C
    """Inside a Kirby-Yoshi egg."""
    CAPTURE_LEA_DEAD = 0x14D
    """Capture variant "LEA_DEAD" - undocumented in the SSBM action state table;
appears in capture sequences during single-player."""
    CAPTURE_LIKE_LIKE = 0x14E
    """Capture variant "LIKE_LIKE" - associated with stage-hazard captures
(Like Like enemy in Zelda-themed stages). Semantics unclear."""
    DOWN_REFLECT = 0x14F
    """Reflect while lying down (e.g. powershield from a knockdown state)."""
    CAPTURE_CRAZYHAND = 0x150
    """Crazy Hand captures (mirror of Master Hand set)."""
    CAPTURE_DAMAGE_CRAZYHAND = 0x151
    CAPTURE_WAIT_CRAZYHAND = 0x152
    THROWN_CRAZY_HAND = 0x153
    BARREL_CANNON_WAIT = 0x154
    """Inside a Barrel Cannon (stage hazard)."""
    # --- Neutral-B (chargeable characters via the chargeable-neutral-B character set) ---
    LASER_GUN_PULL = 0x155
    """Fox/Falco laser gun pull-out (the visible "draw the blaster" frames)."""
    NEUTRAL_B_CHARGING = 0x156
    """Neutral-B charging (held). For chargeable chars (Samus, Mewtwo, etc.)
this is the sustained charge; non-chargeable chars transition straight to
``NEUTRAL_B_ATTACKING``."""
    NEUTRAL_B_ATTACKING = 0x157
    """Neutral-B attacking (grounded, fire frames)."""
    NEUTRAL_B_FULL_CHARGE = 0x158
    """Fully-charged neutral-B hold (chargeable chars max out)."""
    WAIT_ITEM = 0x159
    """WAIT_ITEM (some neutral-B variants use an intermediate "wait for item"
state; largely undocumented in the SSBM action state table)."""
    NEUTRAL_B_CHARGING_AIR = 0x15A
    """Air variants of the neutral-B set above."""
    NEUTRAL_B_ATTACKING_AIR = 0x15B
    NEUTRAL_B_FULL_CHARGE_AIR = 0x15C
    DOWN_B_GROUND_START = 0x168
    """--- Down-B (Fox/Falco shine; Classifies as the attacking state; on the
the bot package action-set the attack-type mapping) ---
Down-B startup on the ground (Fox/Falco shine deploy). Alias of
``SWORD_DANCE_2_MID_AIR`` (Python Enum dereferences value 0x168 to the
first-defined member - ``DOWN_B_GROUND_START`` here)."""
    DOWN_B_GROUND = 0x169
    """Down-B active on the ground (charge loop / sustained). Alias of
    ``SWORD_DANCE_3_HIGH_AIR``."""
    REFLECTOR_HIT_GROUND = 0x16A
    """Fox/Falco grounded Reflector animation after reflecting a projectile."""
    REFLECTOR_END_GROUND = 0x16B
    """Fox/Falco grounded Reflector release animation."""
    SHINE_TURN = 0x16c
    """Shine turn (Fox/Falco shine while turning - the body reorients). Alias
    of ``SWORD_DANCE_4_HIGH_AIR``."""
    DOWN_B_STUN = 0x16d
    """Legacy name for Fox/Falco's aerial Reflector startup state."""
    DOWN_B_AIR_START = 0x16D
    """Alias of ``DOWN_B_STUN`` retained as the accurate Fox/Falco state name."""
    DOWN_B_AIR = 0x16e
    """Down-B active in the air. Alias of ``SWORD_DANCE_4_LOW_AIR``."""
    # --- Up-B (recovery special) ---
    UP_B_GROUND = 0x16f
    """Character-relative action ID used by grounded Up-B animations."""
    REFLECTOR_HIT_AIR = 0x16F
    """Alias of ``UP_B_GROUND`` for Fox/Falco's aerial projectile-reflect animation."""
    SHINE_RELEASE_AIR = 0x170
    """Shine release in the air (Fox/Falco air-shine out frames). Canonical for
value 0x170 (UP_B_AIR is an alias of this member)."""
    REFLECTOR_END_AIR = 0x170
    """Alias of ``SHINE_RELEASE_AIR`` for Fox/Falco's aerial Reflector release."""
    SWORD_DANCE_1 = 0x15d
    """--- Side-B (Marth/Roy dancing blade; shared with Zelda/Sheik side-B
and the character-specific side-B variants listed below) ---
Marth/Roy sword-dance first hit (Side-B startup). Several characters
reuse these raw IDs (see the side-B action set)."""
    SWORD_DANCE_2_HIGH = 0x15e
    """Sword dance second hit, high. Canonical for 0x15e;
``FOX_ILLUSION_START`` is an alias."""
    SWORD_DANCE_2_MID = 0x15f
    """Sword dance second hit, mid. Canonical for 0x15f;
``FOX_ILLUSION`` is an alias."""
    SWORD_DANCE_3_HIGH = 0x160
    """Sword dance third hit, high. Canonical for 0x160;
``FOX_ILLUSION_SHORTENED`` is an alias."""
    SWORD_DANCE_3_MID = 0x161
    """Sword dance third hit, mid. Canonical for 0x161;
``FIREFOX_WAIT_GROUND`` is an alias."""
    SWORD_DANCE_3_LOW = 0x162
    """Sword dance third hit, low. Canonical for 0x162;
``FIREFOX_WAIT_AIR`` is an alias."""
    SWORD_DANCE_4_HIGH = 0x163
    """Sword dance fourth hit, high. Canonical for 0x163;
``FIREFOX_GROUND`` is an alias."""
    SWORD_DANCE_4_MID = 0x164
    """Sword dance fourth hit, mid. Canonical for 0x164;
``FIREFOX_AIR`` is an alias."""
    SWORD_DANCE_4_LOW = 0x165
    """Sword dance fourth hit, low."""
    # --- Side-B aerial variants (some collide with DOWN_B_* values above) ---
    SWORD_DANCE_1_AIR = 0x166
    """Side-B airborne startup."""
    SWORD_DANCE_2_HIGH_AIR = 0x167
    """Side-B airborne second hit, high. Canonical for 0x167 (no alias)."""
    SWORD_DANCE_2_MID_AIR = 0x168
    """Alias of ``DOWN_B_GROUND_START`` (0x168). See that member for use."""
    SWORD_DANCE_3_HIGH_AIR = 0x169
    """Alias of ``DOWN_B_GROUND`` (0x169). See that member for use."""
    SWORD_DANCE_3_MID_AIR = 0x16a
    """Alias of ``REFLECTOR_HIT_GROUND`` (0x16a)."""
    SWORD_DANCE_3_LOW_AIR = 0x16b
    """Alias of ``REFLECTOR_END_GROUND`` (0x16b)."""
    SWORD_DANCE_4_HIGH_AIR = 0x16c
    """Alias of ``SHINE_TURN`` (0x16c). See that member for use."""
    SWORD_DANCE_4_MID_AIR = 0x16d
    """Alias of ``DOWN_B_STUN`` / ``DOWN_B_AIR_START`` (0x16d)."""
    SWORD_DANCE_4_LOW_AIR = 0x16e
    """Alias of ``DOWN_B_AIR`` (0x16e). See that member for use."""
    # --- Fox/Falco-specific side-B / up-B variants (aliases of SWORD_DANCE) ---
    FOX_ILLUSION_START = 0x15e
    """Alias of ``SWORD_DANCE_2_HIGH`` (0x15e). Fox Illusion startup (the
dash-charge before the dash). Fox/Falco side-B."""
    FOX_ILLUSION = 0x15f
    """Alias of ``SWORD_DANCE_2_MID`` (0x15f). Fox Illusion active dash."""
    FOX_ILLUSION_SHORTENED = 0x160
    """Alias of ``SWORD_DANCE_3_HIGH`` (0x160). Fox Illusion shortened
(length-cancelled / "shorten" variant)."""
    FIREFOX_WAIT_GROUND = 0x161
    """Alias of ``SWORD_DANCE_3_MID`` (0x161). Firefox (Fox/Falco Up-B) wait
on the ground (the "charging" pause before the boost)."""
    FIREFOX_WAIT_AIR = 0x162
    """Alias of ``SWORD_DANCE_3_LOW`` (0x162). Firefox wait in the air."""
    FIREFOX_GROUND = 0x163
    """Alias of ``SWORD_DANCE_4_HIGH`` (0x163). Firefox boost on the ground."""
    FIREFOX_AIR = 0x164
    """Alias of ``SWORD_DANCE_4_MID`` (0x164). Firefox boost in the air."""
    UP_B_AIR = 0x170
    """Alias of ``SHINE_RELEASE_AIR`` (0x170). The upswing of the UP-B
(Marth's dolphin slash and the like). Despite the name, libmelee
resolves 0x170 to ``SHINE_RELEASE_AIR`` since the latter is defined
first. Treat as Marth-specific Up-B aerial upswing.
The upswing of the UP-B. (At least for marth)"""
    # --- Marth counter (Classifies as the attacking state via the attack action set) ---
    MARTH_COUNTER = 0x171
    """Marth's Down-B counter (the counter window + retaliation). Also used by
Roy."""
    PARASOL_FALLING = 0x172
    """Peach's parasol (Up-B) - falling with the parasol open post-jump.
Different from the item parasol (``ITEM_PARASOL_*``)."""
    MARTH_COUNTER_FALLING = 0x173
    """Marth's counter-falling variant - counter triggers while airborne."""
    # --- Ness shield (PSI Magnet / Yo-yo defense variants) ---
    NESS_SHEILD_START = 0x174
    """Ness shield-startup (his shield is his bat/yoyo animation). Canonical for
0x174 (``NESS_SHEILD`` is an alias of this member). Note the typo
("SHEILD") in libmelee / SSBM naming - preserved for compatibility."""
    NESS_SHEILD = 0x174
    """Alias of ``NESS_SHEILD_START``. The sustained Ness-shield hold."""
    NESS_SHEILD_AIR = 0x175
    """Ness shield-air (his midair "shield" - PSI Magnet active)."""
    ZITABATA = 0x176
    """ZITABATA (translates roughly to "shield-bounce" - Ness's down-B
PSI Magnet yoyo strike). Classifies as the attacking state via frame data."""
    NESS_SHEILD_AIR_END = 0x177
    """Ness shield-air end (PSI Magnet release)."""
    # --- Bowser / Koopa throw variants (continuations) ---
    THROWN_KOOPA_END_F = 0x178
    """Thrown by Bowser - end of forward throw (the release frame)."""
    THROWN_KOOPA_END_B = 0x179
    """Thrown by Bowser - end of back throw."""
    CAPTURE_KOOPA_AIR_HIT = 0x17A
    """Hit while in Bowser's aerial grab."""
    THROWN_KOOPA_AIR_END_F = 0x17B
    """Thrown by Bowser aerial grab - end forward."""
    THROWN_KOOPA_AIR_END_B = 0x17C
    """Thrown by Bowser aerial grab - end back."""
    THROWN_KIRBY_DRINK_S_SHOT = 0x17D
    """Kirby's drink-shot star projectile (swallowed enemy spit as star)."""
    THROWN_KIRBY_SPIT_S_SHOT = 0x17E
    """Kirby's regular spit star projectile (without swallow)."""
    # --- Donkey Kong side-B (Hand Slap; Classifies as the attacking state) ---
    DK_GROUND_POUND_START = 0x17F
    """DK's Ground Pound (Hand Slap) - startup (the leap before the slam)."""
    DK_GROUND_POUND = 0x180
    """DK's Ground Pound - active slam (the shockwave hitbox)."""
    DK_GROUND_POUND_END = 0x181
    """DK's Ground Pound - end (recovery to standing)."""
    # --- Kirby Blade (Kirby copy of Marth/Roy sword dance) ---
    KIRBY_BLADE_GROUND = 0x184
    """Kirby blade grounded (from Marth/Roy copy ability)."""
    KIRBY_BLADE_UP = 0x185
    """Kirby blade upswing."""
    KIRBY_BLADE_APEX = 0x186
    """Kirby blade apex (mid-swing)."""
    KIRBY_BLADE_DOWN = 0x187
    """Kirby blade downswing."""
    # --- Kirby Stone (down-B) ---
    KIRBY_STONE_FORMING_GROUND = 0x189
    """Stone forming (grounded). Brief startup before invulnerable stone form."""
    KIRBY_STONE_RESTING = 0x18A
    """Stone resting (invulnerable stationary stone on ground)."""
    KIRBY_STONE_RELEASE = 0x18B
    """Stone release (returning to normal Kirby)."""
    KIRBY_STONE_FORMING_AIR = 0x18C
    """Stone forming in the air (preparing to drop)."""
    KIRBY_STONE_FALLING = 0x18D
    """Stone falling (the plunging drop). Canonical for 0x18d;
``KIRBY_STONE_UNFORMING`` is an alias."""
    KIRBY_STONE_UNFORMING = 0x18D
    """Alias of ``KIRBY_STONE_FALLING`` (0x18d). The un-forming animation
returning to normal - shares the same raw action ID as the falling
state in SSBM (the falling frame IS the un-forming frame internally)."""

    # Complete list at: https://docs.google.com/spreadsheets/d/1JX2w-r2fuvWuNgGb6D3Cs4wHQKLFegZe2jhbBuIhCG8/edit?gid=20#gid=20
class ProjectileType(Enum):
    """Primary type of prejectile or item """
    BOB_OMB = 0x06 # Bob-omb (BombHei)
    MR_SATURN = 0x07 # Mr. Saturn (Dosei)
    BEAMSWORD = 0x0C # Beam Sword
    MARIO_FIREBALL = 0x30 # Mario's fire
    DR_MARIO_CAPSULE = 0x31 # Dr.Mario's Capsule
    KIRBY_CUTTER = 0x32 # Kirby's Cutter beam
    KIRBY_HAMMER = 0x33 # Kirby's Hammer
    FOX_LASER = 0x36 # Fox's Laser
    FALCO_LASER = 0x37 # Falco's Laser
    FOX_SHADOW = 0x38 # Fox's shadow
    FALCO_SHADOW = 0x39 # Falco's shadow
    LINK_BOMB = 0x3A # Link's bomb
    YLINK_BOMB = 0x3B # Young Link's bomb
    LINK_BOOMERANG = 0x3C # Link's boomerang
    YLINK_BOOMERANG = 0x3D # Young Link's boomerang
    LINK_HOOKSHOT = 0x3E # Link's Hookshot
    YLINK_HOOKSHOT = 0x3F # Young Link's Hookshot
    ARROW = 0x40 # Arrow
    FIRE_ARROW = 0x41 # Fire Arrow
    PK_FIRE = 0x42 # PK Fire
    PK_FLASH_1 = 0x43 # PK Flash
    PK_FLASH_2 = 0x44 # PK Flash
    PK_THUNDER_HEAD = 0x45 # PK Thunder (Primary)
    PK_THUNDER_TAIL_1 = 0x46 # PK Thunder
    PK_THUNDER_TAIL_2 = 0x47 # PK Thunder
    PK_THUNDER_TAIL_3 = 0x48 # PK Thunder
    PK_THUNDER_TAIL_4 = 0x49 # PK Thunder
    FOX_BLASTER = 0x4A # Fox's Blaster
    FALCO_BLASTER = 0x4B # Falco's Blaster
    LINK_ARROW = 0x4C # Link's Arrow
    YLINK_ARROW = 0x4D # Young Link's arrow
    PK_FLASH_EXPLOSION = 0x4E # PK Flash (explosion)
    NEEDLE_THROWN = 0x4F # Needle(thrown)
    NEEDLE = 0x50 # Needle
    PIKACHU_THUNDER = 0x51 # Pikachu's Thunder
    PICHU_THUNDER = 0x52 # Pichu's Thunder
    MARIO_CAPE = 0x53 # Mario's cape
    DR_MARIO_CAPE = 0x54 # Dr.Mario's cape
    SHEIK_SMOKE = 0x55 # Smoke (Sheik)
    YOSHI_EGG_THROWN = 0x56 # Yoshi's egg(thrown)
    YOSHI_TONGUE = 0x57 # Yoshi's Tongue??
    YOSHI_STAR = 0x58 # Yoshi's Star
    PIKACHU_THUNDERJOLT_1 = 0x59 # Pikachu's thunder (B)
    PIKACHU_THUNDERJOLT_2 = 0x5A # Pikachu's thunder (B)
    PICHU_THUNDERJOLT_1 = 0x5B # Pichu's thunder (B)
    PICHU_THUNDERJOLT_2 = 0x5C # Pichu's thunder (B)
    SAMUS_BOMB = 0x5D # Samus's bomb
    SAMUS_CHARGE_BEAM = 0x5E # Samus's chargeshot
    SAMUS_MISSLE = 0x5F # Missile
    SAMUS_GRAPPLE_BEAM = 0x60 # Grapple beam
    SHEIK_CHAIN = 0x61 # Sheik's chain
    PEACH_BOMBER = 0x62 # Peach's Side-B
    TURNIP = 0x63 # Turnip
    BOWSER_FLAME = 0x64 # Bowser's flame
    NESS_BATT = 0x65 # Ness's bat
    NESS_YOYO = 0x66 # Yoyo
    PEACH_PARASOL = 0x67 # Peach's parasol
    PEACH_TOAD = 0x68 # Peach's Toad
    LUIGI_FIRE = 0x69 # Luigi's fire
    ICE_BLOCK = 0x6A # Ice(Iceclimbers)
    IC_BLIZZARD = 0x6B # Blizzard
    ZELDA_FIRE = 0x6C # Zelda's fire
    ZELDA_FIRE_EXPLOSION = 0x6D # Zelda's fire (explosion)
    MEWTO_DISABLE = 0x6E # Mewtwo's down-B
    TOAD_SPORE = 0x6F # Toad's spore
    SHADOWBALL = 0x70 # Mewtwo's Shadowball
    IC_UP_B = 0x71 # Iceclimbers' Up  #B
    PESTICIDE = 0x72 # Pesticide
    MANHOLE = 0x73 # Manhole
    GW_FIRE = 0x74 # Fire(G&W)
    PARACHUTE = 0x75 # Parachute
    TURTLE = 0x76 # Turtle
    SPERKY = 0x77 # Sperky
    JUDGE = 0x78 # Judge
    SAUSAGE = 0x7A # Sausage
    YLINK_MILK = 0x7B # Milk (Young Link)
    FIREFIGHTER = 0x7C # Firefighter(G&W)
    KIRBY_MARIO_FIRE = 0x82 # Kirby copy Mario's Fire (B)
    KIRBY_DR_MARIO_FIRE = 0x83 # Kirby copy Dr. Mario's Capsule (B)
    KIRBY_LUIGI_FIRE = 0x84 # Kirby copy Luigi's Fire (B)
    KIRBY_IC_BLOCK = 0x85 # Kirby copy IceClimber's IceCube (B)
    KIRBY_TOAD_SPORE = 0x87 # Kirby copy Toad's Spore (B)
    KIRBY_FOX_LASER = 0x88 # Kirby copy Fox's Laser (B)
    KIRBY_FALCO_LASER = 0x89 # Kirby copy Falco's Laser (B)
    KIRBY_LINK_ARROW = 0x8C # Kirby copy Link's Arrow (B)
    KIRBY_YLINK_ARROW = 0x8D # Kirby copy Young Link's Arrow (B)
    KIRBY_LINK_ARROW_2 = 0x8E # Kirby copy Link's Arrow (B)
    KIRBY_YLINK_ARROW_2 = 0x8F # Kirby copy Young Link's Arrow (B)
    KIRBY_SHADOWBALL = 0x90 # Kirby copy Mewtwo's Shadowball (B)
    KIRBY_PK_FLASH = 0x91 # Kirby copy PK Flash (B)
    KIRBY_PK_FLASH_EXPLOSION = 0x92 # Kirby copy PK Flash Explosion (B)
    KIRBY_PIKACHU_THUNDERJOLT_1 = 0x93 # Kirby copy Pikachu's Thunder (B)
    KIRBY_PIKACHU_THUNDERJOLT_2 = 0x94 # Kirby copy Pikachu's Thunder (B)
    KIRBY_PICHU_THUNDERJOLT_1 = 0x95 # Kirby copy Pichu's Thunder (B)
    KIRBY_PICHU_THUNDERJOLT_2 = 0x96 # Kirby copy Pichu's Thunder (B)
    KIRBY_SAMUS_CHARGESHOT = 0x97 # Kirby copy Samus' Chargeshot (B)
    KIRBY_SHEIK_NEEDLE_THROWN = 0x98 # Kirby copy Sheik's Needle (thrown) (B)
    KIRBY_SHEIK_NEEDLE_GROUND = 0x99 # Kirby copy Sheik's Needle (ground) (B)
    KIRBY_BOWSER_FLAME = 0x9A # Kirby copy Bowser's Flame (B)
    KIRBY_SAUSAGE = 0x9B # Kirby copy Mr. Game & Watch's Sausage (B)
    KIRBY_YOSHI_TONGUE = 0x9D # Yoshi's Tongue?? (B)
    SHY_GUY = 0xD2
    UNKNOWN_PROJECTILE = 0xff
