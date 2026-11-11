"""Samus ground-slide and platform-launch super wavedash input montage."""

from __future__ import annotations

import math
from enum import Enum, auto
from typing import Final

from melee.bot.character_state import AttackType, CharacterState
from melee.bot.input_montage import Abort, InputMontage
from melee.bot.simple_controls import SimpleControls, StickReferenceAxis
from melee.bot.stateful_input_montage import StatefulInputMontage
from melee.bot.techskill.common import (
    GROUND_MOVEMENT_ACTIONS,
    WavedashDirection,
    is_interrupted,
    player,
)
from melee.enums import Action, Button, Character, Stage
from melee.gamestate import GameState, PlayerState, StageSegment, StageSurface, StageSurfaceKind


class SWDType(Enum):
    """Samus super wavedash route."""

    Grounded = auto()
    PlatformLaunch = auto()
    Aerial = auto()


class _SuperWavedashPhase(Enum):
    BombRequested = auto()
    OppositeRequested = auto()
    DesiredRequested = auto()
    NeutralRequested = auto()
    PlatformApproach = auto()
    PlatformDrift = auto()
    PlatformBrake = auto()
    PlatformOpposite = auto()
    PlatformDesired = auto()


# NTSC 1.02 PlSs.dat: common walk_accel_mul=0.1, walk_max_vel=1;
# special x64=22, x5C=0.8. Reversing -0.8 yields -0.8 + 2.2 = +1.4.
# The two input frames therefore travel a net 0.6 toward the chosen edge.
_BOMB_WALK_SPEED: Final = 0.8
_BOMB_REVERSAL_SPEED: Final = 0.1 * 22.0 - _BOMB_WALK_SPEED
_BOMB_REVERSAL_TRAVEL: Final = _BOMB_REVERSAL_SPEED - _BOMB_WALK_SPEED
_BOMB_AIR_INITIAL_Y: Final = 0.8999999761581421
_BOMB_ECB_BOTTOM: Final = 2.0
_BOMB_ECB_HALF_WIDTH: Final = 3.0
_STATIC_GEOMETRY_STAGES: Final = frozenset({Stage.BATTLEFIELD, Stage.FINAL_DESTINATION, Stage.DREAMLAND})


def _matching_geometry(state: GameState) -> bool:
    geometry = state.stage_geometry
    if geometry is None or geometry.stage != state.stage:
        return False
    age = state.frame - geometry.requested_at_frame
    return age >= 0 and (state.stage in _STATIC_GEOMETRY_STAGES or age <= 30)


def _floor_contact_y(segment: StageSegment, x: float) -> float | None:
    """Root height where the morph ECB bottom point crosses this segment.

    mpColl_80044628_Floor sweeps bottom=(0,2) with zero expansion.
    Shared endpoints participate, but the diamond's sides cannot land.
    """
    a, b = sorted((segment.start, segment.end), key=lambda point: point.x)
    if b.x <= a.x or not a.x <= x <= b.x:
        return None
    slope = (b.y - a.y) / (b.x - a.x)
    return a.y + slope * (x - a.x) - _BOMB_ECB_BOTTOM


def _aerial_landing_surface(player_state: CharacterState, state: GameState) -> StageSurface | None:
    """Predict first floor crossing on one-based bomb frame 40, not before it."""
    value = player_state.player()
    geometry = state.stage_geometry
    if (value is None or value.on_ground or not _matching_geometry(state) or geometry is None
            or value.controller_state.button.get(Button.BUTTON_B, False)
            or value.speed_x_attack != 0 or value.speed_y_attack != 0):
        return None
    x, y = float(value.position.x), float(value.position.y)
    gravity = player_state.frame_data.characterdata[Character.SAMUS]["Gravity"]
    terminal = player_state.frame_data.characterdata[Character.SAMUS]["TerminalVelocity"]
    if not all(math.isfinite(component) for component in (x, y, value.speed_air_x_self, gravity, terminal)) or gravity <= 0 or terminal <= 0:
        return None
    vy = _BOMB_AIR_INITIAL_Y
    for frame in range(1, 41):
        previous_y = y
        vy = max(vy - gravity, -terminal)
        # Down+B and subsequent neutral packets have horizontal target zero.
        # CalcSelfAccel_AccelToVel applies -self_vel.x even with friction=0.
        y += vy
        contacts: list[tuple[float, StageSurface]] = []
        for surface in geometry.surfaces:
            for segment in surface.segments:
                left, right = sorted((segment.start.x, segment.end.x))
                if x + _BOMB_ECB_HALF_WIDTH < left or x - _BOMB_ECB_HALF_WIDTH > right:
                    continue
                if not all(math.isfinite(component) for component in (
                        segment.start.x, segment.start.y, segment.end.x, segment.end.y)):
                    return None
                if surface.kind not in {StageSurfaceKind.SOLID_FLOOR, StageSurfaceKind.SEMISOLID}:
                    # Do not predict through walls intersecting the swept body.
                    low, high = sorted((segment.start.y, segment.end.y))
                    if low <= max(y, y - vy) + 8 and high >= min(y, y - vy):
                        return None
                    continue
                contact_y = _floor_contact_y(segment, x)
                if contact_y is not None and vy < 0 and previous_y > contact_y >= y:
                    contacts.append(((previous_y - contact_y) / -vy, surface))
        if contacts:
            # Consider every segment before selecting first contact; iteration
            # order must not let a lower floor hide an earlier raised segment.
            return min(contacts, key=lambda contact: contact[0])[1] if frame == 40 else None
    return None


_BOMB_ACTIONS: Final = frozenset(
    {
        Action.SAMUS_SPECIAL_LW_BOMB,
        Action.SAMUS_SPECIAL_AIR_LW_BOMB,
    }
)


def _apply_bomb_input(controls: SimpleControls) -> None:
    controls.release_all()
    controls.tilt_stick(StickReferenceAxis.DOWN, 0.0)
    controls.press_button(Button.BUTTON_B)


def _apply_horizontal_input(
    controls: SimpleControls,
    direction: WavedashDirection,
) -> None:
    controls.release_all()
    axis = StickReferenceAxis.RIGHT if direction is WavedashDirection.Right else StickReferenceAxis.LEFT
    controls.tilt_stick(axis, 0.0)


class SuperWavedashMontage(StatefulInputMontage[_SuperWavedashPhase]):
    """Perform Samus's grounded, platform-launch, or aerial super wavedash.

    ``direction`` is the desired travel direction. The montage starts
    down-B, requests the opposite direction while observing bomb animation frame
    40, requests the travel direction on frame 41, and neutralizes on frame 42.
    Those pending inputs reach Melee on animation frames 41, 42, and 43.

    This supports standing and crouched bomb starts. Crouching skips the first two
    displayed animation frames but reaches the same frame-41/frame-42 input window.
    ``swd_type=SWDType.Aerial`` waits for an airborne initiation height predicting
    first landing on observed frame 40. It uses matching live collision segments,
    including slopes and connected junctions. Landing preserves animation time,
    rather than starting a new input window. All animation frames here are
    libmelee's one-based values, not elapsed ticks since the B press.

    ``swd_type=SWDType.PlatformLaunch`` instead approaches a flat semisolid's edge during
    morph-ball physics, reverses on the departure frame, and finishes as soon as
    an airborne burst is observed. It requires matching collision geometry and
    rejects changed surfaces, missed frames, and unsuccessful departures. Geometry
    is not frame-atomic; this stock-physics prediction still needs live validation.
    Callers own recovery after launch. No stage coordinates are hardcoded.
    """

    def __init__(
        self,
        direction: WavedashDirection,
        frame_limit: int = 64,
        cancel_montage: InputMontage | None = None,
        *,
        swd_type: SWDType = SWDType.Grounded,
    ) -> None:
        super().__init__(
            frame_limit,
            _SuperWavedashPhase.BombRequested,
            cancel_montage,
            name="Super Wavedash",
        )
        self._direction = direction
        self._swd_type = swd_type
        self._platform: StageSurface | None = None
        self._aerial_surface: StageSurface | None = None
        self._request_frame: int | None = None
        self._request_action_frame: int | None = None

    def can_start(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> bool:
        del controls, opponent_state
        player_state_value = player(player_state)
        if (player_state_value is None or player_state_value.character is not Character.SAMUS
                or player_state_value.off_stage or not player_state.can_attack(AttackType.DOWN_B)):
            return False
        match self._swd_type:
            case SWDType.Grounded:
                return player_state_value.on_ground
            case SWDType.PlatformLaunch:
                return _matching_geometry(state)
            case SWDType.Aerial:
                return _aerial_landing_surface(player_state, state) is not None

    def stateful_should_abort(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _SuperWavedashPhase,
    ) -> Abort | None:
        del controls, opponent_state, input_state
        player_state_value = player(player_state)
        if player_state_value is None:
            return Abort("player state became unavailable")
        if player_state_value.character is not Character.SAMUS:
            return Abort("player is no longer Samus")
        if player_state_value.off_stage and self._swd_type is not SWDType.PlatformLaunch:
            return Abort("player moved offstage")
        if is_interrupted(player_state, player_state_value, include_hitlag=True):
            return Abort("player was interrupted")
        if self._aerial_surface is not None and (
                not _matching_geometry(state) or state.stage_geometry is None
                or self._aerial_surface not in state.stage_geometry.surfaces):
            return Abort("aerial landing geometry changed or became unavailable")
        return None

    def stateful_on_tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _SuperWavedashPhase,
    ) -> tuple[_SuperWavedashPhase, InputMontage | bool | Abort]:
        del opponent_state
        player_state_value = player(player_state)
        if player_state_value is None:
            controls.release_all()
            return input_state, Abort("player state became unavailable")

        if self._swd_type is SWDType.PlatformLaunch and player_state_value.action in _BOMB_ACTIONS:
            return self._tick_platform_launch(controls, player_state, state, input_state)
        if self._swd_type is SWDType.PlatformLaunch and input_state is not _SuperWavedashPhase.BombRequested:
            return input_state, Abort("player left bomb state before platform launch")

        match input_state:
            case _SuperWavedashPhase.BombRequested:
                if player_state_value.action in _BOMB_ACTIONS:
                    if (self._swd_type is SWDType.Aerial and player_state_value.on_ground
                            and player_state_value.action_frame < 40):
                        return input_state, Abort("aerial bomb landed before the predicted frame-40 window")
                    return self._tick_bomb_window(controls, player_state_value)
                if self._swd_type is SWDType.Aerial:
                    if self._aerial_surface is not None:
                        return input_state, Abort("aerial bomb input did not begin on the scheduled frame")
                    self._aerial_surface = _aerial_landing_surface(player_state, state)
                    if self._aerial_surface is None:
                        return input_state, Abort("aerial bomb initiation window is unavailable")
                if player_state.can_attack(AttackType.DOWN_B):
                    _apply_bomb_input(controls)
                    return input_state, self
                controls.release_all()
                return input_state, Abort("bomb did not begin")
            case _SuperWavedashPhase.OppositeRequested:
                if player_state_value.action not in _BOMB_ACTIONS or player_state_value.action_frame != 41:
                    controls.release_all()
                    return input_state, Abort("frame-42 direction window was missed")
                if (
                    player_state_value.action is not Action.SAMUS_SPECIAL_LW_BOMB
                    or not player_state_value.on_ground
                ):
                    controls.release_all()
                    return input_state, Abort(
                        "Samus was not in grounded bomb state during the frame-42 direction window"
                    )
                _apply_horizontal_input(controls, self._direction)
                return _SuperWavedashPhase.DesiredRequested, self
            case _SuperWavedashPhase.DesiredRequested:
                controls.release_all()
                if player_state_value.action not in _BOMB_ACTIONS or player_state_value.action_frame != 42:
                    return input_state, Abort("post-input neutral frame was missed")
                return _SuperWavedashPhase.NeutralRequested, self
            case _SuperWavedashPhase.NeutralRequested:
                controls.release_all()
                if player_state_value.action in _BOMB_ACTIONS:
                    return input_state, self
                if player_state_value.on_ground and player_state_value.action in GROUND_MOVEMENT_ACTIONS:
                    return input_state, True
                return input_state, Abort("bomb ended outside actionable ground movement")
            case _:
                return input_state, Abort("unexpected super wavedash phase")

    def _tick_bomb_window(
        self,
        controls: SimpleControls,
        player_state_value: PlayerState,
    ) -> tuple[_SuperWavedashPhase, InputMontage | Abort]:
        if player_state_value.action_frame < 40:
            controls.release_all()
            return _SuperWavedashPhase.BombRequested, self
        if player_state_value.action_frame > 40:
            controls.release_all()
            return _SuperWavedashPhase.BombRequested, Abort("frame-41 opposite-direction window was missed")
        if (
            player_state_value.action is not Action.SAMUS_SPECIAL_LW_BOMB
            or not player_state_value.on_ground
        ):
            controls.release_all()
            return _SuperWavedashPhase.BombRequested, Abort(
                "Samus was not in grounded bomb state during the frame-41 opposite-direction window"
            )

        # DESNOTE(jbarber, 2026-11-07): Bot input is committed by the next
        # Console.step. Observed animation frames 40 and 41 therefore schedule
        # the opposite/desired inputs for Samus bomb frames 41 and 42. Slippi's
        # post-frame state is captured after collision, so the standard route has
        # already changed from airborne state 356 to grounded state 355 by frame
        # 40. Aerial entry and crouched entry use the same animation window;
        # AirToGroundStateChange preserves cur_anim_frame. Samus's actiondata.csv
        # rows 355/356 are already one-based (zeroindex=False): do not add one.
        # See https://www.ssbwiki.com/Super_wavedash and
        # https://github.com/doldecomp/melee/blob/2f8eab8ebd7a2d25541e125abfa246defe1bacec/src/melee/ft/kinds/ftSamus/ftsamusspeciallw1.c
        # https://github.com/project-slippi/slippi-wiki/blob/master/SPEC.md#post-frame-update
        opposite = WavedashDirection.Left if self._direction is WavedashDirection.Right else WavedashDirection.Right
        _apply_horizontal_input(controls, opposite)
        return _SuperWavedashPhase.OppositeRequested, self

    def _tick_platform_launch(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        state: GameState,
        phase: _SuperWavedashPhase,
    ) -> tuple[_SuperWavedashPhase, InputMontage | bool | Abort]:
        value = player_state.player()
        controls.release_all()
        if value is None:
            return phase, Abort("player state became unavailable")
        geometry = state.stage_geometry
        if geometry is None or geometry.stage != state.stage:
            return phase, Abort("matching platform geometry is unavailable")
        age = state.frame - geometry.requested_at_frame
        if age < 0 or (state.stage not in {Stage.BATTLEFIELD, Stage.FINAL_DESTINATION, Stage.DREAMLAND} and age > 30):
            return phase, Abort("platform geometry is stale or future-dated")
        if self._platform is not None and self._platform not in geometry.surfaces:
            return phase, Abort("launch platform changed")

        if phase in {_SuperWavedashPhase.PlatformOpposite, _SuperWavedashPhase.PlatformDesired}:
            if (self._request_frame is None or self._request_action_frame is None
                    or state.frame != self._request_frame + 1
                    or value.action_frame != self._request_action_frame + 1):
                return phase, Abort("platform reversal input frame was missed")
        sign = 1.0 if self._direction is WavedashDirection.Right else -1.0
        if phase is _SuperWavedashPhase.PlatformDesired:
            if (not value.on_ground and value.action is Action.SAMUS_SPECIAL_AIR_LW_BOMB
                    and math.isfinite(value.speed_air_x_self)
                    and sign * value.speed_air_x_self > _BOMB_WALK_SPEED):
                return phase, True
            return phase, Abort("reversal did not produce an airborne platform burst")

        # PlSs scripts set command0 at frame 10 and clear it at 43. Use 10..39 in the
        # one-based animation domain, leaving time for the two reversal inputs.
        if value.action_frame >= 40:
            return phase, Abort("platform launch morph window was missed")
        if phase is _SuperWavedashPhase.BombRequested:
            phase = _SuperWavedashPhase.PlatformApproach
        if phase is _SuperWavedashPhase.PlatformApproach:
            if not value.on_ground or value.action_frame < 10:
                return phase, self
            surface = player_state.current_stage_surface
            if surface is None or surface.kind is not StageSurfaceKind.SEMISOLID:
                return phase, Abort("platform launch requires a semisolid surface")
            points = tuple(point for segment in surface.segments for point in (segment.start, segment.end))
            if (not all(math.isfinite(point.x) and math.isfinite(point.y) for point in points)
                    or any(point.y != points[0].y for point in points)
                    or abs(float(value.position.y) - points[0].y) > 0.001):
                return phase, Abort("platform launch requires a flat finite surface")
            self._platform = surface
            # One neutral packet removes inherited grounded momentum.
            return _SuperWavedashPhase.PlatformDrift, self
        if (value.action is not Action.SAMUS_SPECIAL_LW_BOMB or not value.on_ground
                or player_state.current_stage_surface != self._platform):
            return phase, Abort("player left the launch platform before reversal")
        if self._platform is None:
            return phase, Abort("launch platform is unavailable")
        xs = tuple(point.x for segment in self._platform.segments for point in (segment.start, segment.end))
        left, right = min(xs), max(xs)
        x = float(value.position.x)
        distance = right - x if sign > 0 else x - left
        opposite_clearance = x - left if sign > 0 else right - x
        if (not all(math.isfinite(component) for component in (
                x, float(value.speed_ground_x_self), float(value.speed_air_x_self)))
                or not 0 < distance
                or (phase is not _SuperWavedashPhase.PlatformOpposite and opposite_clearance <= _BOMB_WALK_SPEED)):
            return phase, Abort("insufficient platform clearance for reversal")
        match phase:
            case _SuperWavedashPhase.PlatformDrift:
                if distance < _BOMB_REVERSAL_TRAVEL:
                    return _SuperWavedashPhase.PlatformBrake, self
                axis = StickReferenceAxis.RIGHT if sign > 0 else StickReferenceAxis.LEFT
                # Approach by at most half the remaining distance; no guessed
                # stage-specific X coordinate or full-speed step over the edge.
                controls.tilt_stick(axis, 0.0, magnitude=min(1.0, distance / (2 * _BOMB_WALK_SPEED)))
                return phase, self
            case _SuperWavedashPhase.PlatformBrake:
                if abs(value.speed_ground_x_self) > 0.0001 or distance >= _BOMB_REVERSAL_TRAVEL:
                    return phase, Abort("platform brake did not establish the reversal position")
                opposite = WavedashDirection.Left if sign > 0 else WavedashDirection.Right
                _apply_horizontal_input(controls, opposite)
                self._request_frame = state.frame
                self._request_action_frame = value.action_frame
                return _SuperWavedashPhase.PlatformOpposite, self
            case _SuperWavedashPhase.PlatformOpposite:
                if (abs(value.speed_ground_x_self + sign * _BOMB_WALK_SPEED) > 0.0001
                        or distance >= _BOMB_REVERSAL_SPEED):
                    return phase, Abort("opposite input did not establish the platform burst")
                _apply_horizontal_input(controls, self._direction)
                self._request_frame = state.frame
                self._request_action_frame = value.action_frame
                return _SuperWavedashPhase.PlatformDesired, self
            case _:
                return phase, Abort("unexpected platform launch phase")


__all__ = ["SWDType", "SuperWavedashMontage"]
