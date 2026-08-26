"""Samus grounded super wavedash input montage."""

from __future__ import annotations

from enum import Enum, auto
from typing import Final

from melee.bot.character_state import AttackType, CharacterState
from melee.bot.input_montage import Abort, InputMontage
from melee.bot.simple_controls import SimpleControls, StickReferenceAxis
from melee.bot.stateful_input_montage import StatefulInputMontage
from melee.bot.techskill.common import (
    GROUND_MOVEMENT_ACTIONS,
    WavedashDirection,
    is_interrupted,
    player,
)
from melee.enums import Action, Button, Character
from melee.gamestate import GameState, PlayerState


class _SuperWavedashPhase(Enum):
    BombRequested = auto()
    OppositeRequested = auto()
    DesiredRequested = auto()
    NeutralRequested = auto()


_BOMB_ACTIONS: Final = frozenset(
    {
        Action.SAMUS_SPECIAL_LW_BOMB,
        Action.SAMUS_SPECIAL_AIR_LW_BOMB,
    }
)


def _apply_bomb_input(controls: SimpleControls) -> None:
    controls.release_all()
    controls.tilt_stick(StickReferenceAxis.DOWN, 0.0)
    controls.press_button(Button.BUTTON_B)


def _apply_horizontal_input(
    controls: SimpleControls,
    direction: WavedashDirection,
) -> None:
    controls.release_all()
    axis = StickReferenceAxis.RIGHT if direction is WavedashDirection.Right else StickReferenceAxis.LEFT
    controls.tilt_stick(axis, 0.0)


class SuperWavedashMontage(StatefulInputMontage[_SuperWavedashPhase]):
    """Perform Samus's standard grounded super wavedash.

    ``direction`` is the desired travel direction. The montage starts grounded
    down-B, requests the opposite direction while observing bomb animation frame
    40, requests the travel direction on frame 41, and neutralizes on frame 42.
    Those pending inputs reach Melee on animation frames 41, 42, and 43.

    This supports standing and crouched bomb starts. Crouching skips the first two
    displayed animation frames but reaches the same frame-41/frame-42 input window.
    The height-dependent falling variant is intentionally outside this montage.
    """

    def __init__(
        self,
        direction: WavedashDirection,
        frame_limit: int = 64,
        cancel_montage: InputMontage | None = None,
    ) -> None:
        super().__init__(
            frame_limit,
            _SuperWavedashPhase.BombRequested,
            cancel_montage,
            name="Super Wavedash",
        )
        self._direction = direction

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
            and player_state_value.character is Character.SAMUS
            and player_state_value.on_ground
            and not player_state_value.off_stage
            and player_state.can_attack(AttackType.DOWN_B)
        )

    def stateful_should_abort(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _SuperWavedashPhase,
    ) -> Abort | None:
        del controls, opponent_state, state, input_state
        player_state_value = player(player_state)
        if player_state_value is None:
            return Abort("player state became unavailable")
        if player_state_value.character is not Character.SAMUS:
            return Abort("player is no longer Samus")
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
        input_state: _SuperWavedashPhase,
    ) -> tuple[_SuperWavedashPhase, InputMontage | bool | Abort]:
        del opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None:
            controls.release_all()
            return input_state, Abort("player state became unavailable")

        match input_state:
            case _SuperWavedashPhase.BombRequested:
                if player_state_value.action in _BOMB_ACTIONS:
                    return self._tick_bomb_window(controls, player_state_value)
                if player_state_value.on_ground and player_state.can_attack(AttackType.DOWN_B):
                    _apply_bomb_input(controls)
                    return input_state, self
                controls.release_all()
                return input_state, Abort("grounded bomb did not begin")
            case _SuperWavedashPhase.OppositeRequested:
                if player_state_value.action not in _BOMB_ACTIONS or player_state_value.action_frame != 41:
                    controls.release_all()
                    return input_state, Abort("frame-42 direction window was missed")
                if not player_state_value.on_ground:
                    controls.release_all()
                    return input_state, Abort("Samus was airborne during the frame-42 direction window")
                _apply_horizontal_input(controls, self._direction)
                return _SuperWavedashPhase.DesiredRequested, self
            case _SuperWavedashPhase.DesiredRequested:
                controls.release_all()
                if player_state_value.action not in _BOMB_ACTIONS or player_state_value.action_frame != 42:
                    return input_state, Abort("post-input neutral frame was missed")
                return _SuperWavedashPhase.NeutralRequested, self
            case _SuperWavedashPhase.NeutralRequested:
                controls.release_all()
                if player_state_value.action in _BOMB_ACTIONS:
                    return input_state, self
                if player_state_value.on_ground and player_state_value.action in GROUND_MOVEMENT_ACTIONS:
                    return input_state, True
                return input_state, Abort("bomb ended outside actionable ground movement")

    def _tick_bomb_window(
        self,
        controls: SimpleControls,
        player_state_value: PlayerState,
    ) -> tuple[_SuperWavedashPhase, InputMontage | Abort]:
        if player_state_value.action_frame < 40:
            controls.release_all()
            return _SuperWavedashPhase.BombRequested, self
        if player_state_value.action_frame > 40:
            controls.release_all()
            return _SuperWavedashPhase.BombRequested, Abort("frame-41 opposite-direction window was missed")
        if not player_state_value.on_ground:
            controls.release_all()
            return _SuperWavedashPhase.BombRequested, Abort(
                "Samus was airborne during the frame-41 opposite-direction window"
            )

        # DESNOTE(jbarber, 2026-08-26): Bot input is committed by the next
        # Console.step. Observed animation frames 40 and 41 therefore schedule
        # the opposite/desired inputs for Samus bomb frames 41 and 42. A crouched
        # bomb begins its displayed animation two frames later but uses the same
        # underlying animation-frame window.
        # See https://www.ssbwiki.com/Super_wavedash and
        # https://github.com/doldecomp/melee/blob/master/src/melee/ft/chara/ftSamus/ftSs_SpecialLw_1.c
        opposite = WavedashDirection.Left if self._direction is WavedashDirection.Right else WavedashDirection.Right
        _apply_horizontal_input(controls, opposite)
        return _SuperWavedashPhase.OppositeRequested, self


__all__ = ["SuperWavedashMontage"]
