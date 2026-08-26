"""Double jump cancel aerial input montage."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum, auto
from typing import Final

from melee.bot.character_state import AttackType, CharacterState
from melee.bot.input_montage import Abort, InputMontage
from melee.bot.simple_controls import AttackFrameData, Hold, SimpleControls
from melee.bot.stateful_input_montage import StatefulInputMontage
from melee.bot.techskill.common import is_interrupted, player, validate_button
from melee.enums import Action, Button, Character
from melee.gamestate import GameState


class _DoubleJumpCancelPhase(Enum):
    Initial = auto()
    FirstJumpRequested = auto()
    AirJumpReady = auto()
    AirJumpRequested = auto()
    AttackPending = auto()


@dataclass(frozen=True)
class _DoubleJumpCancelState:
    phase: _DoubleJumpCancelPhase
    hold: Hold | None = None


_DOUBLE_JUMP_CANCEL_CHARACTERS: Final = frozenset(
    {
        Character.YOSHI,
        Character.NESS,
        Character.PEACH,
        Character.MEWTWO,
    }
)
_AERIAL_ATTACKS: Final = frozenset(
    {
        AttackType.NAIR,
        AttackType.FAIR,
        AttackType.BAIR,
        AttackType.UAIR,
        AttackType.DAIR,
    }
)
_ACTIONS_FOR_AERIAL: Final[dict[AttackType, frozenset[Action]]] = {
    AttackType.NAIR: frozenset({Action.NAIR, Action.NAIR_LANDING}),
    AttackType.FAIR: frozenset({Action.FAIR, Action.FAIR_LANDING}),
    AttackType.BAIR: frozenset({Action.BAIR, Action.BAIR_LANDING}),
    AttackType.UAIR: frozenset({Action.UAIR, Action.UAIR_LANDING}),
    AttackType.DAIR: frozenset({Action.DAIR, Action.DAIR_LANDING}),
}
_FIRST_JUMP_ACTIONS: Final = frozenset(
    {
        Action.JUMPING_FORWARD,
        Action.JUMPING_BACKWARD,
    }
)
_AERIAL_JUMP_ACTIONS: Final = frozenset(
    {
        Action.JUMPING_ARIAL_FORWARD,
        Action.JUMPING_ARIAL_BACKWARD,
    }
)


class DoubleJumpCancelMontage(StatefulInputMontage[_DoubleJumpCancelState]):
    """Double jump and cancel its momentum with an aerial attack.

    The montage supports Yoshi, Ness, Peach, and Mewtwo. It may start from an
    actionable grounded or airborne state, an existing jump squat, or a first-jump
    animation. Airborne starts spend one neutral input frame before pressing jump
    so a previously held X/Y button cannot suppress the required fresh edge.

    ``attack_delay_frames`` counts complete double-jump animation frames before
    the aerial request. Zero requests the aerial while observing double-jump frame
    one, producing the earliest possible cancel. Practical low aerials often need
    a later request so their hitbox becomes active before landing.
    """

    def __init__(
        self,
        attack_type: AttackType,
        frame_limit: int = 24,
        cancel_montage: InputMontage | None = None,
        *,
        attack_delay_frames: int = 0,
        jump_button: Button = Button.BUTTON_Y,
    ) -> None:
        if attack_type not in _AERIAL_ATTACKS:
            raise ValueError("attack_type must be an aerial attack")
        if attack_delay_frames < 0:
            raise ValueError("attack_delay_frames must be greater than or equal to zero")
        validate_button(
            jump_button,
            frozenset({Button.BUTTON_X, Button.BUTTON_Y}),
            "jump_button",
        )
        super().__init__(
            frame_limit,
            _DoubleJumpCancelState(_DoubleJumpCancelPhase.Initial),
            cancel_montage,
            name="Double Jump Cancel",
        )
        self._attack_type = attack_type
        self._attack_delay_frames = attack_delay_frames
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
            or player_state_value.character not in _DOUBLE_JUMP_CANCEL_CHARACTERS
            or player_state_value.jumps_left <= 0
        ):
            return False
        if player_state_value.action is not Action.KNEE_BEND and not player_state.can_jump():
            return False
        self._character = player_state_value.character
        return True

    def stateful_should_abort(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _DoubleJumpCancelState,
    ) -> Abort | None:
        del controls, opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None:
            return Abort("player state became unavailable")
        if player_state_value.character is not self._character:
            return Abort("player character changed")
        if input_state.phase is _DoubleJumpCancelPhase.AttackPending:
            return None
        if is_interrupted(player_state, player_state_value, include_hitlag=True):
            return Abort("player was interrupted")
        return None

    def stateful_on_tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _DoubleJumpCancelState,
    ) -> tuple[_DoubleJumpCancelState, InputMontage | bool | Abort]:
        del opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None:
            controls.release_all()
            return input_state, Abort("player state became unavailable")

        match input_state.phase:
            case _DoubleJumpCancelPhase.Initial:
                controls.release_all()
                if player_state_value.on_ground:
                    if player_state_value.action is not Action.KNEE_BEND:
                        controls.press_button(self._jump_button)
                    return replace(input_state, phase=_DoubleJumpCancelPhase.FirstJumpRequested), self
                return replace(input_state, phase=_DoubleJumpCancelPhase.AirJumpReady), self
            case _DoubleJumpCancelPhase.FirstJumpRequested:
                controls.release_all()
                if player_state_value.action is Action.KNEE_BEND:
                    return input_state, self
                if player_state_value.action in _FIRST_JUMP_ACTIONS and not player_state_value.on_ground:
                    controls.press_button(self._jump_button)
                    return replace(input_state, phase=_DoubleJumpCancelPhase.AirJumpRequested), self
                return input_state, Abort("first jump did not become actionable")
            case _DoubleJumpCancelPhase.AirJumpReady:
                controls.release_all()
                if player_state_value.on_ground or not player_state.can_jump():
                    return input_state, Abort("double jump could not be requested")
                controls.press_button(self._jump_button)
                return replace(input_state, phase=_DoubleJumpCancelPhase.AirJumpRequested), self
            case _DoubleJumpCancelPhase.AirJumpRequested:
                controls.release_all()
                if player_state_value.action not in _AERIAL_JUMP_ACTIONS:
                    return input_state, Abort("double-jump animation did not begin")
                if player_state_value.action_frame < self._attack_delay_frames + 1:
                    return input_state, self

                # DESNOTE(jbarber, 2026-08-26): Melee's aerial attack IASA runs
                # during the special aerial-jump actions used by Yoshi, Ness,
                # Peach, and Mewtwo. Requesting the aerial from an observed jump
                # packet schedules it for the next game frame and cancels the
                # remaining double-jump momentum. Yoshi's armor ends with the same
                # action transition; PlayerState.invulnerable does not represent it.
                # See https://www.ssbwiki.com/Double_jump_cancel and
                # https://github.com/doldecomp/melee/blob/master/src/melee/ft/chara/ftCommon/ftCo_JumpAerial.c
                result = controls.attack(self._attack_type)
                if isinstance(result, AttackFrameData):
                    controls.release_all()
                    return input_state, True
                if isinstance(result, Hold):
                    return replace(
                        input_state,
                        phase=_DoubleJumpCancelPhase.AttackPending,
                        hold=result,
                    ), self
                return input_state, Abort("requested aerial attack could not start")
            case _DoubleJumpCancelPhase.AttackPending:
                if input_state.hold is None:
                    controls.release_all()
                    return input_state, Abort("aerial attack hold became unavailable")
                if player_state_value.action in _ACTIONS_FOR_AERIAL[self._attack_type]:
                    controls.release_all()
                    return input_state, True
                if player_state_value.on_ground:
                    return input_state, Abort("player landed before the requested aerial attack was observed")
                result = controls.attack(self._attack_type, hold=input_state.hold)
                if isinstance(result, AttackFrameData):
                    controls.release_all()
                    return input_state, True
                if isinstance(result, Hold):
                    return replace(input_state, hold=result), self
                controls.release_all()
                return input_state, Abort("requested aerial attack was not observed")


__all__ = ["DoubleJumpCancelMontage"]
