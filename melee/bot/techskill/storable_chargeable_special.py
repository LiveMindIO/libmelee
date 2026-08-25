"""Montages for chargeable specials that Melee can store between uses."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum, auto
from typing import Final, Self

from melee.bot.character_state import AttackType, CharacterState
from melee.bot.input_montage import Abort, InputMontage, MontageState
from melee.bot.simple_controls import SimpleControls
from melee.bot.stateful_input_montage import StatefulInputMontage
from melee.bot.techskill.common import is_interrupted, player
from melee.enums import Action, Button, Character
from melee.gamestate import GameState, PlayerState


class ChargeStoreInput(Enum):
    """In-game transition used to cancel and preserve a neutral-B charge."""

    SHIELD = auto()
    GRAB = auto()
    ROLL_FORWARD = auto()
    ROLL_BACKWARD = auto()


class _ChargeIntent(Enum):
    Fire = auto()
    Store = auto()


class _ChargePhase(Enum):
    Starting = auto()
    Charging = auto()
    Transitioning = auto()


@dataclass(frozen=True)
class _ChargeConfig:
    name: str
    character: Character
    max_charge: int
    start_actions: frozenset[Action]
    loop_actions: frozenset[Action]
    full_actions: frozenset[Action]
    fire_actions: frozenset[Action]
    store_actions: frozenset[Action]
    hold_b: bool
    fire_with_button: bool
    supports_grab_store: bool
    supports_roll_store: bool
    supports_air_charge: bool
    auto_store_at_full: bool
    minimum_charge: int = 0
    transition_wait_limit: int = 3


@dataclass(frozen=True)
class _ChargeState:
    phase: _ChargePhase = _ChargePhase.Starting
    raw_charge: int | None = None
    transition_ready: bool = False
    on_ground: bool = True
    transition_wait_frames: int = 0


_ROLL_ACTIONS: Final = frozenset({Action.ROLL_FORWARD, Action.ROLL_BACKWARD})
_FRAME_LIMIT: Final = 60 * 60
_START_WAIT_LIMIT: Final = 3


_DK_CONFIG: Final = _ChargeConfig(
    name="Giant Punch",
    character=Character.DK,
    max_charge=10,
    start_actions=frozenset({Action(369), Action(374)}),
    loop_actions=frozenset({Action(370), Action(375)}),
    full_actions=frozenset(),
    fire_actions=frozenset({Action(372), Action(373), Action(377), Action(378)}),
    store_actions=frozenset({Action(371), Action(376)}),
    hold_b=False,
    fire_with_button=True,
    supports_grab_store=True,
    supports_roll_store=True,
    supports_air_charge=True,
    auto_store_at_full=True,
    transition_wait_limit=120,
)
_SAMUS_CONFIG: Final = _ChargeConfig(
    name="Charge Shot",
    character=Character.SAMUS,
    max_charge=7,
    start_actions=frozenset({Action(343)}),
    loop_actions=frozenset({Action(344)}),
    full_actions=frozenset(),
    fire_actions=frozenset({Action(346), Action(347), Action(348)}),
    store_actions=frozenset({Action(345)}),
    hold_b=False,
    fire_with_button=True,
    supports_grab_store=True,
    supports_roll_store=True,
    supports_air_charge=False,
    auto_store_at_full=True,
)
_SHEIK_CONFIG: Final = _ChargeConfig(
    name="Needle Storm",
    character=Character.SHEIK,
    max_charge=6,
    start_actions=frozenset({Action(341), Action(345)}),
    loop_actions=frozenset({Action(342), Action(346)}),
    full_actions=frozenset(),
    fire_actions=frozenset({Action(344), Action(348)}),
    store_actions=frozenset({Action(343), Action(347)}),
    hold_b=True,
    fire_with_button=False,
    supports_grab_store=True,
    supports_roll_store=False,
    supports_air_charge=True,
    auto_store_at_full=False,
    minimum_charge=1,
)
_MEWTWO_CONFIG: Final = _ChargeConfig(
    name="Shadow Ball",
    character=Character.MEWTWO,
    max_charge=7,
    start_actions=frozenset({Action(341), Action(346)}),
    loop_actions=frozenset({Action(342), Action(347)}),
    full_actions=frozenset({Action(343), Action(348)}),
    fire_actions=frozenset({Action(345), Action(350)}),
    store_actions=frozenset({Action(344), Action(349)}),
    hold_b=False,
    fire_with_button=True,
    supports_grab_store=False,
    supports_roll_store=True,
    supports_air_charge=True,
    auto_store_at_full=False,
)


class _StorableChargeableSpecialMontage(StatefulInputMontage[_ChargeState]):
    """Internal shared state machine; concrete fighter classes are public."""

    def __init__(self, config: _ChargeConfig) -> None:
        super().__init__(_FRAME_LIMIT, _ChargeState(), name=config.name)
        self._config = config
        self._intent: _ChargeIntent | None = None
        self._store_input = ChargeStoreInput.SHIELD

    def fire(self) -> Self:
        """Queue firing, unless a prior transition input is already committed."""
        if (
            self.get_montage_state() in {MontageState.Waiting, MontageState.Active}
            and self._input_state.phase is not _ChargePhase.Transitioning
        ):
            self._intent = _ChargeIntent.Fire
        return self

    def can_fire(self) -> bool:
        """Return whether :meth:`fire` can transition on the next active tick."""
        return (
            self.get_montage_state() is MontageState.Active
            and self._input_state.phase is _ChargePhase.Charging
            and self._input_state.transition_ready
            and self.current_power() is not None
        )

    def store(self, transition: ChargeStoreInput = ChargeStoreInput.SHIELD) -> Self:
        """Queue an in-game charge-preserving cancel and return ``self``.

        Shield uses L, grab uses Z, and roll uses a facing-relative horizontal
        main-stick input. Mewtwo rejects grab because Z synthesizes A and fires
        Shadow Ball before its shoulder-cancel check. Sheik rejects roll because
        Needle Storm has no direct roll transition. Once a fire or store input is
        committed, later requests do not replace that in-flight transition.
        """
        self._validate_store_input(transition)
        if (
            self.get_montage_state() in {MontageState.Waiting, MontageState.Active}
            and self._input_state.phase is not _ChargePhase.Transitioning
        ):
            self._intent = _ChargeIntent.Store
            self._store_input = transition
        return self

    def can_store(self, transition: ChargeStoreInput = ChargeStoreInput.SHIELD) -> bool:
        """Return whether the requested storage transition can commit next tick."""
        if not self._store_input_supported(transition):
            return False
        return (
            self.get_montage_state() is MontageState.Active
            and self._input_state.phase is _ChargePhase.Charging
            and self._input_state.transition_ready
            and (
                transition not in {ChargeStoreInput.ROLL_FORWARD, ChargeStoreInput.ROLL_BACKWARD}
                or self._input_state.on_ground
            )
            and self.current_power() is not None
        )

    def current_power(self) -> float | None:
        """Return exact normalized stored charge from Gecko telemetry."""
        raw_charge = self._input_state.raw_charge
        if raw_charge is None:
            return None
        charge_span = self._config.max_charge - self._config.minimum_charge
        if charge_span <= 0:
            return 1.0
        normalized_charge = max(raw_charge, self._config.minimum_charge)
        return min(
            1.0,
            max(0.0, (normalized_charge - self._config.minimum_charge) / charge_span),
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
            or player_state_value.character is not self._config.character
            or player_state_value.neutral_b_charge is None
        ):
            return False
        if (
            player_state_value.neutral_b_charge >= self._config.max_charge
            and self._config.character in {Character.DK, Character.SAMUS, Character.MEWTWO}
            and self._intent is not _ChargeIntent.Fire
        ):
            return False
        if (
            not player_state_value.on_ground
            and not self._config.supports_air_charge
            and self._intent is not _ChargeIntent.Fire
        ):
            return False
        return player_state.can_attack(AttackType.NEUTRAL_B)

    def stateful_should_abort(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _ChargeState,
    ) -> Abort | None:
        del controls, opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None:
            return Abort("player state became unavailable")
        if player_state_value.character is not self._config.character:
            return Abort("player character changed")
        if player_state_value.neutral_b_charge is None:
            return Abort("neutral-B charge telemetry became unavailable")
        if (
            input_state.phase in {_ChargePhase.Starting, _ChargePhase.Charging}
            and not self._config.supports_air_charge
            and not player_state_value.on_ground
            and self._intent is not _ChargeIntent.Fire
        ):
            return Abort("player left the ground while neutral-B charge was active")
        if is_interrupted(player_state, player_state_value, include_hitlag=False):
            return Abort("player was interrupted")
        return None

    def stateful_on_tick(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _ChargeState,
    ) -> tuple[_ChargeState, InputMontage | bool | Abort]:
        del opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None or player_state_value.neutral_b_charge is None:
            return input_state, Abort("neutral-B charge telemetry became unavailable")
        input_state = replace(
            input_state,
            raw_charge=player_state_value.neutral_b_charge,
            on_ground=player_state_value.on_ground,
        )

        if input_state.phase is _ChargePhase.Starting:
            controls.release_all()
            controls.press_button(Button.BUTTON_B)
            return replace(input_state, phase=_ChargePhase.Charging), self

        if input_state.phase is _ChargePhase.Transitioning:
            return self._tick_transition(controls, player_state_value, input_state)

        action = player_state_value.action
        if action in self._config.fire_actions:
            if self._intent is _ChargeIntent.Fire:
                return input_state, True
            return input_state, Abort("neutral-B fired instead of storing charge")
        if action in self._config.store_actions:
            if self._intent is _ChargeIntent.Store:
                return input_state, True
            if (
                self._intent is None
                and self._config.auto_store_at_full
                and player_state_value.neutral_b_charge >= self._config.max_charge
            ):
                return input_state, True
            return input_state, Abort("neutral-B charge was stored instead of firing")
        if (
            self._config.auto_store_at_full
            and player_state_value.neutral_b_charge >= self._config.max_charge
            and action not in self._config.start_actions | self._config.loop_actions
        ):
            if self._intent is _ChargeIntent.Fire:
                return input_state, Abort("neutral-B charge was stored instead of firing")
            return input_state, True

        transition_ready = action in self._config.loop_actions | self._config.full_actions
        input_state = replace(
            input_state,
            transition_ready=transition_ready,
            transition_wait_frames=(
                0
                if action in self._config.start_actions | self._config.loop_actions | self._config.full_actions
                else input_state.transition_wait_frames
            ),
        )
        roll_waiting_for_ground = (
            self._intent is _ChargeIntent.Store
            and self._store_input in {ChargeStoreInput.ROLL_FORWARD, ChargeStoreInput.ROLL_BACKWARD}
            and not player_state_value.on_ground
        )
        if transition_ready and self._intent is not None and not roll_waiting_for_ground:
            if self._intent is _ChargeIntent.Fire:
                self._apply_fire_input(controls)
            else:
                self._apply_store_input(controls, player_state)
            return (
                replace(
                    input_state,
                    phase=_ChargePhase.Transitioning,
                    transition_wait_frames=0,
                ),
                self,
            )

        if action in self._config.start_actions | self._config.loop_actions | self._config.full_actions:
            self._apply_charge_input(controls)
            return input_state, self
        if input_state.transition_wait_frames >= _START_WAIT_LIMIT:
            return input_state, Abort("neutral-B charge did not start")
        self._apply_charge_input(controls)
        return (
            replace(
                input_state,
                transition_wait_frames=input_state.transition_wait_frames + 1,
            ),
            self,
        )

    def _tick_transition(
        self,
        controls: SimpleControls,
        player_state_value: PlayerState,
        input_state: _ChargeState,
    ) -> tuple[_ChargeState, InputMontage | bool | Abort]:
        controls.release_all()
        action = player_state_value.action
        if action in self._config.fire_actions:
            if self._intent is _ChargeIntent.Fire:
                return input_state, True
            return input_state, Abort("neutral-B fired instead of storing charge")
        if action in self._config.store_actions or action in _ROLL_ACTIONS:
            if self._intent is _ChargeIntent.Store:
                return input_state, True
            return input_state, Abort("neutral-B charge was stored instead of firing")
        if (
            self._intent is _ChargeIntent.Store
            and self._config.auto_store_at_full
            and player_state_value.neutral_b_charge is not None
            and player_state_value.neutral_b_charge >= self._config.max_charge
            and action not in self._config.start_actions | self._config.loop_actions
        ):
            return input_state, True
        if input_state.transition_wait_frames < self._config.transition_wait_limit:
            return (
                replace(
                    input_state,
                    transition_wait_frames=input_state.transition_wait_frames + 1,
                ),
                self,
            )
        transition_name = "fire" if self._intent is _ChargeIntent.Fire else "store"
        return input_state, Abort(f"neutral-B {transition_name} transition did not start")

    def _apply_charge_input(self, controls: SimpleControls) -> None:
        controls.release_all()
        if self._config.hold_b:
            controls.press_button(Button.BUTTON_B)

    def _apply_fire_input(self, controls: SimpleControls) -> None:
        controls.release_all()
        if self._config.fire_with_button:
            controls.press_button(Button.BUTTON_B)

    def _apply_store_input(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
    ) -> None:
        controls.release_all()
        if self._config.hold_b:
            controls.press_button(Button.BUTTON_B)
        match self._store_input:
            case ChargeStoreInput.SHIELD:
                controls.press_button(Button.BUTTON_L)
            case ChargeStoreInput.GRAB:
                controls.press_button(Button.BUTTON_Z)
            case ChargeStoreInput.ROLL_FORWARD:
                controls.tilt_stick(player_state.forward_axis(), 0.0)
            case ChargeStoreInput.ROLL_BACKWARD:
                controls.tilt_stick(player_state.backward_axis(), 0.0)

    def _validate_store_input(self, transition: ChargeStoreInput) -> None:
        if not self._store_input_supported(transition):
            raise ValueError(f"{transition.name} cannot store {self._config.character.name} neutral-B charge")

    def _store_input_supported(self, transition: ChargeStoreInput) -> bool:
        if transition is ChargeStoreInput.GRAB:
            return self._config.supports_grab_store
        if transition in {ChargeStoreInput.ROLL_FORWARD, ChargeStoreInput.ROLL_BACKWARD}:
            return self._config.supports_roll_store
        return True


class DonkeyKongGiantPunchMontage(_StorableChargeableSpecialMontage):
    """Charge, fire, or store Donkey Kong's ten-wind Giant Punch."""

    def __init__(self) -> None:
        super().__init__(_DK_CONFIG)


class SamusChargeShotMontage(_StorableChargeableSpecialMontage):
    """Charge, fire, or store Samus's seven-level Charge Shot."""

    def __init__(self) -> None:
        super().__init__(_SAMUS_CONFIG)


class SheikNeedleStormMontage(_StorableChargeableSpecialMontage):
    """Charge, fire, or store Sheik's one-to-six-needle volley."""

    def __init__(self) -> None:
        super().__init__(_SHEIK_CONFIG)


class MewtwoShadowBallMontage(_StorableChargeableSpecialMontage):
    """Charge, fire, or store Mewtwo's seven-level Shadow Ball."""

    def __init__(self) -> None:
        super().__init__(_MEWTWO_CONFIG)


__all__ = [
    "ChargeStoreInput",
    "DonkeyKongGiantPunchMontage",
    "MewtwoShadowBallMontage",
    "SamusChargeShotMontage",
    "SheikNeedleStormMontage",
]
