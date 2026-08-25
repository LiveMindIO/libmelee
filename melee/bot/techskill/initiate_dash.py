"""Grounded dash initiation that leaves horizontal movement held."""

from __future__ import annotations

from enum import Enum, auto

from melee.bot.character_state import CharacterState, HorizontalStickReferenceAxis
from melee.bot.input_montage import Abort, InputMontage
from melee.bot.simple_controls import SimpleControls, StickReferenceAxis
from melee.bot.stateful_input_montage import StatefulInputMontage
from melee.bot.techskill.common import is_interrupted, player
from melee.enums import Action, Character
from melee.gamestate import GameState


class _DashPhase(Enum):
    Initial = auto()
    NeutralRequested = auto()
    DashRequested = auto()


class InitiateDashMontage(StatefulInputMontage[_DashPhase]):
    """Smash the main stick left or right, neutralizing first when needed.

    The montage starts only while grounded and on stage. A player already moving
    in the requested direction receives one neutral reset frame first; a
    stationary player or one moving in the opposite direction skips that frame.

    Successful completion after observing :attr:`Action.DASHING` deliberately
    leaves the main stick held at maximum in ``direction``. This remains true when
    :meth:`InputMontage.tick` returns ``True`` or an eligible montage selected by
    :meth:`InputMontage.add_branch`; a returned continuation is not ticked during
    the completion frame. On a later frame, the caller or continuation must reset
    the stick after the player reaches the desired location.
    """

    def __init__(
        self,
        direction: HorizontalStickReferenceAxis,
        frame_limit: int = 3,
        cancel_montage: InputMontage | None = None,
    ) -> None:
        super().__init__(
            frame_limit,
            _DashPhase.Initial,
            cancel_montage,
            name="Initiate Dash",
        )
        self._direction = direction
        self._character: Character | None = None

    def can_start(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> bool:
        del controls, opponent_state, state
        player_state_value = player(player_state)
        if (
            player_state_value is None
            or not player_state_value.on_ground
            or player_state_value.off_stage
            or is_interrupted(player_state, player_state_value, include_hitlag=True)
        ):
            return False
        self._character = player_state_value.character
        return True

    def stateful_should_abort(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _DashPhase,
    ) -> Abort | None:
        del controls, opponent_state, state, input_state
        player_state_value = player(player_state)
        if player_state_value is None:
            return Abort("player state became unavailable")
        if player_state_value.character is not self._character:
            return Abort("player character changed")
        if not player_state_value.on_ground:
            return Abort("player left the ground before dashing")
        if player_state_value.off_stage:
            return Abort("player moved offstage")
        if is_interrupted(player_state, player_state_value, include_hitlag=True):
            return Abort("player was interrupted")
        return None

    def stateful_on_tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _DashPhase,
    ) -> tuple[_DashPhase, InputMontage | bool | Abort]:
        del opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None:
            return input_state, Abort("player state became unavailable")

        match input_state:
            case _DashPhase.Initial:
                # DESNOTE(jbarber, 2026-08-19): Inputs commit on the next
                # Console.step. Existing same-direction movement needs a neutral
                # reset tick, while stationary or opposite-direction movement can
                # request the full horizontal pulse immediately.
                controls.release_all()
                horizontal_speed = float(player_state_value.speed_ground_x_self)
                moving_in_requested_direction = (
                    self._direction is StickReferenceAxis.RIGHT and horizontal_speed > 0.0
                ) or (self._direction is StickReferenceAxis.LEFT and horizontal_speed < 0.0)
                if moving_in_requested_direction:
                    return _DashPhase.NeutralRequested, self
                controls.tilt_stick(self._direction, 0.0)
                return _DashPhase.DashRequested, self
            case _DashPhase.NeutralRequested:
                controls.release_all()
                controls.tilt_stick(self._direction, 0.0)
                return _DashPhase.DashRequested, self
            case _DashPhase.DashRequested if player_state_value.action is Action.DASHING:
                return input_state, True
            case _:
                return input_state, Abort("dash input did not produce DASHING")


__all__ = ["InitiateDashMontage"]
