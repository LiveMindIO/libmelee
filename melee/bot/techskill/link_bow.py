"""Caller-controlled Link and Young Link bow-charge montage."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum, auto
from typing import Final, Self

from melee.bot.character_state import AttackType, CharacterState
from melee.bot.input_montage import Abort, InputMontage, MontageState
from melee.bot.simple_controls import AttackFrameData, Hold, SimpleControls
from melee.bot.stateful_input_montage import StatefulInputMontage
from melee.bot.techskill.common import is_interrupted, player
from melee.enums import Action, Button, Character
from melee.gamestate import GameState, PlayerState

_BOW_START_ACTIONS: Final = frozenset({Action(344), Action(347)})
_BOW_FULL_CHARGE_ACTIONS: Final = frozenset({Action(345), Action(348)})
_BOW_RELEASE_ACTIONS: Final = frozenset({Action(346), Action(349)})
# DESNOTE(jbarber, 2026-08-23): The bow IASA increments its private charge
# counter only after each character's subaction enables release. A bot request
# commits one Console.step later, so observed frame 17 for Link or 14 for Young
# Link is the first safe release request and maps to normalized power 0. Their
# PlLk.dat/PlCl.dat ext_attr x0 counters cap at 60/45; entering the loop state
# sets the counter directly to that cap. See:
# https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftLink/ftLk_SpecialN.c#L418-L450
# https://www.ssbwiki.com/Link_(SSBM)/Neutral_special
# https://www.ssbwiki.com/Young_Link_(SSBM)/Neutral_special
_FIRST_RELEASE_REQUEST_FRAME: Final[dict[Character, int]] = {
    Character.LINK: 17,
    Character.YLINK: 14,
}
_MAX_CHARGE_FRAMES: Final[dict[Character, int]] = {
    Character.LINK: 60,
    Character.YLINK: 45,
}
_FRAME_LIMIT: Final = 60 * 60
_START_WAIT_LIMIT: Final = 2
_RELEASE_WAIT_LIMIT: Final = 2


class _LinkBowPhase(Enum):
    Charging = auto()
    Released = auto()


@dataclass(frozen=True)
class _LinkBowState:
    phase: _LinkBowPhase = _LinkBowPhase.Charging
    hold: Hold | None = None
    character: Character | None = None
    charge_frames: int | None = None
    start_wait_frames: int = 0
    release_wait_frames: int = 0


class LinkBowMontage(StatefulInputMontage[_LinkBowState]):
    """Charge and caller-release Link or Young Link's bow.

    The montage starts neutral-B from any state where the selected Link can use
    it, then retains B through the grounded or aerial charge animation. Call
    :meth:`release` to queue the shot. The request is sticky and may be made
    before startup; the montage releases B on the first safe active tick.

    :meth:`current_power` returns ``None`` until release can safely commit. Once
    ready, it reports normalized projectile charge from ``0.0`` through ``1.0``.
    Link's power saturates after 60 charge ticks and Young Link's after 45; each
    character's fully charged loop reports ``1.0`` and may remain held. The value
    freezes when the shot is released. :meth:`can_release` is exactly the
    non-``None`` power test.

    Callers must retain and tick the returned montage, and return from frame
    policy after each tick so fallback inputs do not overwrite held or released
    B. A caller that never releases eventually reaches the montage's finite
    one-minute safety timeout rather than holding the sequence forever.
    """

    def __init__(self) -> None:
        super().__init__(_FRAME_LIMIT, _LinkBowState())
        self._release_requested = False

    def release(self) -> Self:
        """Request bow release on the first safe active tick and return ``self``.

        This records intent without changing pending controller input. It is
        sticky and idempotent before startup and while charging, and has no
        effect after the release command or terminal completion.
        """
        if (
            self.get_montage_state() in {MontageState.Waiting, MontageState.Active}
            and self._input_state.phase is _LinkBowPhase.Charging
        ):
            self._release_requested = True
        return self

    def current_power(self) -> float | None:
        """Return normalized bow charge, or ``None`` before release is safe."""
        input_state = self._input_state
        if (
            input_state.phase is not _LinkBowPhase.Charging
            or input_state.charge_frames is None
            or input_state.character is None
        ):
            return None
        return min(
            1.0,
            input_state.charge_frames / _MAX_CHARGE_FRAMES[input_state.character],
        )

    def can_release(self) -> bool:
        """Return whether the bow can safely be released on the next tick."""
        return self.current_power() is not None

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
            and player_state_value.character in _MAX_CHARGE_FRAMES
            and player_state.can_attack(AttackType.NEUTRAL_B)
        )

    def stateful_should_abort(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _LinkBowState,
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
        input_state: _LinkBowState,
    ) -> tuple[_LinkBowState, InputMontage | bool | Abort]:
        del opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None:
            return input_state, Abort("player state became unavailable")

        match input_state.phase:
            case _LinkBowPhase.Charging if input_state.hold is None:
                result = controls.attack(AttackType.NEUTRAL_B)
                if not isinstance(result, Hold):
                    return input_state, Abort("bow input was not accepted")
                return (
                    replace(
                        input_state,
                        hold=result,
                        character=player_state_value.character,
                    ),
                    self,
                )
            case _LinkBowPhase.Charging:
                return self._tick_charge(controls, player_state_value, input_state)
            case _LinkBowPhase.Released:
                controls.release_all()
                if player_state_value.action in _BOW_RELEASE_ACTIONS:
                    return input_state, True
                if (
                    player_state_value.action in _BOW_START_ACTIONS | _BOW_FULL_CHARGE_ACTIONS
                    and input_state.release_wait_frames < _RELEASE_WAIT_LIMIT
                ):
                    return (
                        replace(
                            input_state,
                            release_wait_frames=input_state.release_wait_frames + 1,
                        ),
                        self,
                    )
                return input_state, Abort("released bow shot did not start")

    def _tick_charge(
        self,
        controls: SimpleControls,
        player_state_value: PlayerState,
        input_state: _LinkBowState,
    ) -> tuple[_LinkBowState, InputMontage | bool | Abort]:
        hold = input_state.hold
        character = input_state.character
        if hold is None or character is None:
            return input_state, Abort("bow hold became unavailable")

        if player_state_value.action in _BOW_FULL_CHARGE_ACTIONS:
            charge_frames = _MAX_CHARGE_FRAMES[character]
        elif player_state_value.action in _BOW_START_ACTIONS:
            if (
                input_state.charge_frames is None
                and player_state_value.action_frame < _FIRST_RELEASE_REQUEST_FRAME[character]
            ):
                charge_frames = None
            elif input_state.charge_frames is None:
                charge_frames = 0
            else:
                charge_frames = min(
                    input_state.charge_frames + 1,
                    _MAX_CHARGE_FRAMES[character],
                )
        elif input_state.charge_frames is not None:
            return input_state, Abort("bow charge was interrupted")
        elif input_state.start_wait_frames >= _START_WAIT_LIMIT:
            return input_state, Abort("bow charge did not start")
        else:
            charge_frames = None
            input_state = replace(
                input_state,
                start_wait_frames=input_state.start_wait_frames + 1,
            )

        input_state = replace(input_state, charge_frames=charge_frames)
        if self._release_requested and charge_frames is not None:
            result = controls.release(hold)
            if not isinstance(result, AttackFrameData):
                return input_state, Abort("bow shot could not be released")
            return replace(input_state, phase=_LinkBowPhase.Released), self

        controls.release_all()
        controls.press_button(Button.BUTTON_B)
        return input_state, self


__all__ = ["LinkBowMontage"]
