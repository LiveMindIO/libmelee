"""Momentum-preserving reversed jump that transfers ownership of held jump.

``SmashTurnJumpMontage`` deliberately finishes with its configured X/Y button
held. The caller or selected branch must continue or release that input.
"""

from __future__ import annotations

from enum import Enum, auto

from melee.bot.character_state import CharacterState
from melee.bot.input_montage import Abort, InputMontage
from melee.bot.simple_controls import SimpleControls
from melee.bot.stateful_input_montage import StatefulInputMontage
from melee.bot.techskill.common import is_interrupted, player, validate_button
from melee.enums import Action, Button, Character
from melee.gamestate import GameState


class _SmashTurnJumpPhase(Enum):
    Initial = auto()
    TurnRequested = auto()
    JumpRequested = auto()


class SmashTurnJumpMontage(StatefulInputMontage[_SmashTurnJumpPhase]):
    """Reverse an initial dash, then jump with the retained dash momentum.

    A smash turn jump and a perfect pivot jump are two names for this same
    technique.

    The one-frame smash turn reverses facing before jump squat begins. Horizontal
    momentum continues in the original dash direction, allowing movement with the
    character's back toward that direction for setups such as back aerials.

    Success leaves ``jump_button`` held in the controller's pending state. This is
    true whether :meth:`InputMontage.tick` returns ``True`` or returns a montage
    selected through :meth:`InputMontage.add_branch`. The selected branch is not
    ticked in that completion frame. On the next frame, the caller or branch must
    deliberately keep holding or release jump for the desired short-hop or
    full-hop timing; this montage never releases a successful jump.
    """

    def __init__(
        self,
        frame_limit: int = 4,
        cancel_montage: InputMontage | None = None,
        *,
        jump_button: Button = Button.BUTTON_Y,
    ) -> None:
        """Configure the pivot jump and the button left held on success.

        Args:
            frame_limit: Maximum active montage ticks before timeout.
            cancel_montage: Optional fallback returned when actively cancelled.
            jump_button: X or Y button pressed for the jump and intentionally left
                held for the caller or selected branch to manage after success.
        """
        super().__init__(frame_limit, _SmashTurnJumpPhase.Initial, cancel_montage)
        validate_button(
            jump_button,
            frozenset({Button.BUTTON_X, Button.BUTTON_Y}),
            "jump_button",
        )
        self._jump_button = jump_button
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
            or player_state_value.action is not Action.DASHING
            or not player_state_value.on_ground
            or player_state_value.off_stage
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
        input_state: _SmashTurnJumpPhase,
    ) -> Abort | None:
        del controls, opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None:
            return Abort("player state became unavailable")
        if player_state_value.character is not self._character:
            return Abort("player character changed")
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
        input_state: _SmashTurnJumpPhase,
    ) -> tuple[_SmashTurnJumpPhase, InputMontage | bool | Abort]:
        del opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None:
            return input_state, Abort("player state became unavailable")

        match input_state, player_state_value.action:
            case _SmashTurnJumpPhase.Initial, Action.DASHING:
                # DESNOTE(jbarber, 2026-08-18): A full backward input reverses
                # facing on turn frame 1. Jumping on that frame retains the dash's
                # momentum while beginning jump squat with the reversed facing.
                # See https://www.ssbwiki.com/Turn#Smash_turn
                controls.release_all()
                controls.smash_turn()
                return _SmashTurnJumpPhase.TurnRequested, self
            case _SmashTurnJumpPhase.TurnRequested, Action.TURNING:
                controls.release_all()
                controls.press_button(self._jump_button)
                return _SmashTurnJumpPhase.JumpRequested, self
            case _SmashTurnJumpPhase.JumpRequested, Action.KNEE_BEND:
                return input_state, True
            case _:
                return input_state, Abort("turn or jump-squat confirmation was missed")


__all__ = ["SmashTurnJumpMontage"]
