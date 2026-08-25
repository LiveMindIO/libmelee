"""Read-only character state classification for Crowd Control bots.

A :class:`CharacterState` wraps one controller port's per-frame
:class:`melee.gamestate.PlayerState` snapshot and answers high-level combat
questions ("am I in hitstun?", "can a grab start here?", "what motion state am
I in?") without touching controller inputs. :class:`SimpleControls` builds on a
:class:`CharacterState` instance for those state checks and layers attack input
application on top.

Bots that only need to *read* state (and never apply inputs) can construct a
:class:`CharacterState` directly. Bots that drive a controller should reach the
same answers through ``simple_controls.character_state`` rather than calling the
deprecated thin delegates on :class:`SimpleControls` (``simple_controls.can_attack``,
``simple_controls.get_state``, etc.) — those wrappers exist only for backward
compatibility and will be removed.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import Final, Literal, TypeAlias, overload

from typing_extensions import deprecated

from melee.bot.framedata_query import _SPECIAL_SLOT_ACTION_IDS
from melee.enums import Action, Character
from melee.framedata import FrameData
from melee.gamestate import (
    GameState,
    StageLedge,
    StageLedgeSide,
    StagePoint,
    StageSegment,
    StageSurface,
    StageSurfaceKind,
    UnknownAnimation,
)
from melee.gamestate import PlayerState as LibPlayerState

# Ground locomotion states where Slippi may falsely report hitstun_frames_left=1.
_FALSE_HITSTUN_NEUTRAL_ACTIONS: Final = frozenset(
    {
        Action.STANDING,
        Action.WALK_SLOW,
        Action.WALK_MIDDLE,
        Action.WALK_FAST,
        Action.TURNING,
        Action.TURNING_RUN,
        Action.DASHING,
        Action.RUNNING,
        Action.RUN_DIRECT,
        Action.RUN_BRAKE,
        Action.KNEE_BEND,
        Action.CROUCH_START,
        Action.CROUCHING,
        Action.CROUCH_END,
        Action.LANDING,
        Action.LANDING_SPECIAL,
        Action.NAIR_LANDING,
        Action.FAIR_LANDING,
        Action.BAIR_LANDING,
        Action.UAIR_LANDING,
        Action.DAIR_LANDING,
    }
)
_ACTIONABLE_AIR: Final = frozenset(
    {
        Action.JUMPING_FORWARD,
        Action.JUMPING_BACKWARD,
        Action.JUMPING_ARIAL_FORWARD,
        Action.JUMPING_ARIAL_BACKWARD,
        Action.FALLING,
        Action.FALLING_FORWARD,
        Action.FALLING_BACKWARD,
        Action.FALLING_AERIAL,
        Action.FALLING_AERIAL_FORWARD,
        Action.FALLING_AERIAL_BACKWARD,
        Action.PLATFORM_DROP,
    }
)
_JIGGLYPUFF_AERIAL_JUMP_IDS: Final = frozenset(range(341, 346))
_PEACH_FLOAT_MOVEMENT_IDS: Final = frozenset({341, 342, 343})
# DESNOTE(jbarber, 2026-08-22): DamageFall (TUMBLING) omits EscapeAir but checks
# aerial specials, tether Z-air, aerial attacks, and aerial jump after hitstun.
# Keep it attackable without adding it to the normal-air dodge set above.
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_DamageFall.c#L119-L139
_ATTACKABLE_AIR: Final = _ACTIONABLE_AIR | {Action.TUMBLING}
# Characters whose neutral-B enters NEUTRAL_B_CHARGING instead of firing immediately.
_NEUTRAL_B_CHARGEABLE: Final = frozenset(
    {
        Character.BOWSER,
        Character.DOC,
        Character.FALCO,
        Character.FOX,
        Character.GAMEANDWATCH,
        Character.KIRBY,
        Character.LINK,
        Character.LUIGI,
        Character.MARIO,
        Character.MEWTWO,
        Character.NANA,
        Character.NESS,
        Character.PEACH,
        Character.PICHU,
        Character.PIKACHU,
        Character.POPO,
        Character.ROY,
        Character.SAMUS,
        Character.SHEIK,
        Character.YLINK,
        Character.YOSHI,
        Character.ZELDA,
    }
)
_GRABBER_ACTIONS: Final = frozenset(
    {
        Action.GRAB,
        Action.GRAB_PULLING,
        Action.GRAB_RUNNING,
        Action.GRAB_RUNNING_PULLING,
        Action.GRAB_WAIT,
        Action.GRAB_PUMMEL,
        Action.GRAB_BREAK,
        Action.GRAB_PULLING_HIGH,
        Action.GRAB_JUMP,
        Action.THROW_FORWARD,
        Action.THROW_BACK,
        Action.THROW_UP,
        Action.THROW_DOWN,
    }
)
_GRABBED_VICTIM_ACTIONS: Final = frozenset(
    {
        Action.GRABBED,
        Action.GRABBED_WAIT_HIGH,
        Action.GRAB_PULL,
        Action.GRAB_PUMMELED,
        Action.PUMMELED_HIGH,
        Action.GRAB_ESCAPE,
        Action.GRAB_NECK,
        Action.GRAB_FOOT,
    }
)
# DESNOTE(jbarber, 2026-08-22): Throw direction checks run from CatchWait IASA.
# CatchAttack (pummel) has no IASA callback, so a throw cannot begin until the
# state returns to CatchWait.
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_CatchWait.c
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_CatchAttack.c
_GRAB_THROW_INPUT_ACTIONS: Final = frozenset(
    {
        Action.GRAB_WAIT,
    }
)
_LEDGE_HANG_ACTIONS: Final = frozenset(
    {
        Action.EDGE_HANGING,
    }
)
_LEDGE_GETUP_ACTIONS: Final = frozenset(
    {
        Action.EDGE_GETUP_SLOW,
        Action.EDGE_GETUP_QUICK,
        Action.EDGE_ATTACK_SLOW,
        Action.EDGE_ATTACK_QUICK,
        Action.EDGE_ROLL_SLOW,
        Action.EDGE_ROLL_QUICK,
        Action.EDGE_JUMP_1_SLOW,
        Action.EDGE_JUMP_2_SLOW,
        Action.EDGE_JUMP_1_QUICK,
        Action.EDGE_JUMP_2_QUICK,
    }
)
# Actions where the character is on the ground after a knockdown. The broad
# family covers everything classified as :attr:`CharacterStatus.Downed` by
# :func:`get_state`: lying idle, taking damage while down, missed-tech
# bounce, and committed passive getup options (stand/spot/attack). The
# subset :data:`_VULNERABLE_KNOCKDOWN_ACTIONS` excludes the getup options —
# those are still classified as ``Downed`` (the player is locked into the
# animation and cannot attack), but :func:`is_downed` excludes them because
# the character is no longer "lying on the ground vulnerable": they have
# committed to standing up / attacking, with body-property invulnerability
# frames during the getup animation.
#
# Active roll getup options (``GROUND_ROLL_*_UP`` / ``GROUND_ROLL_*_DOWN`` /
# ``GROUND_ROLL_SPOT_DOWN``) are intentionally EXCLUDED from the broad family
# entirely — once the player commits to a roll from knockdown the character
# has full invulnerability and is effectively dodging, not lying down.
# Those actions live in :data:`_GETUP_ROLL_ACTIONS` and classify as
# :attr:`CharacterStatus.Dodging`.
_KNOCKDOWN_ACTIONS: Final = frozenset(
    {
        # Lying idle / being hit while down:
        Action.LYING_GROUND_UP,
        Action.LYING_GROUND_UP_HIT,
        Action.LYING_GROUND_DOWN,
        Action.DAMAGE_GROUND,
        # Missed-tech bounce (failed to tech a knockdown):
        Action.TECH_MISS_UP,
        Action.TECH_MISS_DOWN,
        # Committed passive getup options (player chose to stand / spot / attack
        # without rolling):
        Action.GROUND_GETUP,
        Action.NEUTRAL_GETUP,
        Action.GETUP_ATTACK,
        Action.GROUND_ATTACK_UP,
        Action.GROUND_SPOT_UP,
    }
)
# Active dodge getup options: the player committed to a roll or spot-dodge
# from knockdown. These provide invulnerability and behave like normal rolls
# / spot dodges (``CharacterStatus.Dodging``), NOT knockdown. 4 of the 5
# are also in libmelee ``FrameData.is_roll``; ``GROUND_ROLL_SPOT_DOWN``
# (knockdown spot-dodge) is libmelee-omitted so we maintain our own bucket.
_GETUP_ROLL_ACTIONS: Final = frozenset(
    {
        Action.GROUND_ROLL_FORWARD_UP,
        Action.GROUND_ROLL_BACKWARD_UP,
        Action.GROUND_ROLL_FORWARD_DOWN,
        Action.GROUND_ROLL_BACKWARD_DOWN,
        Action.GROUND_ROLL_SPOT_DOWN,
    }
)
# In-progress passive getup animations: the player committed to stand up /
# spot / attack (no roll). Animation plays out with body-property
# invulnerability and the character will stand at the end. Useful for bots
# that want to "skip" the wait (release inputs) until standing again. Roll
# getups are intentionally excluded (see :data:`_GETUP_ROLL_ACTIONS`).
_GETTING_UP_ACTIONS: Final = frozenset(
    {
        Action.GROUND_GETUP,
        Action.NEUTRAL_GETUP,
        Action.GETUP_ATTACK,
        Action.GROUND_ATTACK_UP,
        Action.GROUND_SPOT_UP,
    }
)
# Truly vulnerable knockdown actions: lying idle / taking damage while down /
# missed-tech bounce. The character is on the ground without an active
# getup animation, fully vulnerable. This is what :func:`is_downed` checks —
# computed as :data:`_KNOCKDOWN_ACTIONS` minus :data:`_GETTING_UP_ACTIONS`.
_VULNERABLE_KNOCKDOWN_ACTIONS: Final = _KNOCKDOWN_ACTIONS - _GETTING_UP_ACTIONS
_TAUNT_ACTIONS: Final = frozenset(
    {
        Action.TAUNT_LEFT,
        Action.TAUNT_RIGHT,
    }
)
_CHARACTER_TAUNT_ACTIONS: Final[dict[Character, frozenset[Action]]] = {
    Character.DOC: frozenset({Action(341), Action(342)}),
    Character.YLINK: frozenset({Action(342), Action(343)}),
    Character.FOX: frozenset(Action(action_id) for action_id in range(370, 376)),
    Character.FALCO: frozenset(Action(action_id) for action_id in range(370, 376)),
}
_SHIELD_BREAK_ACTIONS: Final = frozenset(
    {
        Action.SHIELD_BREAK_FLY,
        Action.SHIELD_BREAK_FALL,
        Action.SHIELD_BREAK_DOWN_U,
        Action.SHIELD_BREAK_DOWN_D,
        Action.SHIELD_BREAK_STAND_U,
        Action.SHIELD_BREAK_STAND_D,
        Action.SHIELD_BREAK_TEETER,
    }
)
_WALK_ACTIONS: Final = frozenset(
    {
        Action.WALK_SLOW,
        Action.WALK_MIDDLE,
        Action.WALK_FAST,
        Action.TURNING,
    }
)
_RUN_ACTIONS: Final = frozenset(
    {
        Action.DASHING,
        Action.RUNNING,
        Action.RUN_DIRECT,
        Action.RUN_BRAKE,
        Action.TURNING_RUN,
    }
)
_CARRYING_ENEMY_ACTIONS: Final = frozenset({Action.GRAB_JUMP})
_GRABBING_ENEMY_ACTIONS: Final = frozenset(
    {
        Action.GRAB,
        Action.GRAB_PULLING,
        Action.GRAB_RUNNING,
        Action.GRAB_RUNNING_PULLING,
        Action.GRAB_WAIT,
        Action.GRAB_PUMMEL,
        Action.GRAB_BREAK,
        Action.GRAB_PULLING_HIGH,
        Action.THROW_FORWARD,
        Action.THROW_BACK,
        Action.THROW_UP,
        Action.THROW_DOWN,
    }
)
# Characters whose aerial Z input is a tether/ranged grab (Z Air).
_Z_AIR_CHARACTERS: Final = frozenset(
    {
        Character.SAMUS,
        Character.LINK,
        Character.YLINK,
    }
)


class StickReferenceAxis(Enum):
    """Conventional absolute axis from which a signed angle is measured.

    Right is 0 degrees and positive rotation is counter-clockwise.
    """

    UP = 90.0
    RIGHT = 0.0
    DOWN = 270.0
    LEFT = 180.0


HorizontalStickReferenceAxis: TypeAlias = Literal[
    StickReferenceAxis.LEFT,
    StickReferenceAxis.RIGHT,
]

GroundDodgeStickReferenceAxis: TypeAlias = Literal[
    StickReferenceAxis.LEFT,
    StickReferenceAxis.RIGHT,
    StickReferenceAxis.DOWN,
]


class AttackType(Enum):
    """Logical attack input a bot can request from :class:`SimpleControls`.

    Values map to Melee stick and button combinations (main stick + ``A`` for
    ground tilts and smashes, C-stick for directional aerials, ``A`` for neutral
    aerial, main stick + ``B`` for specials, ``Z`` for grab). Directional attacks
    use the controlled port's ``PlayerState.facing`` to pick left vs right unless
    an explicit left/right variant is requested.

    Ground-only: ``JAB``, ``FTILT``, ``LTILT``, ``RTILT``, ``UTILT``, ``DTILT``,
    ``FSMASH``, ``LSMASH``, ``RSMASH``, ``USMASH``, ``DSMASH``, ``GRAB``.

    ``DASH_ATTACK`` requires ``Action.DASHING``, ``Action.RUNNING``, or
    ``Action.RUN_DIRECT``. The bot must enter dash/run with raw movement inputs
    before calling it; SimpleControls does not move on the bot's behalf.

    Air-only: ``NAIR``, ``FAIR``, ``BAIR``, ``UAIR``, ``DAIR``.

    Specials (ground or air): ``NEUTRAL_B``, ``SIDE_B``, ``LSPECIAL``, ``RSPECIAL``,
    ``UP_B``, ``DOWN_B``. ``LEFT_B`` and ``RIGHT_B`` are deprecated aliases for
    ``LSPECIAL`` and ``RSPECIAL``.

    Grab throws (requires ``GRAB_WAIT``): ``FTHROW``, ``BTHROW``,
    ``UTHROW``, ``DTHROW``. Throws are stick-only; ``A`` pummels during a grab.
    ``Z_AIR`` is air-only for tether-grab characters (Samus, Link, Young Link).

    Directional throws use ``PlayerState.facing`` for forward/back; up/down are
    absolute. DK forward-grab behavior (cargo carry) is not implemented by the
    standard :class:`SimpleControls` path and must be handled by bot logic for now.
    """

    JAB = auto()
    FTILT = auto()
    LTILT = auto()
    RTILT = auto()
    UTILT = auto()
    DTILT = auto()
    FSMASH = auto()
    LSMASH = auto()
    RSMASH = auto()
    USMASH = auto()
    DSMASH = auto()
    DASH_ATTACK = auto()
    NAIR = auto()
    FAIR = auto()
    BAIR = auto()
    UAIR = auto()
    DAIR = auto()
    NEUTRAL_B = auto()
    SIDE_B = auto()
    LSPECIAL = auto()
    RSPECIAL = auto()
    LEFT_B = LSPECIAL
    RIGHT_B = RSPECIAL
    UP_B = auto()
    DOWN_B = auto()
    GRAB = auto()
    Z_AIR = auto()
    FTHROW = auto()
    BTHROW = auto()
    UTHROW = auto()
    DTHROW = auto()


class CharacterStatus(Enum):
    """High-level motion/combat state for a libmelee port snapshot.

    Distinct from :class:`melee.gamestate.PlayerState` (the per-frame struct).
    Prefer :func:`get_state` / :meth:`CharacterState.get_state` over reading raw
    ``Action`` IDs in bot logic.
    """

    GrabbingLedge = auto()
    """Hanging from a ledge (``EDGE_HANGING``). The character is attached to a
    stage edge and can choose a getup option (neutral/roll/attack/jump/let-go).
    Blocks attack, grab, and shield input until a ledge getup begins."""

    Attacking = auto()
    """An attack with active or upcoming hitboxes, caught via libmelee
    ``FrameData.is_attack`` or membership in ``_ALL_ATTACK_ACTIONS``. Includes
    ground normals/tilts/smashes, aerials, specials, and getup attacks.
    Blocks new attack/grab input until the move ends."""

    Taunting = auto()
    """A taunt animation (``TAUNT_LEFT`` / ``TAUNT_RIGHT``). Blocks all combat
    input for the duration. Cosmetic only; never deals damage."""

    Hitstun = auto()
    """Real hitstun: ``hitstun_frames_left > 0`` AND the action is not one
    where Slippi leaves a stale ``hitstun_frames_left=1`` false-positive
    (lying, locomotion, attack, shield, roll, tech, grab, etc. — see
    :func:`_stale_hitstun_is_actionable`). The character cannot act.
    Distinct from :attr:`HitLag` (frozen on hit connect) and from
    :attr:`Downed` (lying on the ground after knockdown but able to choose a
    getup). When ``hitstun_frames_left > 1`` on a knockdown action, the state
    is reported as :attr:`Hitstun` (real knockdown hitstun) rather than
    :attr:`Downed`."""

    HitLag = auto()
    """Hitlag: ``hitlag_left > 0``. Both attacker and defender freeze briefly
    when a hit connects. The character is locked out of all input until hitlag
    clears; treated as a subset of hitstun by :func:`in_hitstun`."""

    Tumbling = auto()
    """Airborne knockback tumble (``TUMBLING``) after reported hitstun has
    cleared. Permits aerial attacks, specials, tether Z-air, and aerial jump,
    but not air dodge."""

    Shielding = auto()
    """Holding shield (``SHIELD`` / ``SHIELD_START`` / ``SHIELD_REFLECT`` /
    ``SHIELD_STUN`` / ``SHIELD_RELEASE``). Blocks attack/grab input but allows
    grab out of shield (``can_attack(AttackType.GRAB)`` permits this as a
    special case)."""

    ShieldBroken = auto()
    """Shield-break animation suite (``SHIELD_BREAK_FLY`` through
    ``SHIELD_BREAK_STAND_D`` and ``SHIELD_BREAK_TEETER``). The character is
    stun-locked for an extended duration; blocks all input."""

    Dodging = auto()
    """A roll, spot-dodge, or ``AIRDODGE``. Ground dodges and successful techs
    are caught through libmelee ``FrameData.is_roll``; air dodge is classified
    explicitly. The character is intangible or has body-property invulnerability
    for part of the animation. Also includes the 5 active roll-getup options from
    knockdown (``GROUND_ROLL_*_UP`` / ``GROUND_ROLL_*_DOWN`` /
    ``GROUND_ROLL_SPOT_DOWN`` — see :data:`_GETUP_ROLL_ACTIONS`): once the
    player commits to a roll from knockdown they are dodging, not lying
    down."""

    GrabbedByEnemy = auto()
    """Held in an opponent's grab (``GRABBED`` / ``GRABBED_WAIT_HIGH`` /
    ``GRAB_PULL`` / ``GRAB_PUMMELED`` / ``PUMMELED_HIGH`` / ``GRAB_ESCAPE`` /
    ``GRAB_NECK`` / ``GRAB_FOOT``). Blocks all input except mash-out."""

    GrabbingEnemy = auto()
    """Grabbing or throwing an opponent (``GRAB`` / ``GRAB_PULLING`` /
    ``GRAB_RUNNING`` / ``GRAB_RUNNING_PULLING`` / ``GRAB_WAIT`` /
    ``GRAB_PUMMEL`` / ``GRAB_BREAK`` / ``GRAB_PULLING_HIGH`` /
    ``THROW_FORWARD`` / ``THROW_BACK`` / ``THROW_UP`` / ``THROW_DOWN``).
    Blocks new grab input; allows pummel/throw direction."""

    CarryingEnemy = auto()
    """Cargo-carrying a grabbed opponent (``GRAB_JUMP``, used by DK's
    forward-throw cargo carry). A specialized grab state."""

    Downed = auto()
    """On the ground after a knockdown, in a vulnerable or recovering state:
    lying idle (``LYING_GROUND_UP`` / ``LYING_GROUND_UP_HIT`` /
    ``LYING_GROUND_DOWN``), taking damage while down (``DAMAGE_GROUND``),
    missed-tech bounce (``TECH_MISS_UP`` / ``TECH_MISS_DOWN``), or a committed
    passive getup animation (``GROUND_GETUP`` / ``NEUTRAL_GETUP`` /
    ``GETUP_ATTACK`` / ``GROUND_ATTACK_UP`` / ``GROUND_SPOT_UP``). When
    ``hitstun_frames_left > 1`` on one of these, :meth:`get_state` reports
    :attr:`Hitstun` instead (real knockdown hitstun); when stale (=1) the
    character is actionable and reported as :attr:`Downed`. Blocks attack and
    grab input so naive bots release inputs; bots with explicit getup
    dispatch should check :meth:`is_downed` / :meth:`is_getting_up` first.
    Distinct from :attr:`Dodging` (successful techs classify as Dodging, not
    Downed). Active roll getup options (``GROUND_ROLL_*_UP`` /
    ``GROUND_ROLL_*_DOWN`` / ``GROUND_ROLL_SPOT_DOWN``) are also excluded;
    once the player commits to a roll from knockdown they are dodging, not
    lying down."""

    Standing = auto()
    """Grounded, on-stage, neither walking nor running (``STANDING``,
    ``CROUCH_*``, ``TURNING`` without run, ``KNEE_BEND`` jump startup,
    landings that don't transition elsewhere). Default actionable ground
    state."""

    InAir = auto()
    """Airborne without an active attack, grab, or tumble (``FALLING*``,
    ``JUMPING_*``). Actionable for aerials and air dodge."""

    Walking = auto()
    """Walking (``WALK_SLOW`` / ``WALK_MIDDLE`` / ``WALK_FAST`` / ``TURNING``
    from walk). Actionable."""

    Running = auto()
    """Running (``DASHING`` / ``RUNNING`` / ``RUN_DIRECT`` / ``RUN_BRAKE`` /
    ``TURNING_RUN``). Actionable; ``DASH_ATTACK`` requires being here."""


# CharacterStatus values blocked by the deprecated broad attack-state query.
_BLOCKS_ATTACK_INPUT: Final = frozenset(
    {
        CharacterStatus.HitLag,
        CharacterStatus.Hitstun,
        CharacterStatus.GrabbedByEnemy,
        CharacterStatus.ShieldBroken,
        CharacterStatus.GrabbingLedge,
        CharacterStatus.Shielding,
        CharacterStatus.Dodging,
        CharacterStatus.Taunting,
        CharacterStatus.Downed,
    }
)


# States where grab input cannot begin. Unlike ``_BLOCKS_ATTACK_INPUT``, shield
# is NOT blocked (grab out of shield is allowed), but Attacking, GrabbingEnemy,
# and CarryingEnemy ARE blocked (can't start a new grab mid-attack or mid-grab).
# Downed is also blocked (knockdown lying/getup states can't start a grab).
_BLOCKS_GRAB_INPUT: Final = frozenset(
    {
        CharacterStatus.HitLag,
        CharacterStatus.Hitstun,
        CharacterStatus.GrabbedByEnemy,
        CharacterStatus.ShieldBroken,
        CharacterStatus.GrabbingLedge,
        CharacterStatus.Dodging,
        CharacterStatus.Taunting,
        CharacterStatus.Attacking,
        CharacterStatus.GrabbingEnemy,
        CharacterStatus.CarryingEnemy,
        CharacterStatus.Downed,
    }
)


# AttackType groupings used by attack-input gating and recognition.
_GROUND_ATTACKS: Final = frozenset(
    {
        AttackType.JAB,
        AttackType.FTILT,
        AttackType.LTILT,
        AttackType.RTILT,
        AttackType.UTILT,
        AttackType.DTILT,
        AttackType.FSMASH,
        AttackType.LSMASH,
        AttackType.RSMASH,
        AttackType.USMASH,
        AttackType.DSMASH,
    }
)
_AIR_ATTACKS: Final = frozenset(
    {
        AttackType.NAIR,
        AttackType.FAIR,
        AttackType.BAIR,
        AttackType.UAIR,
        AttackType.DAIR,
    }
)
# DESNOTE(jbarber, 2026-08-22): Common grounded actions do not share one IASA
# table. These capability-specific sets follow the direct transitions in the
# common Wait, Walk, Turn, Dash, Run, Squat, Ottotto, and KneeBend states.
# Character-owned action states are intentionally conservative.
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_Wait.c
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_Walk.c
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_Turn.c
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_Dash.c
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_Run.c
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_RunDirect.c
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_TurnRun.c
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_RunBrake.c
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_Squat.c
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_SquatWait.c
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_SquatRv.c
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_Ottotto.c
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_KneeBend.c
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_AppealS.c
_GROUND_NORMAL_ACTIONS: Final = frozenset(
    {
        Action.STANDING,
        Action.WALK_SLOW,
        Action.WALK_MIDDLE,
        Action.WALK_FAST,
        Action.TURNING,
        Action.CROUCH_START,
        Action.CROUCHING,
        Action.CROUCH_END,
        Action.EDGE_TEETERING_START,
        Action.EDGE_TEETERING,
    }
)
_GROUND_SPECIAL_ALL_ACTIONS: Final = frozenset(
    {
        Action.STANDING,
        Action.WALK_SLOW,
        Action.WALK_MIDDLE,
        Action.WALK_FAST,
        Action.RUNNING,
        Action.RUN_DIRECT,
        Action.CROUCH_START,
        Action.EDGE_TEETERING_START,
        Action.EDGE_TEETERING,
    }
)
_GROUND_GRAB_ACTIONS: Final = frozenset(
    {
        Action.STANDING,
        Action.WALK_SLOW,
        Action.WALK_MIDDLE,
        Action.WALK_FAST,
        Action.TURNING,
        Action.DASHING,
        Action.RUNNING,
        Action.RUN_DIRECT,
        Action.KNEE_BEND,
        Action.CROUCH_START,
        Action.EDGE_TEETERING_START,
        Action.EDGE_TEETERING,
    }
)
_GROUND_JUMP_ACTIONS: Final = frozenset(
    {
        Action.STANDING,
        Action.WALK_SLOW,
        Action.WALK_MIDDLE,
        Action.WALK_FAST,
        Action.TURNING,
        Action.DASHING,
        Action.RUNNING,
        Action.RUN_DIRECT,
        Action.TURNING_RUN,
        Action.RUN_BRAKE,
        Action.CROUCH_START,
        Action.CROUCHING,
        Action.CROUCH_END,
        Action.EDGE_TEETERING_START,
        Action.EDGE_TEETERING,
    }
)
_GROUND_TAUNT_ACTIONS: Final = frozenset(
    {
        Action.STANDING,
        Action.WALK_SLOW,
        Action.WALK_MIDDLE,
        Action.WALK_FAST,
        Action.TURNING,
        Action.DASHING,
        Action.RUNNING,
        Action.RUN_DIRECT,
        Action.CROUCH_START,
        Action.CROUCHING,
        Action.CROUCH_END,
        Action.EDGE_TEETERING_START,
        Action.EDGE_TEETERING,
    }
)
# DESNOTE(jbarber, 2026-08-22): Pass and DamageFall run aerial-jump checks;
# FallSpecial also permits an aerial jump despite rejecting EscapeAir and normal
# offense. The remaining-jump count is still required at the public boundary.
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_Pass.c
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_DamageFall.c#L119-L139
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_FallSpecial.c#L80-L85
_AIR_JUMP_ACTIONS: Final = _ATTACKABLE_AIR | frozenset(
    {
        Action.DEAD_FALL,
        Action.SPECIAL_FALL_FORWARD,
        Action.SPECIAL_FALL_BACK,
    }
)
# DESNOTE(jbarber, 2026-08-22): These common actions have a direct Escape path.
# DASHING and SHIELD_RELEASE remain action-level answers because PlayerState does
# not expose their internal timing windows; SHIELD_STUN has an empty IASA.
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_Escape.c
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_Wait.c#L39-L62
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_Guard.c
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_Dash.c#L84-L139
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_KneeBend.c#L61-L68
_GROUND_DODGE_ACTIONS: Final = frozenset(
    {
        Action.STANDING,
        Action.DASHING,
        Action.SHIELD_START,
        Action.SHIELD,
        Action.SHIELD_RELEASE,
        Action.SHIELD_REFLECT,
    }
)
_SHIELD_CANCEL_ACTIONS: Final = frozenset(
    {
        Action.SHIELD_START,
        Action.SHIELD,
        Action.SHIELD_RELEASE,
        Action.SHIELD_REFLECT,
    }
)
# DESNOTE(jbarber, 2026-08-22): Guard transitions are action-specific, so the
# broad false-hitstun neutral bucket cannot back can_shield(). Landing and dash
# have hidden interrupt windows; report dash as action-level eligible and reject
# landing states rather than claiming eligibility that PlayerState cannot prove.
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_Wait.c#L39-L62
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_Walk.c#L75-L99
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_Turn.c
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_Run.c
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_Squat.c
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_TurnRun.c
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_RunBrake.c
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_KneeBend.c#L61-L68
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_Landing.c#L157-L185
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_LandingAir.c
_SHIELD_START_ACTIONS: Final = frozenset(
    {
        Action.STANDING,
        Action.WALK_SLOW,
        Action.WALK_MIDDLE,
        Action.WALK_FAST,
        Action.TURNING,
        Action.DASHING,
        Action.RUNNING,
        Action.RUN_DIRECT,
        Action.CROUCH_START,
        Action.CROUCHING,
        Action.CROUCH_END,
        Action.EDGE_TEETERING_START,
        Action.EDGE_TEETERING,
    }
)
# DESNOTE(jbarber, 2026-08-22): Yoshi's character-specific guard actions occupy
# raw IDs whose canonical Action aliases describe unrelated moves. GuardOn,
# GuardHold, GuardOff, and GuardOn_1 have Escape paths; GuardDamage (344) does not.
# GuardOff exposes only spot dodge, and Catch is absent from it.
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftYoshi/ftYs_Guard.c
_YOSHI_SHIELD_IDS: Final = frozenset({341, 342, 343, 344, 345})
_YOSHI_DODGEABLE_SHIELD_IDS: Final = frozenset({341, 342, 343, 345})
_YOSHI_GRABBABLE_SHIELD_IDS: Final = frozenset({341, 342, 345})
_SPECIAL_ATTACKS: Final = frozenset(
    {
        AttackType.NEUTRAL_B,
        AttackType.SIDE_B,
        AttackType.LSPECIAL,
        AttackType.RSPECIAL,
        AttackType.UP_B,
        AttackType.DOWN_B,
    }
)
_AERIAL_ATTACKS: Final = _AIR_ATTACKS
_GRAB_THROW_ATTACKS: Final = frozenset(
    {
        AttackType.FTHROW,
        AttackType.BTHROW,
        AttackType.UTHROW,
        AttackType.DTHROW,
    }
)


def _action_set(*names: str) -> frozenset[Action]:
    """Build a frozenset of ``Action`` members from enum attribute names."""
    return frozenset(getattr(Action, name) for name in names)


def _relative_attack_type(attack_type: AttackType) -> AttackType:
    """Resolve an absolute horizontal request to its facing-relative move."""
    if attack_type in {AttackType.LTILT, AttackType.RTILT}:
        return AttackType.FTILT
    if attack_type in {AttackType.LSMASH, AttackType.RSMASH}:
        return AttackType.FSMASH
    if attack_type in {AttackType.LSPECIAL, AttackType.RSPECIAL}:
        return AttackType.SIDE_B
    return attack_type


# Action IDs that count as a given AttackType once the move is active in-game.
# Side-B lists SWORD_DANCE_* because many characters reuse those raw IDs; see
# libmelee Action enum / framedata.csv for character-specific mappings.
_ACTIONS_FOR_TYPE: Final = {
    AttackType.JAB: _action_set(
        "NEUTRAL_ATTACK_1",
        "NEUTRAL_ATTACK_2",
        "NEUTRAL_ATTACK_3",
        "LOOPING_ATTACK_START",
        "LOOPING_ATTACK_MIDDLE",
        "LOOPING_ATTACK_END",
    ),
    AttackType.FTILT: _action_set(
        "FTILT_HIGH",
        "FTILT_HIGH_MID",
        "FTILT_MID",
        "FTILT_LOW_MID",
        "FTILT_LOW",
    ),
    AttackType.UTILT: _action_set("UPTILT"),
    AttackType.DTILT: _action_set("DOWNTILT"),
    AttackType.FSMASH: _action_set(
        "FSMASH_HIGH",
        "FSMASH_MID_HIGH",
        "FSMASH_MID",
        "FSMASH_MID_LOW",
        "FSMASH_LOW",
    ),
    AttackType.USMASH: _action_set("UPSMASH"),
    AttackType.DSMASH: _action_set("DOWNSMASH"),
    AttackType.DASH_ATTACK: _action_set("DASH_ATTACK"),
    AttackType.NAIR: _action_set("NAIR", "NAIR_LANDING"),
    AttackType.FAIR: _action_set("FAIR", "FAIR_LANDING"),
    AttackType.BAIR: _action_set("BAIR", "BAIR_LANDING"),
    AttackType.UAIR: _action_set("UAIR", "UAIR_LANDING"),
    AttackType.DAIR: _action_set("DAIR", "DAIR_LANDING"),
    AttackType.NEUTRAL_B: _action_set(
        "NEUTRAL_B_ATTACKING",
        "NEUTRAL_B_ATTACKING_AIR",
        "NEUTRAL_B_CHARGING",
        "NEUTRAL_B_CHARGING_AIR",
        "NEUTRAL_B_FULL_CHARGE",
        "NEUTRAL_B_FULL_CHARGE_AIR",
    ),
    AttackType.SIDE_B: _action_set(
        "SWORD_DANCE_1",
        "SWORD_DANCE_1_AIR",
        "SWORD_DANCE_2_HIGH",
        "SWORD_DANCE_2_MID",
        "SWORD_DANCE_3_HIGH",
        "SWORD_DANCE_3_MID",
        "SWORD_DANCE_3_LOW",
        "SWORD_DANCE_4_HIGH",
        "SWORD_DANCE_4_MID",
        "SWORD_DANCE_4_LOW",
        "SWORD_DANCE_2_HIGH_AIR",
        "SWORD_DANCE_3_MID_AIR",
        "SWORD_DANCE_3_LOW_AIR",
    ),
    AttackType.UP_B: _action_set(
        "UP_B_GROUND",
    ),
    AttackType.DOWN_B: _action_set(
        "DOWN_B_GROUND",
        "DOWN_B_GROUND_START",
        "DOWN_B_STUN",
        "DOWN_B_AIR",
    ),
    AttackType.GRAB: _action_set(
        "GRAB",
        "GRAB_RUNNING",
        "GRAB_PULLING",
        "GRAB_RUNNING_PULLING",
    ),
    AttackType.Z_AIR: frozenset(),
    AttackType.FTHROW: _action_set("THROW_FORWARD"),
    AttackType.BTHROW: _action_set("THROW_BACK"),
    AttackType.UTHROW: _action_set("THROW_UP"),
    AttackType.DTHROW: _action_set("THROW_DOWN"),
}

# DESNOTE(jbarber, 2026-08-23): Ness, Peach, and Game & Watch replace common
# normal-smash motion states with character-owned IDs. Link and Young Link add a
# character-owned second forward-smash slash. Keep these mappings character
# relative because the same raw IDs identify unrelated moves for other fighters.
# See https://github.com/doldecomp/melee/tree/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara
_CHARACTER_NORMAL_ACTIONS: Final[dict[Character, dict[AttackType, frozenset[Action]]]] = {
    Character.NESS: {
        AttackType.FSMASH: frozenset({Action(341)}),
        AttackType.USMASH: frozenset({Action(342), Action(343), Action(344)}),
        AttackType.DSMASH: frozenset({Action(345), Action(346), Action(347)}),
    },
    Character.PEACH: {
        AttackType.NAIR: _ACTIONS_FOR_TYPE[AttackType.NAIR] | {Action(344)},
        AttackType.FAIR: _ACTIONS_FOR_TYPE[AttackType.FAIR] | {Action(345)},
        AttackType.BAIR: _ACTIONS_FOR_TYPE[AttackType.BAIR] | {Action(346)},
        AttackType.UAIR: _ACTIONS_FOR_TYPE[AttackType.UAIR] | {Action(347)},
        AttackType.DAIR: _ACTIONS_FOR_TYPE[AttackType.DAIR] | {Action(348)},
        AttackType.FSMASH: frozenset({Action(349), Action(350), Action(351)}),
    },
    Character.GAMEANDWATCH: {
        AttackType.JAB: frozenset(Action(action_id) for action_id in range(341, 345)),
        AttackType.DTILT: frozenset({Action(345)}),
        AttackType.FSMASH: frozenset({Action(346)}),
        AttackType.NAIR: frozenset({Action(347), Action(350)}),
        AttackType.BAIR: frozenset({Action(348), Action(351)}),
        AttackType.UAIR: frozenset({Action(349), Action(352)}),
    },
    Character.LINK: {
        AttackType.FSMASH: _ACTIONS_FOR_TYPE[AttackType.FSMASH] | {Action(341)},
    },
    Character.YLINK: {
        AttackType.FSMASH: _ACTIONS_FOR_TYPE[AttackType.FSMASH] | {Action(341)},
    },
}
_CHARACTER_ALL_NORMAL_ACTIONS: Final[dict[Character, frozenset[Action]]] = {
    character: frozenset(action for actions in attacks.values() for action in actions)
    for character, attacks in _CHARACTER_NORMAL_ACTIONS.items()
}
_CHARACTER_Z_AIR_ACTIONS: Final[dict[Character, frozenset[Action]]] = {
    Character.SAMUS: frozenset({Action(357), Action(358)}),
    Character.LINK: frozenset({Action(360), Action(361)}),
    Character.YLINK: frozenset({Action(360), Action(361)}),
}

# DESNOTE(jbarber, 2026-08-21): Action names are aliases for character-relative
# raw IDs. Use each doldecomp MotionState table's move-ID assignment rather than
# adding raw ranges to the global set and changing other fighters' meanings. See
# https://github.com/doldecomp/melee/tree/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara
_SPECIAL_SLOT_FOR_ATTACK_TYPE: Final[dict[AttackType, str]] = {
    AttackType.NEUTRAL_B: "neutral-special",
    AttackType.SIDE_B: "side-special",
    AttackType.UP_B: "up-special",
    AttackType.DOWN_B: "down-special",
}
_CHARACTER_SPECIAL_ACTIONS: Final[dict[Character, dict[str, frozenset[Action]]]] = {
    character: {slot: frozenset(Action(action_id) for action_id in action_ids) for slot, action_ids in slots.items()}
    for character, slots in _SPECIAL_SLOT_ACTION_IDS.items()
}
_CHARACTER_ALL_SPECIAL_ACTIONS: Final[dict[Character, frozenset[Action]]] = {
    character: frozenset(action for actions in slots.values() for action in actions)
    for character, slots in _CHARACTER_SPECIAL_ACTIONS.items()
}


def _actions_for_attack_type(
    character: Character,
    attack_type: AttackType,
) -> frozenset[Action]:
    """Return active actions for a move, including character-specific aliases."""
    relative_attack_type = _relative_attack_type(attack_type)
    if relative_attack_type is AttackType.Z_AIR:
        return _CHARACTER_Z_AIR_ACTIONS.get(character, frozenset())
    character_normals = _CHARACTER_NORMAL_ACTIONS.get(character)
    if character_normals is not None and relative_attack_type in character_normals:
        return character_normals[relative_attack_type]
    special_slot = _SPECIAL_SLOT_FOR_ATTACK_TYPE.get(relative_attack_type)
    character_specials = _CHARACTER_SPECIAL_ACTIONS.get(character)
    if special_slot is not None and character_specials is not None:
        return character_specials[special_slot]
    return _ACTIONS_FOR_TYPE[relative_attack_type]


def _special_is_available(player: LibPlayerState, attack_type: AttackType) -> bool:
    relative_attack_type = _relative_attack_type(attack_type)
    # DESNOTE(jbarber, 2026-08-24): The common IASA dispatch can expose a special
    # input even when a fighter's callback table has no implementation for that
    # slot/context. DK has no aerial Hand Slap, while Nana's side- and up-special
    # entries are partner states that she cannot initiate from player input.
    # See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/ftdata.c#L324-L430
    if player.character is Character.DK and relative_attack_type is AttackType.DOWN_B:
        return player.on_ground
    return not (
        player.character is Character.NANA
        and relative_attack_type in {AttackType.SIDE_B, AttackType.UP_B}
    )


def _is_actionable_air(player: LibPlayerState) -> bool:
    return player.action in _ACTIONABLE_AIR or (
        player.character is Character.JIGGLYPUFF and player.action.value in _JIGGLYPUFF_AERIAL_JUMP_IDS
    )


def _is_attackable_air(player: LibPlayerState) -> bool:
    # Peach's character-owned Float IASA dispatches aerial attacks and specials.
    return (
        _is_actionable_air(player)
        or player.action is Action.TUMBLING
        or (player.character is Character.PEACH and player.action.value == 341)
    )


_ALL_ATTACK_ACTIONS: Final = frozenset(action for actions in _ACTIONS_FOR_TYPE.values() for action in actions)


def _is_attack_action(
    character: Character,
    action: Action,
    frame_data: FrameData,
) -> bool:
    """Return whether a character-relative action is an attack or special."""
    return (
        action in _ALL_ATTACK_ACTIONS
        or action in _CHARACTER_ALL_NORMAL_ACTIONS.get(character, ())
        or action in _CHARACTER_ALL_SPECIAL_ACTIONS.get(character, ())
        or action in _CHARACTER_Z_AIR_ACTIONS.get(character, ())
        or frame_data.is_attack(character, action)
    )


def _is_taunt_action(character: Character, action: Action) -> bool:
    return action in _TAUNT_ACTIONS or action in _CHARACTER_TAUNT_ACTIONS.get(character, ())


_PLATFORM_KINDS: Final = frozenset(
    {StageSurfaceKind.SOLID_FLOOR, StageSurfaceKind.SEMISOLID}
)
_WALL_KINDS: Final = frozenset(
    {StageSurfaceKind.LEFT_WALL, StageSurfaceKind.RIGHT_WALL}
)
_PLATFORM_DROP_ACTIONS: Final = frozenset(
    {
        Action.STANDING,
        Action.WALK_SLOW,
        Action.WALK_MIDDLE,
        Action.WALK_FAST,
        Action.RUN_BRAKE,
        Action.CROUCH_START,
        Action.CROUCHING,
    }
)


def _point_distance_squared(first: StagePoint, second: StagePoint) -> float:
    return (first.x - second.x) ** 2 + (first.y - second.y) ** 2


def _segment_distance_squared(point: StagePoint, segment: StageSegment) -> float:
    delta_x = segment.end.x - segment.start.x
    delta_y = segment.end.y - segment.start.y
    length_squared = delta_x**2 + delta_y**2
    if length_squared == 0:
        return _point_distance_squared(point, segment.start)
    projection = (
        (point.x - segment.start.x) * delta_x
        + (point.y - segment.start.y) * delta_y
    ) / length_squared
    projection = min(1.0, max(0.0, projection))
    closest = StagePoint(
        x=segment.start.x + projection * delta_x,
        y=segment.start.y + projection * delta_y,
    )
    return _point_distance_squared(point, closest)


def _surface_distance_squared(point: StagePoint, surface: StageSurface) -> float:
    return min(
        _segment_distance_squared(point, segment) for segment in surface.segments
    )


class CharacterState:
    """Read-only high-level state for one controller port.

    Construct with a :class:`melee.gamestate.GameState` snapshot, a port number,
    and an optional shared :class:`melee.framedata.FrameData`. Public methods read
    the port bound at construction; :meth:`can_attack` also receives the intended
    :class:`AttackType`.

    :class:`SimpleControls` owns a :class:`CharacterState` (exposed via
    ``simple_controls.character_state``) and routes every state check through it.
    Prefer ``simple_controls.character_state.can_attack(attack_type)`` over the
    deprecated ``simple_controls.can_attack()`` wrapper.
    """

    def __init__(
        self,
        game_state: GameState,
        port: int,
        *,
        frame_data: FrameData | None = None,
    ) -> None:
        """Bind a frame snapshot and port for state classification.

        Args:
            game_state: Current libmelee game state.
            port: Controller port (1–4) whose ``PlayerState`` is classified.
            frame_data: Optional shared ``FrameData`` instance. When omitted, a
                new helper is constructed (loads ``framedata.csv``). The runtime
                passes its match-scoped instance to avoid reloading CSV data every
                frame.
        """
        self._game_state = game_state
        self._port = port
        self._frame_data = frame_data or FrameData()

    @property
    def game_state(self) -> GameState:
        """Bound libmelee :class:`GameState` snapshot."""
        return self._game_state

    @property
    def port(self) -> int:
        """Bound controller port (1–4)."""
        return self._port

    @property
    def position_x(self) -> float:
        """Horizontal stage position of the bound port (negative = left).

        Returns 0.0 when the port is absent from the snapshot.
        """
        player = self._game_state.players.get(self._port)
        if player is None:
            return 0.0
        return float(player.position.x)

    @property
    def position_y(self) -> float:
        """Vertical position of the bound port (positive = above stage).

        Returns 0.0 when the port is absent from the snapshot.
        """
        player = self._game_state.players.get(self._port)
        if player is None:
            return 0.0
        return float(player.position.y)

    @property
    def speed_air_x_self(self) -> float:
        """Self-induced horizontal air speed (see libmelee :class:`PlayerState`).

        Returns 0.0 when the port is absent from the snapshot.
        """
        player = self._game_state.players.get(self._port)
        if player is None:
            return 0.0
        return float(player.speed_air_x_self)

    @property
    def speed_ground_x_self(self) -> float:
        """Self-induced horizontal ground speed (see libmelee :class:`PlayerState`).

        Returns 0.0 when the port is absent from the snapshot.
        """
        player = self._game_state.players.get(self._port)
        if player is None:
            return 0.0
        return float(player.speed_ground_x_self)

    @property
    def speed_y_self(self) -> float:
        """Self-induced vertical speed (see libmelee :class:`PlayerState`).

        Negative values are downward. Returns 0.0 when the port is absent.
        """
        player = self._game_state.players.get(self._port)
        if player is None:
            return 0.0
        return float(player.speed_y_self)

    @property
    def speed_x_attack(self) -> float:
        """Knockback / attack-induced horizontal speed (libmelee ``PlayerState``).

        Returns 0.0 when the port is absent from the snapshot.
        """
        player = self._game_state.players.get(self._port)
        if player is None:
            return 0.0
        return float(player.speed_x_attack)

    @property
    def speed_y_attack(self) -> float:
        """Knockback / attack-induced vertical speed (libmelee ``PlayerState``).

        Returns 0.0 when the port is absent from the snapshot.
        """
        player = self._game_state.players.get(self._port)
        if player is None:
            return 0.0
        return float(player.speed_y_attack)

    @property
    def frame_data(self) -> FrameData:
        """Shared libmelee :class:`FrameData` helper used by classification."""
        return self._frame_data

    def player(self) -> LibPlayerState | None:
        """Return the raw libmelee :class:`PlayerState` for the bound port.

        Returns ``None`` when the port is absent from the current snapshot.
        Bots that need per-frame fields (``position``, ``facing``, ``percent``,
        ``action``, ...) should go through this rather than reconstructing a
        ``PlayerState`` lookup.
        """
        return self._game_state.players.get(self._port)

    @property
    def nearest_grabbable_ledge(self) -> StageLedge | None:
        """Grabbable ledge nearest to the character's current position."""
        geometry = self._game_state.stage_geometry
        if geometry is None or not geometry.ledges or self.player() is None:
            return None
        position = self._stage_position()
        return min(
            geometry.ledges,
            key=lambda ledge: _point_distance_squared(position, ledge.position),
        )

    @property
    def nearest_platform(self) -> StageSurface | None:
        """Nearest solid or drop-through continuous platform."""
        return self._nearest_surface(_PLATFORM_KINDS)

    @property
    def nearest_solid_platform(self) -> StageSurface | None:
        """Nearest continuous solid floor surface."""
        return self._nearest_surface(frozenset({StageSurfaceKind.SOLID_FLOOR}))

    @property
    def nearest_semisolid_platform(self) -> StageSurface | None:
        """Nearest continuous drop-through platform surface."""
        return self._nearest_surface(frozenset({StageSurfaceKind.SEMISOLID}))

    @property
    def nearest_left_wall(self) -> StageSurface | None:
        """Nearest continuous left-wall surface."""
        return self._nearest_surface(frozenset({StageSurfaceKind.LEFT_WALL}))

    @property
    def nearest_right_wall(self) -> StageSurface | None:
        """Nearest continuous right-wall surface."""
        return self._nearest_surface(frozenset({StageSurfaceKind.RIGHT_WALL}))

    @property
    def nearest_wall(self) -> StageSurface | None:
        """Nearest continuous wall surface on either side."""
        return self._nearest_surface(_WALL_KINDS)

    @property
    def current_stage_segment(self) -> StageSegment | None:
        """Floor segment under the grounded character, otherwise ``None``."""
        player = self.player()
        geometry = self._game_state.stage_geometry
        if player is None or not player.on_ground or geometry is None:
            return None
        position = self._stage_position()
        floor_segments = (
            segment for segment in geometry.segments if segment.kind in _PLATFORM_KINDS
        )
        segment = min(
            floor_segments,
            key=lambda candidate: _segment_distance_squared(position, candidate),
            default=None,
        )
        if segment is None:
            return None
        return segment

    @property
    def current_stage_surface(self) -> StageSurface | None:
        """Continuous floor surface currently supporting the grounded character."""
        segment = self.current_stage_segment
        geometry = self._game_state.stage_geometry
        if segment is None or geometry is None:
            return None
        return next(
            (surface for surface in geometry.surfaces if segment in surface.segments),
            None,
        )

    @property
    def left_ledge_distance(self) -> float | None:
        """Horizontal distance to the left grabbable ledge of the current surface."""
        return self._current_surface_ledge_distance(StageLedgeSide.LEFT)

    @property
    def right_ledge_distance(self) -> float | None:
        """Horizontal distance to the right grabbable ledge of the current surface."""
        return self._current_surface_ledge_distance(StageLedgeSide.RIGHT)

    @property
    def left_segment_edge_distance(self) -> float | None:
        """Horizontal distance to the current segment's left endpoint."""
        segment = self.current_stage_segment
        if segment is None:
            return None
        return abs(self.position_x - min(segment.start.x, segment.end.x))

    @property
    def right_segment_edge_distance(self) -> float | None:
        """Horizontal distance to the current segment's right endpoint."""
        segment = self.current_stage_segment
        if segment is None:
            return None
        return abs(max(segment.start.x, segment.end.x) - self.position_x)

    def _stage_position(self) -> StagePoint:
        return StagePoint(x=self.position_x, y=self.position_y)

    def _nearest_surface(
        self,
        kinds: frozenset[StageSurfaceKind],
    ) -> StageSurface | None:
        geometry = self._game_state.stage_geometry
        if geometry is None or self.player() is None:
            return None
        position = self._stage_position()
        surfaces = (surface for surface in geometry.surfaces if surface.kind in kinds)
        return min(
            surfaces,
            key=lambda surface: _surface_distance_squared(position, surface),
            default=None,
        )

    def _current_surface_ledge_distance(
        self,
        side: StageLedgeSide,
    ) -> float | None:
        surface = self.current_stage_surface
        geometry = self._game_state.stage_geometry
        if surface is None or geometry is None:
            return None
        line_ids = {segment.line_id for segment in surface.segments}
        ledges = tuple(
            ledge
            for ledge in geometry.ledges
            if ledge.line_id in line_ids and ledge.side is side
        )
        if not ledges:
            return None
        select = min if side is StageLedgeSide.LEFT else max
        ledge = select(ledges, key=lambda candidate: candidate.position.x)
        return abs(self.position_x - ledge.position.x)

    def forward_axis(self) -> HorizontalStickReferenceAxis:
        """Return the absolute horizontal axis the bound player faces.

        Defaults to right when the port is absent, matching
        :attr:`melee.gamestate.PlayerState.facing`.
        """
        target = self.player()
        if target is None or target.facing:
            return StickReferenceAxis.RIGHT
        return StickReferenceAxis.LEFT

    def backward_axis(self) -> HorizontalStickReferenceAxis:
        """Return the absolute horizontal axis behind the bound player.

        Defaults to left when the port is absent, opposite the default forward
        axis.
        """
        if self.forward_axis() is StickReferenceAxis.RIGHT:
            return StickReferenceAxis.LEFT
        return StickReferenceAxis.RIGHT

    def get_state(self) -> CharacterStatus:
        """Return the high-level :class:`CharacterStatus` of the bound port.

        Applies the Slippi false-hitstun guard: stale ``hitstun_frames_left``
        while the character is already actionable is reported as locomotion or
        combat state, not :attr:`CharacterStatus.Hitstun`.
        """
        target = self.player()
        if target is None:
            return CharacterStatus.Standing
        return get_state(target, self._frame_data)

    def in_hitstun(self) -> bool:
        """Return whether the port is in hitlag or real hitstun."""
        target = self.player()
        if target is None:
            return False
        return in_hitstun(target, self._frame_data)

    def is_grabbed(self) -> bool:
        """Return whether the port is being held by an opponent's grab."""
        target = self.player()
        if target is None:
            return False
        return is_grabbed(target, self._frame_data)

    def is_grabbing(self) -> bool:
        """Return whether the port is grabbing or cargo-carrying an opponent."""
        target = self.player()
        if target is None:
            return False
        return is_grabbing(target, self._frame_data)

    def is_carrying_enemy(self) -> bool:
        """Return whether the port is cargo-carrying a grabbed opponent."""
        target = self.player()
        if target is None:
            return False
        return is_carrying_enemy(target, self._frame_data)

    def is_shielding(self) -> bool:
        """Return whether the port is holding or stunned in shield (not broken)."""
        target = self.player()
        if target is None:
            return False
        return is_shielding(target, self._frame_data)

    def is_shield_broken(self) -> bool:
        """Return whether the port is in a shield-break animation."""
        target = self.player()
        if target is None:
            return False
        return is_shield_broken(target, self._frame_data)

    def is_dodging(self) -> bool:
        """Return whether the port is in a roll or spot-dodge animation."""
        target = self.player()
        if target is None:
            return False
        return is_dodging(target, self._frame_data)

    def is_downed(self) -> bool:
        """Return whether the port is lying vulnerable on the ground in a
        knockdown state.

        See :func:`is_downed` for semantics. Bots with explicit getup dispatch
        should call this before :meth:`can_attack` so they reach their getup
        logic instead of being blocked by the ``Downed`` ->
        ``_BLOCKS_ATTACK_INPUT`` rule.
        """
        target = self.player()
        if target is None:
            return False
        return is_downed(target, self._frame_data)

    def is_getting_up(self) -> bool:
        """Return whether the port is in a committed passive getup animation
        (stand / spot / attack from a knockdown).

        See :func:`is_getting_up` for semantics. Disjoint from
        :meth:`is_downed` — when ``is_getting_up()`` is ``True``, the
        character is no longer lying vulnerable (they have committed to
        a getup animation with invulnerability frames).
        """
        target = self.player()
        if target is None:
            return False
        return is_getting_up(target, self._frame_data)

    def is_grabbing_ledge(self) -> bool:
        """Return whether the port is hanging from a ledge."""
        target = self.player()
        if target is None:
            return False
        return is_grabbing_ledge(target, self._frame_data)

    @overload
    @deprecated("Pass the intended AttackType to can_attack().")
    def can_attack(self) -> bool: ...

    @overload
    def can_attack(self, attack_type: AttackType) -> bool: ...

    def can_attack(self, attack_type: AttackType | None = None) -> bool:
        """Return whether an attack could start from the current state.

        The no-argument broad combat-state query is deprecated. Pass the exact
        :class:`AttackType` the bot intends to request.
        """
        target = self.player()
        if target is None:
            return False
        if attack_type is None:
            return _can_attack_by_combat_state(target, self._frame_data)
        return can_attack(target, self._frame_data, attack_type)

    def can_shield(self) -> bool:
        """Return whether shield input is not blocked by combat state."""
        target = self.player()
        if target is None:
            return False
        return can_shield(target, self._frame_data)

    def can_dodge(self) -> bool:
        """Return whether a ground dodge has an input path from this state."""
        target = self.player()
        if target is None:
            return False
        return can_dodge(target, self._frame_data)

    def can_airdodge(self) -> bool:
        """Return whether an air dodge could start from this state."""
        target = self.player()
        if target is None:
            return False
        return can_airdodge(target, self._frame_data)

    def can_jump(self) -> bool:
        """Return whether a ground or remaining aerial jump could start."""
        target = self.player()
        if target is None:
            return False
        return can_jump(target, self._frame_data)

    def can_platform_drop(self) -> bool:
        """Return whether down input can drop through the supporting semisolid."""
        target = self.player()
        segment = self.current_stage_segment
        if (
            target is None
            or segment is None
            or segment.kind is not StageSurfaceKind.SEMISOLID
            or not isinstance(target.action, Action)
        ):
            return False
        return target.action in _PLATFORM_DROP_ACTIONS

    @deprecated("Use can_attack(AttackType.GRAB) instead.")
    def can_grab(self) -> bool:
        """Deprecated: use ``can_attack(AttackType.GRAB)``."""
        target = self.player()
        if target is None:
            return False
        return can_attack(target, self._frame_data, AttackType.GRAB)

    def can_z_air(self) -> bool:
        """Return whether a tether Z Air could start in the current air state."""
        target = self.player()
        if target is None:
            return False
        return can_attack(target, self._frame_data, AttackType.Z_AIR)

    @deprecated("Use can_attack() with the intended aerial type instead.")
    def can_air_attack(self) -> bool:
        """Deprecated: use ``can_attack`` with the intended aerial type."""
        target = self.player()
        if target is None:
            return False
        return can_attack(target, self._frame_data, AttackType.NAIR)

    def is_taunting(self) -> bool:
        """Return whether the controlled port is in a taunt animation."""
        target = self.player()
        if target is None:
            return False
        return is_taunting(target, self._frame_data)

    def can_taunt(self) -> bool:
        """Return whether taunt input could start from the current state.

        Does not consider an active taunt animation — use :meth:`is_taunting`
        for that. Requires grounded, on-stage, actionable locomotion — stricter
        than :meth:`can_attack` because taunt also fails during grab animations
        and while airborne.
        """
        target = self.player()
        if target is None:
            return False
        return can_taunt(target, self._frame_data)


def is_taunting(player: LibPlayerState, frame_data: FrameData | None = None) -> bool:
    """Return whether ``player`` is performing a taunt animation."""
    if frame_data is not None:
        return get_state(player, frame_data) is CharacterStatus.Taunting
    return isinstance(player.action, Action) and _is_taunt_action(player.character, player.action)


def can_taunt(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Return whether taunt input could start from ``player``'s current state.

    Shared helper for bots and :class:`CharacterState`. Taunt requires a common
    grounded action with a direct Appeal transition.
    """
    if is_taunting(player, frame_data):
        return False
    if not _can_attack_by_combat_state(player, frame_data):
        return False
    if not player.on_ground:
        return False
    if player.action in _GRABBER_ACTIONS:
        return False
    if player.action in _LEDGE_HANG_ACTIONS:
        return False
    if not isinstance(player.action, Action):
        return False
    return player.action in _GROUND_TAUNT_ACTIONS


def get_state(player: LibPlayerState, frame_data: FrameData) -> CharacterStatus:
    """Classify ``player`` into a high-level :class:`CharacterStatus`.

    Applies the Slippi false-hitstun guard: stale ``hitstun_frames_left`` while
    the character is already actionable is reported as locomotion or combat
    states, not :attr:`CharacterStatus.Hitstun`.
    """
    if player.hitlag_left > 0:
        return CharacterStatus.HitLag
    if player.action in _GRABBED_VICTIM_ACTIONS:
        return CharacterStatus.GrabbedByEnemy
    if isinstance(player.action, Action) and player.action in _LEDGE_HANG_ACTIONS:
        return CharacterStatus.GrabbingLedge
    if isinstance(player.action, Action) and player.action in _CARRYING_ENEMY_ACTIONS:
        return CharacterStatus.CarryingEnemy
    if isinstance(player.action, Action) and player.action in _SHIELD_BREAK_ACTIONS:
        return CharacterStatus.ShieldBroken
    if _in_real_hitstun(player, frame_data):
        return CharacterStatus.Hitstun
    if player.action is Action.TUMBLING:
        return CharacterStatus.Tumbling
    if isinstance(player.action, Action) and player.action in _GETUP_ROLL_ACTIONS:
        return CharacterStatus.Dodging
    if isinstance(player.action, Action) and player.action in _KNOCKDOWN_ACTIONS:
        return CharacterStatus.Downed
    if (
        player.character is Character.YOSHI
        and isinstance(player.action, Action)
        and player.action.value in _YOSHI_SHIELD_IDS
    ):
        return CharacterStatus.Shielding
    if isinstance(player.action, Action) and frame_data.is_shield(player.action):
        return CharacterStatus.Shielding
    if isinstance(player.action, Action) and _is_taunt_action(player.character, player.action):
        return CharacterStatus.Taunting
    if isinstance(player.action, Action) and frame_data.is_roll(
        player.character,
        player.action,
    ):
        return CharacterStatus.Dodging
    # DESNOTE(jbarber, 2026-08-22): FrameData.is_roll omits EscapeAir, whose
    # common motion state is Action.AIRDODGE (236), so classify it explicitly.
    # See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/ftmotionstates.c#L2736-L2745
    if player.action is Action.AIRDODGE:
        return CharacterStatus.Dodging
    if isinstance(player.action, Action) and player.action in _GRABBING_ENEMY_ACTIONS:
        return CharacterStatus.GrabbingEnemy
    if isinstance(player.action, Action) and (
        (player.character is Character.JIGGLYPUFF and player.action.value in _JIGGLYPUFF_AERIAL_JUMP_IDS)
        or (player.character is Character.PEACH and player.action.value in _PEACH_FLOAT_MOVEMENT_IDS)
    ):
        return CharacterStatus.InAir
    if isinstance(player.action, Action) and _is_attack_action(
        player.character,
        player.action,
        frame_data,
    ):
        return CharacterStatus.Attacking
    if player.on_ground and isinstance(player.action, Action):
        if player.action in _WALK_ACTIONS:
            return CharacterStatus.Walking
        if player.action in _RUN_ACTIONS:
            return CharacterStatus.Running
        return CharacterStatus.Standing
    return CharacterStatus.InAir


def in_hitstun(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Return whether ``player`` is in hitlag or real hitstun."""
    if player.hitlag_left > 0:
        return True
    return _in_real_hitstun(player, frame_data)


def is_grabbed(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Return whether ``player`` is held in an opponent's grab."""
    del frame_data
    return player.action in _GRABBED_VICTIM_ACTIONS


def is_grabbing(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Return whether ``player`` is grabbing or cargo-carrying an opponent."""
    state = get_state(player, frame_data)
    return state in {CharacterStatus.GrabbingEnemy, CharacterStatus.CarryingEnemy}


def is_carrying_enemy(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Return whether ``player`` is cargo-carrying a grabbed opponent."""
    return get_state(player, frame_data) is CharacterStatus.CarryingEnemy


def is_shielding(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Return whether ``player`` is holding or stunned in shield (not broken)."""
    return get_state(player, frame_data) is CharacterStatus.Shielding


def is_shield_broken(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Return whether ``player`` is in a shield-break animation."""
    return get_state(player, frame_data) is CharacterStatus.ShieldBroken


def is_grabbing_ledge(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Return whether ``player`` is hanging from a ledge."""
    return get_state(player, frame_data) is CharacterStatus.GrabbingLedge


def is_dodging(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Return whether ``player`` is in a ground- or air-dodge animation."""
    return get_state(player, frame_data) is CharacterStatus.Dodging


def is_downed(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Return whether ``player`` is currently lying vulnerable on the ground
    in a knockdown state.

    Covers only the truly vulnerable knockdown actions: lying idle
    (``LYING_GROUND_*``), taking damage while down (``DAMAGE_GROUND``), and
    missed-tech bounce (``TECH_MISS_*``). The character is fully vulnerable —
    no invulnerability frames, no committed getup animation in-progress.

    Excluded by design:

    * **Committed passive getups** (``GROUND_GETUP`` / ``NEUTRAL_GETUP`` /
      ``GETUP_ATTACK`` / ``GROUND_ATTACK_UP`` / ``GROUND_SPOT_UP``) — these
      have body-property invulnerability frames during the getup animation.
      Use :func:`is_getting_up` to detect them.
    * **Active roll getups** (``GROUND_ROLL_*``) — these are full dodges
      (have invulnerability), classify as :attr:`CharacterStatus.Dodging`,
      and never counted as ``Downed``.

    Distinct from :func:`get_state` returning :attr:`CharacterStatus.Downed`:
    that classification is broader because it catches both vulnerable
    knockdown and committed passive getups for the purpose of blocking
    attack/grab input. When real hitstun (>1 frame) is active on a knocked-
    down action, :func:`get_state` reports :attr:`CharacterStatus.Hitstun`
    instead, but this function still returns ``True`` — the underlying
    action is still a vulnerable knockdown action regardless of hitstun.

    Bots with explicit getup dispatch should call this before :func:`can_attack`
    so they reach their getup logic instead of being blocked by the
    ``Downed`` -> ``_BLOCKS_ATTACK_INPUT`` rule.
    """
    del frame_data
    if not isinstance(player.action, Action):
        return False
    return player.action in _VULNERABLE_KNOCKDOWN_ACTIONS


def is_getting_up(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Return whether ``player`` is in a committed passive getup animation.

    The player has committed to a stand / spot / attack getup option from a
    knockdown (no roll selected). The animation is in-progress and cannot be
    canceled; the character has body-property invulnerability frames for part
    of it. Useful for bots that want to skip releasing inputs once a getup
    is already committed, vs. waiting on the lying-down decision window.

    Disjoint from :func:`is_downed` — when ``is_getting_up()`` is ``True``,
    ``is_downed()`` is ``False`` (the character is no longer vulnerable /
    lying idle). Both still classify as :attr:`CharacterStatus.Downed` under
    :func:`get_state`. Active roll getups are excluded here too (see
    :data:`_GETUP_ROLL_ACTIONS`).
    """
    del frame_data
    if not isinstance(player.action, Action):
        return False
    return player.action in _GETTING_UP_ACTIONS


def _can_attack_by_combat_state(
    player: LibPlayerState,
    frame_data: FrameData,
) -> bool:
    """Return the legacy broad combat-state eligibility result."""
    return get_state(player, frame_data) not in _BLOCKS_ATTACK_INPUT


@overload
@deprecated("Pass the intended AttackType to can_attack().")
def can_attack(player: LibPlayerState, frame_data: FrameData) -> bool: ...


@overload
def can_attack(
    player: LibPlayerState,
    frame_data: FrameData,
    attack_type: AttackType,
) -> bool: ...


def can_attack(
    player: LibPlayerState,
    frame_data: FrameData,
    attack_type: AttackType | None = None,
) -> bool:
    """Return whether ``attack_type`` could start from ``player``'s state.

    Calling without ``attack_type`` retains the deprecated broad combat-state
    query for compatibility.
    """
    if attack_type is None:
        return _can_attack_by_combat_state(player, frame_data)

    match attack_type:
        case AttackType.GRAB:
            return _can_grab(player, frame_data)
        case AttackType.Z_AIR:
            return _can_z_air(player, frame_data)
        case _:
            pass

    if not _can_attack_by_combat_state(player, frame_data):
        return False
    if not isinstance(player.action, Action):
        return False
    if attack_type in _SPECIAL_ATTACKS and not _special_is_available(player, attack_type):
        return False

    # DESNOTE(jbarber, 2026-08-21): KneeBend IASA checks only up-special (through
    # the misleadingly named ftCo_Attack100_CheckInput), grab, and up-smash.
    # AttackAir starts in Jump IASA after jump squat.
    # See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_KneeBend.c#L61-L68
    # See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_Attack100.c#L154-L164
    match attack_type, player.action, player.on_ground:
        case attack, action, _ if attack in _GRAB_THROW_ATTACKS:
            return action in _GRAB_THROW_INPUT_ACTIONS
        case _, action, _ if action in _GRABBER_ACTIONS:
            return False
        case attack, Action.KNEE_BEND, True:
            return attack in {AttackType.UP_B, AttackType.USMASH}
        case AttackType.DASH_ATTACK, action, True:
            return action in {Action.DASHING, Action.RUNNING, Action.RUN_DIRECT}
        case AttackType.DASH_ATTACK, _, _:
            return False
        case attack, Action.DASHING, True if attack in _GROUND_ATTACKS:
            return attack in {AttackType.FSMASH, AttackType.LSMASH, AttackType.RSMASH}
        case attack, action, True if attack in _GROUND_ATTACKS:
            return action in _GROUND_NORMAL_ACTIONS
        case attack, action, False if attack in _AIR_ATTACKS:
            return _is_attackable_air(player)
        case attack, _, _ if attack in _GROUND_ATTACKS | _AIR_ATTACKS:
            return False
        case (
            AttackType.SIDE_B | AttackType.LSPECIAL | AttackType.RSPECIAL,
            Action.DASHING,
            True,
        ):
            return True
        case attack, Action.TURNING, True if attack in _SPECIAL_ATTACKS:
            return attack is not AttackType.NEUTRAL_B
        case attack, Action.CROUCH_END, True if attack in _SPECIAL_ATTACKS:
            return attack in {AttackType.UP_B, AttackType.DOWN_B}
        case attack, Action.CROUCHING, True if attack in _SPECIAL_ATTACKS:
            return attack in {AttackType.UP_B, AttackType.DOWN_B}
        case attack, action, True if attack in _SPECIAL_ATTACKS:
            return action in _GROUND_SPECIAL_ALL_ACTIONS
        case attack, action, False if attack in _SPECIAL_ATTACKS:
            return _is_attackable_air(player)
        case attack, _, _ if attack in _SPECIAL_ATTACKS:
            return False
        case _:
            return False


def can_shield(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Return whether the action has a direct grounded Guard transition.

    Dash eligibility is action-level because its internal Guard window is not
    represented by :class:`PlayerState`.
    """
    if not player.on_ground or not isinstance(player.action, Action):
        return False
    if player.hitlag_left > 0 or _in_real_hitstun(player, frame_data):
        return False
    return player.action in _SHIELD_START_ACTIONS


def _is_common_actionable_shield_phase(player: LibPlayerState) -> bool:
    """Return whether a standard shield phase exposes common cancel checks."""
    if not isinstance(player.action, Action):
        return False
    return player.character is not Character.YOSHI and player.action in _SHIELD_CANCEL_ACTIONS


def can_dodge(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Return whether the current action has a direct ground Escape path.

    Early dash and shield-release paths depend on internal engine fields absent
    from :class:`PlayerState`, so this reports action-level eligibility.
    """
    if not player.on_ground or not isinstance(player.action, Action):
        return False
    if player.hitlag_left > 0 or _in_real_hitstun(player, frame_data):
        return False
    if player.character is Character.YOSHI and player.action.value in _YOSHI_DODGEABLE_SHIELD_IDS:
        return True
    return player.action in _GROUND_DODGE_ACTIONS


def can_airdodge(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Return whether an air dodge could start from a normal jump/fall state.

    Helpless ``DEAD_FALL`` / ``SPECIAL_FALL_*`` states after Up-B are excluded.
    """
    # DESNOTE(jbarber, 2026-08-22): Normal Jump/Fall IASA calls EscapeAir;
    # DamageFall and FallSpecial do not. DEAD_FALL is neutral helpless FallSpecial.
    # See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_Fall.c#L119-L156
    # See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_Jump.c#L178-L194
    # See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_EscapeAir.c#L27-L35
    # See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_DamageFall.c#L119-L139
    # See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_FallSpecial.c#L80-L85
    if player.on_ground or not isinstance(player.action, Action):
        return False
    if player.hitlag_left > 0 or _in_real_hitstun(player, frame_data):
        return False
    return _is_actionable_air(player)


def can_jump(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Return whether a ground or remaining aerial jump could start.

    Actionable shield phases permit jump-canceling for the roster. Yoshi's unique
    shield permits it only from GuardOn_1 (the powershield state); shield stun does
    not. Outside shield, the player must be in an actionable ground or air state
    and retain an aerial jump when airborne.
    """
    # GuardSetOff (SHIELD_STUN) has an empty IASA; other common actionable shield
    # phases check jump. Yoshi's GuardOn_1 delegates to the common GuardReflect
    # IASA and is its only shield state that checks jump.
    # See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_Guard.c
    if player.hitlag_left > 0 or _in_real_hitstun(player, frame_data):
        return False
    if (
        player.on_ground
        and player.character is Character.YOSHI
        and isinstance(player.action, Action)
        and player.action.value == 345
    ):
        return True
    if player.on_ground and _is_common_actionable_shield_phase(player):
        return True
    if is_shielding(player, frame_data):
        return False
    if not _can_attack_by_combat_state(player, frame_data) or not isinstance(player.action, Action):
        return False
    if player.on_ground:
        return player.action in _GROUND_JUMP_ACTIONS
    return player.jumps_left > 0 and (
        player.action in _AIR_JUMP_ACTIONS
        or (player.character is Character.JIGGLYPUFF and player.action.value in _JIGGLYPUFF_AERIAL_JUMP_IDS)
    )


@deprecated("Use can_attack(..., AttackType.GRAB) instead.")
def can_grab(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Deprecated: use ``can_attack(..., AttackType.GRAB)``."""
    return can_attack(player, frame_data, AttackType.GRAB)


def _can_grab(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Return whether a grounded grab could start (including out of shield)."""
    if not player.on_ground or not isinstance(player.action, Action):
        return False
    if player.hitlag_left > 0 or _in_real_hitstun(player, frame_data):
        return False
    if player.character is Character.YOSHI and 341 <= player.action.value <= 345:
        return player.action.value in _YOSHI_GRABBABLE_SHIELD_IDS
    if get_state(player, frame_data) in _BLOCKS_GRAB_INPUT:
        return False
    # GuardSetOff (SHIELD_STUN) has an empty IASA; actionable shield phases call
    # Catch input checks. Shield release remains an action-level conditional path.
    # See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_Guard.c
    if _is_common_actionable_shield_phase(player):
        return True
    if is_shielding(player, frame_data):
        return False
    return player.action in _GROUND_GRAB_ACTIONS


def can_z_air(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Return whether a tether Z Air could start in the current air state."""
    return can_attack(player, frame_data, AttackType.Z_AIR)


def _can_z_air(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Return whether a tether Z Air could start in the current air state."""
    if player.character not in _Z_AIR_CHARACTERS:
        return False
    if get_state(player, frame_data) in _BLOCKS_GRAB_INPUT:
        return False
    if player.on_ground or not isinstance(player.action, Action):
        return False
    return player.action in _ATTACKABLE_AIR


@deprecated("Use can_attack() with the intended aerial type instead.")
def can_air_attack(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Deprecated: use ``can_attack`` with the intended aerial type."""
    return can_attack(player, frame_data, AttackType.NAIR)


def _in_real_hitstun(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Return whether positive ``hitstun_frames_left`` is genuine hitstun."""
    return player.hitstun_frames_left > 0 and not _stale_hitstun_is_actionable(
        player,
        frame_data,
    )


def _stale_hitstun_is_actionable(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Return whether positive ``hitstun_frames_left`` should not block inputs."""
    if isinstance(player.action, UnknownAnimation):
        return True
    action = player.action
    if action is Action.AIRDODGE:
        return True
    if action in _FALSE_HITSTUN_NEUTRAL_ACTIONS:
        return True
    if _is_actionable_air(player):
        return True
    if _is_taunt_action(player.character, action):
        return True
    if _is_attack_action(player.character, action, frame_data):
        return True
    if frame_data.is_shield(action):
        return True
    if frame_data.is_roll(player.character, action):
        return True
    # Active roll getup options (libmelee ``is_roll`` omits
    # ``GROUND_ROLL_SPOT_DOWN``; check our own bucket too so stale hitstun
    # does not lock these into ``CharacterStatus.Hitstun``).
    if action in _GETUP_ROLL_ACTIONS:
        return True
    if action in _GRABBER_ACTIONS:
        return True
    # Knockdown / getup family: Slippi leaves a stale
    # ``hitstun_frames_left=1`` here, but the character is actionable (can
    # pick a getup option). Real knockdown hitstun (>1) still counts.
    if action in _KNOCKDOWN_ACTIONS:
        return player.hitstun_frames_left <= 1
    return False


def z_air_is_supported(character: Character) -> bool:
    """Return whether ``character`` has a tether aerial grab (Z Air)."""
    return character in _Z_AIR_CHARACTERS


def neutral_b_is_chargeable(character: Character) -> bool:
    """Return whether ``character`` has a hold-to-charge neutral special.

    Chargeable characters enter ``NEUTRAL_B_CHARGING`` / ``NEUTRAL_B_CHARGING_AIR``
    when neutral-B is held. Other characters fire neutral-B immediately.

    Args:
        character: libmelee ``Character`` to query.

    Returns:
        ``True`` if :meth:SimpleControls.attack with ``AttackType.NEUTRAL_B``
        should use a charging :class:`Hold`.
    """
    return character in _NEUTRAL_B_CHARGEABLE


def attack_is_holdable(attack_type: AttackType, character: Character) -> bool:
    """Return whether ``attack_type`` supports a charging :class:`Hold`.

    Smashes are always holdable. Neutral-B is holdable only when
    :func:`neutral_b_is_chargeable` is ``True`` for ``character``. All other
    attack types use short commit holds (``charging=False``).

    Args:
        attack_type: Move to inspect.
        character: Character performing the move.

    Returns:
        ``True`` if :meth:`SimpleControls.attack` begins a charging hold.
    """
    if attack_type in {
        AttackType.FSMASH,
        AttackType.LSMASH,
        AttackType.RSMASH,
        AttackType.USMASH,
        AttackType.DSMASH,
    }:
        return True
    if attack_type is AttackType.NEUTRAL_B:
        return neutral_b_is_chargeable(character)
    return False


def _is_special_action(action: Action) -> bool:
    """Return whether ``action`` is any B-special animation.

    Uses the same raw action-ID threshold as libmelee ``FrameData.is_bmove``.

    This is intentionally broad: side-B, up-B, and down-B share many
    character-specific ``Action`` names (often ``SWORD_DANCE_*``), so
    :meth:`SimpleControls._current_attack_action` pairs this with membership in
    ``_ACTIONS_FOR_TYPE`` first.
    """
    return action.value >= Action.LASER_GUN_PULL.value


__all__ = [
    "AttackType",
    "CharacterState",
    "CharacterStatus",
    "GroundDodgeStickReferenceAxis",
    "HorizontalStickReferenceAxis",
    "StickReferenceAxis",
    "attack_is_holdable",
    "can_air_attack",
    "can_airdodge",
    "can_attack",
    "can_dodge",
    "can_grab",
    "can_jump",
    "can_shield",
    "can_taunt",
    "can_z_air",
    "get_state",
    "in_hitstun",
    "is_carrying_enemy",
    "is_dodging",
    "is_downed",
    "is_getting_up",
    "is_grabbed",
    "is_grabbing",
    "is_grabbing_ledge",
    "is_shield_broken",
    "is_shielding",
    "is_taunting",
    "neutral_b_is_chargeable",
    "z_air_is_supported",
]
