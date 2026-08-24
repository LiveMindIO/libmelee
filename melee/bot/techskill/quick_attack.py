"""Reactive Pikachu Quick Attack and Pichu Agility input montage."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Final, Self

from melee.bot.character_state import AttackType, CharacterState
from melee.bot.input_montage import Abort, InputMontage, MontageState
from melee.bot.simple_controls import SimpleControls, StickReferenceAxis, stick_coordinates
from melee.bot.stateful_input_montage import StatefulInputMontage
from melee.bot.techskill.common import is_interrupted, player
from melee.enums import Action, Button, Character
from melee.gamestate import GameState


@dataclass(frozen=True)
class QuickAttackDirection:
    """Absolute full-magnitude direction for one Quick Attack segment."""

    reference_axis: StickReferenceAxis
    angle_degrees: float = 0.0

    def __post_init__(self) -> None:
        stick_coordinates(self.reference_axis, self.angle_degrees)


class _QuickAttackPhase(Enum):
    InitialInputRequested = auto()
    InitialStartup = auto()
    FirstSegment = auto()
    AwaitingSecondSegment = auto()


_QUICK_ATTACK_CHARACTERS: Final = frozenset({Character.PIKACHU, Character.PICHU})
_STARTUP_ACTIONS: Final = frozenset(
    {
        Action.PIKACHU_SPECIAL_HI_START0,
        Action.PIKACHU_SPECIAL_AIR_HI_START0,
    }
)
_TRAVEL_ACTIONS: Final = frozenset(
    {
        Action.PIKACHU_SPECIAL_HI_START1,
        Action.PIKACHU_SPECIAL_AIR_HI_START1,
    }
)
_END_ACTIONS: Final = frozenset(
    {
        Action.PIKACHU_SPECIAL_HI_END,
        Action.PIKACHU_SPECIAL_AIR_HI_END,
    }
)
_LEDGE_ACTIONS: Final = frozenset({Action.EDGE_CATCHING, Action.EDGE_HANGING})
_POST_MOVE_ACTIONS: Final = _LEDGE_ACTIONS | {
    Action.DEAD_FALL,
    Action.SPECIAL_FALL_FORWARD,
    Action.SPECIAL_FALL_BACK,
    Action.LANDING_SPECIAL,
}
# DESNOTE(jbarber, 2026-08-23): Pikachu and Pichu have two zips. Their shared
# end animation samples zip 2 before the next frame's input refresh. Frame 7 is
# therefore the last reliable observation from which a bot can queue direction;
# frame 8 remains usable only while hitlag defers the animation callback. The
# game then requires more than 38 degrees of separation for Pikachu and 5 for Pichu.
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftPikachu/ftPk_SpecialHi.c#L619-L700
# and https://www.ssbwiki.com/Pikachu_(SSBM)/Up_special
# and https://www.ssbwiki.com/Pichu_(SSBM)#Differences_from_Pikachu
_LAST_SECOND_SEGMENT_INPUT_FRAME: Final = 7
_HITLAG_SECOND_SEGMENT_INPUT_FRAME: Final = 8


def _apply_direction(
    controls: SimpleControls,
    direction: QuickAttackDirection,
) -> None:
    controls.release_all()
    controls.tilt_stick(direction.reference_axis, direction.angle_degrees)


def _apply_start_input(controls: SimpleControls) -> None:
    controls.release_all()
    controls.tilt_stick(StickReferenceAxis.UP, 0.0)
    controls.press_button(Button.BUTTON_B)


class QuickAttackMontage(StatefulInputMontage[_QuickAttackPhase]):
    """Perform one or two caller-directed Quick Attack/Agility segments.

    The montage initiates Up-B with cardinal up+B, then the constructor's
    ``initial_direction`` controls the first movement segment throughout startup.
    :meth:`add_segment` can queue the optional second direction before activation
    or reactively during startup, the first zip, and the first seven frames of
    the inter-segment end state. The first request is sticky; further or late
    requests do nothing. :meth:`can_add_segment` reports whether that slot and
    observable request window remain available.

    Melee supports exactly two movement segments. Both movement directions use
    continuous full-circle analog input at full magnitude. The game accepts segment two only
    when its angle differs from segment one by more than 38 degrees for Pikachu or
    5 degrees for Pichu. The montage detects a rejected requested segment and
    aborts rather than reporting that both segments completed, unless the move
    safely reaches the ledge first.
    """

    def __init__(
        self,
        initial_direction: QuickAttackDirection,
        frame_limit: int = 96,
        cancel_montage: InputMontage | None = None,
    ) -> None:
        super().__init__(
            frame_limit,
            _QuickAttackPhase.InitialInputRequested,
            cancel_montage,
            name="Quick Attack / Agility",
        )
        self._initial_direction = initial_direction
        self._second_direction: QuickAttackDirection | None = None
        self._segments_open = True
        self._character: Character | None = None
        self._last_end_frame: int | None = None

    def add_segment(self, direction: QuickAttackDirection) -> Self:
        """Queue the optional second direction while its slot/window is open."""
        if self.can_add_segment():
            self._second_direction = direction
        return self

    def can_add_segment(self) -> bool:
        """Return whether a second direction can still be queued."""
        return (
            self.get_montage_state() in {MontageState.Waiting, MontageState.Active}
            and self._segments_open
            and self._second_direction is None
        )

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
            or player_state_value.character not in _QUICK_ATTACK_CHARACTERS
            or not player_state.can_attack(AttackType.UP_B)
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
        input_state: _QuickAttackPhase,
    ) -> Abort | None:
        del controls, opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None:
            return Abort("player state became unavailable")
        if player_state_value.character is not self._character:
            return Abort("player character changed")
        # DESNOTE(jbarber, 2026-08-23): should_abort runs before pre-tick
        # listeners. Reopen here so a listener can react to frame-8 hitlag that
        # deferred the sample after an ordinary frame 7 closed the normal window.
        if input_state is _QuickAttackPhase.AwaitingSecondSegment and player_state_value.action in _END_ACTIONS:
            if (
                player_state_value.action_frame == _HITLAG_SECOND_SEGMENT_INPUT_FRAME
                and player_state_value.hitlag_left > 0
                and self._second_direction is None
            ):
                self._segments_open = True
            elif player_state_value.action_frame > _LAST_SECOND_SEGMENT_INPUT_FRAME:
                self._segments_open = False
        if (
            input_state
            in {
                _QuickAttackPhase.FirstSegment,
                _QuickAttackPhase.AwaitingSecondSegment,
            }
            and player_state_value.action in _POST_MOVE_ACTIONS
        ):
            return None
        if is_interrupted(player_state, player_state_value, include_hitlag=False):
            return Abort("player was interrupted")
        return None

    def stateful_on_tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _QuickAttackPhase,
    ) -> tuple[_QuickAttackPhase, InputMontage | bool | Abort]:
        del opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None or self._character is None:
            controls.release_all()
            return input_state, Abort("player state or captured character became unavailable")

        action = player_state_value.action
        if input_state is not _QuickAttackPhase.InitialInputRequested and action in _LEDGE_ACTIONS:
            controls.release_all()
            self._segments_open = False
            return input_state, True
        match input_state:
            case _QuickAttackPhase.InitialInputRequested:
                _apply_start_input(controls)
                return _QuickAttackPhase.InitialStartup, self
            case _QuickAttackPhase.InitialStartup:
                if action in _STARTUP_ACTIONS:
                    _apply_direction(controls, self._initial_direction)
                    return input_state, self
                if action in _TRAVEL_ACTIONS:
                    return self._first_segment_tick(controls)
                if action in _END_ACTIONS:
                    return self._end_state_tick(
                        controls,
                        player_state_value.action_frame,
                        player_state_value.hitlag_left,
                    )
                if player_state.can_attack(AttackType.UP_B):
                    _apply_start_input(controls)
                    return input_state, self
                controls.release_all()
                return input_state, Abort("initial Quick Attack segment did not start")
            case _QuickAttackPhase.FirstSegment:
                if action in _TRAVEL_ACTIONS:
                    return self._first_segment_tick(controls)
                if action in _END_ACTIONS:
                    return self._end_state_tick(
                        controls,
                        player_state_value.action_frame,
                        player_state_value.hitlag_left,
                    )
                return self._after_first_segment(controls, input_state, action)
            case _QuickAttackPhase.AwaitingSecondSegment:
                if action in _END_ACTIONS:
                    return self._end_state_tick(
                        controls,
                        player_state_value.action_frame,
                        player_state_value.hitlag_left,
                    )
                if action in _TRAVEL_ACTIONS:
                    controls.release_all()
                    self._segments_open = False
                    if self._second_direction is None:
                        return input_state, Abort("unexpected second Quick Attack segment")
                    return input_state, True
                return self._after_first_segment(controls, input_state, action)

    def _first_segment_tick(
        self,
        controls: SimpleControls,
    ) -> tuple[_QuickAttackPhase, InputMontage]:
        if self._second_direction is None:
            controls.release_all()
        else:
            _apply_direction(controls, self._second_direction)
        return _QuickAttackPhase.FirstSegment, self

    def _end_state_tick(
        self,
        controls: SimpleControls,
        action_frame: int,
        hitlag_left: int,
    ) -> tuple[_QuickAttackPhase, InputMontage | bool]:
        # DESNOTE(jbarber, 2026-08-23): A zip can collide with terrain and enter
        # its end state before Slippi exposes a travel packet. The first end
        # confirms zip 1; after the sample deadline, an end-frame reset confirms
        # that zip 2 launched and immediately collided.
        # See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftPikachu/ftPk_SpecialHi.c#L299-L450
        previous_end_frame = self._last_end_frame
        self._last_end_frame = action_frame
        if (
            previous_end_frame is not None
            and self._second_direction is not None
            and not self._segments_open
            and action_frame < previous_end_frame
        ):
            controls.release_all()
            return _QuickAttackPhase.AwaitingSecondSegment, True
        input_window_open = action_frame <= _LAST_SECOND_SEGMENT_INPUT_FRAME or (
            action_frame == _HITLAG_SECOND_SEGMENT_INPUT_FRAME and hitlag_left > 0
        )
        if input_window_open and self._second_direction is not None:
            _apply_direction(controls, self._second_direction)
        else:
            controls.release_all()
        if action_frame >= _LAST_SECOND_SEGMENT_INPUT_FRAME and hitlag_left == 0:
            self._segments_open = False
        if action_frame > _HITLAG_SECOND_SEGMENT_INPUT_FRAME and self._second_direction is None:
            return _QuickAttackPhase.AwaitingSecondSegment, True
        return _QuickAttackPhase.AwaitingSecondSegment, self

    def _after_first_segment(
        self,
        controls: SimpleControls,
        input_state: _QuickAttackPhase,
        action: Action,
    ) -> tuple[_QuickAttackPhase, bool | Abort]:
        controls.release_all()
        self._segments_open = False
        if action in _LEDGE_ACTIONS or self._second_direction is None:
            return input_state, True
        return input_state, Abort("second Quick Attack segment did not start")


__all__ = ["QuickAttackDirection", "QuickAttackMontage"]
