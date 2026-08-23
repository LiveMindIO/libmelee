"""Caller-timed Link forward-smash follow-up montage."""

from __future__ import annotations

from typing import Final, Self

from melee.bot.character_state import CharacterState, HorizontalStickReferenceAxis
from melee.bot.input_montage import Abort, InputMontage, MontageState
from melee.bot.simple_controls import SimpleControls, StickReferenceAxis
from melee.bot.techskill.common import player
from melee.bot.techskill.smash_attack import (
    SmashAttackMontage,
    _SmashAttackPhase,
    _SmashAttackState,
)
from melee.enums import Action, Button, Character
from melee.gamestate import GameState


_FIRST_SLASH_ACTION: Final = Action.FSMASH_MID
_SECOND_SLASH_ACTION: Final = Action(341)
# DESNOTE(jbarber, 2026-08-22): Link's first-slash subaction sets command variable
# 0 at frame 19 and clears it at frame 50. doldecomp's IASA path enters action
# 341 only while that variable is nonzero and A has a fresh pressed edge. Since
# controller input queued by a bot commits on the next Console.step, callers may
# request the follow-up while observing frames 18 through 48, committing it on
# valid game frames 19 through 49. Attacker hitlag must clear before the request
# or the edge can expire while IASA is frozen.
# See https://github.com/doldecomp/melee/blob/a983c0f9cd41d4a46001c493a1929891ac80f9ab/src/melee/ft/ftattacks4combo.c#L8-L46
# and https://www.ssbwiki.com/Link_(SSBM)/Forward_smash
_FIRST_FOLLOWUP_REQUEST_FRAME: Final = 18
_LAST_FOLLOWUP_REQUEST_FRAME: Final = 48
_FIRST_SLASH_FRAME_BUDGET: Final = 52


class LinkForwardSmashMontage(SmashAttackMontage):
    """Perform Link's first forward smash with an optional caller-timed follow-up.

    ``direction`` is absolute left or right. ``max_charge_frames`` has the same
    contract as :class:`SmashAttackMontage`: 0 (the default) releases on the
    first safe tick for minimum charge, while values through 60 retain A+stick
    for at most that many post-initiation ticks. :meth:`release_charge` is
    inherited and can request an earlier release regardless of that cap.

    Follow-up timing is opt-in and caller-controlled:

    * Call ``montage.followup()`` immediately after construction to request the
      fastest valid second slash. The request remains pending through startup,
      charging, release, and hitlag; the montage sends A on the first tick for
      which :meth:`can_followup` is true.
    * For a delayed second slash, do not call ``followup()`` initially. Register
      a pre-tick listener that checks its own timing condition and
      ``montage.can_followup(player_state)`` before calling ``montage.followup()``.
      Because pre-tick listeners run before this montage's input tick, a request
      made there is applied in that same bot tick and committed by the next
      ``Console.step``.
    * If no follow-up is requested, the montage finishes successfully when no
      further follow-up can be queued. A requested follow-up that misses the
      valid window aborts instead of emitting a late A input.

    ``can_followup(player_state)`` describes the *request* window visible to bot
    code, not the hidden game-frame window: it is true only while this montage
    is awaiting the first slash, Link is in ``FSMASH_MID`` on observed frames
    18 through 48 inclusive, attacker hitlag is zero, and no follow-up input has
    already been sent. Input queued then commits on game frames 19 through 49,
    while the first slash's command variable is enabled. The follow-up succeeds
    only after character-relative action 341 is observed. Each observed
    first-slash attacker-hitlag tick extends the montage safety budget by one, so
    hitlag cannot consume a caller's later valid follow-up opportunity.

    Fast follow-up example::

        montage = LinkForwardSmashMontage(StickReferenceAxis.RIGHT).followup()

    Delayed follow-up example::

        montage = LinkForwardSmashMontage(StickReferenceAxis.RIGHT)

        def delay_followup(controls, player_state, opponent_state, game_state):
            del controls, opponent_state, game_state
            player = player_state.player()
            if (
                player is not None
                and player.action_frame >= 30
                and montage.can_followup(player_state)
            ):
                montage.followup()
            return PreTickResult.CONTINUE

        montage.add_pre_tick_listener(delay_followup)

    Args:
        direction: Absolute ``StickReferenceAxis.LEFT`` or
            ``StickReferenceAxis.RIGHT`` first-slash direction.
        max_charge_frames: Maximum post-initiation ticks to retain A+stick,
            from 0 (minimum charge) through 60 (Melee's maximum).
    """

    def __init__(
        self,
        direction: HorizontalStickReferenceAxis,
        max_charge_frames: int = 0,
    ) -> None:
        if direction not in {StickReferenceAxis.LEFT, StickReferenceAxis.RIGHT}:
            raise ValueError(
                "direction must be StickReferenceAxis.LEFT or StickReferenceAxis.RIGHT"
            )
        super().__init__(direction, max_charge_frames=max_charge_frames)
        self._frame_limit += _FIRST_SLASH_FRAME_BUDGET
        self._followup_requested = False
        self._followup_input_sent = False

    def followup(self) -> Self:
        """Request the second slash on the next valid follow-up tick.

        The request is sticky and idempotent. Calling this immediately after
        construction configures the fastest follow-up. Calling it from a
        pre-tick listener after :meth:`can_followup` and a caller-owned delay
        condition are both true schedules a delayed follow-up through the same
        API. This method records intent only; controller input is emitted by the
        next active montage tick whose observed state can safely commit A inside
        Link's game window.

        Calling this after the follow-up input has already been sent or after
        terminal completion has no effect. A pending request that outlives the
        valid window aborts rather than turning into another attack after the
        first slash ends.
        """
        if (
            self.get_montage_state() in {MontageState.Waiting, MontageState.Active}
            and not self._followup_input_sent
        ):
            self._followup_requested = True
        return self

    def can_followup(self, player_state: CharacterState) -> bool:
        """Return whether calling :meth:`followup` can queue A on this bot tick.

        ``True`` means all observable requirements are currently satisfied:
        this montage has released and confirmed Link's first slash, no follow-up
        input has been sent, the current action is ``FSMASH_MID``, its observed
        frame is 18 through 48 inclusive, and attacker hitlag is zero. The A edge
        written during this tick will therefore commit on game frame 19 through
        49, where doldecomp's command-variable check accepts it.

        This method is pure: it neither requests nor emits the follow-up. Use it
        in delayed pre-tick listeners, then call :meth:`followup` when both this
        result and the caller's desired timing condition are true.
        """
        player_state_value = player(player_state)
        return (
            self.get_montage_state() is MontageState.Active
            and self._input_state.phase
            in {_SmashAttackPhase.Released, _SmashAttackPhase.Started}
            and not self._followup_input_sent
            and player_state_value is not None
            and player_state_value.character is Character.LINK
            and player_state_value.action is _FIRST_SLASH_ACTION
            and _FIRST_FOLLOWUP_REQUEST_FRAME
            <= player_state_value.action_frame
            <= _LAST_FOLLOWUP_REQUEST_FRAME
            and player_state_value.hitlag_left == 0
        )

    def can_start(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        opponent_state: CharacterState,
        state: GameState,
    ) -> bool:
        """Return whether Link can start the configured first forward smash."""
        player_state_value = player(player_state)
        return (
            player_state_value is not None
            and player_state_value.character is Character.LINK
            and player_state_value.on_ground
            and not player_state_value.off_stage
            and super().can_start(
                controls,
                player_state,
                opponent_state,
                state,
            )
        )

    def _after_smash_started(
        self,
        controls: SimpleControls,
        player_state: CharacterState,
        input_state: _SmashAttackState,
    ) -> tuple[_SmashAttackState, InputMontage | bool | Abort]:
        player_state_value = player(player_state)
        if player_state_value is None:
            return input_state, Abort("player state became unavailable")

        controls.release_all()
        if (
            player_state_value.action is _FIRST_SLASH_ACTION
            and player_state_value.hitlag_left > 0
        ):
            self._frame_limit += 1
        if self._followup_input_sent:
            if player_state_value.action is _SECOND_SLASH_ACTION:
                return input_state, True
            if (
                player_state_value.action is _FIRST_SLASH_ACTION
                and player_state_value.action_frame < 50
            ):
                return input_state, self
            return input_state, Abort("second forward slash did not start")

        if player_state_value.action is not _FIRST_SLASH_ACTION:
            if self._followup_requested:
                return input_state, Abort("requested follow-up window was missed")
            return input_state, True

        if self._followup_requested and self.can_followup(player_state):
            controls.press_button(Button.BUTTON_A)
            self._followup_input_sent = True
            return input_state, self

        if player_state_value.action_frame > _LAST_FOLLOWUP_REQUEST_FRAME:
            if self._followup_requested:
                return input_state, Abort("requested follow-up window was missed")
            return input_state, True
        return input_state, self


__all__ = ["LinkForwardSmashMontage"]
