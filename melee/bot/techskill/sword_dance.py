"""Marth Dancing Blade and Roy Double-Edge Dance input montage."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum, auto
from typing import Final

from melee.bot.character_state import AttackType, CharacterState, HorizontalStickReferenceAxis
from melee.bot.input_montage import Abort, InputMontage, MontageState
from melee.bot.simple_controls import SimpleControls, StickReferenceAxis
from melee.bot.stateful_input_montage import StatefulInputMontage
from melee.bot.techskill.common import is_interrupted, player
from melee.enums import Action, Button, Character
from melee.gamestate import GameState, PlayerState


@dataclass(frozen=True)
class _SwordDanceStep:
    actions: frozenset[Action]
    marth_request_window: tuple[int, int] | None
    roy_request_window: tuple[int, int] | None

    def request_window(self, character: Character | None) -> tuple[int, int] | None:
        if character is Character.MARTH:
            return self.marth_request_window
        if character is Character.ROY:
            return self.roy_request_window
        return None


# DESNOTE(jbarber, 2026-08-23): SmashWiki and PlayerState.action_frame are both
# one-based. Request windows end one observed frame earlier because controller
# input commits during the following Console.step. Marth and Roy share
# motion-state IDs but not every timing window.
# https://www.ssbwiki.com/Marth_(SSBM)/Side_special
# https://www.ssbwiki.com/Roy_(SSBM)/Side_special
_FIRST_STEP: Final = _SwordDanceStep(
    frozenset({Action(349), Action(358)}),
    (6, 24),
    (7, 25),
)
_SECOND_UP: Final = _SwordDanceStep(
    frozenset({Action(350), Action(359)}),
    (15, 30),
    (16, 32),
)
_SECOND_SIDE: Final = _SwordDanceStep(
    frozenset({Action(351), Action(360)}),
    (15, 31),
    (16, 32),
)
_THIRD_UP: Final = _SwordDanceStep(
    frozenset({Action(352), Action(361)}),
    (16, 36),
    (17, 37),
)
_THIRD_SIDE: Final = _SwordDanceStep(
    frozenset({Action(353), Action(362)}),
    (14, 35),
    (15, 36),
)
_THIRD_DOWN: Final = _SwordDanceStep(
    frozenset({Action(354), Action(363)}),
    (17, 33),
    (22, 34),
)
_FOURTH_UP: Final = _SwordDanceStep(
    frozenset({Action(355), Action(364)}),
    None,
    None,
)
_FOURTH_SIDE: Final = _SwordDanceStep(
    frozenset({Action(356), Action(365)}),
    None,
    None,
)
_FOURTH_DOWN: Final = _SwordDanceStep(
    frozenset({Action(357), Action(366)}),
    None,
    None,
)

_NEXT_STEPS: Final[tuple[dict[StickReferenceAxis, _SwordDanceStep], ...]] = (
    {
        StickReferenceAxis.UP: _SECOND_UP,
        StickReferenceAxis.LEFT: _SECOND_SIDE,
        StickReferenceAxis.RIGHT: _SECOND_SIDE,
        StickReferenceAxis.DOWN: _SECOND_SIDE,
    },
    {
        StickReferenceAxis.UP: _THIRD_UP,
        StickReferenceAxis.LEFT: _THIRD_SIDE,
        StickReferenceAxis.RIGHT: _THIRD_SIDE,
        StickReferenceAxis.DOWN: _THIRD_DOWN,
    },
    {
        StickReferenceAxis.UP: _FOURTH_UP,
        StickReferenceAxis.LEFT: _FOURTH_SIDE,
        StickReferenceAxis.RIGHT: _FOURTH_SIDE,
        StickReferenceAxis.DOWN: _FOURTH_DOWN,
    },
)
_SWORD_DANCE_CHARACTERS: Final = frozenset({Character.MARTH, Character.ROY})
_ALL_SWORD_DANCE_ACTIONS: Final = frozenset(
    action
    for step in (
        _FIRST_STEP,
        _SECOND_UP,
        _SECOND_SIDE,
        _THIRD_UP,
        _THIRD_SIDE,
        _THIRD_DOWN,
        _FOURTH_UP,
        _FOURTH_SIDE,
        _FOURTH_DOWN,
    )
    for action in step.actions
)
_FRAME_LIMIT: Final = 180
_START_WAIT_LIMIT: Final = 3
_TRANSITION_WAIT_LIMIT: Final = 3
_MAX_FOLLOWUP_SEGMENTS: Final = 3


class _SwordDancePhase(Enum):
    InitialInputRequested = auto()
    AwaitingStartup = auto()
    Active = auto()
    Transitioning = auto()


@dataclass(frozen=True)
class _SwordDanceState:
    phase: _SwordDancePhase = _SwordDancePhase.InitialInputRequested
    step: _SwordDanceStep = _FIRST_STEP
    expected_step: _SwordDanceStep | None = None
    confirmed_followups: int = 0
    wait_frames: int = 0


class SwordDanceMontage(StatefulInputMontage[_SwordDanceState]):
    """Perform a caller-directed Marth or Roy Sword Dance chain.

    ``initial_direction`` is the absolute left/right input for the first side-B.
    Up to three follow-up segments may be queued before startup or added
    reactively while each current segment's input window remains open.

    :meth:`add_segment` returns ``True`` only when it appends the direction. The
    second hit accepts all four cardinal axes; down and both horizontal axes
    select its side branch. The third and fourth hits use distinct up, side, and
    down branches, with left and right both selecting side. Attempts made after
    the current slot closes, after terminal completion, or beyond the four-hit
    limit return ``False`` without changing the route.

    The montage sends one fresh B edge for each continuation and confirms the
    selected ground or aerial action before advancing. It succeeds when the last
    available reactive slot closes or when the fourth hit is confirmed.
    """

    def __init__(self, initial_direction: HorizontalStickReferenceAxis) -> None:
        super().__init__(
            _FRAME_LIMIT,
            _SwordDanceState(),
            name="Dancing Blade / Double-Edge Dance",
        )
        self._initial_direction = initial_direction
        self._segments: list[StickReferenceAxis] = []
        self._segment_slot_open = True
        self._character: Character | None = None

    def add_segment(self, direction: StickReferenceAxis) -> bool:
        """Append one legal follow-up direction while its slot is open."""
        if not self.can_add_segment(direction):
            return False
        self._segments.append(direction)
        return True

    def can_add_segment(self, direction: StickReferenceAxis) -> bool:
        """Return whether ``direction`` can be appended to the current route."""
        return (
            self.get_montage_state() in {MontageState.Waiting, MontageState.Active}
            and self._segment_slot_open
            and len(self._segments) < _MAX_FOLLOWUP_SEGMENTS
            and direction in _NEXT_STEPS[len(self._segments)]
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
            or player_state_value.character not in _SWORD_DANCE_CHARACTERS
            or not player_state.can_attack(AttackType.SIDE_B)
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
        input_state: _SwordDanceState,
    ) -> Abort | None:
        del controls, opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None:
            return Abort("player state became unavailable")
        if player_state_value.character is not self._character:
            return Abort("player character changed")

        # DESNOTE(jbarber, 2026-08-23): should_abort runs before caller pre-tick
        # listeners. Close an expired slot here so a listener cannot append an
        # input after the branch-specific observation deadline.
        if (
            input_state.phase is _SwordDancePhase.Active
            and player_state_value.action in input_state.step.actions
            and (request_window := input_state.step.request_window(self._character)) is not None
            and player_state_value.action_frame > request_window[1]
        ):
            self._segment_slot_open = False

        if is_interrupted(player_state, player_state_value, include_hitlag=False):
            return Abort("player was interrupted")
        return None

    def stateful_on_tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _SwordDanceState,
    ) -> tuple[_SwordDanceState, InputMontage | bool | Abort]:
        del opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None:
            return input_state, Abort("player state became unavailable")

        match input_state.phase:
            case _SwordDancePhase.InitialInputRequested:
                self._apply_segment_input(controls, self._initial_direction)
                return replace(input_state, phase=_SwordDancePhase.AwaitingStartup), self
            case _SwordDancePhase.AwaitingStartup:
                return self._tick_startup(controls, player_state_value, input_state)
            case _SwordDancePhase.Active:
                return self._tick_active(controls, player_state_value, input_state)
            case _SwordDancePhase.Transitioning:
                return self._tick_transition(controls, player_state_value, input_state)

    def _tick_startup(
        self,
        controls: SimpleControls,
        player_state_value: PlayerState,
        input_state: _SwordDanceState,
    ) -> tuple[_SwordDanceState, InputMontage | Abort]:
        controls.release_all()
        if player_state_value.action in _FIRST_STEP.actions:
            self._segment_slot_open = len(self._segments) < _MAX_FOLLOWUP_SEGMENTS
            return (
                replace(
                    input_state,
                    phase=_SwordDancePhase.Active,
                    wait_frames=0,
                ),
                self,
            )
        if input_state.wait_frames >= _START_WAIT_LIMIT:
            return input_state, Abort("Sword Dance did not start")
        return replace(input_state, wait_frames=input_state.wait_frames + 1), self

    def _tick_active(
        self,
        controls: SimpleControls,
        player_state_value: PlayerState,
        input_state: _SwordDanceState,
    ) -> tuple[_SwordDanceState, InputMontage | bool | Abort]:
        if player_state_value.action not in input_state.step.actions:
            controls.release_all()
            if len(self._segments) > input_state.confirmed_followups:
                return input_state, Abort("Sword Dance ended before the queued segment started")
            self._segment_slot_open = False
            return input_state, True

        if player_state_value.hitlag_left > 0:
            controls.release_all()
            self._frame_limit += 1
            return input_state, self

        request_window = input_state.step.request_window(self._character)
        if request_window is None:
            controls.release_all()
            self._segment_slot_open = False
            return input_state, True
        first_request_frame, last_request_frame = request_window

        if len(self._segments) <= input_state.confirmed_followups:
            controls.release_all()
            if player_state_value.action_frame >= last_request_frame:
                self._segment_slot_open = False
                return input_state, True
            return input_state, self

        direction = self._segments[input_state.confirmed_followups]
        expected_step = _NEXT_STEPS[input_state.confirmed_followups][direction]
        if player_state_value.action_frame < first_request_frame:
            controls.release_all()
            return input_state, self
        if player_state_value.action_frame > last_request_frame:
            self._segment_slot_open = False
            return input_state, Abort("queued Sword Dance segment missed its input window")

        self._apply_segment_input(controls, direction)
        self._segment_slot_open = False
        return (
            replace(
                input_state,
                phase=_SwordDancePhase.Transitioning,
                expected_step=expected_step,
                wait_frames=0,
            ),
            self,
        )

    def _tick_transition(
        self,
        controls: SimpleControls,
        player_state_value: PlayerState,
        input_state: _SwordDanceState,
    ) -> tuple[_SwordDanceState, InputMontage | bool | Abort]:
        controls.release_all()
        expected_step = input_state.expected_step
        if expected_step is None:
            return input_state, Abort("expected Sword Dance segment became unavailable")
        if player_state_value.action in expected_step.actions:
            confirmed_followups = input_state.confirmed_followups + 1
            next_state = replace(
                input_state,
                phase=_SwordDancePhase.Active,
                step=expected_step,
                expected_step=None,
                confirmed_followups=confirmed_followups,
                wait_frames=0,
            )
            if confirmed_followups >= _MAX_FOLLOWUP_SEGMENTS:
                return next_state, True
            self._segment_slot_open = len(self._segments) < _MAX_FOLLOWUP_SEGMENTS
            return next_state, self

        if player_state_value.hitlag_left > 0:
            self._frame_limit += 1
            return input_state, self
        if player_state_value.action in input_state.step.actions:
            if input_state.wait_frames < _TRANSITION_WAIT_LIMIT:
                return replace(input_state, wait_frames=input_state.wait_frames + 1), self
            return input_state, Abort("queued Sword Dance segment did not start")
        if player_state_value.action in _ALL_SWORD_DANCE_ACTIONS:
            return input_state, Abort("Sword Dance entered the wrong directional segment")
        return input_state, Abort("Sword Dance ended before the queued segment started")

    @staticmethod
    def _apply_segment_input(
        controls: SimpleControls,
        direction: StickReferenceAxis,
    ) -> None:
        controls.release_all()
        controls.tilt_stick(direction, 0.0)
        controls.press_button(Button.BUTTON_B)


__all__ = ["SwordDanceMontage"]
