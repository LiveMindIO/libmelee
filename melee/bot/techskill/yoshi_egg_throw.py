"""Caller-aimed Yoshi Egg Throw input montage."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from enum import Enum, auto
from typing import Final, Self

from melee.bot.character_state import AttackType, CharacterState
from melee.bot.input_montage import Abort, InputMontage, MontageState
from melee.bot.simple_controls import SimpleControls, StickReferenceAxis
from melee.bot.stateful_input_montage import StatefulInputMontage
from melee.bot.techskill.common import is_interrupted, player
from melee.enums import Action, Button, Character
from melee.gamestate import GameState


class YoshiEggThrowAim(Enum):
    """Absolute horizontal aim for Yoshi's Egg Throw."""

    LEFT = auto()
    NEUTRAL = auto()
    RIGHT = auto()


class _YoshiEggThrowPhase(Enum):
    StartInput = auto()
    AwaitingAction = auto()
    Throwing = auto()


@dataclass(frozen=True)
class _YoshiEggThrowState:
    phase: _YoshiEggThrowPhase = _YoshiEggThrowPhase.StartInput
    character: Character | None = None
    start_wait_frames: int = 0


_EGG_THROW_ACTIONS: Final = frozenset(
    {
        Action.YOSHI_SPECIAL_HI,
        Action.YOSHI_SPECIAL_AIR_HI,
    }
)
_COMPLETION_ACTIONS: Final = frozenset(
    {
        Action.STANDING,
        Action.FALLING,
        Action.EDGE_CATCHING,
        Action.EDGE_HANGING,
    }
)
_START_WAIT_LIMIT: Final = 3

# DESNOTE(jbarber, 2026-09-09): Egg Throw's animation callback increments its
# private charge only while B is held, but the animation script launches the egg
# independently and samples horizontal stick at that point. Ground/air collision
# transitions preserve the move variables and callback across actions 364/365.
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftYoshi/ftYs_SpecialHi.c


class YoshiEggThrowMontage(StatefulInputMontage[_YoshiEggThrowState]):
    """Aim and charge Yoshi's grounded or aerial Egg Throw.

    Egg Throw begins with cardinal up+B. While its grounded or aerial action is
    active, ``aim`` applies an absolute horizontal main-stick direction at the
    requested stick ``magnitude``. The neutral aim leaves the stick centered, so
    its magnitude has no effect.

    B remains held on every action tick until :meth:`release_charge` is called.
    That sticky request releases B on the next active tick but retains aim through
    the rest of the animation. Releasing B only stops further charge accumulation;
    Egg Throw's animation script still decides when the egg launches. The montage
    intentionally exposes no power estimate because libmelee does not report the
    move's private charge counter.

    Ground-to-air and air-to-ground transitions preserve the montage across
    Yoshi's action states 364 and 365. Completion is reported only after the
    action exits normally to standing, falling, or a ledge catch/hang.
    """

    def __init__(
        self,
        aim: YoshiEggThrowAim = YoshiEggThrowAim.NEUTRAL,
        magnitude: float = 1.0,
        frame_limit: int = 96,
        cancel_montage: InputMontage | None = None,
    ) -> None:
        if not math.isfinite(magnitude) or not 0.0 <= magnitude <= 1.0:
            raise ValueError("magnitude must be finite and between 0 and 1 inclusive")
        super().__init__(
            frame_limit,
            _YoshiEggThrowState(),
            cancel_montage,
            name="Yoshi Egg Throw",
        )
        self._aim = aim
        self._magnitude = magnitude
        self._release_requested = False

    def release_charge(self) -> Self:
        """Stop adding charge on the next active tick and return ``self``.

        The request is sticky and idempotent while the montage is waiting or
        active. It does not launch the egg or alter pending controller input by
        itself.
        """
        if self.get_montage_state() in {MontageState.Waiting, MontageState.Active}:
            self._release_requested = True
        return self

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
            and player_state_value.character is Character.YOSHI
            and player_state.can_attack(AttackType.UP_B)
        )

    def stateful_should_abort(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _YoshiEggThrowState,
    ) -> Abort | None:
        del controls, opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None:
            return Abort("player state became unavailable")
        if input_state.character is not None and player_state_value.character is not input_state.character:
            return Abort("player character changed")
        if is_interrupted(player_state, player_state_value, include_hitlag=False):
            return Abort("player was interrupted")
        return None

    def stateful_on_tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _YoshiEggThrowState,
    ) -> tuple[_YoshiEggThrowState, InputMontage | bool | Abort]:
        del opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None:
            return input_state, Abort("player state became unavailable")

        match input_state.phase:
            case _YoshiEggThrowPhase.StartInput:
                self._apply_start_input(controls)
                return (
                    replace(
                        input_state,
                        phase=_YoshiEggThrowPhase.AwaitingAction,
                        character=player_state_value.character,
                    ),
                    self,
                )
            case _YoshiEggThrowPhase.AwaitingAction:
                if player_state_value.action in _EGG_THROW_ACTIONS:
                    self._apply_throw_input(controls)
                    return replace(input_state, phase=_YoshiEggThrowPhase.Throwing), self
                if (
                    input_state.start_wait_frames < _START_WAIT_LIMIT
                    and player_state.can_attack(AttackType.UP_B)
                ):
                    self._apply_start_input(controls)
                    return replace(input_state, start_wait_frames=input_state.start_wait_frames + 1), self
                return input_state, Abort("Yoshi Egg Throw did not start")
            case _YoshiEggThrowPhase.Throwing:
                if player_state_value.action in _EGG_THROW_ACTIONS:
                    self._apply_throw_input(controls)
                    return input_state, self
                if player_state_value.action in _COMPLETION_ACTIONS:
                    controls.release_all()
                    return input_state, True
                return input_state, Abort("Yoshi Egg Throw was interrupted")

    @staticmethod
    def _apply_start_input(controls: SimpleControls) -> None:
        controls.release_all()
        controls.tilt_stick(StickReferenceAxis.UP, 0.0)
        controls.press_button(Button.BUTTON_B)

    def _apply_throw_input(self, controls: SimpleControls) -> None:
        controls.release_all()
        match self._aim:
            case YoshiEggThrowAim.LEFT:
                controls.tilt_stick(StickReferenceAxis.LEFT, 0.0, magnitude=self._magnitude)
            case YoshiEggThrowAim.NEUTRAL:
                pass
            case YoshiEggThrowAim.RIGHT:
                controls.tilt_stick(StickReferenceAxis.RIGHT, 0.0, magnitude=self._magnitude)
        if not self._release_requested:
            controls.press_button(Button.BUTTON_B)


__all__ = ["YoshiEggThrowAim", "YoshiEggThrowMontage"]
