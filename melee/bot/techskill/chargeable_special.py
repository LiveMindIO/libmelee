"""Caller-released chargeable special montages."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum, auto
from typing import Final, Self, cast

from melee.bot.character_state import (
    AttackType,
    CharacterState,
    HorizontalStickReferenceAxis,
)
from melee.bot.input_montage import Abort, InputMontage, MontageState
from melee.bot.simple_controls import SimpleControls
from melee.bot.stateful_input_montage import StatefulInputMontage
from melee.bot.techskill.common import is_interrupted, player
from melee.enums import Action, Button, Character
from melee.gamestate import GameState


class _ChargeableSpecialPhase(Enum):
    Preparing = auto()
    Starting = auto()
    Charging = auto()
    Released = auto()


@dataclass(frozen=True)
class _ChargeableSpecialConfig:
    name: str
    characters: frozenset[Character]
    attack_type: AttackType
    start_actions: frozenset[Action]
    charge_actions: frozenset[Action]
    full_hold_actions: frozenset[Action]
    completion_actions: frozenset[Action]
    initial_charge: int
    charge_increment: int
    power_floor: int
    full_charge: tuple[tuple[Character, int], ...]
    prepare_side_input: bool = False


@dataclass(frozen=True)
class _ChargeableSpecialState:
    phase: _ChargeableSpecialPhase
    character: Character | None = None
    input_started: bool = False
    charge: int | None = None
    preparation_frames: int = 0
    transition_wait_frames: int = 0


_FRAME_LIMIT: Final = 60 * 60
_START_WAIT_LIMIT: Final = 3
_RELEASE_WAIT_LIMIT: Final = 3
_NO_SMASH_BONUS_PREP_FRAMES: Final = 4

# DESNOTE(jbarber, 2026-08-23): These counters and transitions come from each
# fighter's NTSC 1.02 DAT attributes and doldecomp callbacks. Side-B montages
# either reset the stick before side-B to grant the x673-based 20-count smash
# bonus, or hold the direction through that timer before pressing B to suppress
# it. The first observed hold packet is counted as one animation callback; live
# packet alignment still needs Dolphin validation. See:
# https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftPurin/ftPr_SpecialN.c
# https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftLuigi/ftLg_SpecialS.c
# https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftPikachu/ftPk_SpecialS.c
# https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/chara/ftMars/ftMs_SpecialN.c
_ROLLOUT_CONFIG: Final = _ChargeableSpecialConfig(
    name="Rollout",
    characters=frozenset({Character.JIGGLYPUFF}),
    attack_type=AttackType.NEUTRAL_B,
    start_actions=frozenset({Action(346), Action(347), Action(354), Action(355)}),
    charge_actions=frozenset({Action(348), Action(356)}),
    full_hold_actions=frozenset({Action(349), Action(357)}),
    completion_actions=frozenset({Action(350), Action(358), Action(362)}),
    initial_charge=50,
    charge_increment=3,
    power_floor=50,
    full_charge=((Character.JIGGLYPUFF, 180),),
)
_GREEN_MISSILE_CONFIG: Final = _ChargeableSpecialConfig(
    name="Green Missile",
    characters=frozenset({Character.LUIGI}),
    attack_type=AttackType.SIDE_B,
    start_actions=frozenset({Action(343), Action(349)}),
    charge_actions=frozenset({Action(344), Action(350)}),
    full_hold_actions=frozenset(),
    completion_actions=frozenset({Action(347), Action(348), Action(351), Action(353), Action(354)}),
    initial_charge=20,
    charge_increment=1,
    power_floor=0,
    full_charge=((Character.LUIGI, 91),),
    prepare_side_input=True,
)
_SKULL_BASH_CONFIG: Final = _ChargeableSpecialConfig(
    name="Skull Bash",
    characters=frozenset({Character.PIKACHU, Character.PICHU}),
    attack_type=AttackType.SIDE_B,
    start_actions=frozenset({Action(343), Action(348)}),
    charge_actions=frozenset({Action(344), Action(349)}),
    full_hold_actions=frozenset(),
    completion_actions=frozenset({Action(345), Action(347), Action(350), Action(352)}),
    initial_charge=20,
    charge_increment=1,
    power_floor=0,
    full_charge=((Character.PIKACHU, 91), (Character.PICHU, 181)),
    prepare_side_input=True,
)
_SHIELD_BREAKER_CONFIG: Final = _ChargeableSpecialConfig(
    name="Shield Breaker",
    characters=frozenset({Character.MARTH}),
    attack_type=AttackType.NEUTRAL_B,
    start_actions=frozenset({Action(341), Action(345)}),
    charge_actions=frozenset({Action(342), Action(346)}),
    full_hold_actions=frozenset(),
    completion_actions=frozenset({Action(343), Action(344), Action(347), Action(348)}),
    initial_charge=0,
    charge_increment=1,
    power_floor=0,
    full_charge=((Character.MARTH, 121),),
)
_FLARE_BLADE_CONFIG: Final = _ChargeableSpecialConfig(
    name="Flare Blade",
    characters=frozenset({Character.ROY}),
    attack_type=AttackType.NEUTRAL_B,
    start_actions=frozenset({Action(341), Action(345)}),
    charge_actions=frozenset({Action(342), Action(346)}),
    full_hold_actions=frozenset(),
    completion_actions=frozenset({Action(343), Action(344), Action(347), Action(348)}),
    initial_charge=0,
    charge_increment=1,
    power_floor=0,
    full_charge=((Character.ROY, 211),),
)


class _ChargeableSpecialMontage(StatefulInputMontage[_ChargeableSpecialState]):
    """Internal shared lifecycle for specials released by letting go of B."""

    def __init__(
        self,
        config: _ChargeableSpecialConfig,
        direction: HorizontalStickReferenceAxis | None = None,
        use_smash_bonus: bool = False,
    ) -> None:
        phase = _ChargeableSpecialPhase.Preparing if config.prepare_side_input else _ChargeableSpecialPhase.Starting
        super().__init__(
            _FRAME_LIMIT,
            _ChargeableSpecialState(phase=phase),
            name=config.name,
        )
        self._config = config
        self._direction = direction
        self._use_smash_bonus = use_smash_bonus
        self._initial_charge = config.initial_charge if not config.prepare_side_input or use_smash_bonus else 0
        self._release_requested = False

    def release(self) -> Self:
        """Queue release for the first safe charge tick and return ``self``."""
        if (
            self.get_montage_state() in {MontageState.Waiting, MontageState.Active}
            and self._input_state.phase is not _ChargeableSpecialPhase.Released
        ):
            self._release_requested = True
        return self

    def can_release(self) -> bool:
        """Return whether releasing B can transition on the next active tick."""
        return (
            self.get_montage_state() is MontageState.Active
            and self._input_state.phase is _ChargeableSpecialPhase.Charging
            and self._input_state.charge is not None
        )

    def current_power(self) -> float | None:
        """Return locally tracked normalized charge while release remains available."""
        input_state = self._input_state
        character = input_state.character
        charge = input_state.charge
        if input_state.phase is not _ChargeableSpecialPhase.Charging or character is None or charge is None:
            return None
        full_charge = self._full_charge(character)
        charge_span = full_charge - self._config.power_floor
        return min(
            1.0,
            max(0.0, (charge - self._config.power_floor) / charge_span),
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
        return (
            player_state_value is not None
            and player_state_value.character in self._config.characters
            and player_state.can_attack(self._config.attack_type)
        )

    def stateful_should_abort(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
        input_state: _ChargeableSpecialState,
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
        input_state: _ChargeableSpecialState,
    ) -> tuple[_ChargeableSpecialState, InputMontage | bool | Abort]:
        del opponent_state, state
        player_state_value = player(player_state)
        if player_state_value is None:
            return input_state, Abort("player state became unavailable")

        if input_state.phase is _ChargeableSpecialPhase.Preparing:
            return self._tick_preparation(
                controls,
                player_state_value.character,
                input_state,
            )

        if input_state.phase is _ChargeableSpecialPhase.Released:
            return self._tick_released(controls, player_state_value.action, input_state)

        if not input_state.input_started:
            self._apply_start_input(controls)
            return (
                replace(
                    input_state,
                    character=player_state_value.character,
                    input_started=True,
                ),
                self,
            )

        action = player_state_value.action
        if action in self._config.completion_actions:
            controls.release_all()
            return replace(input_state, phase=_ChargeableSpecialPhase.Released), True
        if action in self._config.charge_actions:
            return self._tick_charge(controls, input_state)
        if action in self._config.full_hold_actions:
            full_state = replace(
                input_state,
                phase=_ChargeableSpecialPhase.Charging,
                charge=self._full_charge(player_state_value.character),
                transition_wait_frames=0,
            )
            return self._hold_or_release(controls, full_state)
        if action in self._config.start_actions:
            self._apply_charge_input(controls)
            return replace(input_state, transition_wait_frames=0), self
        if input_state.transition_wait_frames >= _START_WAIT_LIMIT:
            return input_state, Abort(f"{self._config.name} charge did not start")
        self._apply_charge_input(controls)
        return (
            replace(
                input_state,
                transition_wait_frames=input_state.transition_wait_frames + 1,
            ),
            self,
        )

    def _tick_charge(
        self,
        controls: SimpleControls,
        input_state: _ChargeableSpecialState,
    ) -> tuple[_ChargeableSpecialState, InputMontage | bool | Abort]:
        character = input_state.character
        if character is None:
            return input_state, Abort("charge character became unavailable")
        prior_charge = self._initial_charge if input_state.charge is None else input_state.charge
        charge_state = replace(
            input_state,
            phase=_ChargeableSpecialPhase.Charging,
            charge=min(
                self._full_charge(character),
                prior_charge + self._config.charge_increment,
            ),
            transition_wait_frames=0,
        )
        return self._hold_or_release(controls, charge_state)

    def _hold_or_release(
        self,
        controls: SimpleControls,
        input_state: _ChargeableSpecialState,
    ) -> tuple[_ChargeableSpecialState, InputMontage | bool | Abort]:
        if self._release_requested:
            controls.release_all()
            return replace(input_state, phase=_ChargeableSpecialPhase.Released), self
        self._apply_charge_input(controls)
        return input_state, self

    def _tick_preparation(
        self,
        controls: SimpleControls,
        character: Character,
        input_state: _ChargeableSpecialState,
    ) -> tuple[_ChargeableSpecialState, InputMontage]:
        controls.release_all()
        if self._use_smash_bonus:
            return (
                replace(
                    input_state,
                    phase=_ChargeableSpecialPhase.Starting,
                    character=character,
                ),
                self,
            )
        direction = cast(HorizontalStickReferenceAxis, self._direction)
        controls.tilt_stick(direction, 0.0)
        preparation_frames = input_state.preparation_frames + 1
        return (
            replace(
                input_state,
                phase=(
                    _ChargeableSpecialPhase.Starting
                    if preparation_frames >= _NO_SMASH_BONUS_PREP_FRAMES
                    else _ChargeableSpecialPhase.Preparing
                ),
                character=character,
                preparation_frames=preparation_frames,
            ),
            self,
        )

    def _tick_released(
        self,
        controls: SimpleControls,
        action: Action,
        input_state: _ChargeableSpecialState,
    ) -> tuple[_ChargeableSpecialState, InputMontage | bool | Abort]:
        controls.release_all()
        if action in self._config.completion_actions:
            return input_state, True
        if (
            action in self._config.start_actions | self._config.charge_actions | self._config.full_hold_actions
            and input_state.transition_wait_frames < _RELEASE_WAIT_LIMIT
        ):
            return (
                replace(
                    input_state,
                    transition_wait_frames=input_state.transition_wait_frames + 1,
                ),
                self,
            )
        return input_state, Abort(f"released {self._config.name} did not start")

    def _apply_start_input(self, controls: SimpleControls) -> None:
        controls.release_all()
        if self._direction is not None:
            controls.tilt_stick(self._direction, 0.0)
        controls.press_button(Button.BUTTON_B)

    @staticmethod
    def _apply_charge_input(controls: SimpleControls) -> None:
        controls.release_all()
        controls.press_button(Button.BUTTON_B)

    def _full_charge(self, character: Character) -> int:
        for configured_character, full_charge in self._config.full_charge:
            if character is configured_character:
                return full_charge
        raise RuntimeError(f"missing {self._config.name} charge limit for {character.name}")


class JigglypuffRolloutMontage(_ChargeableSpecialMontage):
    """Charge and caller-release Jigglypuff's Rollout on ground or in air."""

    def __init__(self) -> None:
        super().__init__(_ROLLOUT_CONFIG)


class LuigiGreenMissileMontage(_ChargeableSpecialMontage):
    """Charge and caller-release Green Missile in an absolute direction.

    Args:
        direction: Absolute ``StickReferenceAxis.LEFT`` or ``RIGHT`` launch input.
        use_smash_bonus: When ``True`` (the default), commit one neutral frame
            before horizontal+B so Melee grants Green Missile's 20-count smash
            bonus. When ``False``, hold ``direction`` through the three-frame tap
            window before pressing B, guaranteeing a zero-count normal start.

    """

    def __init__(
        self,
        direction: HorizontalStickReferenceAxis,
        use_smash_bonus: bool = True,
    ) -> None:
        super().__init__(_GREEN_MISSILE_CONFIG, direction, use_smash_bonus)


class SkullBashMontage(_ChargeableSpecialMontage):
    """Charge and caller-release Pikachu or Pichu's Skull Bash.

    Args:
        direction: Absolute ``StickReferenceAxis.LEFT`` or ``RIGHT`` launch input.
        use_smash_bonus: When ``True`` (the default), commit one neutral frame
            before horizontal+B so Melee grants Skull Bash's 20-count smash
            bonus. When ``False``, hold ``direction`` through the three-frame tap
            window before pressing B, guaranteeing a zero-count normal start.

    """

    def __init__(
        self,
        direction: HorizontalStickReferenceAxis,
        use_smash_bonus: bool = True,
    ) -> None:
        super().__init__(_SKULL_BASH_CONFIG, direction, use_smash_bonus)


class ShieldBreakerMontage(_ChargeableSpecialMontage):
    """Charge and caller-release Marth's Shield Breaker."""

    def __init__(self) -> None:
        super().__init__(_SHIELD_BREAKER_CONFIG)


class FlareBladeMontage(_ChargeableSpecialMontage):
    """Charge and caller-release Roy's Flare Blade."""

    def __init__(self) -> None:
        super().__init__(_FLARE_BLADE_CONFIG)


__all__ = [
    "FlareBladeMontage",
    "JigglypuffRolloutMontage",
    "LuigiGreenMissileMontage",
    "ShieldBreakerMontage",
    "SkullBashMontage",
]
