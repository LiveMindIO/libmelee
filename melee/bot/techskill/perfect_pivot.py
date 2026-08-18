"""Frame-perfect grounded attack out of an initial dash."""

from __future__ import annotations

from enum import Enum, auto

from melee.bot.character_state import AttackType, CharacterState
from melee.bot.input_montage import InputMontage
from melee.bot.simple_controls import SimpleControls
from melee.bot.stateful_input_montage import StatefulInputMontage
from melee.bot.techskill.common import is_interrupted, player
from melee.enums import Action, Character
from melee.gamestate import GameState


class _PerfectPivotPhase(Enum):
    Initial = auto()
    TurnRequested = auto()
    AttackRequested = auto()


class PerfectPivotMontage(StatefulInputMontage[_PerfectPivotPhase]):
    """Reverse an initial dash and attack during its one-frame turn state.

    Every :class:`AttackType` is accepted and delegated to
    :meth:`SimpleControls.attack`. The montage aborts if that attack cannot begin
    from the grounded turn state, as with state-dependent dash attacks or throws.
    On the following frame it neutralizes all inputs before reporting success, so
    chargeable attacks are not held unintentionally.

    Use :attr:`AttackType.LSMASH` or :attr:`AttackType.RSMASH` when requesting a
    horizontal smash. The facing-relative :attr:`AttackType.FSMASH` resolves
    against the character's already-reversed facing on the turn frame, which can
    make the intended screen direction unclear.

    Examples::

        pivot_left = PerfectPivotMontage(AttackType.LSMASH)
        pivot_right = PerfectPivotMontage(AttackType.RSMASH)
    """

    def __init__(
        self,
        attack_type: AttackType,
        frame_limit: int = 4,
        cancel_montage: InputMontage | None = None,
    ) -> None:
        super().__init__(frame_limit, _PerfectPivotPhase.Initial, cancel_montage)
        if not isinstance(attack_type, AttackType):
            raise ValueError("attack_type must be an AttackType")
        self._attack_type = attack_type
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
        input_state: _PerfectPivotPhase,
    ) -> bool:
        del controls, opponent_state, state
        if input_state is _PerfectPivotPhase.AttackRequested:
            return False
        player_state_value = player(player_state)
        return (
            player_state_value is None
            or player_state_value.character is not self._character
            or player_state_value.off_stage
            or is_interrupted(
                player_state,
                player_state_value,
                include_hitlag=True,
            )
        )

    def stateful_on_tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _PerfectPivotPhase,
    ) -> tuple[_PerfectPivotPhase, InputMontage | bool]:
        del opponent_state, state
        if input_state is _PerfectPivotPhase.AttackRequested:
            controls.release_all()
            return input_state, True

        player_state_value = player(player_state)
        if player_state_value is None:
            return input_state, False

        match input_state, player_state_value.action:
            case _PerfectPivotPhase.Initial, Action.DASHING:
                # DESNOTE(jbarber, 2026-08-18): Controller input is committed on the
                # next Console.step, so reverse during DASHING and attack only after
                # TURNING is observable. Melee's smash turn makes that stand-like
                # attack window exactly one frame.
                # See https://www.youtube.com/watch?v=GV2yx9I9IN4 and
                # https://github.com/doldecomp/melee/blob/master/src/melee/ft/chara/ftCommon/ftCo_Turn.c
                controls.release_all()
                controls.tilt_stick(player_state.backward_axis(), 0.0)
                return _PerfectPivotPhase.TurnRequested, self
            case _PerfectPivotPhase.TurnRequested, Action.TURNING:
                if controls.attack(self._attack_type) is None:
                    return input_state, False
                return _PerfectPivotPhase.AttackRequested, self
            case _:
                return input_state, False


__all__ = ["PerfectPivotMontage"]
