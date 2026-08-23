"""Link forward-smash double-slash input montage."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum, auto
from typing import Final

from melee.bot.character_state import (
    AttackType,
    CharacterState,
    HorizontalStickReferenceAxis,
)
from melee.bot.input_montage import Abort, InputMontage
from melee.bot.simple_controls import (
    AttackFrameData,
    Hold,
    SimpleControls,
    StickReferenceAxis,
)
from melee.bot.stateful_input_montage import StatefulInputMontage
from melee.bot.techskill.common import is_interrupted, player
from melee.enums import Action, Button, Character
from melee.gamestate import GameState


class _LinkForwardSmashPhase(Enum):
    FirstSlashRequested = auto()
    FirstSlashReleased = auto()
    SecondSlashRequested = auto()


@dataclass(frozen=True)
class _LinkForwardSmashState:
    phase: _LinkForwardSmashPhase
    hold: Hold | None = None


_ATTACK_BY_DIRECTION: Final[dict[HorizontalStickReferenceAxis, AttackType]] = {
    StickReferenceAxis.LEFT: AttackType.LSMASH,
    StickReferenceAxis.RIGHT: AttackType.RSMASH,
}
_FIRST_SLASH_ACTION: Final = Action.FSMASH_MID
_SECOND_SLASH_ACTION: Final = Action(341)
# DESNOTE(jbarber, 2026-08-22): Link's first-slash script opens its continuation
# at frame 19. Controller input queued while observing frame 18 commits on that
# frame; the common IASA path then requires the newly pressed A edge and enters
# Link's character-relative action 341.
# See https://www.ssbwiki.com/Link_(SSBM)/Forward_smash and
# https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/ftattacks4combo.c#L8-L46
_COMBO_REQUEST_FRAME: Final = 18
_DEFAULT_FRAME_LIMIT: Final = 40


class LinkForwardSmashMontage(StatefulInputMontage[_LinkForwardSmashState]):
    """Perform Link's uncharged forward smash and earliest second slash.

    ``direction`` is an absolute screen direction. The montage releases the
    initial smash input on the following game frame, then presses A for exactly
    one input frame while observing frame 18 so it commits on frame 19.
    """

    def __init__(
        self,
        direction: HorizontalStickReferenceAxis,
        frame_limit: int = _DEFAULT_FRAME_LIMIT,
    ) -> None:
        if direction not in _ATTACK_BY_DIRECTION:
            raise ValueError(
                "direction must be StickReferenceAxis.LEFT or StickReferenceAxis.RIGHT"
            )
        super().__init__(
            frame_limit,
            _LinkForwardSmashState(_LinkForwardSmashPhase.FirstSlashRequested),
        )
        self._attack_type = _ATTACK_BY_DIRECTION[direction]

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
            and player_state_value.character is Character.LINK
            and player_state_value.on_ground
            and not player_state_value.off_stage
            and player_state.can_attack(self._attack_type)
        )

    def stateful_should_abort(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _LinkForwardSmashState,
    ) -> Abort | None:
        del controls, opponent_state, state, input_state
        player_state_value = player(player_state)
        if player_state_value is None:
            return Abort("player state became unavailable")
        if player_state_value.character is not Character.LINK:
            return Abort("player is no longer Link")
        if player_state_value.off_stage:
            return Abort("player moved offstage")
        if is_interrupted(player_state, player_state_value, include_hitlag=False):
            return Abort("player was interrupted")
        return None

    def stateful_on_tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _LinkForwardSmashState,
    ) -> tuple[_LinkForwardSmashState, InputMontage | bool | Abort]:
        del opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None:
            controls.release_all()
            return input_state, Abort("player state became unavailable")

        match input_state.phase:
            case _LinkForwardSmashPhase.FirstSlashRequested:
                if input_state.hold is not None:
                    if not isinstance(controls.release(input_state.hold), AttackFrameData):
                        return input_state, Abort(
                            "first forward-smash input could not be released"
                        )
                    return (
                        replace(
                            input_state,
                            phase=_LinkForwardSmashPhase.FirstSlashReleased,
                        ),
                        self,
                    )
                result = controls.attack(self._attack_type)
                if not isinstance(result, Hold):
                    return input_state, Abort(
                        "first forward-smash input was not accepted"
                    )
                return replace(input_state, hold=result), self
            case _LinkForwardSmashPhase.FirstSlashReleased:
                if player_state_value.action is not _FIRST_SLASH_ACTION:
                    controls.release_all()
                    return input_state, Abort("first forward slash did not start")
                controls.release_all()
                if player_state_value.action_frame < _COMBO_REQUEST_FRAME:
                    return input_state, self
                if player_state_value.action_frame > _COMBO_REQUEST_FRAME:
                    return input_state, Abort("earliest second-slash input frame was missed")
                if player_state_value.hitlag_left == 0:
                    controls.press_button(Button.BUTTON_A)
                    return (
                        replace(input_state, phase=_LinkForwardSmashPhase.SecondSlashRequested),
                        self,
                    )
                return input_state, self
            case _LinkForwardSmashPhase.SecondSlashRequested:
                controls.release_all()
                if player_state_value.action is _SECOND_SLASH_ACTION:
                    return input_state, True
                if (
                    player_state_value.action is _FIRST_SLASH_ACTION
                    and player_state_value.action_frame <= _COMBO_REQUEST_FRAME
                ):
                    return input_state, self
                return input_state, Abort("second forward slash did not start")


__all__ = ["LinkForwardSmashMontage"]
