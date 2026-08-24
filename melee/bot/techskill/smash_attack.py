"""Caller-controlled charged smash-attack input montage."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum, auto
from typing import Final, Self

from melee.bot.character_state import AttackType, CharacterState, _actions_for_attack_type
from melee.bot.input_montage import Abort, InputMontage, MontageState
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

_ATTACK_BY_AXIS: Final[dict[StickReferenceAxis, AttackType]] = {
    StickReferenceAxis.UP: AttackType.USMASH,
    StickReferenceAxis.DOWN: AttackType.DSMASH,
    StickReferenceAxis.LEFT: AttackType.LSMASH,
    StickReferenceAxis.RIGHT: AttackType.RSMASH,
}
_GAME_MAX_CHARGE_FRAMES: Final = 60
_GAME_MAX_POWER_MULTIPLIER: Final = 1.3671
_STARTUP_FRAME_ALLOWANCE: Final = 30
_LIFECYCLE_FRAME_OVERHEAD: Final = 4
_NESS_EXPLICIT_CHARGE_ACTIONS: Final[dict[AttackType, Action]] = {
    AttackType.USMASH: Action(343),
    AttackType.DSMASH: Action(346),
}
_NESS_EXPLICIT_RELEASE_ACTIONS: Final[dict[AttackType, Action]] = {
    AttackType.USMASH: Action(344),
    AttackType.DSMASH: Action(347),
}


class _SmashAttackPhase(Enum):
    Charging = auto()
    Released = auto()
    Started = auto()


@dataclass(frozen=True)
class _SmashAttackState:
    phase: _SmashAttackPhase = _SmashAttackPhase.Charging
    hold: Hold | None = None
    frame_data: AttackFrameData | None = None
    charge_frames: int = 0
    release_wait_frames: int = 0
    last_action: Action | None = None
    last_action_frame: int | None = None
    last_game_frame: int | None = None


def _validate_max_charge_frames(max_charge_frames: int) -> None:
    if max_charge_frames == 1 or not 0 <= max_charge_frames <= _GAME_MAX_CHARGE_FRAMES:
        raise ValueError("max_charge_frames must be 0 or between 2 and 60")


class SmashAttackMontage(StatefulInputMontage[_SmashAttackState]):
    """Perform one caller-timed, absolute-direction charged smash.

    ``axis`` maps up, down, left, and right to ``USMASH``, ``DSMASH``,
    ``LSMASH``, and ``RSMASH`` respectively. ``max_charge_frames`` is the
    maximum number of observed in-game charge ticks for which this montage keeps
    A+stick held; advancing startup animation frames do not count. It must be
    0 or from 2 through Melee's 60-frame maximum. Passing 0
    requests the minimum possible charge: the initial A+stick frame is still
    committed, then the montage releases it on the following tick.

    A one-frame charge cannot be requested because ``PlayerState`` does not expose
    the engine counter or charge-window entry before the first charged frame has
    already occurred. Rejecting 1 avoids silently producing a two-frame charge.

    Call :meth:`release_charge` at any time before automatic release to request
    an earlier release. The request is sticky and idempotent. It does not mutate
    controller state immediately; the next active :meth:`InputMontage.tick`
    releases the stored :class:`Hold`. This queued contract lets a pre-tick
    listener choose release timing without flushing or issuing a second input in
    the same game frame. Calling it before the first tick still commits the
    required initial smash input and releases on the first safe later tick.

    The montage succeeds only after a later ``PlayerState`` confirms the smash
    action. Callers must retain and tick the returned montage, and must return
    from their frame policy after every montage tick so no fallback input
    overwrites the pending charge or release command.

    Args:
        axis: Absolute screen direction for the smash input.
        max_charge_frames: Maximum engine charge ticks, either 0 (minimum charge)
            or from 2 through 60 (Melee's maximum).

    Raises:
        ValueError: If ``max_charge_frames`` is 1 or outside the inclusive range
            0 through 60.
    """

    def __init__(
        self,
        axis: StickReferenceAxis,
        max_charge_frames: int = _GAME_MAX_CHARGE_FRAMES,
    ) -> None:
        _validate_max_charge_frames(max_charge_frames)
        super().__init__(
            max_charge_frames + _STARTUP_FRAME_ALLOWANCE + _LIFECYCLE_FRAME_OVERHEAD,
            _SmashAttackState(),
        )
        self._axis = axis
        self._attack_type = _ATTACK_BY_AXIS[axis]
        self._max_charge_frames = max_charge_frames
        self._release_requested = False

    def release_charge(self) -> Self:
        """Request release on the next active tick and return ``self``.

        This method records intent only. It is safe to call before the montage
        starts, from a pre-tick listener, or repeatedly. The next active tick
        after the initial smash input exists calls :meth:`SimpleControls.release`;
        it never uses montage cancellation as an attack-release mechanism.

        Calling this method after release or terminal completion has no effect.
        Use :meth:`InputMontage.cancel` only to abandon the sequence entirely;
        cancellation neutralizes input and does not perform the smash.
        """
        if (
            self.get_montage_state() in {MontageState.Waiting, MontageState.Active}
            and self._input_state.phase is _SmashAttackPhase.Charging
        ):
            self._release_requested = True
        return self

    def current_power(self) -> float:
        """Return the smash's current damage multiplier.

        The multiplier begins at ``1.0`` before charging and increases linearly
        with observed montage charge ticks to Melee's ``1.3671`` maximum after
        60 ticks. Releasing or finishing freezes the returned value at the power
        accumulated before release.
        """
        charge_ratio = min(self._input_state.charge_frames, _GAME_MAX_CHARGE_FRAMES) / _GAME_MAX_CHARGE_FRAMES
        return 1.0 + charge_ratio * (_GAME_MAX_POWER_MULTIPLIER - 1.0)

    def get_framedata(self) -> AttackFrameData | None:
        """Return requested/observed smash framedata once initiation succeeds."""
        return self._input_state.frame_data

    def can_start(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> bool:
        del controls, opponent_state, state
        return player_state.can_attack(self._attack_type)

    def stateful_should_abort(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _SmashAttackState,
    ) -> Abort | None:
        del controls, opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None:
            return Abort("player state became unavailable")
        if input_state.hold is not None and player_state_value.character is not input_state.hold.character:
            return Abort("player character changed")
        if player_state_value.off_stage:
            return Abort("player moved offstage")
        automatic_full_charge_release = (
            input_state.phase is _SmashAttackPhase.Charging
            and isinstance(player_state_value.action, Action)
            and self._is_automatic_full_charge_release(
                input_state,
                player_state_value.action,
                player_state_value.action_frame,
                player_state_value.character,
            )
        )
        if is_interrupted(
            player_state,
            player_state_value,
            include_hitlag=(input_state.phase is _SmashAttackPhase.Charging and not automatic_full_charge_release),
        ):
            return Abort("player was interrupted")
        return None

    def stateful_on_tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _SmashAttackState,
    ) -> tuple[_SmashAttackState, InputMontage | bool | Abort]:
        del opponent_state
        player_state_value = player(player_state)
        if player_state_value is None:
            return input_state, Abort("player state became unavailable")

        match input_state.phase:
            case _SmashAttackPhase.Charging if input_state.hold is None:
                result = controls.attack(self._attack_type)
                if not isinstance(result, Hold):
                    return input_state, Abort("smash attack input was not accepted")
                frame_data = AttackFrameData(
                    character=result.character,
                    action=result.action,
                    frame_data=result.frame_data,
                )
                return replace(input_state, hold=result, frame_data=frame_data), self
            case _SmashAttackPhase.Charging:
                hold = input_state.hold
                if hold is None:
                    return input_state, Abort("smash attack hold became unavailable")
                if isinstance(player_state_value.action, Action) and self._is_automatic_full_charge_release(
                    input_state,
                    player_state_value.action,
                    player_state_value.action_frame,
                    player_state_value.character,
                ):
                    controls.release_all()
                    started_state = replace(
                        input_state,
                        phase=_SmashAttackPhase.Started,
                        frame_data=AttackFrameData(
                            character=player_state_value.character,
                            action=player_state_value.action,
                            frame_data=hold.frame_data,
                        ),
                        charge_frames=_GAME_MAX_CHARGE_FRAMES,
                    )
                    return self._after_smash_started(
                        controls,
                        player_state,
                        started_state,
                    )

                if self._release_requested or self._max_charge_frames == 0:
                    result = controls.release(hold)
                    if not isinstance(result, AttackFrameData):
                        return input_state, Abort("smash attack could not be released")
                    return (
                        replace(
                            input_state,
                            phase=_SmashAttackPhase.Released,
                            frame_data=result,
                        ),
                        self,
                    )

                result = controls.attack(self._attack_type, hold=hold)
                if isinstance(result, AttackFrameData):
                    charge_frames = input_state.charge_frames
                    observed_charge_tick = self._is_observed_charge_tick(
                        input_state,
                        state.frame,
                        result.action,
                        player_state_value.action_frame,
                        player_state_value.character,
                    )
                    if observed_charge_tick:
                        charge_frames += 1
                    projected_charge_frames = charge_frames + 1
                    if observed_charge_tick and projected_charge_frames >= self._max_charge_frames:
                        release_result = controls.release(hold)
                        if not isinstance(release_result, AttackFrameData):
                            return input_state, Abort("smash attack could not be released")
                        return (
                            replace(
                                input_state,
                                phase=_SmashAttackPhase.Released,
                                frame_data=release_result,
                                charge_frames=projected_charge_frames,
                                last_action=result.action,
                                last_action_frame=player_state_value.action_frame,
                                last_game_frame=state.frame,
                            ),
                            self,
                        )
                    controls.release_all()
                    controls.tilt_stick(self._axis, 0.0)
                    controls.press_button(Button.BUTTON_A)
                    return (
                        replace(
                            input_state,
                            frame_data=result,
                            charge_frames=charge_frames,
                            last_action=result.action,
                            last_action_frame=player_state_value.action_frame,
                            last_game_frame=state.frame,
                        ),
                        self,
                    )
                if isinstance(result, Hold):
                    return (
                        replace(
                            input_state,
                            hold=result,
                        ),
                        self,
                    )
                return input_state, Abort("smash attack could not continue charging")
            case _SmashAttackPhase.Released:
                if isinstance(
                    player_state_value.action, Action
                ) and player_state_value.action in _actions_for_attack_type(
                    player_state_value.character, self._attack_type
                ):
                    started_state = replace(
                        input_state,
                        phase=_SmashAttackPhase.Started,
                    )
                    return self._after_smash_started(
                        controls,
                        player_state,
                        started_state,
                    )
                if input_state.release_wait_frames < 1:
                    return (
                        replace(
                            input_state,
                            release_wait_frames=input_state.release_wait_frames + 1,
                        ),
                        self,
                    )
                return input_state, Abort("released smash attack did not start")
            case _SmashAttackPhase.Started:
                return self._after_smash_started(
                    controls,
                    player_state,
                    input_state,
                )

    def _is_observed_charge_tick(
        self,
        input_state: _SmashAttackState,
        game_frame: int,
        action: Action,
        action_frame: int,
        character: Character,
    ) -> bool:
        # DESNOTE(jbarber, 2026-08-23): Common smashes stop animation advancement
        # while SmashAttr is Charging, so repeated action frames distinguish the
        # charge window from startup. Ness instead enters dedicated up/down-smash
        # charge states. See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/ft_0DF0.c#L50-L164
        if input_state.last_game_frame is None or game_frame <= input_state.last_game_frame:
            return False
        if input_state.last_action is not action:
            return False
        if character is Character.NESS and _NESS_EXPLICIT_CHARGE_ACTIONS.get(self._attack_type) is action:
            return True
        return input_state.last_action_frame == action_frame

    def _is_automatic_full_charge_release(
        self,
        input_state: _SmashAttackState,
        action: Action,
        action_frame: int,
        character: Character,
    ) -> bool:
        if input_state.charge_frames == 0:
            return False
        if character is Character.NESS:
            return _NESS_EXPLICIT_RELEASE_ACTIONS.get(self._attack_type) is action
        return (
            input_state.last_action is action
            and input_state.last_action_frame is not None
            and action_frame > input_state.last_action_frame
        )

    def _after_smash_started(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        input_state: _SmashAttackState,
    ) -> tuple[_SmashAttackState, InputMontage | bool | Abort]:
        """Internal continuation point after the released smash is observed."""
        del controls, player_state
        return input_state, True


__all__ = ["SmashAttackMontage"]
