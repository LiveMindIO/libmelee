Framedata
----------------------

.. toctree::
   :maxdepth: 1

   framedata_extraction

.. automodule:: melee.framedata
   :members:
   :undoc-members:

ISO-backed framedata
~~~~~~~~~~~~~~~~~~~~

``DiscFrameData`` is the phase-one, read-only API for a legally supplied NTSC
1.02 Melee ISO. It reads fighter DAT members directly from the disc image at
runtime and does not extract or write Nintendo data::

   data = melee.DiscFrameData("/path/to/melee.iso")
   print(data.available_fighter_codes)
   action = data.action_for_state(melee.Character.FOX, melee.Action.NEUTRAL_ATTACK_1)
   assert action is not None
   print(action.symbol, action.animation_frame_count, action.timeline.iasa_frame)

``action_for_state`` maps a public ``Character`` and runtime ``Action`` through
the NTSC 1.02 executable's common and character-specific ``MotionState`` tables.
It returns ``None`` when the resolved record has neither an animation nor a
subaction script, or when the state is not present in that character's table.
Nana states with no local animation use the corresponding Popo record, matching
the executable's non-demo runtime fallback.
``dat_action_index`` exposes the mapped index directly. The
integer passed to the lower-level ``action`` method is instead a fighter DAT
action-table index and is not generally equal to ``PlayerState.action``.

``motion_state(character, action)`` exposes the complete immutable executable
record used for that mapping: its virtual address, DAT action index, motion and
move flags, move ID, and animation/input/physics/collision/camera callback
pointers. Null callbacks are represented as ``None``. These pointers are
provenance for auditing behavior against doldecomp; libmelee does not execute or
claim to reproduce their PowerPC code. ``DiscBuild.doldecomp_revision`` records
the exact doldecomp revision used to audit the NTSC 1.02 layouts and addresses.

``FrameData`` is deprecated. Existing code can opt into the ISO-backed timing
facade while retaining its query method signatures::

   data = melee.FrameData(iso_path="/path/to/melee.iso")
   print(data.first_hitbox_frame(melee.Character.FOX, melee.Action.NEUTRAL_ATTACK_1))

The facade supports ``is_attack``, ``attack_state``, ``first_hitbox_frame``,
``last_hitbox_frame``, ``hitbox_count``, ``iasa``, ``frame_count``, and
``last_roll_frame`` from the ISO. Geometry-dependent methods such as
``range_forward``, ``range_backward``, ``in_range``, and ``roll_end_position``
raise ``DiscFrameDataError`` in this mode rather than misrepresenting bone-local
DAT coordinates as posed fighter-relative geometry. Construction without
``iso_path`` temporarily retains the historical CSV-backed behavior. Article
and projectile attacks are not yet included. ISO-backed hitbox-related queries
raise ``DiscFrameDataError`` for known article-dependent states, including
special states without fighter hitboxes and the mixed fighter/article hitboxes
of Link, Young Link, and Samus ground tether grabs. ``frame_count`` remains
available because it does not require article data. The context-free facade
omits hitboxes whose creation requires a runtime thrown-hitbox owner; the
lower-level timeline retains those script-declared candidates and their
condition flag.

Every exported ``local_frame`` and ``FrameSnapshot.local_frame`` is one-indexed
script time. For a record with a non-empty timeline, ``ActionRecord.frame(1)``
addresses the initial snapshot. The ISO-backed ``FrameData`` compatibility
methods additionally apply audited action-specific offsets where runtime state
entry makes normalized ``PlayerState.action_frame`` one frame later. Lower-level
``DiscFrameData.action`` queries may expose empty DAT-table records; these have
``timeline.frame_count == 0``, and ``frame(1)`` raises ``IndexError``.
Raw/effective script timing remains available separately as ``animation_time``;
timer times zero and one both map to public frame one, and later fractional
times round up. FigaTree frame counts are exclusive source-time endpoints, so
an animation ending at source time 18 normally has public snapshots ``1..17``
while retaining ``animation_frame_count == 18``. A reached state-changing event
at that endpoint adds the required final snapshot rather than being discarded.

This phase parses action symbols, raw flags, FigaTree frame counts, guarded
subaction control flow, local-frame snapshots, hitbox generations and
mutations, throws, hurt-state events, and DAT-level Allow Interrupt events. All
hitbox XYZ values are explicitly bone-local. The API does not yet evaluate
skeletons/animation tracks into root or world geometry, parse articles and
static hurtbox capsules, or reproduce executable callbacks and contextual
gameplay calculations such as knockback, hitlag, landing transitions, and
callback-specific cancels.

``Set Timer Animation`` suspends script execution until an animation wrap. Phase
one marks that command with ``animation_timer_encountered`` and reports only the
initial animation cycle; it does not evaluate post-wrap commands. A ``goto``
that re-enters previously executed control flow exposes
``script_loop_encountered``. When the loop advances time and a finite animation
endpoint is known, interpretation continues only through the remainder of that
initial cycle, including commands whose timer becomes due exactly at the
endpoint; a wait that would overshoot the endpoint stops interpretation.
Unknown-duration and zero-progress loops stop at the first-pass boundary.
Exceptionally long persistent scripts are bounded to 10,000 script frames and
set ``frame_guard_encountered`` instead of allocating their full duration.

.. automodule:: melee.disc_framedata
   :members:
