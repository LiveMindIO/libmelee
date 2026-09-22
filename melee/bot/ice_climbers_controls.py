"""Ungated Ice Climbers inputs with delayed Nana result tracking."""

from __future__ import annotations

import copy
import math
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from typing import Final, Protocol, TypeVar

from melee.bot.character_state import (
    AttackType,
    CharacterState,
    GroundDodgeStickReferenceAxis,
    StickReferenceAxis,
)
from melee.bot.simple_controls import (
    MIN_SHIELD,
    ActionFrameData,
    AttackFrameData,
    ControllerPacket,
    LedgeRecoveryOption,
    SimpleControls,
    _observed_action_frame_data,
    stick_coordinates,
)
from melee.controller import Controller, fix_analog_trigger
from melee.enums import Button, Character
from melee.framedata import FrameData
from melee.gamestate import GameState, PlayerState

NANA_INPUT_DELAY_FRAMES: Final = 6
ResultT = TypeVar("ResultT")


class _DirectionalTilt(Protocol):
    def __call__(
        self,
        angle_degrees: float,
        *,
        magnitude: float = 1.0,
        stick: Button = Button.BUTTON_MAIN,
    ) -> ActionFrameData | None: ...


class NanaActionStatus(Enum):
    """Whether a delayed Nana action could be evaluated at its exact frame."""

    EXECUTED = auto()
    NANA_ABSENT = auto()
    FRAME_SKIPPED = auto()
    RESET = auto()


NanaControlOutput = ActionFrameData | None


@dataclass(frozen=True, slots=True)
class NanaAction:
    """One immutable physical Popo packet delta delayed for Nana."""

    id: int
    input_frame: int
    execution_frame: int
    previous_packet: ControllerPacket
    current_packet: ControllerPacket


@dataclass(frozen=True, slots=True)
class NanaActionResult:
    """The observed Nana result evaluated at the action's execution frame."""

    action: NanaAction
    status: NanaActionStatus
    output: NanaControlOutput


class _IceClimbersInputControls(SimpleControls):
    """One-frame ungated input operations used by the public facade."""

    def attack_once(
        self,
        attack_type: AttackType,
    ) -> AttackFrameData | None:
        player = self._player()
        if player is None:
            return None
        can_execute = self.character_state.can_attack(attack_type)
        current = self._attack_frame_data(player, attack_type)
        stick_x, stick_y = self._stick_for_attack(player, attack_type)
        requested = self._begin_commit_attack(
            attack_type,
            player,
            stick_x,
            stick_y,
        )
        if not can_execute:
            return None
        if current is not None:
            return current
        return AttackFrameData(
            character=player.character,
            action=requested.action,
            frame_data=self._frame_data,
        )

    def shield_once(self, strength: float) -> ActionFrameData | None:
        if not math.isfinite(strength) or not 0.0 <= strength <= 1.0:
            raise ValueError("strength must be finite and between 0 and 1 inclusive")
        self._release_button(Button.BUTTON_L)
        self._release_button(Button.BUTTON_R)
        self._press_shoulder(Button.BUTTON_L, 0.0)
        self._press_shoulder(Button.BUTTON_R, 0.0)
        if strength > 0.0:
            requested_strength = max(strength, MIN_SHIELD)
            if not self._controller.analog_input_correction_enabled:
                requested_strength = fix_analog_trigger(requested_strength)
            self._press_shoulder(Button.BUTTON_L, requested_strength)
            if strength == 1.0:
                self.press_button(Button.BUTTON_L)
        return self._pending_action_frame_data()

    def platform_drop_once(self) -> ActionFrameData | None:
        return self.tilt_stick(StickReferenceAxis.DOWN, 0.0)

    def dodge_once(
        self,
        direction: GroundDodgeStickReferenceAxis,
        *,
        dodge_button: Button,
    ) -> ActionFrameData | None:
        if direction not in {
            StickReferenceAxis.LEFT,
            StickReferenceAxis.RIGHT,
            StickReferenceAxis.DOWN,
        }:
            raise ValueError(
                "direction must be StickReferenceAxis.LEFT, StickReferenceAxis.RIGHT, or StickReferenceAxis.DOWN"
            )
        self._validate_dodge_button(dodge_button)
        self.release_all()
        self.tilt_stick(direction, 0.0)
        return self.press_button(dodge_button)

    def air_dodge_once(
        self,
        reference_axis: StickReferenceAxis,
        angle_degrees: float,
        *,
        magnitude: float,
        dodge_button: Button,
    ) -> ActionFrameData | None:
        self._validate_dodge_button(dodge_button)
        stick_x, stick_y = stick_coordinates(
            reference_axis,
            angle_degrees,
            magnitude=magnitude,
        )
        self.release_all()
        self.tilt_analog(Button.BUTTON_MAIN, stick_x, stick_y)
        return self.press_button(dodge_button)

    def ledge_recovery_once(self, option: LedgeRecoveryOption) -> ActionFrameData | None:
        player = self._player()
        if player is None:
            return None
        self._apply_ledge_recovery_inputs(player, option)
        return self._pending_action_frame_data()

    def taunt_once(self) -> ActionFrameData | None:
        self.release_all()
        return self.press_button(Button.BUTTON_D_UP)


class NanaActionQueue:
    """Evaluate queued inputs against Nana exactly six game frames later.

    The queue is owned by :class:`IceClimbersControls`. Its public readers require
    the current frame so stale bot code cannot consume results before the controls
    have advanced to that frame.
    """

    def __init__(self) -> None:
        self._pending: deque[NanaAction] = deque()
        self._completed: deque[NanaActionResult] = deque()
        self._next_id = 1
        self._advanced_frame: int | None = None
        self._last_nana_player: PlayerState | None = None
        self._last_nana_frame: int | None = None
        self._captured_packet: ControllerPacket | None = None
        self._captured_frame: int | None = None

    def pending(self, frame: int) -> tuple[NanaAction, ...]:
        """Return queued actions after verifying the queue reached ``frame``."""
        self._require_frame(frame)
        return tuple(self._pending)

    def drain(self, frame: int) -> tuple[NanaActionResult, ...]:
        """Remove and return completed results after verifying ``frame``."""
        self._require_frame(frame)
        results = tuple(self._completed)
        self._completed.clear()
        return results

    def _require_frame(self, frame: int) -> None:
        if self._advanced_frame != frame:
            raise ValueError(
                "NanaActionQueue must be advanced to the requested frame through IceClimbersControls.update()"
            )

    def _schedule(self, previous_packet: ControllerPacket, current_packet: ControllerPacket, frame: int) -> None:
        action = NanaAction(
            id=self._next_id,
            input_frame=frame,
            execution_frame=frame + NANA_INPUT_DELAY_FRAMES,
            previous_packet=previous_packet,
            current_packet=current_packet,
        )
        self._next_id += 1
        self._pending.append(action)

    def _advance(
        self,
        game_state: GameState,
        port: int,
        frame_data: FrameData,
        frame: int,
        committed_packet: ControllerPacket,
    ) -> None:
        if self._advanced_frame == frame:
            return
        if self._advanced_frame is None:
            self._seed_frame(game_state, port, frame_data, frame, committed_packet)
            return
        if frame < self._advanced_frame:
            self._completed = deque(
                NanaActionResult(result.action, NanaActionStatus.RESET, None)
                if result.action.execution_frame >= frame
                else result
                for result in self._completed
            )
            self._complete_pending(NanaActionStatus.RESET)
            self._reset_tracking()
            self._seed_frame(game_state, port, frame_data, frame, committed_packet)
            return

        if frame != self._advanced_frame + 1:
            while self._pending:
                action = self._pending.popleft()
                status = NanaActionStatus.FRAME_SKIPPED if action.execution_frame < frame else NanaActionStatus.RESET
                self._completed.append(NanaActionResult(action, status, None))
            self._reset_tracking()
            self._seed_frame(game_state, port, frame_data, frame, committed_packet)
            return

        assert self._captured_packet is not None
        assert self._captured_frame == frame - 1
        self._schedule(self._captured_packet, committed_packet, frame)

        nana = CharacterState(game_state, port, frame_data=frame_data).get_nana()
        if nana is None:
            while self._pending:
                action = self._pending.popleft()
                status = NanaActionStatus.NANA_ABSENT if action.execution_frame == frame else NanaActionStatus.RESET
                self._completed.append(NanaActionResult(action, status, None))
            self._reset_tracking()
            self._captured_packet = committed_packet
            self._captured_frame = frame
            self._advanced_frame = frame
            return
        due: list[NanaAction] = []
        while self._pending and self._pending[0].execution_frame <= frame:
            due.append(self._pending.popleft())
        source_player = self._last_nana_player if self._last_nana_frame == frame - 1 else None
        for action in due:
            output = (
                None
                if source_player is None
                else _observed_action_frame_data(
                    nana,
                    frame_data,
                    source_player=source_player,
                    previous_packet=action.previous_packet,
                    current_packet=action.current_packet,
                )
            )
            self._completed.append(NanaActionResult(action, NanaActionStatus.EXECUTED, output))
        nana_player = nana.player()
        self._last_nana_player = copy.deepcopy(nana_player) if nana_player is not None else None
        self._last_nana_frame = frame if nana_player is not None else None
        self._captured_packet = committed_packet
        self._captured_frame = frame
        self._advanced_frame = frame

    def _seed_frame(
        self,
        game_state: GameState,
        port: int,
        frame_data: FrameData,
        frame: int,
        committed_packet: ControllerPacket,
    ) -> None:
        nana = CharacterState(game_state, port, frame_data=frame_data).get_nana()
        nana_player = nana.player() if nana is not None else None
        self._last_nana_player = copy.deepcopy(nana_player) if nana_player is not None else None
        self._last_nana_frame = frame if nana_player is not None else None
        self._captured_packet = committed_packet
        self._captured_frame = frame
        self._advanced_frame = frame

    def _complete_pending(self, status: NanaActionStatus) -> None:
        while self._pending:
            action = self._pending.popleft()
            self._completed.append(NanaActionResult(action, status, None))

    def _reset_tracking(self) -> None:
        self._last_nana_player = None
        self._last_nana_frame = None
        self._captured_packet = None
        self._captured_frame = None


class IceClimbersControls:
    """Apply Ice Climbers inputs without current-state actionability gates.

    Construct one instance from the raw controller and retain it for the bot's
    match. Call :meth:`update` once for every game-state snapshot before applying
    inputs. Each input is sent immediately; whole flushed Popo packets are queued
    and compared with Nana's observed action six frames later.
    This facade intentionally has no ``Hold`` lifecycle; use an input montage when
    a move needs multi-frame input ownership.
    """

    def __init__(
        self,
        controller: Controller,
        *,
        frame_data: FrameData | None = None,
    ) -> None:
        self._ice_frame_data = frame_data or FrameData()
        self._controller = controller
        self._port = controller.port
        self._controls: _IceClimbersInputControls | None = None
        self._bound_frame: int | None = None
        self._nana_action_queue = NanaActionQueue()

    @property
    def nana_action_queue(self) -> NanaActionQueue:
        """Queue of delayed Nana actions; its readers require the current frame."""
        return self._nana_action_queue

    @property
    def character_state(self) -> CharacterState:
        """Popo state bound by the latest :meth:`update` call."""
        return self._current_controls().character_state

    def update(self, game_state: GameState, frame: int) -> None:
        """Bind a snapshot and advance delayed Nana actions to ``frame``."""
        if frame != game_state.frame:
            raise ValueError("frame must match game_state.frame")
        player = game_state.players.get(self._port)
        if player is None or player.character is not Character.POPO:
            raise ValueError("IceClimbersControls requires Popo at its controller port")
        self._controls = _IceClimbersInputControls(
            game_state,
            self._port,
            self._controller,
            frame_data=self._ice_frame_data,
        )
        self._nana_action_queue._advance(
            game_state,
            self._port,
            self._ice_frame_data,
            frame,
            ControllerPacket.from_command_state(
                self._controller.prev,
                analog_input_correction_enabled=getattr(self._controller, "analog_input_correction_enabled", True),
            ),
        )
        self._bound_frame = frame

    def _frame(self) -> int:
        if self._bound_frame is None or self._controls is None:
            raise RuntimeError("IceClimbersControls.update() must bind the current frame first")
        return self._bound_frame

    def _current_controls(self) -> _IceClimbersInputControls:
        self._frame()
        assert self._controls is not None
        return self._controls

    def _record(self, operation: Callable[[], ResultT]) -> ResultT:
        self._frame()
        return operation()

    def tilt_stick(
        self,
        reference_axis: StickReferenceAxis,
        angle_degrees: float,
        *,
        magnitude: float = 1.0,
        stick: Button = Button.BUTTON_MAIN,
    ) -> ActionFrameData | None:
        return self._record(
            lambda: self._current_controls().tilt_stick(
                reference_axis,
                angle_degrees,
                magnitude=magnitude,
                stick=stick,
            ),
        )

    def tilt_analog(self, stick: Button, x: float, y: float) -> ActionFrameData | None:
        return self._record(
            lambda: self._current_controls().tilt_analog(stick, x, y),
        )

    def tilt_turn(self) -> ActionFrameData | None:
        return self._record(
            lambda: self._current_controls().tilt_turn(),
        )

    def smash_turn(self) -> ActionFrameData | None:
        return self._record(
            lambda: self._current_controls().smash_turn(),
        )

    def shield(self, strength: float) -> ActionFrameData | None:
        return self._record(
            lambda: self._current_controls().shield_once(strength),
        )

    def platform_drop(self) -> ActionFrameData | None:
        return self._record(
            lambda: self._current_controls().platform_drop_once(),
        )

    def dodge(
        self,
        direction: GroundDodgeStickReferenceAxis,
        *,
        dodge_button: Button = Button.BUTTON_L,
    ) -> ActionFrameData | None:
        return self._record(
            lambda: self._current_controls().dodge_once(
                direction,
                dodge_button=dodge_button,
            ),
        )

    def air_dodge(
        self,
        reference_axis: StickReferenceAxis,
        angle_degrees: float = 0.0,
        *,
        magnitude: float = 1.0,
        dodge_button: Button = Button.BUTTON_L,
    ) -> ActionFrameData | None:
        return self._record(
            lambda: self._current_controls().air_dodge_once(
                reference_axis,
                angle_degrees,
                magnitude=magnitude,
                dodge_button=dodge_button,
            ),
        )

    def _directional_tilt(
        self,
        method: _DirectionalTilt,
        angle_degrees: float,
        magnitude: float,
        stick: Button,
    ) -> ActionFrameData | None:
        return self._record(
            lambda: method(angle_degrees, magnitude=magnitude, stick=stick),
        )

    def down_left(
        self, angle_degrees: float, *, magnitude: float = 1.0, stick: Button = Button.BUTTON_MAIN
    ) -> ActionFrameData | None:
        return self._directional_tilt(self._current_controls().down_left, angle_degrees, magnitude, stick)

    def down_right(
        self, angle_degrees: float, *, magnitude: float = 1.0, stick: Button = Button.BUTTON_MAIN
    ) -> ActionFrameData | None:
        return self._directional_tilt(self._current_controls().down_right, angle_degrees, magnitude, stick)

    def up_left(
        self, angle_degrees: float, *, magnitude: float = 1.0, stick: Button = Button.BUTTON_MAIN
    ) -> ActionFrameData | None:
        return self._directional_tilt(self._current_controls().up_left, angle_degrees, magnitude, stick)

    def up_right(
        self, angle_degrees: float, *, magnitude: float = 1.0, stick: Button = Button.BUTTON_MAIN
    ) -> ActionFrameData | None:
        return self._directional_tilt(self._current_controls().up_right, angle_degrees, magnitude, stick)

    def left_up(
        self, angle_degrees: float, *, magnitude: float = 1.0, stick: Button = Button.BUTTON_MAIN
    ) -> ActionFrameData | None:
        return self._directional_tilt(self._current_controls().left_up, angle_degrees, magnitude, stick)

    def left_down(
        self, angle_degrees: float, *, magnitude: float = 1.0, stick: Button = Button.BUTTON_MAIN
    ) -> ActionFrameData | None:
        return self._directional_tilt(self._current_controls().left_down, angle_degrees, magnitude, stick)

    def right_up(
        self, angle_degrees: float, *, magnitude: float = 1.0, stick: Button = Button.BUTTON_MAIN
    ) -> ActionFrameData | None:
        return self._directional_tilt(self._current_controls().right_up, angle_degrees, magnitude, stick)

    def right_down(
        self, angle_degrees: float, *, magnitude: float = 1.0, stick: Button = Button.BUTTON_MAIN
    ) -> ActionFrameData | None:
        return self._directional_tilt(self._current_controls().right_down, angle_degrees, magnitude, stick)

    def press_button(self, button: Button) -> ActionFrameData | None:
        return self._record(
            lambda: self._current_controls().press_button(button),
        )

    def release_all(self) -> None:
        return self._record(
            lambda: self._current_controls().release_all(),
        )

    def attack(self, attack_type: AttackType) -> AttackFrameData | None:
        """Apply one attack-input frame and report Popo's current eligibility.

        The buttons are written even when this returns ``None`` so the same input
        can reach Nana after her delay. A returned ``AttackFrameData`` identifies
        the requested or already-active attack but does not claim that a newly
        requested move has appeared in telemetry. Use a montage rather than a
        ``Hold`` for chargeable or otherwise multi-frame attacks.
        """
        return self._record(
            lambda: self._current_controls().attack_once(attack_type),
        )

    def ledge_recovery(self, option: LedgeRecoveryOption) -> ActionFrameData | None:
        return self._record(
            lambda: self._current_controls().ledge_recovery_once(option),
        )

    def taunt(self) -> ActionFrameData | None:
        return self._record(
            lambda: self._current_controls().taunt_once(),
        )
