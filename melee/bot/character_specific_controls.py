"""Character-specific attack overrides for :class:`SimpleControls`.

libmelee's ``Action`` enum names are Fox/Marth-centric, so many characters need
custom recognition or sustained input for specials. Implementations return
:data:`NO_OVERRIDE` for moves they do not handle so :class:`SimpleControls` can
fall back to the standard path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Protocol

from melee.controller import Controller
from melee.enums import Action, Button, Character
from melee.framedata import FrameData
from melee.gamestate import GameState, PlayerState as LibPlayerState

from melee.bot.simple_controls import (
    AttackFrameData,
    AttackType,
    Hold,
    CharacterStatus,
    can_attack,
)

# Ground locomotion plus active hand-slap animations (sustained down+B).
_HAND_SLAP_ACTIONS: Final = frozenset(
    {
        Action.DK_GROUND_POUND_START,
        Action.DK_GROUND_POUND,
        Action.DK_GROUND_POUND_END,
    }
)
_HAND_SLAP_READY_ACTIONS: Final = frozenset(
    {
        Action.STANDING,
        Action.WALK_SLOW,
        Action.WALK_MIDDLE,
        Action.WALK_FAST,
        Action.TURNING,
        Action.TURNING_RUN,
        Action.DASHING,
        Action.RUNNING,
        Action.RUN_DIRECT,
        Action.RUN_BRAKE,
        Action.KNEE_BEND,
        Action.CROUCH_START,
        Action.CROUCHING,
        Action.CROUCH_END,
        Action.LANDING,
        Action.LANDING_SPECIAL,
    }
) | _HAND_SLAP_ACTIONS
_GRABBER_ACTIONS: Final = frozenset(
    {
        Action.GRAB,
        Action.GRAB_PULLING,
        Action.GRAB_RUNNING,
        Action.GRAB_RUNNING_PULLING,
        Action.GRAB_WAIT,
        Action.GRAB_PUMMEL,
    }
)
_GRABBED_VICTIM_ACTIONS: Final = frozenset(
    {
        Action.GRABBED,
        Action.GRABBED_WAIT_HIGH,
        Action.GRAB_PULL,
        Action.GRAB_PUMMELED,
        Action.PUMMELED_HIGH,
        Action.GRAB_ESCAPE,
        Action.GRAB_NECK,
        Action.GRAB_FOOT,
    }
)
_GRAB_THROW_INPUT_ACTIONS: Final = frozenset({Action.GRAB_WAIT, Action.GRAB_PUMMEL})
_DK_CARGO_CARRY_ACTIONS: Final = frozenset({Action.GRAB_JUMP})


@dataclass(frozen=True, slots=True)
class NoOverride:
    """Sentinel: delegate to standard :class:`SimpleControls` behavior."""


NO_OVERRIDE = NoOverride()

CharacterSpecificAttackResult = None | Hold | AttackFrameData | NoOverride
CharacterSpecificCheckHoldResult = bool | NoOverride
CharacterSpecificReleaseResult = None | AttackFrameData | NoOverride
CharacterSpecificStateResult = CharacterStatus | NoOverride


class CharacterSpecificControls(Protocol):
    """Optional per-character overrides for :class:`SimpleControls` methods."""

    def attack(
        self,
        attack_type: AttackType,
        *,
        hold: Hold | None = None,
    ) -> CharacterSpecificAttackResult:
        """Handle ``attack_type`` or return :data:`NO_OVERRIDE`."""
        ...

    def check_hold(self, hold: Hold) -> CharacterSpecificCheckHoldResult:
        """Validate ``hold`` or return :data:`NO_OVERRIDE`."""
        ...

    def release(self, hold: Hold) -> CharacterSpecificReleaseResult:
        """Release a charging hold or return :data:`NO_OVERRIDE`."""
        ...

    def get_state(
        self,
        player: LibPlayerState | None = None,
    ) -> CharacterSpecificStateResult:
        """Return high-level player state or :data:`NO_OVERRIDE`."""
        ...


class DonkeyKongCharacterSpecificControls(CharacterSpecificControls):
    """Donkey Kong overrides for Hand Slap and cargo carry."""

    def __init__(
        self,
        game_state: GameState,
        port: int,
        controller: Controller,
        frame_data: FrameData,
    ) -> None:
        self._game_state = game_state
        self._port = port
        self._controller = controller
        self._frame_data = frame_data

    def attack(
        self,
        attack_type: AttackType,
        *,
        hold: Hold | None = None,
    ) -> CharacterSpecificAttackResult:
        if attack_type is AttackType.FTHROW:
            return self._attack_forward_cargo(hold)
        if attack_type is not AttackType.DOWN_B:
            return NO_OVERRIDE

        player = self._player()
        if player is None:
            return None

        if hold is not None:
            if not self._hold_matches(hold):
                return None
            hold_valid = self.check_hold(hold)
            if hold_valid is NO_OVERRIDE or not hold_valid:
                return None
            return self._apply_hand_slap(player)

        if not self._can_hold_hand_slap(player):
            return None

        return self._apply_hand_slap(player)

    def check_hold(self, hold: Hold) -> CharacterSpecificCheckHoldResult:
        if hold.attack_type is AttackType.FTHROW:
            if hold.released:
                return False

            player = self._player()
            if player is None:
                return False
            if player.character is not Character.DK or self._port != hold.port:
                return False
            return self._can_continue_forward_cargo(player)

        if hold.attack_type is not AttackType.DOWN_B:
            return NO_OVERRIDE

        if hold.released:
            return False

        player = self._player()
        if player is None:
            return False
        if player.character is not Character.DK or self._port != hold.port:
            return False
        if self._hand_slap_interrupted(player):
            return False

        return self._can_hold_hand_slap(player)

    def release(self, hold: Hold) -> CharacterSpecificReleaseResult:
        _ = hold
        return NO_OVERRIDE

    def get_state(
        self,
        player: LibPlayerState | None = None,
    ) -> CharacterSpecificStateResult:
        _ = player
        return NO_OVERRIDE

    def _player(self) -> LibPlayerState | None:
        return self._game_state.players.get(self._port)

    def _hold_matches(self, hold: Hold, attack_type: AttackType = AttackType.DOWN_B) -> bool:
        return (
            hold.attack_type == attack_type
            and hold.port == self._port
            and not hold.released
        )

    def _can_hold_hand_slap(self, player: LibPlayerState) -> bool:
        return (
            player.on_ground
            and isinstance(player.action, Action)
            and player.action in _HAND_SLAP_READY_ACTIONS
        )

    def _can_start_forward_cargo(self, player: LibPlayerState) -> bool:
        return isinstance(player.action, Action) and (
            player.action in _GRAB_THROW_INPUT_ACTIONS
        )

    def _can_continue_forward_cargo(self, player: LibPlayerState) -> bool:
        if not can_attack(player, self._frame_data):
            return False
        if player.action in _GRABBED_VICTIM_ACTIONS:
            return False
        return isinstance(player.action, Action) and (
            player.action in _GRAB_THROW_INPUT_ACTIONS
            or player.action in _DK_CARGO_CARRY_ACTIONS
        )

    def _hand_slap_interrupted(self, player: LibPlayerState) -> bool:
        if not can_attack(player, self._frame_data):
            return True
        return player.action in _GRABBER_ACTIONS

    def _apply_hand_slap(self, player: LibPlayerState) -> Hold | AttackFrameData:
        self._controller.release_all()
        self._controller.tilt_analog(Button.BUTTON_MAIN, 0.5, 0.0)
        self._controller.press_button(Button.BUTTON_B)

        if isinstance(player.action, Action) and player.action in _HAND_SLAP_ACTIONS:
            return AttackFrameData(
                character=player.character,
                action=player.action,
                frame_data=self._frame_data,
            )

        return Hold(
            attack_type=AttackType.DOWN_B,
            character=player.character,
            action=Action.DK_GROUND_POUND_START,
            frame_data=self._frame_data,
            max_hold_frames=0,
            started_frame=self._game_state.frame,
            stick_x=0.5,
            stick_y=0.0,
            port=self._port,
            charging=False,
        )

    def _attack_forward_cargo(
        self,
        hold: Hold | None,
    ) -> CharacterSpecificAttackResult:
        player = self._player()
        if player is None:
            return None

        if isinstance(player.action, Action) and player.action in _DK_CARGO_CARRY_ACTIONS:
            return AttackFrameData(
                character=player.character,
                action=player.action,
                frame_data=self._frame_data,
            )

        if hold is not None:
            if not self._hold_matches(hold, AttackType.FTHROW):
                return None
            hold_valid = self.check_hold(hold)
            if hold_valid is NO_OVERRIDE or not hold_valid:
                return None
            return self._apply_forward_cargo_input(player)

        if not self._can_start_forward_cargo(player):
            return None

        return self._apply_forward_cargo_input(player)

    def _apply_forward_cargo_input(self, player: LibPlayerState) -> Hold:
        forward = 1.0 if player.facing else 0.0
        self._controller.release_all()
        self._controller.tilt_analog(Button.BUTTON_MAIN, forward, 0.5)

        return Hold(
            attack_type=AttackType.FTHROW,
            character=player.character,
            action=Action.GRAB_JUMP,
            frame_data=self._frame_data,
            max_hold_frames=0,
            started_frame=self._game_state.frame,
            stick_x=forward,
            stick_y=0.5,
            port=self._port,
            charging=False,
        )


class CharacterSpecificControlsFactory:
    """Build per-character :class:`CharacterSpecificControls` handlers."""

    @staticmethod
    def create(
        character: Character,
        *,
        game_state: GameState,
        port: int,
        controller: Controller,
        frame_data: FrameData,
    ) -> CharacterSpecificControls | None:
        """Return character overrides, or ``None`` when standard controls suffice."""
        if character is Character.DK:
            return DonkeyKongCharacterSpecificControls(
                game_state,
                port,
                controller,
                frame_data,
            )
        return None
