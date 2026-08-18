"""Fox multishine input montage."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from melee.bot.character_state import CharacterState
from melee.bot.input_montage import InputMontage
from melee.bot.simple_controls import SimpleControls, StickReferenceAxis
from melee.bot.stateful_input_montage import StatefulInputMontage
from melee.bot.techskill.common import (
    JUMP_SQUAT_FRAMES,
    SHINE_ACTIONS,
    is_interrupted,
    player,
    validate_button,
)
from melee.enums import Action, Button, Character
from melee.gamestate import GameState


class _MultishinePhase(Enum):
    FirstShineRequested = auto()
    JumpRequested = auto()
    NextShineRequested = auto()


@dataclass(frozen=True)
class _MultishineState:
    phase: _MultishinePhase
    shines_requested: int


def _apply_down_input(controls: SimpleControls, button: Button) -> None:
    controls.release_all()
    controls.tilt_stick(StickReferenceAxis.DOWN, 0.0)
    controls.press_button(button)


def _apply_jump_cancel_input(
    controls: SimpleControls,
    jump_button: Button,
    action: Action,
    action_frame: int,
    on_ground: bool,
) -> None:
    controls.release_all()
    can_jump_cancel = action is Action.DOWN_B_GROUND or (
        action in {Action.DOWN_B_STUN, Action.DOWN_B_GROUND_START}
        and action_frame >= 4
        and on_ground
    )
    if can_jump_cancel:
        controls.press_button(jump_button)


class MultishineMontage(StatefulInputMontage[_MultishineState]):
    """Perform a configured number of consecutive Fox shines."""

    def __init__(
        self,
        frame_limit: int | None = None,
        cancel_montage: InputMontage | None = None,
        *,
        jump_button: Button = Button.BUTTON_Y,
        shine_count: int = 2,
    ) -> None:
        if isinstance(shine_count, bool) or not isinstance(shine_count, int) or shine_count < 2:
            raise ValueError("shine_count must be an integer greater than or equal to two")
        if frame_limit is None:
            frame_limit = shine_count * 12
        super().__init__(
            frame_limit,
            _MultishineState(_MultishinePhase.FirstShineRequested, 0),
            cancel_montage,
        )
        validate_button(jump_button, frozenset({Button.BUTTON_X, Button.BUTTON_Y}), "jump_button")
        self._jump_button = jump_button
        self._shine_count = shine_count

    def can_start(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> bool:
        del controls, opponent_state, state
        player_state_value = player(player_state)
        return (
            player_state_value is not None
            and player_state_value.character is Character.FOX
            and player_state_value.action is Action.STANDING
            and player_state_value.on_ground
            and not player_state_value.off_stage
        )

    def stateful_should_abort(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _MultishineState,
    ) -> bool:
        del controls, opponent_state, state, input_state
        player_state_value = player(player_state)
        return (
            player_state_value is None
            or player_state_value.character is not Character.FOX
            or player_state_value.off_stage
            or is_interrupted(player_state, player_state_value, include_hitlag=False)
        )

    def stateful_on_tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _MultishineState,
    ) -> tuple[_MultishineState, InputMontage | bool]:
        del opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None:
            controls.release_all()
            return input_state, False

        match input_state.phase, player_state_value.action:
            case _MultishinePhase.FirstShineRequested, _:
                _apply_down_input(controls, Button.BUTTON_B)
                return _MultishineState(_MultishinePhase.JumpRequested, 1), self
            case _MultishinePhase.JumpRequested, Action.STANDING:
                _apply_down_input(controls, Button.BUTTON_B)
                return input_state, self
            case _MultishinePhase.JumpRequested, action if action in SHINE_ACTIONS:
                _apply_jump_cancel_input(
                    controls,
                    self._jump_button,
                    action,
                    player_state_value.action_frame,
                    player_state_value.on_ground,
                )
                return input_state, self
            case _MultishinePhase.JumpRequested, Action.KNEE_BEND:
                controls.release_all()
                if player_state_value.action_frame < JUMP_SQUAT_FRAMES[Character.FOX]:
                    return input_state, self
                if player_state_value.action_frame == JUMP_SQUAT_FRAMES[Character.FOX]:
                    _apply_down_input(controls, Button.BUTTON_B)
                    return (
                        _MultishineState(
                            _MultishinePhase.NextShineRequested,
                            input_state.shines_requested + 1,
                        ),
                        self,
                    )
                return input_state, False
            case _MultishinePhase.NextShineRequested, action if action in SHINE_ACTIONS:
                if input_state.shines_requested >= self._shine_count:
                    controls.release_all()
                    return input_state, True
                _apply_jump_cancel_input(
                    controls,
                    self._jump_button,
                    action,
                    player_state_value.action_frame,
                    player_state_value.on_ground,
                )
                return (
                    _MultishineState(
                        _MultishinePhase.JumpRequested,
                        input_state.shines_requested,
                    ),
                    self,
                )
            case _MultishinePhase.NextShineRequested, Action.STANDING:
                _apply_down_input(controls, Button.BUTTON_B)
                return input_state, self
            case _MultishinePhase.NextShineRequested, Action.KNEE_BEND:
                controls.release_all()
                return input_state, self
            case _:
                controls.release_all()
                return input_state, False


__all__ = ["MultishineMontage"]
