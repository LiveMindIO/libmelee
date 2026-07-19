"""High-level attack inputs for Crowd Control bots.

Bots normally receive a :class:`SimpleControls` instance from the runtime on each
``game_tick`` call. It validates whether a move can start from the current
``PlayerState``, applies the correct stick and button inputs through libmelee's
``Controller``, and returns structured results so bots do not hand-roll per-move
input timing or action-state guards.

Typical loop::

    hold = self._attack_hold
    if hold is not None and not simple_controls.check_hold(hold):
        hold = None

    if hold is not None:
        result = simple_controls.attack(hold.attack_type, hold=hold)
    else:
        result = simple_controls.attack(AttackType.FTILT)

    if isinstance(result, Hold):
        self._attack_hold = result
    elif isinstance(result, AttackFrameData):
        self._attack_hold = None
        startup = result.frame_data.first_hitbox_frame(
            result.character,
            result.action,
        )

See :class:`SimpleControls` for return-value semantics and charge/release behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Final, cast

from melee.controller import Controller
from melee.enums import Action, Button, Character
from melee.framedata import FrameData
from melee.gamestate import GameState, PlayerState as LibPlayerState, UnknownAnimation

if TYPE_CHECKING:
    from melee.bot.character_specific_controls import CharacterSpecificControls

_INPUT_COMMIT_FRAMES: Final = 12
_SMASH_MAX_CHARGE_FRAMES: Final = 60
_NEUTRAL_B_MAX_CHARGE_FRAMES: Final = 120
_AERIAL_COMMIT_FRAMES: Final = 8
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
# Neutral-B charge animations (misnamed _SMASH_CHARGE_ACTIONS historically).
_SMASH_CHARGE_ACTIONS: Final = frozenset(
    {
        Action.NEUTRAL_B_CHARGING,
        Action.NEUTRAL_B_CHARGING_AIR,
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
# Grab throws only accept input while holding a victim (not during grab startup).
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
_EDGE_ACTIONS: Final = _LEDGE_HANG_ACTIONS | _LEDGE_GETUP_ACTIONS | frozenset(
    {Action.EDGE_CATCHING}
)
_GRAB_THROW_ACTIONS: Final = frozenset(
    {
        Action.THROW_FORWARD,
        Action.THROW_BACK,
        Action.THROW_UP,
        Action.THROW_DOWN,
    }
)
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
    absolute. DK forward-grab behavior is handled by
    :class:`DonkeyKongCharacterSpecificControls` because forward starts cargo
    carry instead of a normal throw.
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


class LedgeRecoveryOption(Enum):
    """Ledge-hang get-up input while ``Action.EDGE_HANGING``.

    * ``NEUTRAL_GETUP`` — tap up on the main stick; climb on without roll or
      attack.
    * ``DODGE_GETUP`` — tap shield (L/R); roll onto the stage.
    * ``ATTACK_GETUP`` — tap ``A``; ledge attack.
    * ``JUMP_RECOVERY`` — tap ``Y`` (or ``X`` in-game) with stick toward stage
      and up; ledge jump.
    * ``LET_GO`` — tap down on the main stick; release the ledge without get-up.
    """

    NEUTRAL_GETUP = auto()
    DODGE_GETUP = auto()
    ATTACK_GETUP = auto()
    JUMP_RECOVERY = auto()
    LET_GO = auto()


class CharacterStatus(Enum):
    """High-level motion/combat state for a libmelee port snapshot.

    Distinct from :class:`melee.gamestate.PlayerState` (the per-frame struct).
    Prefer :func:`get_state` / :meth:`SimpleControls.get_state` over reading raw
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


# Like ``_BLOCKS_ATTACK_INPUT`` but allows grab out of shield.
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


@dataclass(frozen=True, slots=True)
class AttackFrameData:
    """Identifies a move that has started and exposes libmelee frame queries.

    Returned when :meth:`SimpleControls.attack` recognizes the requested move in
    the current ``PlayerState``, or when :meth:`SimpleControls.release` completes
    a charged hold.

    Attributes:
        character: Character performing the move.
        action: libmelee ``Action`` currently reported for the move. May differ
            from the primary action used for pre-move estimates (e.g. angled
            smashes report ``FSMASH_HIGH`` rather than ``FSMASH_MID``).
        frame_data: Shared libmelee ``FrameData`` helper. Use methods such as
            ``first_hitbox_frame(character, action)``, ``iasa(character, action)``,
            ``range_forward(character, action, action_frame)``, and
            ``attack_state(character, action, action_frame)`` for spacing and
            combo decisions.
    """

    character: Character
    action: Action
    frame_data: FrameData


@dataclass(frozen=True, slots=True)
class Hold:
    """Token for a multi-frame attack input sequence.

    Pass the same ``Hold`` back to :meth:`SimpleControls.attack` on subsequent
    frames (via ``hold=``) so input or charge windows continue. Validate with
    :meth:`SimpleControls.check_hold` before continuing; release early charge
    with :meth:`SimpleControls.release`.

    Attributes:
        attack_type: Move being input.
        character: Character that started the sequence.
        action: Primary ``Action`` used for pre-move ``FrameData`` lookups before
            the game reports the actual animation.
        frame_data: libmelee ``FrameData`` helper (same object as on
            :class:`AttackFrameData`).
        max_hold_frames: Maximum charge duration for ``charging`` holds (60 for
            smashes, 120 for chargeable neutral-B). ``0`` for commit-only holds
            (tilts, jabs, etc.).
        started_frame: ``GameState.frame`` when the sequence began.
        stick_x: Main-stick X sent with the input (``0.0`` left, ``1.0`` right).
        stick_y: Main-stick Y or C-stick Y for aerials (``0.0`` down, ``1.0`` up).
        port: Controller port driving the input.
        charging: ``True`` for smash and chargeable neutral-B holds; ``False`` for
            short commit windows (tilts, jabs, grabs, most specials).
        released: ``True`` after :meth:`SimpleControls.release` completes.
        release_frame: ``GameState.frame`` when released, if applicable.
    """

    attack_type: AttackType
    character: Character
    action: Action
    frame_data: FrameData
    max_hold_frames: int
    started_frame: int
    stick_x: float
    stick_y: float
    port: int
    charging: bool
    released: bool = False
    release_frame: int | None = None


class _AutoCharacterSpecific:
    """Sentinel: resolve :class:`CharacterSpecificControls` from the bound port."""


_AUTO_CHARACTER_SPECIFIC = _AutoCharacterSpecific()


class SimpleControls:
    """Apply common Melee attack inputs from a single game-state snapshot.

    Construct a fresh instance each frame (the live-match handler does this
    automatically and passes it into ``CrowdControl.game_tick``). Inputs are
    written to the supplied ``Controller``; the runtime flushes them on the next
    ``console.step()`` — do not call ``controller.flush()`` from bot code.

    Return semantics for :meth:`attack`:

    * ``None`` — the move cannot begin or continue (wrong action state, hitstun,
      grab, invulnerability, commit timeout, or ``hold`` token mismatch).
    * :class:`Hold` — inputs were applied and the caller should invoke
      :meth:`attack` again next frame with the same ``hold`` (or call
      :meth:`check_hold` first to detect interruption).
    * :class:`AttackFrameData` — the requested move is active in
      ``PlayerState.action``.

    Chargeable moves (smashes; neutral-B on chargeable characters) return a
    ``Hold`` with ``charging=True``. Call :meth:`release` to drop the charge early
    or keep calling :meth:`attack` with ``hold=`` until the move starts or
    :meth:`check_hold` returns ``False``.
    """

    def __init__(
        self,
        game_state: GameState,
        port: int,
        controller: Controller,
        *,
        frame_data: FrameData | None = None,
        character_specific: CharacterSpecificControls | None | _AutoCharacterSpecific = (
            _AUTO_CHARACTER_SPECIFIC
        ),
    ) -> None:
        """Bind a frame snapshot and controller for one bot port.

        Args:
            game_state: Current libmelee game state.
            port: Controller port (1–4) whose ``PlayerState`` is controlled.
            controller: Virtual controller receiving stick and button presses.
            frame_data: Optional shared ``FrameData`` instance. When omitted, a
                new helper is constructed (loads ``framedata.csv``). The runtime
                passes its match-scoped instance to avoid reloading CSV data every
                frame.
            character_specific: Optional per-character attack overrides. When
                omitted, :class:`CharacterSpecificControlsFactory` resolves from
                the bound port's ``PlayerState.character``. Pass ``None`` to
                disable overrides for that instance.
        """
        self._game_state = game_state
        self._port = port
        self._controller = controller
        self._frame_data = frame_data or FrameData()
        resolved_specific: CharacterSpecificControls | None
        if character_specific is _AUTO_CHARACTER_SPECIFIC:
            from melee.bot.character_specific_controls import (
                CharacterSpecificControlsFactory,
            )

            player = game_state.players.get(port)
            resolved_specific = (
                CharacterSpecificControlsFactory.create(
                    player.character,
                    game_state=game_state,
                    port=port,
                    controller=controller,
                    frame_data=self._frame_data,
                )
                if player is not None
                else None
            )
        else:
            from melee.bot.character_specific_controls import (
                CharacterSpecificControls as _CharacterSpecificControls,
            )

            resolved_specific = cast(
                _CharacterSpecificControls | None,
                character_specific,
            )
        self._character_specific = resolved_specific

    def attack(
        self,
        attack_type: AttackType,
        *,
        hold: Hold | None = None,
    ) -> None | Hold | AttackFrameData:
        """Begin or continue an attack input sequence.

        On the first call for a move, validates that the port's ``PlayerState`` is
        in an actionable state for ``attack_type``, applies the first frame of
        inputs, and returns a :class:`Hold` (or :class:`AttackFrameData` if the
        character is already performing that move).

        On subsequent frames, pass the previous :class:`Hold` as ``hold`` to apply
        the next frame of inputs. For commit-style moves (tilts, jabs, aerials),
        repeat until the return value is :class:`AttackFrameData`. For charge
        holds, repeat until you call :meth:`release`, :meth:`check_hold` fails,
        or the move begins.

        Args:
            attack_type: Move to perform. Must match ``hold.attack_type`` when
                ``hold`` is provided.
            hold: Optional token from a prior :meth:`attack` call on this move.

        Returns:
            ``None`` if the move cannot start or continue.
            :class:`Hold` while inputs are still being committed or held.
            :class:`AttackFrameData` once the move is recognized in
            ``PlayerState.action``.
        """
        if self._character_specific is not None:
            from melee.bot.character_specific_controls import NO_OVERRIDE

            override = self._character_specific.attack(
                attack_type,
                hold=hold,
            )
            if override is not NO_OVERRIDE:
                return cast(None | Hold | AttackFrameData, override)

        if hold is not None:
            if not self._hold_matches(hold, attack_type):
                return None
            return self._continue_attack(hold)

        player = self._player()
        if player is None or not self._can_begin_attack(player, attack_type):
            return None

        current = self._attack_frame_data(player, attack_type)
        if current is not None:
            return current

        stick_x, stick_y = self._stick_for_attack(player, attack_type)
        if attack_is_holdable(attack_type, player.character):
            return self._begin_chargeable_attack(
                attack_type,
                player,
                stick_x,
                stick_y,
            )

        return self._begin_commit_attack(
            attack_type,
            player,
            stick_x,
            stick_y,
        )

    def get_state(self, player: LibPlayerState | None = None) -> CharacterStatus:
        """Return the high-level state of the controlled port.

        When ``player`` is omitted, reads the port bound at construction.
        """
        target = player if player is not None else self._player()
        if target is None:
            return CharacterStatus.Standing
        if self._character_specific is not None:
            from melee.bot.character_specific_controls import NO_OVERRIDE

            override = self._character_specific.get_state(target)
            if override is not NO_OVERRIDE:
                return cast(CharacterStatus, override)
        return get_state(target, self._frame_data)

    def in_hitstun(self, player: LibPlayerState | None = None) -> bool:
        """Return whether the port is in hitlag or real hitstun."""
        target = player if player is not None else self._player()
        if target is None:
            return False
        return in_hitstun(target, self._frame_data)

    def is_grabbed(self, player: LibPlayerState | None = None) -> bool:
        """Return whether the port is being held by an opponent's grab."""
        target = player if player is not None else self._player()
        if target is None:
            return False
        return is_grabbed(target, self._frame_data)

    def is_grabbing(self, player: LibPlayerState | None = None) -> bool:
        """Return whether the port is grabbing or cargo-carrying an opponent."""
        target = player if player is not None else self._player()
        if target is None:
            return False
        return is_grabbing(target, self._frame_data)

    def is_carrying_enemy(self, player: LibPlayerState | None = None) -> bool:
        """Return whether the port is cargo-carrying a grabbed opponent."""
        target = player if player is not None else self._player()
        if target is None:
            return False
        return is_carrying_enemy(target, self._frame_data)

    def is_shielding(self, player: LibPlayerState | None = None) -> bool:
        """Return whether the port is holding or stunned in shield (not broken)."""
        target = player if player is not None else self._player()
        if target is None:
            return False
        return is_shielding(target, self._frame_data)

    def is_shield_broken(self, player: LibPlayerState | None = None) -> bool:
        """Return whether the port is in a shield-break animation."""
        target = player if player is not None else self._player()
        if target is None:
            return False
        return is_shield_broken(target, self._frame_data)

    def is_dodging(self, player: LibPlayerState | None = None) -> bool:
        """Return whether the port is in a roll or spot-dodge animation."""
        target = player if player is not None else self._player()
        if target is None:
            return False
        return is_dodging(target, self._frame_data)

    def is_grabbing_ledge(self, player: LibPlayerState | None = None) -> bool:
        """Return whether the port is hanging from a ledge."""
        target = player if player is not None else self._player()
        if target is None:
            return False
        return is_grabbing_ledge(target, self._frame_data)

    def can_attack(self, player: LibPlayerState | None = None) -> bool:
        """Return whether standard attack input is not blocked by combat state."""
        target = player if player is not None else self._player()
        if target is None:
            return False
        return can_attack(target, self._frame_data)

    def can_shield(self, player: LibPlayerState | None = None) -> bool:
        """Return whether shield input is not blocked by combat state."""
        return self.can_attack(player)

    def can_grab(self, player: LibPlayerState | None = None) -> bool:
        """Return whether a grounded grab could start (including out of shield)."""
        target = player if player is not None else self._player()
        if target is None:
            return False
        return can_grab(target, self._frame_data)

    def can_z_air(self, player: LibPlayerState | None = None) -> bool:
        """Return whether a tether Z Air could start in the current air state."""
        target = player if player is not None else self._player()
        if target is None:
            return False
        return can_z_air(target, self._frame_data)

    def can_air_attack(self, player: LibPlayerState | None = None) -> bool:
        """Return whether an aerial could start from the current action state."""
        target = player if player is not None else self._player()
        if target is None:
            return False
        return can_air_attack(target, self._frame_data)

    def ledge_recovery(self, option: LedgeRecoveryOption) -> bool:
        """Apply one frame of ledge-hang get-up inputs.

        Only acts when the controlled port is ``Action.EDGE_HANGING``. During
        ``Action.EDGE_CATCHING`` or an active ledge get-up animation, returns
        ``False`` without sending inputs. Call each frame while hanging until the
        character leaves the ledge or begins a get-up option.

        Args:
            option: Get-up choice — neutral climb, shield roll, ledge attack, or
                release the ledge.

        Returns:
            ``True`` if inputs were applied for ``option``; ``False`` otherwise.
        """
        player = self._player()
        if player is None or not self._can_ledge_recovery(player):
            return False

        self._apply_ledge_recovery_inputs(player, option)
        return True

    def is_taunting(self, player: LibPlayerState | None = None) -> bool:
        """Return whether the controlled port is in a taunt animation."""
        target = player if player is not None else self._player()
        if target is None:
            return False
        return is_taunting(target, self._frame_data)

    def can_taunt(self, player: LibPlayerState | None = None) -> bool:
        """Return whether taunt input could start from the current state.

        Does not consider an active taunt animation — use :meth:`is_taunting`
        for that. Applies the same grounded/actionable guards as attack startup.
        """
        target = player if player is not None else self._player()
        if target is None:
            return False
        return can_taunt(target, self._frame_data)

    def taunt(self) -> bool:
        """Apply one frame of taunt input (D-pad Up).

        Melee taunts only accept D-pad Up while grounded. When the port is
        already in ``Action.TAUNT_LEFT`` or ``Action.TAUNT_RIGHT``, sends neutral
        inputs so the animation can play out. Otherwise presses D-pad Up when
        :meth:`can_taunt` is true.

        Returns:
            ``True`` if taunt inputs were applied (neutral during animation or
            D-pad Up to start); ``False`` if the port cannot taunt.
        """
        player = self._player()
        if player is None:
            return False
        if is_taunting(player, self._frame_data):
            self._controller.release_all()
            return True
        if not can_taunt(player, self._frame_data):
            return False
        self._controller.release_all()
        self._controller.press_button(Button.BUTTON_D_UP)
        return True

    def check_hold(self, hold: Hold) -> bool:
        """Return whether a :class:`Hold` is still valid.

        Does **not** apply controller inputs — call :meth:`attack` with ``hold=``
        to sustain inputs after validation succeeds.

        Returns ``False`` when:

        * The hold was already released.
        * The port or character no longer matches.
        * The player entered hitstun, was grabbed, or left a valid state.
        * A charging hold exceeded ``max_hold_frames``.
        * The charge completed and the attack animation started.
        * A commit hold exceeded its frame limit.

        Args:
            hold: Token returned by a prior :meth:`attack` call.

        Returns:
            ``True`` if the hold may continue; ``False`` if it was invalidated.
        """
        if self._character_specific is not None:
            from melee.bot.character_specific_controls import NO_OVERRIDE

            override = self._character_specific.check_hold(hold)
            if override is not NO_OVERRIDE:
                return cast(bool, override)

        if hold.released:
            return False

        player = self._player()
        if player is None:
            return False
        if player.character != hold.character or self._port != hold.port:
            return False
        if self._hold_interrupted(player, hold):
            return False

        if hold.charging:
            held_frames = self._game_state.frame - hold.started_frame
            if held_frames > hold.max_hold_frames:
                return False
            if self._charge_completed(player, hold):
                return False
            return True

        if self._game_state.frame - hold.started_frame >= _commit_frame_limit(hold):
            return False

        return True

    def release(self, hold: Hold) -> None | AttackFrameData:
        """Release a charging :class:`Hold` early.

        Only valid for ``Hold`` values with ``charging=True`` (smashes and
        chargeable neutral-B). Sends ``release_all`` on the controller so the
        charged attack can proceed.

        Args:
            hold: Charging hold to release.

        Returns:
            :class:`AttackFrameData` for the move if release succeeded.
            ``None`` if the hold was not charging, already released, or the player
            can no longer release (hitstun, wrong state, etc.).
        """
        if self._character_specific is not None:
            from melee.bot.character_specific_controls import NO_OVERRIDE

            override = self._character_specific.release(hold)
            if override is not NO_OVERRIDE:
                return cast(None | AttackFrameData, override)

        if hold.released or not hold.charging:
            return None

        player = self._player()
        if player is None or self._hold_interrupted(player, hold):
            return None

        self._controller.release_all()
        action = self._current_attack_action(player, hold.attack_type)
        if action is None:
            action = hold.action

        return AttackFrameData(
            character=player.character,
            action=action,
            frame_data=self._frame_data,
        )

    def _player(self) -> LibPlayerState | None:
        """Return the controlled port's ``PlayerState``, if present."""
        return self._game_state.players.get(self._port)

    def _can_ledge_recovery(self, player: LibPlayerState) -> bool:
        """Return whether ``ledge_recovery`` may act on ``player``."""
        if not isinstance(player.action, Action):
            return False
        if player.action in _LEDGE_GETUP_ACTIONS:
            return False
        return player.action in _LEDGE_HANG_ACTIONS

    def _apply_ledge_recovery_inputs(
        self,
        player: LibPlayerState,
        option: LedgeRecoveryOption,
    ) -> None:
        """Write stick and button state for ``option`` to the controller."""
        self._controller.release_all()
        if option is LedgeRecoveryOption.NEUTRAL_GETUP:
            self._controller.tilt_analog(Button.BUTTON_MAIN, 0.5, 1.0)
            return
        if option is LedgeRecoveryOption.LET_GO:
            self._controller.tilt_analog(Button.BUTTON_MAIN, 0.5, 0.0)
            return

        toward_stage = _toward_stage_stick(player)
        if option is LedgeRecoveryOption.DODGE_GETUP:
            self._controller.tilt_analog(Button.BUTTON_MAIN, toward_stage, 0.5)
            self._controller.press_shoulder(Button.BUTTON_L, 1.0)
            return
        if option is LedgeRecoveryOption.ATTACK_GETUP:
            self._controller.tilt_analog(Button.BUTTON_MAIN, toward_stage, 0.5)
            self._controller.press_button(Button.BUTTON_A)
            return
        if option is LedgeRecoveryOption.JUMP_RECOVERY:
            self._controller.tilt_analog(Button.BUTTON_MAIN, toward_stage, 1.0)
            self._controller.press_button(Button.BUTTON_Y)

    def _hold_matches(self, hold: Hold, attack_type: AttackType) -> bool:
        """Return whether ``hold`` belongs to this port and ``attack_type``."""
        return (
            hold.attack_type == attack_type
            and hold.port == self._port
            and not hold.released
        )

    def _continue_attack(self, hold: Hold) -> None | Hold | AttackFrameData:
        """Apply the next frame of inputs for an in-progress ``hold``.

        Validates via :meth:`check_hold`, applies inputs, and returns
        :class:`Hold`, :class:`AttackFrameData` when the move is recognized, or
        ``None`` on interruption.
        """
        player = self._player()
        if player is None or self._hold_interrupted(player, hold):
            return None

        if not self.check_hold(hold):
            current = self._attack_frame_data(player, hold.attack_type)
            if current is not None:
                return current
            return None

        current = self._attack_frame_data(player, hold.attack_type)
        if current is not None and not hold.charging:
            return current

        if hold.charging:
            self._apply_charge_inputs(hold)
            charging_action = self._current_attack_action(player, hold.attack_type)
            if charging_action is not None and not self._is_charge_action(charging_action):
                return AttackFrameData(
                    character=player.character,
                    action=charging_action,
                    frame_data=self._frame_data,
                )
            return hold

        self._apply_attack_inputs(hold)
        current = self._attack_frame_data(player, hold.attack_type)
        if current is not None:
            return current

        return hold

    def _begin_chargeable_attack(
        self,
        attack_type: AttackType,
        player: LibPlayerState,
        stick_x: float,
        stick_y: float,
    ) -> Hold:
        """Start a smash or chargeable neutral-B hold (``charging=True``)."""
        action = _primary_action(player.character, attack_type)
        max_hold = (
            _NEUTRAL_B_MAX_CHARGE_FRAMES
            if attack_type is AttackType.NEUTRAL_B
            else _SMASH_MAX_CHARGE_FRAMES
        )
        hold = Hold(
            attack_type=attack_type,
            character=player.character,
            action=action,
            frame_data=self._frame_data,
            max_hold_frames=max_hold,
            started_frame=self._game_state.frame,
            stick_x=stick_x,
            stick_y=stick_y,
            port=self._port,
            charging=True,
        )
        self._apply_charge_inputs(hold)
        return hold

    def _begin_commit_attack(
        self,
        attack_type: AttackType,
        player: LibPlayerState,
        stick_x: float,
        stick_y: float,
    ) -> Hold:
        """Start a short commit hold (``charging=False``) for non-charge moves."""
        action = _primary_action(player.character, attack_type)
        hold = Hold(
            attack_type=attack_type,
            character=player.character,
            action=action,
            frame_data=self._frame_data,
            max_hold_frames=0,
            started_frame=self._game_state.frame,
            stick_x=stick_x,
            stick_y=stick_y,
            port=self._port,
            charging=False,
        )
        self._apply_attack_inputs(hold)
        return hold

    def _apply_charge_inputs(self, hold: Hold) -> None:
        """Apply one frame of inputs for a charging hold."""
        self._apply_attack_inputs(hold)

    def _apply_attack_inputs(self, hold: Hold) -> None:
        """Write stick and button state for ``hold.attack_type`` to the controller.

        Grab uses ``Z``; aerials use main-stick drift plus C-stick + ``A``; specials
        use main stick + ``B``; everything else uses main stick + ``A``.
        """
        if hold.attack_type in {AttackType.GRAB, AttackType.Z_AIR}:
            self._controller.release_all()
            self._controller.tilt_analog(Button.BUTTON_MAIN, hold.stick_x, 0.5)
            self._controller.press_button(Button.BUTTON_Z)
            return

        if hold.attack_type in _GRAB_THROW_ATTACKS:
            self._controller.release_all()
            self._controller.tilt_analog(Button.BUTTON_MAIN, hold.stick_x, hold.stick_y)
            return

        if hold.attack_type in _AERIAL_ATTACKS:
            self._controller.release_all()
            self._controller.tilt_analog(Button.BUTTON_MAIN, hold.stick_x, 0.5)
            self._controller.tilt_analog(Button.BUTTON_C, hold.stick_x, hold.stick_y)
            self._controller.press_button(Button.BUTTON_A)
            return

        if hold.attack_type in _SPECIAL_ATTACKS:
            self._controller.release_all()
            self._controller.tilt_analog(Button.BUTTON_MAIN, hold.stick_x, hold.stick_y)
            self._controller.press_button(Button.BUTTON_B)
            return

        self._controller.release_all()
        self._controller.tilt_analog(Button.BUTTON_MAIN, hold.stick_x, hold.stick_y)
        self._controller.press_button(Button.BUTTON_A)

    def _hold_interrupted(self, player: LibPlayerState, hold: Hold) -> bool:
        """Return whether external state invalidated ``hold`` (hitstun, grab, etc.).

        Ground charge holds also fail if the player leaves the ground without
        transitioning into an actionable air state (e.g. falling off a platform
        during smash charge).
        """
        if hold.attack_type is AttackType.Z_AIR:
            if not can_z_air(player, self._frame_data):
                return True
        elif hold.attack_type is AttackType.GRAB:
            if not can_grab(player, self._frame_data):
                return True
        elif not can_attack(player, self._frame_data):
            return True
        if hold.attack_type in _GRAB_THROW_ATTACKS:
            if not isinstance(player.action, Action):
                return True
            if player.action in _GRAB_THROW_INPUT_ACTIONS:
                return False
            return player.action not in _ACTIONS_FOR_TYPE[hold.attack_type]
        if player.action in _GRABBER_ACTIONS and hold.attack_type not in {
            AttackType.GRAB,
            AttackType.Z_AIR,
        }:
            return True
        if hold.charging and hold.attack_type in _GROUND_ATTACKS and not player.on_ground:
            if not isinstance(player.action, Action) or player.action not in _ACTIONABLE_AIR:
                return True
        if hold.attack_type is AttackType.DASH_ATTACK:
            if isinstance(player.action, Action) and player.action == Action.DASH_ATTACK:
                return False
            if player.action != Action.DASHING:
                return True
        return False

    def _can_begin_attack(self, player: LibPlayerState, attack_type: AttackType) -> bool:
        """Return whether ``attack_type`` may start from ``player``'s current state.

        Requires neutral-ish action states (see ``_ACTIONABLE_GROUND`` /
        ``_ACTIONABLE_AIR``), no hitstun, no grab (except ``AttackType.GRAB``),
        and ground/air compatibility for the requested move.
        """
        if attack_type is AttackType.Z_AIR:
            return can_z_air(player, self._frame_data)
        if attack_type is AttackType.GRAB:
            return can_grab(player, self._frame_data)
        if not can_attack(player, self._frame_data):
            return False
        if attack_type in _GRAB_THROW_ATTACKS:
            return isinstance(player.action, Action) and (
                player.action in _GRAB_THROW_INPUT_ACTIONS
            )
        if player.action in _GRABBER_ACTIONS and attack_type not in {
            AttackType.GRAB,
            AttackType.Z_AIR,
        }:
            return False

        if attack_type is AttackType.DASH_ATTACK:
            return (
                player.on_ground
                and isinstance(player.action, Action)
                and player.action == Action.DASHING
            )

        if attack_type in _GROUND_ATTACKS:
            if not player.on_ground:
                return False
            if not isinstance(player.action, Action):
                return False
            return player.action in _ACTIONABLE_GROUND

        if attack_type in _AIR_ATTACKS:
            if player.on_ground and (
                not isinstance(player.action, Action)
                or player.action not in _ACTIONABLE_GROUND
            ):
                return False
            if not player.on_ground and (
                not isinstance(player.action, Action)
                or player.action not in _ACTIONABLE_AIR
            ):
                return False
            return True

        if attack_type in _SPECIAL_ATTACKS:
            if player.on_ground:
                return isinstance(player.action, Action) and player.action in _ACTIONABLE_GROUND
            return isinstance(player.action, Action) and player.action in _ACTIONABLE_AIR

        return False

    def _attack_frame_data(
        self,
        player: LibPlayerState,
        attack_type: AttackType,
    ) -> AttackFrameData | None:
        """Build :class:`AttackFrameData` if ``player`` is performing ``attack_type``."""
        action = self._current_attack_action(player, attack_type)
        if action is None:
            return None
        return AttackFrameData(
            character=player.character,
            action=action,
            frame_data=self._frame_data,
        )

    def _current_attack_action(
        self,
        player: LibPlayerState,
        attack_type: AttackType,
    ) -> Action | None:
        """Map ``player.action`` to ``attack_type``, if the move is active.

        First checks membership in ``_ACTIONS_FOR_TYPE``. Moves without hitboxes
        (grabs, many specials) fall through to ``FrameData.is_grab`` or
        :func:`_is_special_action` because ``FrameData.is_attack`` returns
        ``False`` for them.

        Grab detection uses libmelee ``FrameData.is_grab``, which includes command
        grabs whose ``Action`` names look unrelated (e.g. ``SWORD_DANCE_3_MID`` is
        Falcon's Raptor Boost, not Marth's sword dance).
        """
        if not isinstance(player.action, Action):
            return None
        if player.action not in _ACTIONS_FOR_TYPE[attack_type]:
            return None
        if attack_type in _GRAB_THROW_ATTACKS:
            return player.action
        if not self._frame_data.is_attack(player.character, player.action):
            if attack_type in {AttackType.GRAB, AttackType.Z_AIR} and self._frame_data.is_grab(
                player.character,
                player.action,
            ):
                return player.action
            if attack_type in _SPECIAL_ATTACKS and _is_special_action(
                player.action,
            ):
                return player.action
            return None
        return player.action

    def _stick_for_attack(
        self,
        player: LibPlayerState,
        attack_type: AttackType,
    ) -> tuple[float, float]:
        """Return main-stick ``(x, y)`` for ``attack_type`` using ``player.facing``."""
        toward = 1.0 if player.facing else 0.0
        away = 0.0 if player.facing else 1.0
        mapping: dict[AttackType, tuple[float, float]] = {
            AttackType.JAB: (0.5, 0.5),
            AttackType.FTILT: (toward, 0.5),
            AttackType.UTILT: (0.5, 1.0),
            AttackType.DTILT: (0.5, 0.0),
            AttackType.FSMASH: (toward, 0.5),
            AttackType.USMASH: (0.5, 1.0),
            AttackType.DSMASH: (0.5, 0.0),
            AttackType.DASH_ATTACK: (toward, 0.5),
            AttackType.NAIR: (0.5, 0.5),
            AttackType.FAIR: (toward, 0.5),
            AttackType.BAIR: (away, 0.5),
            AttackType.UAIR: (0.5, 1.0),
            AttackType.DAIR: (0.5, 0.0),
            AttackType.NEUTRAL_B: (0.5, 0.5),
            AttackType.SIDE_B: (toward, 0.5),
            AttackType.UP_B: (0.5, 1.0),
            AttackType.DOWN_B: (0.5, 0.0),
            AttackType.GRAB: (toward, 0.5),
            AttackType.Z_AIR: (0.5, 0.5),
            AttackType.FTHROW: (toward, 0.5),
            AttackType.BTHROW: (away, 0.5),
            AttackType.UTHROW: (0.5, 1.0),
            AttackType.DTHROW: (0.5, 0.0),
        }
        return mapping[attack_type]

    def _is_charge_action(self, action: Action) -> bool:
        """Return whether ``action`` is a hold-to-charge neutral-B state."""
        return action in _SMASH_CHARGE_ACTIONS

    def _charge_completed(self, player: LibPlayerState, hold: Hold) -> bool:
        """Return whether a charging hold finished and the attack animation started."""
        if not isinstance(player.action, Action):
            return False
        if player.action in _SMASH_CHARGE_ACTIONS:
            return False
        return player.action in _ACTIONS_FOR_TYPE[hold.attack_type]

# AttackType groupings used by _can_begin_attack and _apply_attack_inputs.
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


def _toward_stage_stick(player: LibPlayerState) -> float:
    """Return main-stick X that drifts toward stage while ledge hanging.

    Ledge hang faces away from stage, so toward-stage is opposite ``facing``.
    When ``facing`` is neutral, fall back to blast-zone side from ``position.x``.
    """
    if player.facing is True:
        return 0.0
    if player.facing is False:
        return 1.0
    return 1.0 if float(player.position.x) < 0 else 0.0


def is_taunting(player: LibPlayerState, frame_data: FrameData | None = None) -> bool:
    """Return whether ``player`` is performing a taunt animation."""
    if frame_data is not None:
        return get_state(player, frame_data) is CharacterStatus.Taunting
    return isinstance(player.action, Action) and player.action in _TAUNT_ACTIONS


def can_taunt(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Return whether taunt input could start from ``player``'s current state.

    Shared helper for bots and :class:`SimpleControls`. Taunt requires grounded,
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
        or player.action in _GRAB_THROW_ACTIONS
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
    _ = frame_data
    if player.hitlag_left > 0:
        return True
    return _in_real_hitstun(player, frame_data)


def is_grabbed(player: LibPlayerState, frame_data: FrameData) -> bool:
    """Return whether ``player`` is held in an opponent's grab."""
    _ = frame_data
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


def _commit_frame_limit(hold: Hold) -> int:
    """Return max frames allowed for a commit hold before timeout.

    Aerials use ``_AERIAL_COMMIT_FRAMES``; others use ``_INPUT_COMMIT_FRAMES``.
    """
    if hold.attack_type in _AERIAL_ATTACKS:
        return _AERIAL_COMMIT_FRAMES
    return _INPUT_COMMIT_FRAMES


def _primary_action(character: Character, attack_type: AttackType) -> Action:
    """Return a representative ``Action`` for pre-move ``FrameData`` lookups.

    ``character`` is intentionally unused: libmelee's ``Action`` enum labels are
    Fox/Marth-centric names for raw animation IDs, so there is no single correct
    enum member per ``AttackType`` across the roster. The returned action is a
    best-effort default (e.g. ``FSMASH_MID``, ``SWORD_DANCE_1`` for side-B) used
    only to seed :class:`Hold.action` before the game reports the real animation.
    Recognition uses :func:`_current_attack_action` and ``_ACTIONS_FOR_TYPE``.
    """
    _ = character
    return _PRIMARY_ACTION[attack_type]


# DESNOTE(jbarber, 2026-06-25): Per-type default Action labels for Hold.action only.
# Do not assume these match every character's move — see _primary_action.
_PRIMARY_ACTION: Final[dict[AttackType, Action]] = {
    AttackType.JAB: Action.NEUTRAL_ATTACK_1,
    AttackType.FTILT: Action.FTILT_MID,
    AttackType.UTILT: Action.UPTILT,
    AttackType.DTILT: Action.DOWNTILT,
    AttackType.FSMASH: Action.FSMASH_MID,
    AttackType.USMASH: Action.UPSMASH,
    AttackType.DSMASH: Action.DOWNSMASH,
    AttackType.DASH_ATTACK: Action.DASH_ATTACK,
    AttackType.NAIR: Action.NAIR,
    AttackType.FAIR: Action.FAIR,
    AttackType.BAIR: Action.BAIR,
    AttackType.UAIR: Action.UAIR,
    AttackType.DAIR: Action.DAIR,
    AttackType.NEUTRAL_B: Action.NEUTRAL_B_ATTACKING,
    AttackType.SIDE_B: Action.SWORD_DANCE_1,
    AttackType.UP_B: Action.UP_B_GROUND,
    AttackType.DOWN_B: Action.DOWN_B_GROUND,
    AttackType.GRAB: Action.GRAB,
    AttackType.Z_AIR: Action.GRAB,
    AttackType.FTHROW: Action.THROW_FORWARD,
    AttackType.BTHROW: Action.THROW_BACK,
    AttackType.UTHROW: Action.THROW_UP,
    AttackType.DTHROW: Action.THROW_DOWN,
}


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
        ``True`` if :meth:`SimpleControls.attack` with ``AttackType.NEUTRAL_B``
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
