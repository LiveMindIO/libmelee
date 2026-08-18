"""Fox multishine input montage."""

from __future__ import annotations

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
    SecondShineRequested = auto()


def _apply_down_input(controls: SimpleControls, button: Button) -> None:
    controls.release_all()
    controls.tilt_stick(StickReferenceAxis.DOWN, 0.0)
    controls.press_button(button)


class MultishineMontage(StatefulInputMontage[_MultishinePhase]):
    """Perform one Fox multishine cycle, ending when the second shine begins."""

    def __init__(
        self,
        frame_limit: int = 24,
        cancel_montage: InputMontage | None = None,
        *,
        jump_button: Button = Button.BUTTON_Y,
    ) -> None:
        super().__init__(
            frame_limit,
            _MultishinePhase.FirstShineRequested,
            cancel_montage,
        )
        validate_button(
            jump_button,
            frozenset({Button.BUTTON_X, Button.BUTTON_Y}),
            "jump_button",
        )
        self._jump_button = jump_button

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
        input_state: _MultishinePhase,
    ) -> bool:
        del controls, opponent_state, state, input_state
        player_state_value = player(player_state)
        return (
            player_state_value is None
            or player_state_value.character is not Character.FOX
            or player_state_value.off_stage
            or is_interrupted(
                player_state,
                player_state_value,
                include_hitlag=False,
            )
        )

    def stateful_on_tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _MultishinePhase,
    ) -> tuple[_MultishinePhase, InputMontage | bool]:
        del opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None:
            controls.release_all()
            return input_state, False

        match input_state:
            case _MultishinePhase.FirstShineRequested:
                _apply_down_input(controls, Button.BUTTON_B)
                return _MultishinePhase.JumpRequested, self
            case _MultishinePhase.JumpRequested:
                controls.release_all()
                if player_state_value.action in SHINE_ACTIONS:
                    can_jump_cancel = (
                        player_state_value.action is Action.DOWN_B_GROUND
                        or player_state_value.action_frame >= 4
                    )
                    if can_jump_cancel and player_state_value.on_ground:
                        controls.press_button(self._jump_button)
                    return input_state, self
                if player_state_value.action is Action.KNEE_BEND:
                    if (
                        player_state_value.action_frame
                        < JUMP_SQUAT_FRAMES[Character.FOX]
                    ):
                        return input_state, self
                    if (
                        player_state_value.action_frame
                        == JUMP_SQUAT_FRAMES[Character.FOX]
                    ):
                        _apply_down_input(controls, Button.BUTTON_B)
                        return _MultishinePhase.SecondShineRequested, self
                return input_state, False
            case _MultishinePhase.SecondShineRequested:
                controls.release_all()
                if player_state_value.action in SHINE_ACTIONS:
                    return input_state, True
                if player_state_value.action is Action.KNEE_BEND:
                    return input_state, self
                return input_state, False


__all__ = ["MultishineMontage"]
