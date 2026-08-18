"""Frame-perfect grounded attack out of an initial dash."""

from __future__ import annotations

from melee.bot.character_state import AttackType, CharacterState
from melee.bot.input_montage import InputMontage
from melee.bot.simple_controls import SimpleControls, StickReferenceAxis
from melee.bot.techskill.common import is_interrupted, player
from melee.enums import Action, Character
from melee.gamestate import GameState


class PerfectPivotMontage(InputMontage):
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
        super().__init__(frame_limit, cancel_montage)
        if not isinstance(attack_type, AttackType):
            raise ValueError("attack_type must be an AttackType")
        self._attack_type = attack_type
        self._turn_requested = False
        self._attack_requested = False
        self._character: Character | None = None
        self._initial_facing: bool | None = None

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
        self._initial_facing = player_state_value.facing
        return True

    def should_abort(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> bool:
        del controls, opponent_state, state
        if self._attack_requested:
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

    def on_tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> InputMontage | bool:
        del opponent_state, state
        if self._attack_requested:
            controls.release_all()
            return True

        player_state_value = player(player_state)
        if player_state_value is None or self._initial_facing is None:
            return False

        if not self._turn_requested:
            if player_state_value.action is not Action.DASHING:
                return False

            # DESNOTE(jbarber, 2026-08-18): Controller input is committed on the
            # next Console.step, so reverse during DASHING and attack only after
            # TURNING is observable. Melee's smash turn makes that stand-like
            # attack window exactly one frame.
            # See https://www.youtube.com/watch?v=GV2yx9I9IN4 and
            # https://github.com/doldecomp/melee/blob/master/src/melee/ft/chara/ftCommon/ftCo_Turn.c
            controls.release_all()
            reverse = (
                StickReferenceAxis.LEFT
                if self._initial_facing
                else StickReferenceAxis.RIGHT
            )
            controls.tilt_stick(reverse, 0.0)
            self._turn_requested = True
            return self

        if player_state_value.action is not Action.TURNING:
            return False
        if controls.attack(self._attack_type) is None:
            return False
        self._attack_requested = True
        return self


__all__ = ["PerfectPivotMontage"]
