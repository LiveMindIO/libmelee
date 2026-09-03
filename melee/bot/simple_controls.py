"""Attack input application for Crowd Control bots.

:class:`SimpleControls` layers stick/button input sequences on top of a
:class:`melee.bot.character_state.CharacterState` instance. All high-level state
classification ("am I in hitstun?", "can a grab start?", "what motion state am I
in?") lives on :class:`CharacterState`; :class:`SimpleControls` consults it via
``self._character_state`` and adds the controller writes that turn those checks
into attacks, dodges, ledge get-ups, and taunts.

Bots normally receive a :class:`SimpleControls` instance from the runtime on each
``game_tick`` call. For state-only reads prefer ``simple_controls.character_state``
(e.g. ``simple_controls.character_state.can_attack(AttackType.FTILT)``) over the
deprecated thin delegates on :class:`SimpleControls` itself — those wrappers
remain only for backward compatibility and will be removed.

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

import math
import warnings
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Final

from melee.bot.character_state import (
    _ACTIONS_FOR_TYPE,
    _AERIAL_ATTACKS,
    _CHARACTER_ALL_NORMAL_ACTIONS,
    _GRAB_THROW_ATTACKS,
    _GRAB_THROW_INPUT_ACTIONS,
    _GRABBER_ACTIONS,
    _GROUND_ATTACKS,
    _LEDGE_GETUP_ACTIONS,
    _LEDGE_HANG_ACTIONS,
    _SPECIAL_ATTACKS,
    AttackType,
    CharacterState,
    CharacterStatus,
    GroundDodgeStickReferenceAxis,
    HorizontalStickReferenceAxis,
    StickReferenceAxis,
    _actions_for_attack_type,
    _can_attack_by_combat_state,
    _is_special_action,
    _relative_attack_type,
    attack_is_holdable,
    can_air_attack,
    can_airdodge,
    can_attack,
    can_dodge,
    can_grab,
    can_jump,
    can_shield,
    can_taunt,
    can_z_air,
    get_state,
    in_hitstun,
    is_carrying_enemy,
    is_dodging,
    is_grabbed,
    is_grabbing,
    is_grabbing_ledge,
    is_shield_broken,
    is_shielding,
    is_taunting,
    neutral_b_is_chargeable,
    z_air_is_supported,
)
from melee.controller import Controller, fix_analog_trigger
from melee.enums import Action, Button, Character
from melee.framedata import FrameData
from melee.gamestate import GameState
from melee.gamestate import PlayerState as LibPlayerState

if TYPE_CHECKING:
    pass

_INPUT_COMMIT_FRAMES: Final = 12
_SMASH_MAX_CHARGE_FRAMES: Final = 60
_SMASH_STARTUP_FRAME_ALLOWANCE: Final = 30
_NEUTRAL_B_MAX_CHARGE_FRAMES: Final = 120
_AERIAL_COMMIT_FRAMES: Final = 8
_TILT_ATTACK_MAGNITUDE: Final = 0.35
_TILT_TURN_MAGNITUDE: Final = 0.5
_DODGE_BUTTONS: Final = frozenset({Button.BUTTON_L, Button.BUTTON_R})
# DESNOTE(jbarber, 2026-08-22): Melee normalizes analog shoulders over 140
# raw steps, then zeros values <= 0.3. The first usable shield input is
# therefore 43/140; the separate 0.25 shield-press threshold is unreachable
# below that deadzone. See:
# https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/gm/gmmain.c#L59-L72
# https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/types.dox#L35-L45
# https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/fighter.c#L1831-L1885
MIN_SHIELD: Final = 43.0 / 140.0
_DIGITAL_BUTTONS: Final = frozenset(Button) - {
    Button.BUTTON_MAIN,
    Button.BUTTON_C,
}
# Neutral-B charge animations (misnamed _SMASH_CHARGE_ACTIONS historically).
_SMASH_CHARGE_ACTIONS: Final = frozenset(
    {
        Action.NEUTRAL_B_CHARGING,
        Action.NEUTRAL_B_CHARGING_AIR,
    }
)
_MEWTWO_SHADOW_BALL_CHARGE_ACTIONS: Final = frozenset(
    {
        Action.MEWTWO_SPECIAL_N_START,
        Action.MEWTWO_SPECIAL_N_LOOP,
        Action.MEWTWO_SPECIAL_AIR_N_START,
        Action.MEWTWO_SPECIAL_AIR_N_LOOP,
    }
)
_SMASH_ATTACK_TYPES: Final = frozenset(
    {
        AttackType.FSMASH,
        AttackType.LSMASH,
        AttackType.RSMASH,
        AttackType.USMASH,
        AttackType.DSMASH,
    }
)
_NESS_SMASH_CHARGE_ACTIONS: Final[dict[AttackType, Action]] = {
    AttackType.USMASH: Action(343),
    AttackType.DSMASH: Action(346),
}
_NESS_SMASH_RELEASE_ACTIONS: Final[dict[AttackType, Action]] = {
    AttackType.USMASH: Action(344),
    AttackType.DSMASH: Action(347),
}


_CARDINAL_STICK_COORDINATES: Final[dict[float, tuple[float, float]]] = {
    0.0: (1.0, 0.5),
    90.0: (0.5, 1.0),
    180.0: (0.0, 0.5),
    270.0: (0.5, 0.0),
}


def stick_coordinates(
    reference_axis: StickReferenceAxis,
    angle_degrees: float,
    *,
    magnitude: float = 1.0,
) -> tuple[float, float]:
    """Convert an angle and radial magnitude to processed-stick coordinates.

    Positive angles rotate counter-clockwise and negative angles clockwise.
    Angles may have any finite magnitude and are reduced modulo 360 degrees.
    For a counter-clockwise angle from up, the centered components are
    ``-magnitude * sin(angle)`` and ``magnitude * cos(angle)``. An affine map
    from ``[-1, 1]`` to ``[0, 1]`` produces the desired processed-stick X and Y
    coordinates: the position a caller wants :meth:`Console.step` to report.
    Thus a 45-degree unit-magnitude request is approximately
    ``(0.1464, 0.8536)``, while
    magnitude zero is neutral ``(0.5, 0.5)``.

    Pass the returned pair uncorrected to :meth:`Controller.tilt_analog` exactly
    once. The controller applies its existing per-axis input correction when
    enabled. This helper does not model stick gates, emulator processing, game
    processing, or hardware output; exact downstream output is outside its
    contract.

    Exact cardinal directions are snapped to ``0.0``, ``0.5``, and ``1.0``;
    all other results are clamped to ``[0, 1]`` against floating-point leakage.

    Args:
        reference_axis: Absolute controller/screen axis at zero degrees.
        angle_degrees: Signed counter-clockwise rotation in degrees.
        magnitude: Requested radial magnitude from ``0.0`` through ``1.0``.

    Raises:
        ValueError: If an argument is non-finite or ``magnitude`` is outside
            the inclusive range ``[0, 1]``.
    """
    if not math.isfinite(angle_degrees):
        raise ValueError("angle_degrees must be finite")
    if not math.isfinite(magnitude):
        raise ValueError("magnitude must be finite")
    if not 0.0 <= magnitude <= 1.0:
        raise ValueError("magnitude must be between 0 and 1 inclusive")

    if magnitude == 0.0:
        return 0.5, 0.5

    absolute_degrees = (reference_axis.value + angle_degrees % 360.0) % 360.0
    cardinal = _CARDINAL_STICK_COORDINATES.get(absolute_degrees)
    if cardinal is not None:
        return (
            0.5 + magnitude * (cardinal[0] - 0.5),
            0.5 + magnitude * (cardinal[1] - 0.5),
        )

    radians = math.radians(absolute_degrees)
    x = 0.5 + magnitude * math.cos(radians) / 2.0
    y = 0.5 + magnitude * math.sin(radians) / 2.0
    return min(1.0, max(0.0, x)), min(1.0, max(0.0, y))


# DESNOTE(jbarber, 2026-06-25): Per-type default Action labels for Hold.action only.
# Do not assume these match every character's move — see _primary_action.
_PRIMARY_ACTION: Final[dict[AttackType, Action]] = {
    AttackType.JAB: Action.NEUTRAL_ATTACK_1,
    AttackType.FTILT: Action.FTILT_MID,
    AttackType.LTILT: Action.FTILT_MID,
    AttackType.RTILT: Action.FTILT_MID,
    AttackType.UTILT: Action.UPTILT,
    AttackType.DTILT: Action.DOWNTILT,
    AttackType.FSMASH: Action.FSMASH_MID,
    AttackType.LSMASH: Action.FSMASH_MID,
    AttackType.RSMASH: Action.FSMASH_MID,
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
    AttackType.LSPECIAL: Action.SWORD_DANCE_1,
    AttackType.RSPECIAL: Action.SWORD_DANCE_1,
    AttackType.UP_B: Action.UP_B_GROUND,
    AttackType.DOWN_B: Action.DOWN_B_GROUND,
    AttackType.GRAB: Action.GRAB,
    AttackType.Z_AIR: Action.GRAB,
    AttackType.FTHROW: Action.THROW_FORWARD,
    AttackType.BTHROW: Action.THROW_BACK,
    AttackType.UTHROW: Action.THROW_UP,
    AttackType.DTHROW: Action.THROW_DOWN,
}


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


@dataclass(frozen=True, slots=True)
class AttackFrameData:
    """Carries action metadata for a requested move and libmelee frame queries.

    :meth:`SimpleControls.attack` returns this only after recognizing the requested
    move in the current ``PlayerState``. :meth:`SimpleControls.release` instead
    returns it when the release input is accepted and may use the hold's expected
    action before a later frame reports the move. A release result is therefore
    not confirmation that the move has started in-game.

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

    Smash charge observation fields are framework-owned implementation state.
    They are excluded from equality and hashing so callers can retain a token
    while :class:`SimpleControls` advances its charge lifecycle.
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
    released: bool = field(default=False, compare=False, hash=False)
    release_frame: int | None = field(default=None, compare=False, hash=False)
    _smash_charge_frames: int = field(default=0, compare=False, hash=False, repr=False)
    _smash_last_action: Action | None = field(default=None, compare=False, hash=False, repr=False)
    _smash_last_action_frame: int | None = field(default=None, compare=False, hash=False, repr=False)
    _smash_last_game_frame: int | None = field(default=None, compare=False, hash=False, repr=False)
    _smash_charge_complete: bool = field(default=False, compare=False, hash=False, repr=False)


def _warn_state_deprecated(name: str, replacement: str | None = None) -> None:
    """Emit a DeprecationWarning for a SimpleControls state-query delegate."""
    target = replacement or f"simple_controls.character_state.{name}()"
    warnings.warn(
        f"SimpleControls.{name}() is deprecated; use {target} instead.",
        DeprecationWarning,
        stacklevel=3,
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


def _primary_action(
    character: Character,
    attack_type: AttackType,
) -> Action:
    """Return a representative ``Action`` for pre-move ``FrameData`` lookups.

    ``character`` is intentionally unused: libmelee's ``Action`` enum labels are
    Fox/Marth-centric names for raw animation IDs, so there is no single correct
    enum member per ``AttackType`` across the roster. The returned action is a
    best-effort default (e.g. ``FSMASH_MID``, ``SWORD_DANCE_1`` for side-B) used
    only to seed :class:`Hold.action` before the game reports the real animation.
    Recognition uses :meth:`SimpleControls._current_attack_action` and
    ``_ACTIONS_FOR_TYPE``.
    """
    _ = character
    return _PRIMARY_ACTION[_relative_attack_type(attack_type)]


def _commit_frame_limit(hold: Hold) -> int:
    """Return max frames allowed for a commit hold before timeout.

    Aerials use ``_AERIAL_COMMIT_FRAMES``; others use ``_INPUT_COMMIT_FRAMES``.
    """
    if hold.attack_type in _AERIAL_ATTACKS:
        return _AERIAL_COMMIT_FRAMES
    return _INPUT_COMMIT_FRAMES


class SimpleControls:
    """Apply common Melee inputs from a single game-state snapshot.

    Construct a fresh instance each frame (the live-match handler does this
    automatically and passes it into ``BotProtocol.game_tick``). Inputs are
    written to the supplied ``Controller``; the runtime flushes them on the next
    ``console.step()`` — do not call ``controller.flush()`` from bot code.

    State classification (hitstun, grab, ledge hang, actionable locomotion, etc.)
    is delegated to the bound :class:`CharacterState`, exposed via
    :attr:`character_state`. New bot code should read state from
    ``simple_controls.character_state`` rather than the deprecated thin delegates
    defined below (``can_attack``, ``get_state``, ``in_hitstun``, …).

    Return semantics for :meth:`attack`:

    * ``None`` — the move cannot begin or continue (wrong action state, hitstun,
      grab, invulnerability, commit timeout, or ``hold`` token mismatch).
    * :class:`Hold` — inputs were applied and the caller should invoke
      :meth:`attack` again next frame with the same ``hold`` (or call
      :meth:`check_hold` first to detect interruption).
    * :class:`AttackFrameData` — the requested move is active in
      ``PlayerState.action``.

    Chargeable moves (smashes; neutral-B on chargeable characters) return a
    ``Hold`` with ``charging=True``. Allow the initial charge input to commit on a
    later ``console.step()`` before calling :meth:`release`; releasing in the same
    frame neutralizes the still-pending input. A release result acknowledges that
    command but does not confirm observed move startup. Otherwise keep calling
    :meth:`attack` with ``hold=`` until the move starts or :meth:`check_hold`
    returns ``False``.
    """

    def __init__(
        self,
        game_state: GameState,
        port: int,
        controller: Controller,
        *,
        frame_data: FrameData | None = None,
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
        """
        self._game_state = game_state
        self._port = port
        self._controller = controller
        self._frame_data = frame_data or FrameData(_warn_deprecated=False)
        self._character_state = CharacterState(
            game_state,
            port,
            frame_data=self._frame_data,
        )

    @property
    def character_state(self) -> CharacterState:
        """Bound :class:`CharacterState` backing all state classification."""
        return self._character_state

    def tilt_stick(
        self,
        reference_axis: StickReferenceAxis,
        angle_degrees: float,
        *,
        magnitude: float = 1.0,
        stick: Button = Button.BUTTON_MAIN,
    ) -> None:
        """Request a main-stick or C-stick tilt from an absolute axis.

        This mutates only the selected stick's pending controller state. It does
        not call ``release_all()`` or ``flush()``, so existing button, shoulder,
        and other-stick inputs remain intact for the runtime's next
        ``console.step()``.

        Args:
            reference_axis: Absolute controller/screen axis at zero degrees.
            angle_degrees: Signed rotation; positive is counter-clockwise and
                negative is clockwise.
            magnitude: Request-space radial magnitude from ``0.0`` through
                ``1.0``.
            stick: :attr:`Button.BUTTON_MAIN` or :attr:`Button.BUTTON_C`.

        Raises:
            ValueError: If ``stick`` is not the main stick or C-stick, an
                argument is non-finite, or ``magnitude`` is outside ``[0, 1]``.
        """
        if stick not in {Button.BUTTON_MAIN, Button.BUTTON_C}:
            raise ValueError(f"Invalid button type {stick} for tilt_stick.")
        x, y = stick_coordinates(
            reference_axis,
            angle_degrees,
            magnitude=magnitude,
        )
        self._controller.tilt_analog(stick, x, y)

    def tilt_turn(self) -> None:
        """Request a weak backward input that turns the character around.

        A tilt turn reverses facing on character-dependent turn frames 5 through
        9. The half-strength input stays safely inside Melee's tilt-turn range.
        Existing pending buttons and C-stick input are preserved.
        """
        self.tilt_stick(
            self._character_state.backward_axis(),
            0.0,
            magnitude=_TILT_TURN_MAGNITUDE,
        )

    def smash_turn(self) -> None:
        """Request a full backward input that turns the character around.

        A smash turn reverses facing on the first turn frame and can become a
        dash if held. Existing pending buttons and C-stick input are preserved.
        """
        self.tilt_stick(self._character_state.backward_axis(), 0.0)

    def shield(self, strength: float) -> bool:
        """Hold or release shield at a requested analog trigger strength.

        ``0.0`` always releases both shoulder inputs. Positive strengths below
        Melee's first usable analog-trigger step are raised to that minimum;
        larger values are preserved through ``1.0``. Below full depression,
        digital L/R are released because either would force full strength. At
        ``1.0``, digital L is pressed as the trigger click. Main-stick, C-stick,
        and non-shoulder button inputs are preserved.

        Returns:
            ``True`` when shoulder inputs were applied. Positive requests return
            ``False`` without changing pending inputs if the fighter cannot start
            or continue shielding.

        Raises:
            ValueError: If ``strength`` is non-finite or outside ``[0, 1]``.
        """
        if not math.isfinite(strength) or not 0.0 <= strength <= 1.0:
            raise ValueError("strength must be finite and between 0 and 1 inclusive")
        if strength > 0.0 and not (self._character_state.can_shield() or self._character_state.is_shielding()):
            return False

        self._controller.release_button(Button.BUTTON_L)
        self._controller.release_button(Button.BUTTON_R)
        self._controller.press_shoulder(Button.BUTTON_L, 0.0)
        self._controller.press_shoulder(Button.BUTTON_R, 0.0)
        if strength > 0.0:
            requested_strength = max(strength, MIN_SHIELD)
            if not self._controller.analog_input_correction_enabled:
                requested_strength = fix_analog_trigger(requested_strength)
            self._controller.press_shoulder(
                Button.BUTTON_L,
                requested_strength,
            )
            if strength == 1.0:
                self._controller.press_button(Button.BUTTON_L)
        return True

    def platform_drop(self) -> bool:
        """Request a non-fast-fall drop through the supporting semisolid.

        Returns ``False`` unless :meth:`CharacterState.can_platform_drop` is
        true. The main-stick-down request persists until the caller changes it;
        Melee suppresses immediate fast fall when it enters ``PLATFORM_DROP``.
        """
        if not self._character_state.can_platform_drop():
            return False
        self.tilt_stick(StickReferenceAxis.DOWN, 0.0)
        return True

    def dodge(
        self,
        direction: GroundDodgeStickReferenceAxis,
        *,
        dodge_button: Button = Button.BUTTON_L,
    ) -> bool:
        """Apply roll or spot-dodge input for the next committed frame.

        The pending stick and shoulder remain latched until a later frame replaces
        or clears them; this method does not schedule an automatic release.

        Args:
            direction: Absolute :attr:`StickReferenceAxis.LEFT` or
                :attr:`StickReferenceAxis.RIGHT` for a roll, or
                :attr:`StickReferenceAxis.DOWN` for a spot dodge.
            dodge_button: Digital L or R shoulder button.

        Returns:
            ``True`` if dodge inputs were applied; ``False`` when the current
            character state has no direct ground-dodge transition.

        Raises:
            ValueError: If ``direction`` is not left/right/down or
                ``dodge_button`` is not L/R.
        """
        if direction not in {
            StickReferenceAxis.LEFT,
            StickReferenceAxis.RIGHT,
            StickReferenceAxis.DOWN,
        }:
            raise ValueError(
                "direction must be StickReferenceAxis.LEFT, StickReferenceAxis.RIGHT, or StickReferenceAxis.DOWN"
            )
        self._validate_dodge_button(dodge_button)
        if not self._character_state.can_dodge():
            return False
        player = self._character_state.player()
        if player is None:
            return False
        if player.action is Action.DASHING and direction is not self._character_state.forward_axis():
            return False
        if player.action is Action.SHIELD_RELEASE and direction is not StickReferenceAxis.DOWN:
            return False
        if (
            player.character is Character.YOSHI
            and isinstance(player.action, Action)
            and player.action.value == 343
            and direction is not StickReferenceAxis.DOWN
        ):
            return False

        self._controller.release_all()
        self.tilt_stick(direction, 0.0)
        self.press_button(dodge_button)
        return True

    def air_dodge(
        self,
        reference_axis: StickReferenceAxis,
        angle_degrees: float = 0.0,
        *,
        magnitude: float = 1.0,
        dodge_button: Button = Button.BUTTON_L,
    ) -> bool:
        """Apply directional air-dodge input for the next committed frame.

        ``reference_axis``, ``angle_degrees``, and ``magnitude`` use the same
        absolute stick-direction convention as :meth:`tilt_stick`.
        The pending stick and shoulder remain latched until a later frame replaces
        or clears them; this method does not schedule an automatic release.

        Args:
            reference_axis: Absolute controller/screen axis at zero degrees.
            angle_degrees: Signed rotation; positive is counter-clockwise and
                negative is clockwise.
            magnitude: Request-space radial magnitude from ``0.0`` through
                ``1.0``.
            dodge_button: Digital L or R shoulder button.

        Returns:
            ``True`` if air-dodge inputs were applied; ``False`` when the current
            character state cannot air dodge.

        Raises:
            ValueError: If ``dodge_button`` is not L/R, an angle or magnitude is
                non-finite, or ``magnitude`` is outside ``[0, 1]``.
        """
        self._validate_dodge_button(dodge_button)
        stick_x, stick_y = stick_coordinates(
            reference_axis,
            angle_degrees,
            magnitude=magnitude,
        )
        if not self._character_state.can_airdodge():
            return False

        self._controller.release_all()
        self._controller.tilt_analog(Button.BUTTON_MAIN, stick_x, stick_y)
        self.press_button(dodge_button)
        return True

    def down_left(self, angle_degrees: float, *, magnitude: float = 1.0, stick: Button = Button.BUTTON_MAIN) -> None:
        """Tilt from down toward left by an angle from 0 through 90 degrees."""
        self._tilt_between_axes(StickReferenceAxis.DOWN, angle_degrees, -1.0, magnitude, stick)

    def down_right(self, angle_degrees: float, *, magnitude: float = 1.0, stick: Button = Button.BUTTON_MAIN) -> None:
        """Tilt from down toward right by an angle from 0 through 90 degrees."""
        self._tilt_between_axes(StickReferenceAxis.DOWN, angle_degrees, 1.0, magnitude, stick)

    def up_left(self, angle_degrees: float, *, magnitude: float = 1.0, stick: Button = Button.BUTTON_MAIN) -> None:
        """Tilt from up toward left by an angle from 0 through 90 degrees."""
        self._tilt_between_axes(StickReferenceAxis.UP, angle_degrees, 1.0, magnitude, stick)

    def up_right(self, angle_degrees: float, *, magnitude: float = 1.0, stick: Button = Button.BUTTON_MAIN) -> None:
        """Tilt from up toward right by an angle from 0 through 90 degrees."""
        self._tilt_between_axes(StickReferenceAxis.UP, angle_degrees, -1.0, magnitude, stick)

    def left_up(self, angle_degrees: float, *, magnitude: float = 1.0, stick: Button = Button.BUTTON_MAIN) -> None:
        """Tilt from left toward up by an angle from 0 through 90 degrees."""
        self._tilt_between_axes(StickReferenceAxis.LEFT, angle_degrees, -1.0, magnitude, stick)

    def left_down(self, angle_degrees: float, *, magnitude: float = 1.0, stick: Button = Button.BUTTON_MAIN) -> None:
        """Tilt from left toward down by an angle from 0 through 90 degrees."""
        self._tilt_between_axes(StickReferenceAxis.LEFT, angle_degrees, 1.0, magnitude, stick)

    def right_up(self, angle_degrees: float, *, magnitude: float = 1.0, stick: Button = Button.BUTTON_MAIN) -> None:
        """Tilt from right toward up by an angle from 0 through 90 degrees."""
        self._tilt_between_axes(StickReferenceAxis.RIGHT, angle_degrees, 1.0, magnitude, stick)

    def right_down(self, angle_degrees: float, *, magnitude: float = 1.0, stick: Button = Button.BUTTON_MAIN) -> None:
        """Tilt from right toward down by an angle from 0 through 90 degrees."""
        self._tilt_between_axes(StickReferenceAxis.RIGHT, angle_degrees, -1.0, magnitude, stick)

    def _tilt_between_axes(
        self,
        reference_axis: StickReferenceAxis,
        angle_degrees: float,
        rotation_sign: float,
        magnitude: float,
        stick: Button,
    ) -> None:
        if not math.isfinite(angle_degrees) or not 0.0 <= angle_degrees <= 90.0:
            raise ValueError("angle_degrees must be finite and between 0 and 90 inclusive")
        self.tilt_stick(reference_axis, rotation_sign * angle_degrees, magnitude=magnitude, stick=stick)

    def press_button(self, button: Button) -> None:
        """Press one digital controller button without changing other inputs.

        This mutates pending controller state only. The runtime commits it on the
        next :meth:`Console.step`; callers must not flush from bot code.

        Raises:
            ValueError: If ``button`` identifies the main stick or C-stick.
        """
        if button not in _DIGITAL_BUTTONS:
            raise ValueError(f"Invalid button type {button} for press_button.")
        self._controller.press_button(button)

    def release_all(self) -> None:
        """Set all pending controller inputs to neutral without flushing."""
        self._controller.release_all()

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
        if hold is not None:
            if not self._hold_matches(hold, attack_type):
                return None
            return self._continue_attack(hold)

        player = self._player()
        if player is None or not self._character_state.can_attack(attack_type):
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

    def taunt(self) -> bool:
        """Apply one frame of taunt input (D-pad Up).

        Melee taunts only accept D-pad Up while grounded. When the port is
        already in ``Action.TAUNT_LEFT`` or ``Action.TAUNT_RIGHT``, sends neutral
        inputs so the animation can play out. Otherwise presses D-pad Up when
        :meth:`CharacterState.can_taunt` is true.

        Returns:
            ``True`` if taunt inputs were applied (neutral during animation or
            D-pad Up to start); ``False`` if the port cannot taunt.
        """
        player = self._player()
        if player is None:
            return False
        if self._character_state.is_taunting():
            self._controller.release_all()
            return True
        if not self._character_state.can_taunt():
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
            if hold.attack_type in _SMASH_ATTACK_TYPES:
                self._observe_smash_charge(player, hold)
                sequence_frames = self._game_state.frame - hold.started_frame
                if sequence_frames > _SMASH_STARTUP_FRAME_ALLOWANCE and hold._smash_last_action is None:
                    return False
                if sequence_frames > hold.max_hold_frames + _SMASH_STARTUP_FRAME_ALLOWANCE:
                    return False
                return not (hold._smash_charge_complete or hold._smash_charge_frames >= hold.max_hold_frames)
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
        charged attack can proceed. Do not call this in the same frame that
        created ``hold``: pending attack inputs are not committed until the next
        ``console.step()``, so same-frame release neutralizes them before the game
        sees them.

        Args:
            hold: Charging hold to release.

        Returns:
            :class:`AttackFrameData` for the requested move if the release command
            was accepted. When the current ``PlayerState`` has not reported the
            move yet, ``action`` is the hold's expected action; this does not
            confirm that the move started in-game.
            ``None`` if the hold was not charging, already released, or the player
            can no longer release (hitstun, wrong state, etc.).
        """
        if hold.released or not hold.charging:
            return None

        player = self._player()
        if (
            player is None
            or player.character != hold.character
            or self._port != hold.port
            or self._hold_interrupted(player, hold)
        ):
            return None

        self._controller.release_all()
        action = self._current_attack_action(player, hold.attack_type)
        if action is None:
            # DESNOTE(jbarber, 2026-08-18): release() acknowledges a controller
            # command whose result cannot be observed until a later game frame.
            # Preserve useful metadata without claiming PlayerState confirmation.
            action = hold.action
        # DESNOTE(jbarber, 2026-08-21): Hold remains externally immutable and
        # hash-compatible. These non-comparing lifecycle fields are framework-
        # owned so an accepted release cannot be replayed.
        object.__setattr__(hold, "released", True)
        object.__setattr__(hold, "release_frame", self._game_state.frame)

        return AttackFrameData(
            character=player.character,
            action=action,
            frame_data=self._frame_data,
        )

    # ------------------------------------------------------------------
    # Deprecated state-query delegates.
    #
    # These thin wrappers exist only for backward compatibility. New bot code
    # should call the equivalent method on ``self.character_state`` directly.
    # They will be removed once callers have migrated.
    # ------------------------------------------------------------------

    def get_state(self) -> CharacterStatus:
        """Deprecated: use :attr:`character_state` :meth:`.get_state`."""
        _warn_state_deprecated("get_state")
        return self._character_state.get_state()

    def in_hitstun(self) -> bool:
        """Deprecated: use :attr:`character_state` :meth:`.in_hitstun`."""
        _warn_state_deprecated("in_hitstun")
        return self._character_state.in_hitstun()

    def is_grabbed(self) -> bool:
        """Deprecated: use :attr:`character_state` :meth:`.is_grabbed`."""
        _warn_state_deprecated("is_grabbed")
        return self._character_state.is_grabbed()

    def is_grabbing(self) -> bool:
        """Deprecated: use :attr:`character_state` :meth:`.is_grabbing`."""
        _warn_state_deprecated("is_grabbing")
        return self._character_state.is_grabbing()

    def is_carrying_enemy(self) -> bool:
        """Deprecated: use :attr:`character_state` :meth:`.is_carrying_enemy`."""
        _warn_state_deprecated("is_carrying_enemy")
        return self._character_state.is_carrying_enemy()

    def is_shielding(self) -> bool:
        """Deprecated: use :attr:`character_state` :meth:`.is_shielding`."""
        _warn_state_deprecated("is_shielding")
        return self._character_state.is_shielding()

    def is_shield_broken(self) -> bool:
        """Deprecated: use :attr:`character_state` :meth:`.is_shield_broken`."""
        _warn_state_deprecated("is_shield_broken")
        return self._character_state.is_shield_broken()

    def is_dodging(self) -> bool:
        """Deprecated: use :attr:`character_state` :meth:`.is_dodging`."""
        _warn_state_deprecated("is_dodging")
        return self._character_state.is_dodging()

    def is_downed(self) -> bool:
        """Deprecated: use :attr:`character_state` :meth:`.is_downed`."""
        _warn_state_deprecated("is_downed")
        return self._character_state.is_downed()

    def is_getting_up(self) -> bool:
        """Deprecated: use :attr:`character_state` :meth:`.is_getting_up`."""
        _warn_state_deprecated("is_getting_up")
        return self._character_state.is_getting_up()

    def is_grabbing_ledge(self) -> bool:
        """Deprecated: use :attr:`character_state` :meth:`.is_grabbing_ledge`."""
        _warn_state_deprecated("is_grabbing_ledge")
        return self._character_state.is_grabbing_ledge()

    def can_attack(self) -> bool:
        """Deprecated: use ``character_state.can_attack(attack_type)``."""
        _warn_state_deprecated(
            "can_attack",
            "simple_controls.character_state.can_attack(attack_type)",
        )
        player = self._player()
        if player is None:
            return False
        return _can_attack_by_combat_state(player, self._frame_data)

    def can_shield(self) -> bool:
        """Deprecated: use :attr:`character_state` :meth:`.can_shield`."""
        _warn_state_deprecated("can_shield")
        return self._character_state.can_shield()

    def can_jump(self) -> bool:
        """Deprecated: use :attr:`character_state` :meth:`.can_jump`."""
        _warn_state_deprecated("can_jump")
        return self._character_state.can_jump()

    def can_grab(self) -> bool:
        """Deprecated: use ``character_state.can_attack(AttackType.GRAB)``."""
        _warn_state_deprecated(
            "can_grab",
            "simple_controls.character_state.can_attack(AttackType.GRAB)",
        )
        return self._character_state.can_attack(AttackType.GRAB)

    def can_z_air(self) -> bool:
        """Deprecated: use :attr:`character_state` :meth:`.can_z_air`."""
        _warn_state_deprecated("can_z_air")
        return self._character_state.can_z_air()

    def can_air_attack(self) -> bool:
        """Deprecated: use ``character_state.can_attack(aerial_type)``."""
        _warn_state_deprecated(
            "can_air_attack",
            "simple_controls.character_state.can_attack(aerial_type)",
        )
        return self._character_state.can_attack(AttackType.NAIR)

    def is_taunting(self) -> bool:
        """Deprecated: use :attr:`character_state` :meth:`.is_taunting`."""
        _warn_state_deprecated("is_taunting")
        return self._character_state.is_taunting()

    def can_taunt(self) -> bool:
        """Deprecated: use :attr:`character_state` :meth:`.can_taunt`."""
        _warn_state_deprecated("can_taunt")
        return self._character_state.can_taunt()

    # ------------------------------------------------------------------
    # Private helpers.
    # ------------------------------------------------------------------

    def _player(self) -> LibPlayerState | None:
        """Return the controlled port's ``PlayerState``, if present."""
        return self._game_state.players.get(self._port)

    @staticmethod
    def _validate_dodge_button(dodge_button: Button) -> None:
        """Reject buttons that cannot initiate a dodge."""
        if dodge_button not in _DODGE_BUTTONS:
            raise ValueError("dodge_button must be Button.BUTTON_L or Button.BUTTON_R")

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
        return hold.attack_type == attack_type and hold.port == self._port and not hold.released

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
            if hold.attack_type in _SMASH_ATTACK_TYPES and charging_action is not None:
                return hold
            if charging_action is not None and not self._is_charge_action(
                player.character,
                charging_action,
            ):
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
        max_hold = _NEUTRAL_B_MAX_CHARGE_FRAMES if attack_type is AttackType.NEUTRAL_B else _SMASH_MAX_CHARGE_FRAMES
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

        Grab uses ``Z``; directional aerials use main-stick drift plus C-stick;
        neutral aerial uses ``A``; specials use main stick + ``B``; everything
        else uses main stick + ``A``.
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
            if hold.attack_type is AttackType.NAIR:
                self._controller.press_button(Button.BUTTON_A)
            else:
                self._controller.tilt_analog(
                    Button.BUTTON_C,
                    hold.stick_x,
                    hold.stick_y,
                )
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

        Ground charge holds also fail whenever the player leaves the ground.
        """
        if hold.attack_type is AttackType.Z_AIR:
            if self._current_attack_action(player, AttackType.Z_AIR) is not None:
                return False
            if not self._character_state.can_attack(AttackType.Z_AIR):
                return True
        elif hold.attack_type is AttackType.GRAB:
            if self._current_attack_action(player, AttackType.GRAB) is not None:
                return False
            if not self._character_state.can_attack(AttackType.GRAB):
                return True
        elif not _can_attack_by_combat_state(player, self._frame_data):
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
            return True
        if hold.attack_type is AttackType.DASH_ATTACK:
            if isinstance(player.action, Action) and player.action == Action.DASH_ATTACK:
                return False
            if player.action != Action.DASHING:
                return True
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

        First checks character-aware action membership. Moves without hitboxes
        (grabs, many specials) fall through to ``FrameData.is_grab`` or
        :func:`_is_special_action` because ``FrameData.is_attack`` returns
        ``False`` for them.

        Grab detection uses libmelee ``FrameData.is_grab``, which includes command
        grabs whose ``Action`` names look unrelated (e.g. ``SWORD_DANCE_3_MID`` is
        Falcon's Raptor Boost, not Marth's sword dance).
        """
        if not isinstance(player.action, Action):
            return None
        if player.action not in _actions_for_attack_type(player.character, attack_type):
            return None
        if attack_type in _GRAB_THROW_ATTACKS | {AttackType.GRAB, AttackType.Z_AIR}:
            return player.action
        if player.action in _CHARACTER_ALL_NORMAL_ACTIONS.get(player.character, ()):
            return player.action
        if attack_type in _SPECIAL_ATTACKS and _is_special_action(player.action):
            return player.action
        if not self._frame_data.is_attack(player.character, player.action):
            if attack_type in {AttackType.GRAB, AttackType.Z_AIR} and self._frame_data.is_grab(
                player.character,
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
        tilt_offset = _TILT_ATTACK_MAGNITUDE / 2.0
        tilt_low = 0.5 - tilt_offset
        tilt_high = 0.5 + tilt_offset
        tilt_toward = tilt_high if player.facing else tilt_low

        # DESNOTE(jbarber, 2026-08-22): Standing IASA checks smashes before tilts.
        # NTSC 1.02 PlCo.dat uses +/-0.25 tilt thresholds, +/-0.8 horizontal
        # smash thresholds, +0.6625 for up-smash, and -0.6625 for down-smash.
        # A 0.35 centered magnitude stays strictly inside that tilt-only range
        # after Dolphin quantization with analog correction enabled (+/-28 raw)
        # or disabled (-45/+44 raw); the nearest directional boundaries are
        # +/-20 for tilts and conservatively +/-53 for vertical smashes.
        # See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_Wait.c#L43-L56
        # https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_AttackHi4.c#L25-L35
        # https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftCommon/ftCo_AttackLw4.c#L22-L31
        # and https://github.com/barrelofsulfuricacid-gif/ultra-performance-platform-fighter/blob/4012e3ed7c9e5c05f95f25f1beaf407d6d3b21ab/tools/import_ssbm_common_data.py#L108-L116
        mapping: dict[AttackType, tuple[float, float]] = {
            AttackType.JAB: (0.5, 0.5),
            AttackType.FTILT: (tilt_toward, 0.5),
            AttackType.LTILT: (tilt_low, 0.5),
            AttackType.RTILT: (tilt_high, 0.5),
            AttackType.UTILT: (0.5, tilt_high),
            AttackType.DTILT: (0.5, tilt_low),
            AttackType.FSMASH: (toward, 0.5),
            AttackType.LSMASH: (0.0, 0.5),
            AttackType.RSMASH: (1.0, 0.5),
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
            AttackType.LSPECIAL: (0.0, 0.5),
            AttackType.RSPECIAL: (1.0, 0.5),
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

    def _is_charge_action(self, character: Character, action: Action) -> bool:
        """Return whether ``action`` is a hold-to-charge neutral-B state."""
        if character is Character.MEWTWO:
            return action in _MEWTWO_SHADOW_BALL_CHARGE_ACTIONS
        return action in _SMASH_CHARGE_ACTIONS

    def _observe_smash_charge(self, player: LibPlayerState, hold: Hold) -> None:
        """Advance one hold's smash charge state from a fresh game packet."""
        game_frame = self._game_state.frame
        if hold._smash_last_game_frame is not None and game_frame <= hold._smash_last_game_frame:
            return

        action = self._current_attack_action(player, hold.attack_type)
        previous_action = hold._smash_last_action
        previous_action_frame = hold._smash_last_action_frame
        charge_frames = hold._smash_charge_frames
        charge_complete = hold._smash_charge_complete

        if player.character is Character.NESS and action is _NESS_SMASH_RELEASE_ACTIONS.get(hold.attack_type):
            charge_complete = True
        elif action is None:
            if previous_action is not None:
                charge_complete = True
        elif previous_action is action:
            if (
                player.character is Character.NESS and action is _NESS_SMASH_CHARGE_ACTIONS.get(hold.attack_type)
            ) or previous_action_frame == player.action_frame:
                charge_frames += 1
            elif (
                charge_frames > 0 and previous_action_frame is not None and player.action_frame > previous_action_frame
            ):
                charge_complete = True

        # DESNOTE(jbarber, 2026-08-24): Common smashes freeze their animation
        # frame only while SmashAttr is Charging; Ness instead enters dedicated
        # up/down-smash charge and release states. Count those observations
        # rather than sequence time so startup never consumes the 60-tick cap.
        # See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/ft_0DF0.c#L50-L164
        object.__setattr__(hold, "_smash_charge_frames", charge_frames)
        object.__setattr__(hold, "_smash_last_action", action)
        object.__setattr__(
            hold,
            "_smash_last_action_frame",
            player.action_frame if action is not None else None,
        )
        object.__setattr__(hold, "_smash_last_game_frame", game_frame)
        object.__setattr__(hold, "_smash_charge_complete", charge_complete)

    def _charge_completed(self, player: LibPlayerState, hold: Hold) -> bool:
        """Return whether a charging hold finished and the attack animation started."""
        if not isinstance(player.action, Action):
            return False
        if self._is_charge_action(player.character, player.action):
            return False
        return player.action in _actions_for_attack_type(
            player.character,
            hold.attack_type,
        )


__all__ = [
    "AttackFrameData",
    "AttackType",
    "CharacterState",
    "CharacterStatus",
    "GroundDodgeStickReferenceAxis",
    "Hold",
    "HorizontalStickReferenceAxis",
    "LedgeRecoveryOption",
    "MIN_SHIELD",
    "SimpleControls",
    "StickReferenceAxis",
    # Re-exported from melee.bot.character_state for backward compatibility with
    # callers that imported these names from melee.bot.simple_controls.
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
    "is_grabbed",
    "is_grabbing",
    "is_grabbing_ledge",
    "is_shielding",
    "is_shield_broken",
    "is_taunting",
    "neutral_b_is_chargeable",
    "stick_coordinates",
    "z_air_is_supported",
]
