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
from typing import Final

from melee.enums import Action, Character
from melee.framedata import FrameData
from melee.gamestate import GameState, PlayerState as LibPlayerState, UnknownAnimation

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
# States SimpleControls treats as grounded and actionable for starting ground moves.
_ACTIONABLE_GROUND: Final = _FALSE_HITSTUN_NEUTRAL_ACTIONS
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
    }
)
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
_GRAB_THROW_INPUT_ACTIONS: Final = frozenset(
    {
        Action.GRAB_WAIT,
        Action.GRAB_PUMMEL,
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
_TAUNT_ACTIONS: Final = frozenset(
    {
        Action.TAUNT_LEFT,
        Action.TAUNT_RIGHT,
    }
)
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


class AttackType(Enum):
    """Logical attack input a bot can request from :class:`SimpleControls`.

    Values map to Melee stick and button combinations (main stick + ``A`` for
    ground tilts and smashes, C-stick + ``A`` for aerials, main stick + ``B`` for
    specials, ``Z`` for grab). Directional attacks use the controlled port's
    ``PlayerState.facing`` to pick left vs right.

    Ground-only: ``JAB``, ``FTILT``, ``UTILT``, ``DTILT``, ``FSMASH``, ``USMASH``,
    ``DSMASH``, ``GRAB``.

    ``DASH_ATTACK`` requires ``Action.DASHING`` — the bot must enter a dash with
    raw movement inputs before calling it; SimpleControls does not walk or dash
    on the bot's behalf.

    Air-only (or grounded jump startup): ``NAIR``, ``FAIR``, ``BAIR``, ``UAIR``,
    ``DAIR``.

    Specials (ground or air): ``NEUTRAL_B``, ``SIDE_B``, ``UP_B``, ``DOWN_B``.

    Grab throws (requires ``GRAB_WAIT`` / ``GRAB_PUMMEL``): ``FTHROW``, ``BTHROW``,
    ``UTHROW``, ``DTHROW``. Throws are stick-only; ``A`` pummels during a grab.
    ``Z_AIR`` is air-only for tether-grab characters (Samus, Link, Young Link).

    Directional throws use ``PlayerState.facing`` for forward/back; up/down are
    absolute. DK forward-grab behavior (cargo carry) is not implemented by the
    standard :class:`SimpleControls` path and must be handled by bot logic for now.
    """

    JAB = auto()
    FTILT = auto()
    UTILT = auto()
    DTILT = auto()
    FSMASH = auto()
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
    Attacking = auto()
    Taunting = auto()
    Hitstun = auto()
    HitLag = auto()
    Shielding = auto()
    ShieldBroken = auto()
    Dodging = auto()
    GrabbedByEnemy = auto()
    GrabbingEnemy = auto()
    CarryingEnemy = auto()
    Standing = auto()
    InAir = auto()
    Walking = auto()
    Running = auto()


# CharacterStatus values where standard attack/shield input cannot begin.
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
    }
)


# States where grab input cannot begin. Unlike ``_BLOCKS_ATTACK_INPUT``, shield
# is NOT blocked (grab out of shield is allowed), but Attacking, GrabbingEnemy,
# and CarryingEnemy ARE blocked (can't start a new grab mid-attack or mid-grab).
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
    }
)


# AttackType groupings used by attack-input gating and recognition.
_GROUND_ATTACKS: Final = frozenset(
    {
        AttackType.JAB,
        AttackType.FTILT,
        AttackType.UTILT,
        AttackType.DTILT,
        AttackType.FSMASH,
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
_SPECIAL_ATTACKS: Final = frozenset(
    {
        AttackType.NEUTRAL_B,
        AttackType.SIDE_B,
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
    AttackType.Z_AIR: _action_set(
        "GRAB",
        "GRAB_RUNNING",
        "GRAB_PULLING",
        "GRAB_RUNNING_PULLING",
    ),
    AttackType.FTHROW: _action_set("THROW_FORWARD"),
    AttackType.BTHROW: _action_set("THROW_BACK"),
    AttackType.UTHROW: _action_set("THROW_UP"),
    AttackType.DTHROW: _action_set("THROW_DOWN"),
}

_ALL_ATTACK_ACTIONS: Final = frozenset(
    action for actions in _ACTIONS_FOR_TYPE.values() for action in actions
)


class CharacterState:
    """Read-only high-level state for one controller port.

    Construct with a :class:`melee.gamestate.GameState` snapshot, a port number,
    and an optional shared :class:`melee.framedata.FrameData`. All public methods
    accept an optional ``player`` override; when omitted they read the port bound
    at construction.

    :class:`SimpleControls` owns a :class:`CharacterState` (exposed via
    ``simple_controls.character_state``) and routes every state check through it.
    Prefer ``simple_controls.character_state.can_attack(player)`` over the
    deprecated ``simple_controls.can_attack(player)`` wrapper.
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
    def frame_data(self) -> FrameData:
        """Shared libmelee :class:`FrameData` helper used by classification."""
        return self._frame_data

    def player(self, player: LibPlayerState | None = None) -> LibPlayerState | None:
        """Return the ``PlayerState`` that state checks operate on.

        When ``player`` is provided, return it unchanged; otherwise resolve the
        port bound at construction. Returns ``None`` when the port is absent.
        """
        if player is not None:
            return player
        return self._game_state.players.get(self._port)

    def get_state(self, player: LibPlayerState | None = None) -> CharacterStatus:
        """Return the high-level :class:`CharacterStatus` of the bound port.

        Applies the Slippi false-hitstun guard: stale ``hitstun_frames_left``
        while the character is already actionable is reported as locomotion or
        combat state, not :attr:`CharacterStatus.Hitstun`.
        """
        target = self.player(player)
        if target is None:
            return CharacterStatus.Standing
        return get_state(target, self._frame_data)

    def in_hitstun(self, player: LibPlayerState | None = None) -> bool:
        """Return whether the port is in hitlag or real hitstun."""
        target = self.player(player)
        if target is None:
            return False
        return in_hitstun(target, self._frame_data)

    def is_grabbed(self, player: LibPlayerState | None = None) -> bool:
        """Return whether the port is being held by an opponent's grab."""
        target = self.player(player)
        if target is None:
            return False
        return is_grabbed(target, self._frame_data)

    def is_grabbing(self, player: LibPlayerState | None = None) -> bool:
        """Return whether the port is grabbing or cargo-carrying an opponent."""
        target = self.player(player)
        if target is None:
            return False
        return is_grabbing(target, self._frame_data)

    def is_carrying_enemy(self, player: LibPlayerState | None = None) -> bool:
        """Return whether the port is cargo-carrying a grabbed opponent."""
        target = self.player(player)
        if target is None:
            return False
        return is_carrying_enemy(target, self._frame_data)

    def is_shielding(self, player: LibPlayerState | None = None) -> bool:
        """Return whether the port is holding or stunned in shield (not broken)."""
        target = self.player(player)
        if target is None:
            return False
        return is_shielding(target, self._frame_data)

    def is_shield_broken(self, player: LibPlayerState | None = None) -> bool:
        """Return whether the port is in a shield-break animation."""
        target = self.player(player)
        if target is None:
            return False
        return is_shield_broken(target, self._frame_data)

    def is_dodging(self, player: LibPlayerState | None = None) -> bool:
        """Return whether the port is in a roll or spot-dodge animation."""
        target = self.player(player)
        if target is None:
            return False
        return is_dodging(target, self._frame_data)

    def is_grabbing_ledge(self, player: LibPlayerState | None = None) -> bool:
        """Return whether the port is hanging from a ledge."""
        target = self.player(player)
        if target is None:
            return False
        return is_grabbing_ledge(target, self._frame_data)

    def can_attack(self, player: LibPlayerState | None = None) -> bool:
        """Return whether standard attack input is not blocked by combat state."""
        target = self.player(player)
        if target is None:
            return False
        return can_attack(target, self._frame_data)

    def can_shield(self, player: LibPlayerState | None = None) -> bool:
        """Return whether shield input is not blocked by combat state."""
        target = self.player(player)
        if target is None:
            return False
        return can_shield(target, self._frame_data)

    def can_grab(self, player: LibPlayerState | None = None) -> bool:
        """Return whether a grounded grab could start (including out of shield)."""
        target = self.player(player)
        if target is None:
            return False
        return can_grab(target, self._frame_data)

    def can_z_air(self, player: LibPlayerState | None = None) -> bool:
        """Return whether a tether Z Air could start in the current air state."""
        target = self.player(player)
        if target is None:
            return False
        return can_z_air(target, self._frame_data)

    def can_air_attack(self, player: LibPlayerState | None = None) -> bool:
        """Return whether an aerial could start from the current action state."""
        target = self.player(player)
        if target is None:
            return False
        return can_air_attack(target, self._frame_data)

    def is_taunting(self, player: LibPlayerState | None = None) -> bool:
        """Return whether the controlled port is in a taunt animation."""
        target = self.player(player)
        if target is None:
            return False
        return is_taunting(target, self._frame_data)

    def can_taunt(self, player: LibPlayerState | None = None) -> bool:
        """Return whether taunt input could start from the current state.

        Does not consider an active taunt animation — use :meth:`is_taunting`
        for that. Requires grounded, on-stage, actionable locomotion — stricter
        than :meth:`can_attack` because taunt also fails during grab animations
        and while airborne.
        """
        target = self.player(player)
        if target is None:
            return False
        return can_taunt(target, self._frame_data)


def is_taunting(player: LibPlayerState, frame_data: FrameData | None = None) -> bool:
    """Return whether ``player`` is performing a taunt animation."""
    if frame_data is not None:
        return get_state(player, frame_data) is CharacterStatus.Taunting
    return isinstance(player.action, Action) and player.action in _TAUNT_ACTIONS


def can_taunt(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Return whether taunt input could start from ``player``'s current state.

    Shared helper for bots and :class:`CharacterState`. Taunt requires grounded,
    actionable locomotion on stage — not hitstun, grab, ledge hang, or air.
    """
    if is_taunting(player, frame_data):
        return False
    if not can_attack(player, frame_data):
        return False
    if not player.on_ground or player.off_stage:
        return False
    if player.action in _GRABBER_ACTIONS:
        return False
    if player.action in _LEDGE_HANG_ACTIONS:
        return False
    if not isinstance(player.action, Action):
        return False
    return player.action in _ACTIONABLE_GROUND


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
    if isinstance(player.action, Action) and frame_data.is_shield(player.action):
        return CharacterStatus.Shielding
    if isinstance(player.action, Action) and player.action in _TAUNT_ACTIONS:
        return CharacterStatus.Taunting
    if isinstance(player.action, Action) and frame_data.is_roll(
        player.character,
        player.action,
    ):
        return CharacterStatus.Dodging
    if isinstance(player.action, Action) and player.action in _GRABBING_ENEMY_ACTIONS:
        return CharacterStatus.GrabbingEnemy
    if isinstance(player.action, Action) and (
        player.action in _ALL_ATTACK_ACTIONS
        or frame_data.is_attack(player.character, player.action)
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
    return get_state(player, frame_data) is CharacterStatus.GrabbedByEnemy


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
    """Return whether ``player`` is in a roll or spot-dodge animation."""
    return get_state(player, frame_data) is CharacterStatus.Dodging


def can_attack(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Return whether standard attack input is not blocked by combat state."""
    return get_state(player, frame_data) not in _BLOCKS_ATTACK_INPUT


def can_shield(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Return whether shield input is not blocked by combat state."""
    return can_attack(player, frame_data)


def can_grab(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Return whether a grounded grab could start (including out of shield)."""
    if get_state(player, frame_data) in _BLOCKS_GRAB_INPUT:
        return False
    if not player.on_ground or not isinstance(player.action, Action):
        return False
    if is_shielding(player, frame_data):
        return True
    return player.action in _ACTIONABLE_GROUND


def can_z_air(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Return whether a tether Z Air could start in the current air state."""
    if player.character not in _Z_AIR_CHARACTERS:
        return False
    if get_state(player, frame_data) in _BLOCKS_GRAB_INPUT:
        return False
    if player.on_ground or not isinstance(player.action, Action):
        return False
    return player.action in _ACTIONABLE_AIR


def can_air_attack(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Return whether an aerial could start from the current action state."""
    if not can_attack(player, frame_data):
        return False
    if not isinstance(player.action, Action):
        return False
    if player.on_ground:
        return player.action in _ACTIONABLE_GROUND
    return player.action in _ACTIONABLE_AIR


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
    if action in _FALSE_HITSTUN_NEUTRAL_ACTIONS:
        return True
    if action in _ACTIONABLE_AIR:
        return True
    if action in _ALL_ATTACK_ACTIONS:
        return True
    if frame_data.is_attack(player.character, action):
        return True
    if frame_data.is_shield(action):
        return True
    if frame_data.is_roll(player.character, action):
        return True
    if action in _GRABBER_ACTIONS:
        return True
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
    if attack_type in {AttackType.FSMASH, AttackType.USMASH, AttackType.DSMASH}:
        return True
    if attack_type is AttackType.NEUTRAL_B:
        return neutral_b_is_chargeable(character)
    return False


def _is_special_action(action: Action) -> bool:
    """Return whether ``action`` is any B-special animation.

    Uses the same raw action-ID threshold as libmelee ``FrameData.is_bmove`` but
    skips the ``Action.UNKNOWN_ANIMATION`` guard — that member is missing from the
    shipped ``melee`` package and causes ``AttributeError`` if ``is_bmove`` is
    called directly.

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
    "attack_is_holdable",
    "can_air_attack",
    "can_attack",
    "can_grab",
    "can_shield",
    "can_taunt",
    "can_z_air",
    "get_state",
    "in_hitstun",
    "is_carrying_enemy",
    "is_dodging",
    "is_grabbed",
    "is_grabbing",
    "is_grabbing_ledge",
    "is_shield_broken",
    "is_shielding",
    "is_taunting",
    "neutral_b_is_chargeable",
    "z_air_is_supported",
]
