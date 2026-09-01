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
   action = data.action("Fx", 44)
   print(action.symbol, action.animation_frame_count, action.timeline.iasa_frame)

The integer passed to ``action`` is the fighter DAT action-table index. It is
not always the same as ``PlayerState.action`` because runtime motion-state
tables and callbacks live in the game executable.

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
initial animation cycle; it does not evaluate post-wrap commands.

.. automodule:: melee.disc_framedata
   :members:
