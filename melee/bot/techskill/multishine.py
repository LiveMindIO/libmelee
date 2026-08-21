"""Fox and Falco multishine input montage."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum, auto
from typing import Final

from melee.bot.character_state import AttackType, CharacterState
from melee.bot.input_montage import Abort, InputMontage
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
    FinalShineObserved = auto()


@dataclass(frozen=True)
class _MultishineState:
    phase: _MultishinePhase
    shines_requested: int
    shine_hitlag_left: int = 0
    last_reflector_wait_frame: int | None = None
    reflector_wait_extension: int = 0


# DESNOTE(jbarber, 2026-08-19): Reflecting a projectile enters dedicated hit
# states whose IASA callbacks accept no jump. The hit animation latches a
# release when B is not held, so non-final shines must hold B until the loop
# returns; the end states are already committed to releasing the Reflector.
# See https://github.com/doldecomp/melee/blob/master/src/melee/ft/chara/ftFox/ftFx_SpecialLw.c
_REFLECTOR_HIT_ACTIONS: Final = frozenset(
    {
        Action.REFLECTOR_HIT_GROUND,
        Action.REFLECTOR_HIT_AIR,
    }
)
_REFLECTOR_END_ACTIONS: Final = frozenset(
    {
        Action.REFLECTOR_END_GROUND,
        Action.REFLECTOR_END_AIR,
    }
)
_REFLECTOR_WAIT_ACTIONS: Final = _REFLECTOR_HIT_ACTIONS | _REFLECTOR_END_ACTIONS
_MULTISHINE_CHARACTERS: Final = frozenset({Character.FOX, Character.FALCO})
# DESNOTE(jbarber, 2026-08-23): Fox and Falco share Reflector action IDs and a
# frame-4 jump cancel, but Falco has a five-frame rather than three-frame jump
# squat and its stronger shine can produce more attacker hitlag. Extend by the
# observed hitlag rise and use the character-specific jump-squat table instead
# of encoding Fox's timings.
# See https://github.com/doldecomp/melee/blob/master/src/melee/ft/ftcommon.c and
# https://www.ssbwiki.com/Falco_(SSBM)/Down_special
_DEFAULT_FRAMES_PER_SHINE: Final = 12
_REFLECTOR_WAIT_FRAMES_PER_SHINE: Final = 38


def _apply_down_input(controls: SimpleControls, button: Button) -> None:
    controls.release_all()
    controls.tilt_stick(StickReferenceAxis.DOWN, 0.0)
    controls.press_button(button)


def _hold_reflector_input(controls: SimpleControls) -> None:
    controls.release_all()
    controls.press_button(Button.BUTTON_B)


def _apply_jump_cancel_input(
    controls: SimpleControls,
    jump_button: Button,
    action: Action,
    action_frame: int,
    on_ground: bool,
    hitlag_left: int,
) -> None:
    # DESNOTE(jbarber, 2026-08-19): Reflector startup latches release whenever B
    # is not held. Preserve B while a successful shine freezes Fox in attacker
    # hitlag so startup can still reach its jump-cancelable loop afterward.
    # See ftFx_SpecialLwStart_Anim in
    # https://github.com/doldecomp/melee/blob/master/src/melee/ft/chara/ftFox/ftFx_SpecialLw.c
    if hitlag_left > 0:
        _hold_reflector_input(controls)
        return
    controls.release_all()
    # DESNOTE(jbarber, 2026-08-19): Preserve libmelee's historical on-ground
    # handling for action 0x16D. It tolerates a landed aerial-start packet while
    # the on_ground guard prevents an actual aerial jump request.
    # See https://github.com/altf4/libmelee/blob/master/melee/techskill.py
    can_jump_cancel = action is Action.DOWN_B_GROUND or (
        action in {Action.DOWN_B_GROUND_START, Action.DOWN_B_AIR_START} and action_frame >= 4 and on_ground
    )
    if can_jump_cancel:
        controls.press_button(jump_button)


class MultishineMontage(StatefulInputMontage[_MultishineState]):
    """Perform a configured number of consecutive Fox or Falco shines."""

    def __init__(
        self,
        frame_limit: int | None = None,
        cancel_montage: InputMontage | None = None,
        *,
        jump_button: Button = Button.BUTTON_Y,
        shine_count: int = 2,
    ) -> None:
        if shine_count < 2:
            raise ValueError("shine_count must be greater than or equal to two")
        if frame_limit is None:
            frame_limit = shine_count * _DEFAULT_FRAMES_PER_SHINE
        super().__init__(
            frame_limit,
            _MultishineState(_MultishinePhase.FirstShineRequested, 0),
            cancel_montage,
            name="Multishine",
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
            and player_state_value.character in _MULTISHINE_CHARACTERS
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
        input_state: _MultishineState,
    ) -> Abort | None:
        del controls, opponent_state, state, input_state
        player_state_value = player(player_state)
        if player_state_value is None:
            return Abort("player state became unavailable")
        if player_state_value.character not in _MULTISHINE_CHARACTERS:
            return Abort("player is no longer Fox or Falco")
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
        input_state: _MultishineState,
    ) -> tuple[_MultishineState, InputMontage | bool | Abort]:
        del opponent_state
        player_state_value = player(player_state)
        if player_state_value is None:
            controls.release_all()
            return input_state, Abort("player state became unavailable")

        shine_hitlag_left = player_state_value.hitlag_left if player_state_value.action in SHINE_ACTIONS else 0
        if shine_hitlag_left > input_state.shine_hitlag_left:
            self._frame_limit += shine_hitlag_left - input_state.shine_hitlag_left
        input_state = replace(input_state, shine_hitlag_left=shine_hitlag_left)

        if (
            player_state_value.action in _REFLECTOR_WAIT_ACTIONS
            and (input_state.last_reflector_wait_frame is None or state.frame > input_state.last_reflector_wait_frame)
            and input_state.reflector_wait_extension < self._shine_count * _REFLECTOR_WAIT_FRAMES_PER_SHINE
        ):
            # DESNOTE(jbarber, 2026-08-24): Reflector hit/end IASAs are empty,
            # so these unavoidable animations must not consume the normal
            # multishine safety budget. Extend only for fresh game frames so a
            # replayed packet cannot make a stuck montage unbounded.
            # See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftFox/ftFx_SpecialLw.c#L691-L746
            self._frame_limit += 1
            input_state = replace(
                input_state,
                last_reflector_wait_frame=state.frame,
                reflector_wait_extension=input_state.reflector_wait_extension + 1,
            )

        match input_state.phase, player_state_value.action:
            case _MultishinePhase.FirstShineRequested, _:
                _apply_down_input(controls, Button.BUTTON_B)
                return replace(input_state, phase=_MultishinePhase.JumpRequested, shines_requested=1), self
            case _MultishinePhase.JumpRequested, Action.STANDING:
                _apply_down_input(controls, Button.BUTTON_B)
                return input_state, self
            case _MultishinePhase.JumpRequested, action if action in _REFLECTOR_HIT_ACTIONS:
                _hold_reflector_input(controls)
                return input_state, self
            case _MultishinePhase.JumpRequested, action if action in _REFLECTOR_END_ACTIONS:
                controls.release_all()
                return input_state, self
            case _MultishinePhase.JumpRequested, action if action in SHINE_ACTIONS:
                _apply_jump_cancel_input(
                    controls,
                    self._jump_button,
                    action,
                    player_state_value.action_frame,
                    player_state_value.on_ground,
                    player_state_value.hitlag_left,
                )
                return input_state, self
            case _MultishinePhase.JumpRequested, Action.KNEE_BEND:
                controls.release_all()
                jump_squat_frames = JUMP_SQUAT_FRAMES[player_state_value.character]
                if player_state_value.action_frame < jump_squat_frames:
                    return input_state, self
                if player_state_value.action_frame == jump_squat_frames:
                    _apply_down_input(controls, Button.BUTTON_B)
                    return (
                        replace(
                            input_state,
                            phase=_MultishinePhase.NextShineRequested,
                            shines_requested=input_state.shines_requested + 1,
                        ),
                        self,
                    )
                return input_state, Abort(
                    f"{player_state_value.character.name.title()} passed the final jump-squat frame"
                )
            case _MultishinePhase.NextShineRequested, action if action in _REFLECTOR_HIT_ACTIONS:
                if input_state.shines_requested >= self._shine_count:
                    controls.release_all()
                    return (
                        replace(input_state, phase=_MultishinePhase.FinalShineObserved),
                        self,
                    )
                _hold_reflector_input(controls)
                return input_state, self
            case _MultishinePhase.NextShineRequested, action if action in _REFLECTOR_END_ACTIONS:
                controls.release_all()
                if input_state.shines_requested >= self._shine_count:
                    return (
                        replace(input_state, phase=_MultishinePhase.FinalShineObserved),
                        self,
                    )
                return input_state, self
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
                    player_state_value.hitlag_left,
                )
                return (
                    replace(input_state, phase=_MultishinePhase.JumpRequested),
                    self,
                )
            case _MultishinePhase.NextShineRequested, Action.STANDING:
                _apply_down_input(controls, Button.BUTTON_B)
                return input_state, self
            case _MultishinePhase.NextShineRequested, Action.KNEE_BEND:
                controls.release_all()
                return input_state, self
            case _MultishinePhase.FinalShineObserved, action if action in _REFLECTOR_WAIT_ACTIONS:
                controls.release_all()
                return input_state, self
            case _MultishinePhase.FinalShineObserved, action if action in SHINE_ACTIONS or action is Action.STANDING:
                controls.release_all()
                return input_state, True
            case _:
                controls.release_all()
                return input_state, Abort("unexpected action for the current multishine phase")


__all__ = ["MultishineMontage"]
