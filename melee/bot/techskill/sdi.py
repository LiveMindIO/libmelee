"""Smash directional influence input montage."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Final

from melee.bot.character_state import CharacterState
from melee.bot.input_montage import Abort, InputMontage
from melee.bot.simple_controls import SimpleControls, StickReferenceAxis
from melee.bot.stateful_input_montage import StatefulInputMontage
from melee.bot.techskill.common import DEAD_ACTIONS, player
from melee.enums import Action, Button, Character
from melee.gamestate import GameState, PlayerState, UnknownAnimation

_SDI_PULSE_ANGLE_DEGREES: Final = 45.0
_SHIELD_ACTIONS: Final = frozenset(
    {
        Action.SHIELD_START,
        Action.SHIELD,
        Action.SHIELD_RELEASE,
        Action.SHIELD_STUN,
        Action.SHIELD_REFLECT,
    }
)
_HORIZONTAL_DIRECTIONS: Final = frozenset({StickReferenceAxis.LEFT, StickReferenceAxis.RIGHT})


class _SDIKind(Enum):
    Damage = auto()
    Shield = auto()


@dataclass(frozen=True)
class _SDIState:
    positive_pulse: bool = True
    shield_pulse: bool = True


def _is_damage_action(action: Action | UnknownAnimation) -> bool:
    return isinstance(action, Action) and (Action.DAMAGE_HIGH_1.value <= action.value <= Action.DAMAGE_FLY_ROLL.value)


def _sdi_kind(player_state: PlayerState) -> _SDIKind | None:
    if player_state.action in _SHIELD_ACTIONS or player_state.is_powershield:
        return _SDIKind.Shield
    if (
        player_state.is_defender_in_hitlag
        or player_state.hitstun_frames_left > 1
        or _is_damage_action(player_state.action)
    ):
        return _SDIKind.Damage
    return None


class SDIMontage(StatefulInputMontage[_SDIState]):
    """SDI toward one cardinal direction for the current hitlag window.

    During damage hitlag, regular SDI frames alternate full-stick diagonals around
    ``direction``. Crossing the perpendicular stick axis creates one SDI pulse
    each frame while the two vectors average toward the requested cardinal.
    Shield SDI is horizontal-only and alternates the requested direction with
    neutral. Damage hitlag exits with C-stick ASDI while leaving the main stick
    neutral rather than assuming trajectory DI. Shield hitlag instead exits with
    the horizontal main-stick input read by Melee's shield callback.

    The montage starts only when state identifies this player as the hit victim.
    ``hitlag_left`` alone is insufficient because Melee gives hitlag to attackers
    too. It finishes on the first observed frame after hitlag.
    """

    def __init__(
        self,
        direction: StickReferenceAxis,
        frame_limit: int = 32,
        cancel_montage: InputMontage | None = None,
    ) -> None:
        super().__init__(
            frame_limit,
            _SDIState(),
            cancel_montage,
            name="SDI",
        )
        self._direction = direction
        self._character: Character | None = None
        self._stock: int | None = None
        self._kind: _SDIKind | None = None

    def can_start(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> bool:
        del controls, opponent_state, state
        player_state_value = player(player_state)
        kind = None if player_state_value is None else _sdi_kind(player_state_value)
        if (
            player_state_value is None
            or player_state_value.hitlag_left <= 0
            or kind is None
            or player_state.is_grabbed()
            or (kind is _SDIKind.Shield and self._direction not in _HORIZONTAL_DIRECTIONS)
        ):
            return False
        self._character = player_state_value.character
        self._stock = player_state_value.stock
        self._kind = kind
        return True

    def stateful_should_abort(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _SDIState,
    ) -> Abort | None:
        del controls, opponent_state, state, input_state
        player_state_value = player(player_state)
        if player_state_value is None:
            return Abort("player state became unavailable")
        if player_state_value.character is not self._character:
            return Abort("player character changed")
        if player_state_value.stock != self._stock:
            return Abort("player stock changed")
        if player_state_value.action in DEAD_ACTIONS:
            return Abort("player entered a death action")
        if player_state.is_grabbed():
            return Abort("player became grabbed")
        return None

    def stateful_on_tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _SDIState,
    ) -> tuple[_SDIState, InputMontage | bool | Abort]:
        del opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None:
            controls.release_all()
            return input_state, Abort("player state became unavailable")
        controls.release_all()
        if player_state_value.hitlag_left <= 0:
            return input_state, True

        # DESNOTE(jbarber, 2026-08-17): Controller requests are committed by the
        # next Console.step. hitlag_left > 1 therefore queues regular SDI, while
        # hitlag_left == 1 queues the one displacement evaluated as hitlag exits.
        # Damage SDI alternates +/-45 degrees to cross one perpendicular axis
        # every frame. Shield SDI reads only horizontal displacement, so it must
        # return to neutral before repeating its direction and use the main stick
        # rather than C-stick for its post-hitlag displacement.
        # See https://github.com/doldecomp/melee/blob/master/src/melee/ft/chara/ftCommon/ftCo_Damage.c#L573-L669
        if player_state_value.hitlag_left > 1:
            match self._kind, input_state:
                case _SDIKind.Shield, _SDIState(positive_pulse, shield_pulse):
                    if shield_pulse:
                        controls.tilt_stick(self._direction, 0.0)
                    return _SDIState(positive_pulse=positive_pulse, shield_pulse=not shield_pulse), self
                case _, _SDIState(positive_pulse, shield_pulse):
                    pulse_angle = _SDI_PULSE_ANGLE_DEGREES if positive_pulse else -_SDI_PULSE_ANGLE_DEGREES
                    controls.tilt_stick(self._direction, pulse_angle)
                    return _SDIState(positive_pulse=not positive_pulse, shield_pulse=shield_pulse), self

        match self._kind:
            case _SDIKind.Shield:
                controls.tilt_stick(self._direction, 0.0)
                return input_state, self
            case _:
                controls.tilt_stick(self._direction, 0.0, stick=Button.BUTTON_C)
                return input_state, self


__all__ = ["SDIMontage"]
