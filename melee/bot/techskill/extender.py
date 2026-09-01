"""Samus extended grapple input montage."""

from __future__ import annotations

from enum import Enum, auto
from typing import Final

from melee.bot.character_state import AttackType, CharacterState
from melee.bot.input_montage import Abort, InputMontage, MontageState
from melee.bot.simple_controls import SimpleControls
from melee.bot.stateful_input_montage import StatefulInputMontage
from melee.bot.techskill.common import GROUND_MOVEMENT_ACTIONS, is_interrupted, player
from melee.enums import Action, Button, Character
from melee.gamestate import GameState, PlayerState


class _ExtenderPhase(Enum):
    SetupGrabRequested = auto()
    SetupUpRequested = auto()
    SetupDownRequested = auto()
    SetupSecondUpRequested = auto()
    SetupConfirmRequested = auto()
    SetupRecovery = auto()
    ExtenderGrabRequested = auto()
    ExtenderOut = auto()
    LatchRequested = auto()


_SUCCESSFUL_CATCH_ACTIONS: Final = frozenset(
    {
        Action.GRAB_PULLING,
        Action.GRAB_WAIT,
        Action.GRAB_PULLING_HIGH,
    }
)
_SETUP_FIRST_OBSERVED_FRAME: Final = 7
_LATCH_FIRST_OBSERVED_FRAME: Final = 7
_UNSUPPORTED_RUNNING_GRAB_STARTS: Final = frozenset(
    {
        Action.TURNING_RUN,
        Action.DASHING,
        Action.RUNNING,
        Action.RUN_DIRECT,
        Action.RUN_BRAKE,
    }
)
_SUPPORTED_GRAB_STARTS: Final = GROUND_MOVEMENT_ACTIONS - _UNSUPPORTED_RUNNING_GRAB_STARTS


def _apply_button(controls: SimpleControls, button: Button) -> None:
    controls.release_all()
    controls.press_button(button)


class ExtenderMontage(StatefulInputMontage[_ExtenderPhase]):
    """Activate and use Samus's extended grounded Grapple Beam.

    With ``extender_active=False``, the montage first performs a setup grab and
    schedules D-pad Up, Down, Up, then A for grab frames 8 through 11. The setup
    unlocks the extender until Samus loses a stock but does not lengthen that
    grab, so the montage waits for recovery and starts a second grab. Set
    ``extender_active=True`` when the caller already tracks the unlock for the
    current stock to skip the setup grab.

    ``homing=True`` or :meth:`enable_homing` holds digital L while the actual
    extended beam travels. :meth:`grab` queues one fresh A press on the next
    eligible extender tick. Calls before the beam is out are rejected. Melee
    consumes the first accepted press, so a missed latch cannot be retried during
    the same grab. Extended grapples require this explicit latch input even when
    homing is disabled. :meth:`is_extender_active` exposes the montage's inferred
    per-stock activation state.

    Standard Slippi state does not expose the simulated beam-tip position. The
    caller must therefore decide when to call :meth:`grab`; this montage does not
    infer contact from Samus's position or the generic projectile position.
    """

    def __init__(
        self,
        frame_limit: int = 224,
        cancel_montage: InputMontage | None = None,
        *,
        homing: bool = False,
        extender_active: bool = False,
    ) -> None:
        initial_phase = _ExtenderPhase.ExtenderGrabRequested if extender_active else _ExtenderPhase.SetupGrabRequested
        super().__init__(
            frame_limit,
            initial_phase,
            cancel_montage,
            name="Extender",
        )
        self._homing = homing
        self._grab_requested = False
        self._grab_sent = False
        self._extender_out = False
        self._extender_active = extender_active
        self._starting_stock: int | None = None

    def enable_homing(self) -> bool:
        """Enable homing until the extender's one latch input is committed."""
        if self.get_montage_state() not in {MontageState.Waiting, MontageState.Active} or self._grab_sent:
            return False
        self._homing = True
        return True

    def grab(self) -> bool:
        """Queue one fresh A press after the extended beam has started traveling."""
        if (
            self.get_montage_state() is not MontageState.Active
            or self._input_state is not _ExtenderPhase.ExtenderOut
            or not self._extender_out
            or self._grab_requested
            or self._grab_sent
        ):
            return False
        self._grab_requested = True
        return True

    def is_extender_active(self) -> bool:
        """Return whether this montage established or was given the per-stock unlock."""
        return self._extender_active

    def can_start(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> bool:
        del controls, opponent_state, state
        player_state_value = player(player_state)
        can_start = (
            player_state_value is not None
            and player_state_value.character is Character.SAMUS
            and player_state_value.on_ground
            and not player_state_value.off_stage
            and player_state_value.action in _SUPPORTED_GRAB_STARTS
            and player_state.can_attack(AttackType.GRAB)
        )
        if can_start and player_state_value is not None:
            self._starting_stock = player_state_value.stock
        return can_start

    def stateful_should_abort(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _ExtenderPhase,
    ) -> Abort | None:
        del controls, opponent_state, state, input_state
        player_state_value = player(player_state)
        if player_state_value is None:
            return Abort("player state became unavailable")
        if player_state_value.character is not Character.SAMUS:
            return Abort("player is no longer Samus")
        if self._starting_stock is not None and player_state_value.stock != self._starting_stock:
            self._extender_active = False
            return Abort("Samus stock changed and reset the extender")
        if player_state_value.off_stage or not player_state_value.on_ground:
            return Abort("Samus left the grounded extender route")
        if is_interrupted(player_state, player_state_value, include_hitlag=True):
            return Abort("player was interrupted")
        return None

    def stateful_on_tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _ExtenderPhase,
    ) -> tuple[_ExtenderPhase, InputMontage | bool | Abort]:
        del opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None:
            controls.release_all()
            return input_state, Abort("player state became unavailable")

        match input_state:
            case _ExtenderPhase.SetupGrabRequested:
                return self._tick_setup_start(controls, player_state, player_state_value)
            case _ExtenderPhase.SetupUpRequested:
                return self._tick_setup_input(
                    controls,
                    player_state_value,
                    expected_frame=8,
                    button=Button.BUTTON_D_DOWN,
                    next_phase=_ExtenderPhase.SetupDownRequested,
                )
            case _ExtenderPhase.SetupDownRequested:
                return self._tick_setup_input(
                    controls,
                    player_state_value,
                    expected_frame=9,
                    button=Button.BUTTON_D_UP,
                    next_phase=_ExtenderPhase.SetupSecondUpRequested,
                )
            case _ExtenderPhase.SetupSecondUpRequested:
                return self._tick_setup_input(
                    controls,
                    player_state_value,
                    expected_frame=10,
                    button=Button.BUTTON_A,
                    next_phase=_ExtenderPhase.SetupConfirmRequested,
                )
            case _ExtenderPhase.SetupConfirmRequested:
                controls.release_all()
                if player_state_value.action is not Action.GRAB or player_state_value.action_frame != 11:
                    return input_state, Abort("extender activation confirmation frame was missed")
                self._extender_active = True
                return _ExtenderPhase.SetupRecovery, self
            case _ExtenderPhase.SetupRecovery:
                return self._tick_setup_recovery(controls, player_state, player_state_value)
            case _ExtenderPhase.ExtenderGrabRequested:
                if player_state_value.action is Action.GRAB:
                    return self._tick_extender(
                        controls,
                        _ExtenderPhase.ExtenderOut,
                        player_state_value.action_frame,
                    )
                if player_state_value.action in _SUPPORTED_GRAB_STARTS and player_state.can_attack(AttackType.GRAB):
                    _apply_button(controls, Button.BUTTON_Z)
                    return input_state, self
                controls.release_all()
                return input_state, Abort("extended grab did not begin")
            case _ExtenderPhase.ExtenderOut:
                if player_state_value.action in _SUCCESSFUL_CATCH_ACTIONS:
                    controls.release_all()
                    return input_state, Abort("grab connected without a confirmed extender latch input")
                if player_state_value.action is Action.GRAB:
                    return self._tick_extender(controls, input_state, player_state_value.action_frame)
                controls.release_all()
                if player_state_value.action in GROUND_MOVEMENT_ACTIONS:
                    return input_state, Abort("extender ended without grabbing an opponent")
                return input_state, Abort("extended grab was interrupted")
            case _ExtenderPhase.LatchRequested:
                controls.release_all()
                if player_state_value.action in _SUCCESSFUL_CATCH_ACTIONS:
                    return input_state, True
                if player_state_value.action is Action.GRAB:
                    return input_state, self
                if player_state_value.action in GROUND_MOVEMENT_ACTIONS:
                    return input_state, Abort("extender latch did not grab an opponent")
                return input_state, Abort("extended grab was interrupted after the latch input")

    def _tick_setup_start(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        player_state_value: PlayerState,
    ) -> tuple[_ExtenderPhase, InputMontage | Abort]:
        if player_state_value.action in _SUPPORTED_GRAB_STARTS and player_state.can_attack(AttackType.GRAB):
            _apply_button(controls, Button.BUTTON_Z)
            return _ExtenderPhase.SetupGrabRequested, self
        if player_state_value.action is not Action.GRAB:
            controls.release_all()
            return _ExtenderPhase.SetupGrabRequested, Abort("extender setup grab did not begin")
        if player_state_value.action_frame < _SETUP_FIRST_OBSERVED_FRAME:
            controls.release_all()
            return _ExtenderPhase.SetupGrabRequested, self
        if player_state_value.action_frame > _SETUP_FIRST_OBSERVED_FRAME:
            controls.release_all()
            return _ExtenderPhase.SetupGrabRequested, Abort("extender activation frame-8 input window was missed")

        # Bot input reaches Melee on the next Console.step, so observing grab
        # frames 7-10 schedules Up, Down, Up, and A for game frames 8-11.
        # See https://www.ssbwiki.com/Extended_grapple and
        # https://github.com/doldecomp/melee/blob/master/src/melee/it/items/itsamusgrapple.c
        _apply_button(controls, Button.BUTTON_D_UP)
        return _ExtenderPhase.SetupUpRequested, self

    def _tick_setup_input(
        self,
        controls: SimpleControls,
        player_state_value: PlayerState,
        *,
        expected_frame: int,
        button: Button,
        next_phase: _ExtenderPhase,
    ) -> tuple[_ExtenderPhase, InputMontage | Abort]:
        controls.release_all()
        if player_state_value.action is not Action.GRAB or player_state_value.action_frame != expected_frame:
            return next_phase, Abort("extender activation input sequence was interrupted")
        controls.press_button(button)
        return next_phase, self

    def _tick_setup_recovery(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        player_state_value: PlayerState,
    ) -> tuple[_ExtenderPhase, InputMontage | Abort]:
        controls.release_all()
        if player_state_value.action is Action.GRAB:
            return _ExtenderPhase.SetupRecovery, self
        if player_state_value.action in _SUCCESSFUL_CATCH_ACTIONS:
            return _ExtenderPhase.SetupRecovery, Abort("extender setup grab caught an opponent")
        if player_state_value.action in _SUPPORTED_GRAB_STARTS and player_state.can_attack(AttackType.GRAB):
            controls.press_button(Button.BUTTON_Z)
            return _ExtenderPhase.ExtenderGrabRequested, self
        return _ExtenderPhase.SetupRecovery, Abort("Samus did not recover from the extender setup grab")

    def _tick_extender(
        self,
        controls: SimpleControls,
        continuing_phase: _ExtenderPhase,
        action_frame: int,
    ) -> tuple[_ExtenderPhase, InputMontage]:
        controls.release_all()
        if action_frame >= _LATCH_FIRST_OBSERVED_FRAME:
            self._extender_out = True
        if self._grab_requested and action_frame >= _LATCH_FIRST_OBSERVED_FRAME:
            controls.press_button(Button.BUTTON_A)
            self._grab_requested = False
            self._grab_sent = True
            return _ExtenderPhase.LatchRequested, self
        if self._homing:
            controls.press_button(Button.BUTTON_L)
        return continuing_phase, self


__all__ = ["ExtenderMontage"]
