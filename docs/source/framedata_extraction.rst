Melee DAT framedata catalogue
=============================

Research status
---------------

This page is an implementation catalogue for replacing libmelee's historical
runtime-captured framedata with data extracted from a legally supplied Super
Smash Bros. Melee disc image. It was researched against the NTSC 1.02 runtime
and the source revisions listed in `Sources`_. It does not contain or link to
copyrighted game data.

The main conclusion is that there is no single ``frame data`` table in a
fighter DAT. Useful framedata is assembled from four layers:

``raw``
   Fighter attributes, action entries, command words, local hitbox definitions,
   local hurtbox capsules, skeletons, animation keys, and article definitions
   read directly from DAT files.

``timeline``
   Effective event frames and state intervals produced by executing the
   subaction command language, including loops, calls, gotos, asynchronous
   timers, hitbox replacement, and hitbox removal.

``pose``
   Per-frame bone transforms, root motion, and world-space collision geometry
   produced by evaluating compressed animation tracks and the JOBJ hierarchy.

``gameplay``
   Results that require game rules and runtime context, such as actual launch
   velocity, knockback, hitlag, hitstun, shield stun, stale-move effects, DI,
   and whether a transition is accepted from a particular state.

An extractor should preserve these layers instead of flattening them into one
CSV and presenting derived values as though they came directly from the DAT.

Current libmelee coverage
-------------------------

``melee/framedata.csv`` currently stores character, action, and frame plus four
fixed hitbox slots. Each slot has only active, radius, X, and Y. The remaining
columns are root-motion X/Y, IASA, facing changed, and a projectile-spawn
boolean. ``melee/characterdata.csv`` stores jumps and a small subset of movement
attributes. ``melee/actiondata.csv`` stores only the historical zero-index
normalization flag.

The following information is already represented in some form:

* Character ID, action-state ID, and one-indexed action frame.
* Up to four active hitbox circles with a radius and two-dimensional center.
* Selected animation-induced movement, with horizontal aerial movement and all
  negative vertical movement discarded by the old recorder.
* A boolean approximation of IASA, a facing-change marker, and an untyped
  projectile-spawn marker.
* Jumps, friction, body-size approximation, gravity, terminal velocity, maximum
  walk speed, jump speed, fast-fall speed, and selected air-mobility values.

The data is not reproducible with the current recorder. It references obsolete
``GameState`` and ``PlayerState`` fields, appends duplicate headers, and does not
receive hitbox geometry from the current Slippi parser. The checked-in CSV also
contains duplicate and sparse action-frame sequences. This makes the DAT
extractor a replacement data source, not merely another input to the legacy
writer.

Extraction pipeline
-------------------

ISO filesystem
~~~~~~~~~~~~~~

The input should be a user-provided ISO. Read the GameCube filesystem table or
accept a filesystem extracted by a tool such as Dolphin. The relevant files are
the fighter data files (normally ``Pl<code>.dat``), their concatenated animation
archives (normally ``Pl<code>AJ.dat``), and any fighter-owned article/item data
referenced by the fighter root. Costume DATs are useful for models, but the base
fighter and AJ files are the primary move-data inputs.

Record the disc region and revision before parsing. Offsets, action tables,
compiled callbacks, and even move behavior are version-specific. NTSC 1.02
knowledge must not be silently applied to PAL, NTSC 1.00/1.01, or modded files.

HSD DAT container
~~~~~~~~~~~~~~~~~

HSD DAT files are big-endian. The ``0x20``-byte header supplies total size,
data-block size, relocation count, root count, reference count, and four version
bytes. Pointers in the data block are relative to the block beginning at file
offset ``0x20``. A parser must honor the relocation table and named roots rather
than scanning for byte patterns.

The named ``ftData*`` root resolves to a ``0x60``-byte fighter descriptor. Its
important references are:

.. list-table:: Fighter root contents
   :header-rows: 1
   :widths: 12 28 60

   * - Offset
     - Structure
     - Framedata use
   * - ``0x00``
     - Common fighter attributes
     - Movement, weight, shield, landing lag, and other character constants.
   * - ``0x04``
     - Character-specific attributes
     - Special-move parameters; schemas differ by fighter.
   * - ``0x08``
     - Model and bone lookup tables
     - Skeleton resolution, common bone remapping, and model parts.
   * - ``0x0C``
     - Fighter action table
     - Animation, subaction script, and flags for each action.
   * - ``0x10``
     - Per-action dynamic behavior
     - Dynamic-bone flags and bone-table index.
   * - ``0x14`` / ``0x18``
     - Demo actions and dynamics
     - Non-gameplay actions, useful for complete action coverage.
   * - ``0x1C``
     - Model-part animations
     - State-dependent model visibility and part changes.
   * - ``0x20``
     - Shield pose
     - Shield-model skeleton/pose input.
   * - ``0x24`` / ``0x28``
     - Idle-action chance tables
     - Idle action IDs and weights.
   * - ``0x2C``
     - Physics/dynamic bones
     - Secondary bone behavior needed for fully faithful poses.
   * - ``0x30``
     - Hurtbox bank
     - Bone-local hurtbox capsules.
   * - ``0x34``
     - Center bubble
     - Bone ID and radius.
   * - ``0x38``
     - Coin collision spheres
     - Bone, XYZ offset, and size.
   * - ``0x3C``
     - Camera box
     - Camera Y offset and projection extents.
   * - ``0x40``
     - Item pickup ranges
     - Ground/air and light/heavy pickup offsets and ranges.
   * - ``0x44``
     - Environment collision
     - Six ECB bones, multiplier, and ledge-grab dimensions.
   * - ``0x48``
     - Article pointers
     - Fighter-created projectiles/items, states, scripts, and hitboxes.
   * - ``0x4C``
     - Fighter sound table
     - Common and smash sound metadata.
   * - ``0x50``
     - Jostle box
     - Horizontal offset and size.
   * - ``0x54``
     - Common fighter bones
     - Head, arms, and legs used by common-bone IDs.
   * - ``0x58``
     - Inverse-kinematics data
     - IK chains and constraints used by pose evaluation.
   * - ``0x5C``
     - Metal model
     - Alternate model data, normally outside core framedata.

Action entries
~~~~~~~~~~~~~~

Each fighter action entry is ``0x18`` bytes. Preserve all of the following:

.. list-table:: Action-entry catalogue
   :header-rows: 1
   :widths: 16 26 58

   * - Offset
     - Field
     - Output
   * - ``0x00``
     - Animation symbol pointer
     - Original symbol and a separately derived display name.
   * - ``0x04``
     - AJ animation offset
     - Raw offset and resolved embedded animation identity.
   * - ``0x08``
     - Animation DAT size
     - Raw size and validation/alignment result.
   * - ``0x0C``
     - Subaction script pointer
     - Raw pointer, script bytes, and parsed command stream.
   * - ``0x10``
     - Action flag word
     - Raw ``u32`` plus individually decoded flags.
   * - ``0x14``
     - Runtime animation pointer
     - Normally zero on disk; retain raw data if nonzero.

The flag word includes animation-induced/root motion (``0x80000000``), looping
(``0x40000000``), several timing/dynamics/root-translation flags whose names are
not all settled, a 13-bit additional-bone field (``0x003FFE00``), a 3-bit bone or
blend selector (``0x000001C0``), and a 6-bit fighter-kind check
(``0x0000003F``). Friendly labels from editors are partly tentative, so the raw
word is mandatory.

The action-table index is not by itself a complete semantic name. Common and
fighter-specific motion-state tables in the game executable map action-state
IDs to callbacks, while the DAT supplies an animation symbol. Store all three:
action-table index, runtime motion-state ID where known, and original symbol.
For NTSC 1.02, ``MotionState.anim_id`` is the authoritative DAT action-table
index. ``main.dol`` begins at the disc-header offset stored at ``0x420`` and its
section table must be used to translate executable virtual addresses into
bounded file reads; it is not an FST member.

The implemented NTSC 1.02 addresses, fighter-kind ordering, table counts, and
``MotionState`` layout were audited against doldecomp/melee revision
``d15c9cffe939611627b3a7a77a446705d2998f5f``. Keep that revision with exported
build provenance. Callback pointers identify behavior for later analysis, but a
pointer alone does not reproduce the callback's runtime semantics.

Subaction command timeline
--------------------------

Commands use a 6-bit opcode. Historical byte-oriented tools display the opcode
shifted into the first byte, so opcode ``11`` is commonly called command
``0x2C``. Preserve both forms to make research sources comparable.

The control language includes end, synchronous/relative timer, asynchronous or
absolute timer, loop setup/execution, subroutine, return, goto, and animation
timer commands. Correct event frames require an interpreter. Summing timer
arguments is not sufficient because scripts branch, loop, call shared scripts,
set absolute times, execute several events on one frame, and run under animation
rate changes.

For every command, store:

* Action ID, script byte offset, command ordinal, opcode, raw byte length, and
  original command words.
* Decoded parameters and a confidence/source marker for every field name.
* Call/goto target and the resolved control-flow path.
* Effective animation time and exported one-indexed gameplay frame.
* Whether an event was reached through a call, goto, loop iteration, or fallthrough.
* Unknown opcodes and unused bits without dropping or normalizing them.

Combat-relevant fighter commands include:

* Create, modify damage/size/interaction, remove, and clear hitboxes.
* Define throw/release knockback data.
* Allow interrupt (the source of a DAT-level IASA event).
* Reverse direction and change grounded/airborne jump state.
* Set body-wide or per-bone hurtbox collision state.
* Enable jab followup and rapid-jab windows.
* Set generic command variables consumed by action callbacks.
* Set projectile/throw flags, model state, texture/model-part animation, and
  fighter/article visibility.
* Apply self-damage, begin smash charge, toggle bone dynamics, and create wind.
* Spawn visual/audio events. These are lower priority for bots but are useful for
  move presentation and validating event timing.

``Allow Interrupt`` is only one notion of actionability. Final actionable frame,
landing transitions, jump cancels, and special-move branches can also be driven
by compiled callbacks in the DOL. Likewise, command-variable writes must remain
generic in the raw layer. For example, old tools call command ``0x4C``
``autocancel``, but the runtime command only writes one of four command variables;
an aerial callback gives that variable its autocancel meaning.

Hitbox catalogue
----------------

Fighter hitbox creation
~~~~~~~~~~~~~~~~~~~~~~~

The fighter create-hitbox event occupies five 32-bit words in the inspected
runtime. Libmelee currently retains only
active, size, X, and Y. A replacement can retain:

.. list-table:: Fighter hitbox fields missing from libmelee
   :header-rows: 1
   :widths: 29 18 53

   * - Field
     - Encoding
     - Meaning
   * - Hitbox ID
     - 3 bits
     - Slot identity; use a collection rather than four fixed CSV columns.
   * - Hit group
     - 3 bits
     - Replacing an ID with a different group resets victim tracking.
   * - Grabbed-target-only flag
     - 1 bit/raw trailing bits
     - The in-command bit is bugged and is exposed as
       ``bugged_only_hit_grabbed_fighter_flag`` rather than effective runtime
       behavior. Preserve the original words because the runtime also reads a
       trailing bit outside the documented five-word command.
   * - Bone ID
     - 8 bits
     - Bone to which the local hitbox offset is attached.
   * - Common-bone selector
     - 1 bit
     - Chooses common-bone remapping rather than direct part index.
   * - Damage
     - 10 bits
     - Base hitbox damage before runtime modifiers.
   * - Radius/size
     - 16-bit fixed point
     - Divide by ``256.0``. Older ``/255`` extractors are incorrect.
   * - Local Z, Y, X offsets
     - Signed 16-bit fixed point
     - Each divided by ``256.0``; preserve all three axes and source order.
   * - Launch angle
     - 9 bits
     - Raw angle, including special angle codes requiring runtime interpretation.
   * - Knockback growth
     - 9 bits
     - KBG.
   * - Weight-set knockback
     - 9 bits
     - Fixed/weight-dependent knockback parameter, often called WDSK/FKB.
   * - Item-hit interaction
     - 1 bit
     - Item collision behavior.
   * - Requires thrown-hitbox owner
     - 1 bit
     - The runtime skips creation when this bit is set and no thrown-hitbox owner
       exists. Frame snapshots retain the script-declared candidate and expose
       ``requires_thrown_hitbox_owner`` because ISO data alone cannot resolve the
       runtime condition.
   * - Ignore fighter scale
     - 1 bit
     - Runtime divides local offsets by current fighter scale before transform.
   * - Clank flag
     - 1 bit
     - Whether normal hitbox clank interaction is enabled.
   * - Rebound flag
     - 1 bit
     - Rebound behavior after collision.
   * - Base knockback
     - 9 bits
     - BKB.
   * - Element
     - 5 bits
     - Numeric element/status-effect enum.
   * - Shield damage
     - Signed 8 bits
     - Hitbox-specific shield-damage adjustment.
   * - Hit SFX severity
     - 3 bits
     - Weak/moderate/strong-style sound severity.
   * - Hit SFX kind
     - 5 bits
     - Punch, kick, sword, fire, electric, and other sound groups.
   * - Hits grounded
     - 1 bit
     - Grounded-target collision mask.
   * - Hits aerial
     - 1 bit
     - Aerial-target collision mask.
   * - Original words/unused bits
     - Raw bytes
     - Required for unknown fields, future corrections, and round trips.

Element values currently decoded by the NTSC 1.02 runtime/tooling include normal,
fire, electric, slash, coin, ice, short sleep, long sleep, catch/grab, grounded,
cape, inert/empty, disable, darkness, Screw Attack, flower, and a final
special/no-graphic value. Numeric values must remain canonical because historical
tools disagree on some display names.

Hitbox state is an interval, not a one-frame event. The timeline needs to apply
damage-adjust, size-adjust, interaction-flag, remove-one, clear-all, and recreate
events. It should expose both the original event stream and active intervals.
Recreating the same ID can change its properties, and changing hit group resets
the list of victims already struck. The damage-adjust command carries a direct
23-bit value; the size-adjust command carries a 23-bit fixed-point value divided
by ``256.0``. Preserve the interaction command's type and value bits as well as
their interpreted effect.

Fighter hitboxes do not have the explicit timed-rehit field available to item
hitboxes. Rehit behavior follows victim-history state and hitbox recreation or
group changes. Likewise, there is no independent ``priority`` number: whether
two hitboxes clank and which wins is a gameplay result based on damage and
collision flags.

World-space hitboxes are pose data. Runtime maps the script's local Z/Y/X fields
onto its collision-vector axes, resolves common bone IDs, applies scale rules,
and transforms through the animated JOBJ hierarchy. Collision checks sweep from
the previous world center to the current center; the effective volume can be a
capsule between frames even though the script defines a local point and radius.
Store local geometry, current world center, previous world center, and swept
capsule separately.

Throws and grabs
~~~~~~~~~~~~~~~~

The throw command supplies throw/release type, damage, angle, KBG, weight-set
knockback, BKB, element, and hit SFX severity/kind. Store every throw command;
some command grabs have multiple throw and release definitions in one action.
The fighter's common attributes also include a bitmask identifying which normal
throws are weight independent.

Grab collision is commonly represented by catch-element hitboxes plus target
and hurtbox eligibility, not by a separate universal ``grab box`` table. A useful
derived grab timeline should combine catch hitbox geometry, grounded/aerial
masks, grabbed-target-only behavior, each hurtbox's grabbable flag, throw events,
and motion-state callback behavior. Command grabs and tethers need fighter-specific
validation against the DOL and article data.

Articles, projectiles, and item hitboxes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The fighter root can point to articles containing common and extended attributes,
an item hurtbox bank, item-state table, model, dynamics, animations, and item
subaction scripts. Article common attributes include heavy/hold kind, throw-speed
multiplier, spin, gravity, terminal velocity, ECB extents, hitbox decay after
bounce, model scale, and sound/effect IDs.

Item/article create-hitbox commands contain damage, radius, XYZ offset, angle,
KBG, weight-set knockback, BKB, element, clank, shield damage, SFX, grounded and
aerial masks, and additional fields not present on fighter hitbox commands:

* Per-fighter hit cooldown/rehit timing.
* Timed rehit enable flags for fighters, shields, and non-fighters.
* Reflectable, absorbable, shieldable, and deflectable flags.
* Facing-only behavior.
* Fighter and non-fighter interaction masks.
* Ignore-ungrabbable-hurtbox behavior.
* Item/Pokemon/Warp Star and other partially understood flags.

This is much richer than the current one-frame ``projectile`` boolean. A new
model should expose article ID/type, generation event, state, owner, local and
world spawn position, velocity/acceleration, lifetime or state transitions,
hurtboxes, hitboxes, collision masks, reflect/absorb behavior, and all raw flags.
However, a generic fighter ``projectile flag`` command does not identify the
article by itself, and some specials create articles from compiled callbacks.
Connecting a fighter event to the exact spawned article can therefore require
fighter-specific DOL analysis or runtime validation.

Hurtboxes and defensive collision
---------------------------------

Each raw fighter hurtbox record contains:

* Bone index.
* Height class: low, middle, or high.
* Grabbable flag.
* Bone-local endpoint A XYZ.
* Bone-local endpoint B XYZ.
* Radius/scale.

This is a capsule, not libmelee's current single character-size circle. The
subaction timeline can also set body-wide collision state, all-bone state, or an
individual bone state. A per-frame export can therefore include each hurtbox's
local capsule, world capsule, vulnerable/invulnerable/intangible state, height
class, and grab eligibility.

World hurtboxes require the same full animation and skeleton evaluation as
hitboxes. Secondary dynamics, model-part changes, scale, and per-bone collision
commands can affect the result. Armor is not equivalent to invulnerability and
must not be inferred from hurtbox state; super/heavy armor thresholds are often
implemented in fighter-specific attributes and compiled callbacks.

Other defensive geometry worth retaining includes:

* Shield size and shield-break velocity from common attributes, plus shield pose.
* Center bubble bone/radius and coin collision spheres.
* Jostle box offset/size.
* Reflector descriptors when referenced: bone, XYZ offset, radius, maximum
  damage, damage multiplier, velocity multiplier, and flags.
* Absorber and shield descriptors when present in fighter-specific structures.
* Item pickup rectangles for grounded light, aerial light, and heavy items.

Exact active shield, powershield, reflector, absorber, armor, and counter windows
must combine DAT/script data with runtime callbacks. Shield radius at a moment in
a match also depends on shield health and analog shield state, so it is not a
static framedata value.

Animation, bones, and movement
------------------------------

The ``Pl<code>AJ.dat`` file is a concatenation of individually valid, usually
``0x20``-aligned DAT animations. The action entry gives the byte offset and size
needed to isolate its FigaTree.

A FigaTree stores type, floating-point frame count, per-node track counts, and
compressed tracks. Each track retains data length, start frame, track type,
value/tangent formats, quantization scales, and compressed keys. Joint tracks can
animate rotation, translation, and scale on X/Y/Z. Key interpolation includes
constant, linear, Hermite variants, slope updates, and discrete key events.

The pose layer can add data that libmelee currently lacks:

* Exact animation frame count and fractional animation time.
* Every bone's local and world translation, rotation, and scale per frame.
* Signed XYZ root motion, without discarding downward or aerial movement.
* Facing-normalized and unnormalized coordinates.
* World-space hitboxes and hurtboxes, including Z.
* Previous/current transforms for swept collision.
* Model-part state, dynamics flags, and animation-loop boundaries.
* ECB source bones and a derived per-frame ECB.

Correct evaluation must reproduce the JOBJ hierarchy and flags for classical
scaling, scale compensation, independent parent/SRT behavior, quaternion paths,
and special joints. Treating local bone positions as world positions, ignoring
interpolation, or using action-frame integers directly for every track will
produce wrong geometry.

Character attributes missing from libmelee
------------------------------------------

The common fighter attribute block is ``0x184`` bytes. Libmelee retains only a
small subset. The following useful groups can be extracted directly:

Walking and grounded movement
   Initial walk speed, walk acceleration, maximum walk speed, walk animation
   speed, middle/fast walk thresholds, friction, initial dash speed, two
   stop-turn speeds, initial run speed, run animation scale, dash direction
   lockout, dash duration before run, forced tilt-turn velocity, and standing
   turn duration.

Jump and aerial movement
   Jump startup lag, initial horizontal/vertical jump velocity, ground-to-air
   momentum multiplier, maximum short-hop horizontal/vertical velocity, vertical
   and horizontal air-jump multipliers, jump count, gravity, terminal velocity,
   aerial acceleration/speed values, aerial/air friction values, maximum aerial
   horizontal speed, and fast-fall terminal velocity.

Combat and defense
   Weight, model scale, shield size, shield-break launch velocity, clank speed
   multiplier, jab-2/jab-3/rapid-jab windows, and weight-independent throw flags.

Landing and terrain interaction
   Normal landing lag; nair, fair, bair, uair, and dair landing lag; wall-tech
   direction/speed; wall-jump horizontal/vertical velocity; ceiling-tech value;
   ledge-jump horizontal/vertical velocity; ECB bones and multiplier; and
   ledge-grab width, Y offset, and height.

Items and special states
   Item throw velocity and damage scale, running side-special momentum, Yoshi
   egg geometry, selected Kirby star damage, freeze/frozen geometry, Bunny Hood
   and flower attachment geometry, Screw Attack values, Warp Star scaling,
   camera target/sway values, and several still-unknown fields that should be
   retained by offset.

Character-specific attributes at fighter-root offset ``0x04`` are equally
important for specials: charge rates and maxima, projectile speeds, special-move
gravity/traction, armor thresholds, reflector/absorber descriptors, command-grab
parameters, and character-owned article behavior. Their layouts differ by
fighter. Extraction should use typed schemas where decompilation confirms them
and emit offset-addressed raw values for unknown portions rather than dropping
the block.

Derived framedata we can provide
--------------------------------

Once raw, timeline, and pose layers exist, libmelee can reliably derive:

* Startup, each active window, inactive gaps, and recovery/end frames.
* Earliest DAT-script interrupt frame and animation completion frame as distinct
  values.
* Hitbox generations and property changes over a move rather than one merged
  first/last active range.
* Per-hitbox damage, angle, KBG, BKB, weight-set knockback, shield damage,
  element, target masks, clank/rebound flags, bone, and local/world geometry.
* Throw and release timing and parameters.
* Vulnerability, invulnerability, and intangibility intervals per body/bone.
* Root-motion curves, total signed displacement, facing changes, and per-frame
  bone poses.
* Landing-lag constants and contextual autocancel-variable windows, clearly
  labelled with the runtime interpretation used.
* Jab continuation, rapid-jab, smash-charge, self-damage, model/article, and
  article-generation event windows.
* Article/item active windows, rehit timing, and reflection/absorption masks when
  their scripts and state transitions are resolvable.

The following should be optional gameplay calculations with declared inputs,
not static raw fields:

* Knockback magnitude and launch velocity at a supplied target percent, target
  weight, crouch state, stale queue, handicap, and other runtime modifiers.
* Actual launch angle after special-angle handling and DI.
* Hitlag and SDI opportunities; Melee's fighter hitbox command does not carry the
  modern per-hitbox hitlag/SDI multiplier fields found in later games.
* Hitstun, tumble, techability, shield stun, pushback, and shield advantage.
* Whether a hit connects against a supplied defender pose, hurtbox state,
  position, facing, and prior collision history.
* Earliest actionable frame through callback-specific cancels, landing, ledge,
  charge release, or input-dependent branches.

Data outside the fighter DATs
-----------------------------

Some critical semantics are not recoverable from fighter DAT files alone:

* Common and fighter-specific motion-state callback functions are compiled into
  the game executable (DOL). They control transitions, input windows, specials,
  article creation, armor, and other behavior.
* Global knockback, hitlag, hitstun, shield, stale-move, DI, and collision rules
  live in executable code and common data.
* Runtime state supplies percent, stale queue, charge, scale, velocity, facing,
  shield health, controller input, target state, and stage collision.
* Stage DATs provide terrain and moving-platform geometry needed for grounded,
  landing, and ledge outcomes.

An honest API should expose provenance such as ``fighter_dat``, ``article_dat``,
``script_interpreted``, ``animation_resolved``, ``dol_interpreted``, or
``runtime_derived`` for each field or result.

Recommended output model
------------------------

Do not extend the existing wide CSV with more numbered hitbox columns. Use a
versioned, normalized model with collections and preserve a compact generated
artifact for package distribution. At minimum:

``build``
   Schema version, game ID/region/revision, hashes of every input DAT and DOL,
   extractor version/commit, extraction timestamp, coordinate and frame-number
   conventions, warnings, and unknown-field counts.

``character``
   Fighter ID/symbol, common attributes, typed character-specific attributes,
   raw unknown blocks, skeleton/bone mapping, hurtbox definitions, ECB/ledge,
   jostle/center/shield/pickup geometry, and article references.

``action``
   Table index, motion-state ID, original animation symbol, AJ offset/size,
   FigaTree frame count, raw action flags, script offset/hash, and dynamic behavior.

``command``
   Raw bytes/words, decoded opcode/parameters, source confidence, control-flow
   provenance, and resolved animation/gameplay time.

``frame``
   Animation time/rate, signed root motion, facing, command events, interrupt and
   collision states, active hitbox IDs, active articles, optional bone transforms,
   and optional world geometry.

``hitbox_generation``
   Stable action-local generation ID, script hitbox ID/group, active interval,
   every combat parameter, local geometry, mutations, and optional pose samples.

``hurtbox``
   Stable hurtbox ID, bone, local capsule, height/grabbable properties, collision
   state intervals, and optional pose samples.

``article``
   Article index/type, attributes, states, scripts, animations, hurtboxes,
   hitboxes, generation evidence, and unresolved callback dependencies.

Keep the existing one-indexed libmelee API as a presentation layer if desired,
but retain source animation time and raw timer values so zero/one-index conversion
is explicit and reversible. The presentation conversion is
``max(1, ceil(source_time))``: source times zero and one are both public frame
one, while a source time of two is public frame two. A FigaTree frame count is
an exclusive source-time endpoint; for a positive count ``N``, snapshot count is
``max(1, ceil(N) - 1)``.

Suggested implementation sequence
---------------------------------

1. Accept extracted fighter/AJ files first; keep ISO filesystem parsing as a
   separable adapter.
2. Implement a lossless big-endian HSD DAT parser with relocations, roots,
   references, bounds checks, and raw-byte retention. Alternatively, call a
   pinned HSDLib-based exporter and import its versioned output.
3. Extract common attributes, action entries, scripts, static hurtboxes, skeleton,
   and articles without deriving frames. Snapshot-test raw output against known
   offsets and HSDLib.
4. Implement the decompiled command interpreter, including absolute/relative
   timers, loops, calls, returns, gotos, animation speed, and cycle guards.
5. Build hitbox/throw/hurt-state/article timelines while retaining original
   events. Validate representative multihits, command grabs, loops, and hitbox
   mutation against Dolphin/HSDRaw.
6. Decode FigaTree tracks and JOBJ transforms, then add optional local-to-world
   hitbox/hurtbox/ECB pose evaluation.
7. Add DOL-backed semantic adapters only where necessary, with region-specific
   source references and confidence markers.
8. Generate a deterministic, schema-versioned package artifact and compatibility
   views for ``FrameData``. Test completeness, duplicate keys, contiguous frame
   policy, precision, and regeneration hashes.

Tool assessment
---------------

HSDLib / HSDRaw
   Best available base for DAT relocation/root parsing, typed fighter structures,
   skeletons, animations, article/item structures, and editable command schemas.
   Some UI labels and unknown flag names remain tentative.

doldecomp/melee
   Primary authority for NTSC 1.02 runtime behavior and fixed-point conversion.
   Use it to verify what command bits actually do and which values are contextual.

meleeDat2Json and meleeFrameDataExtractor
   Useful compact examples of DAT-to-JSON and script-to-framedata pipelines. They
   are incomplete for specials and defensive states, and meleeDat2Json's historic
   hitbox coordinate/size conversion uses ``/255`` rather than the runtime's
   ``/256``. Do not adopt the output as an authority without correction.

Melee Subaction Unpacker
   Useful historical command/control-flow research. Its README explicitly marks
   guessed command names, and those guesses must not become canonical schema names.

m-ex and MexTK
   Useful for NTSC 1.02 structure names, headers, runtime integration, and modded
   fighter conventions. They are not a complete framedata extraction pipeline.

DAT Texture Wizard
   Useful background for DAT/archive handling but not sufficient for fighter
   script interpretation and per-frame pose evaluation.

No verifiable public source repository named ``ssbm-data-viewer`` or for a Crazy
Hand DAT editor was found during this research. They should not be implementation
dependencies without a concrete, auditable source.

Sources
-------

Primary sources are pinned where a revision was inspected:

* `HSDLib repository <https://github.com/Ploaj/HSDLib>`__ and its pinned
  `HSDRawFile DAT parser <https://github.com/Ploaj/HSDLib/blob/85567e40797de3c820a55476eca54c704921a848/HSDRaw/HSDRawFile.cs>`__.
* HSDLib's pinned `fighter root <https://github.com/Ploaj/HSDLib/blob/85567e40797de3c820a55476eca54c704921a848/HSDRaw/Melee/Pl/SBM_FighterData.cs>`__,
  `action entry <https://github.com/Ploaj/HSDLib/blob/85567e40797de3c820a55476eca54c704921a848/HSDRaw/Melee/Pl/SBM_FighterAction.cs>`__,
  `common attributes <https://github.com/Ploaj/HSDLib/blob/85567e40797de3c820a55476eca54c704921a848/HSDRaw/Melee/Pl/SBM_CommonFighterAttributes.cs>`__,
  `hurtboxes <https://github.com/Ploaj/HSDLib/blob/85567e40797de3c820a55476eca54c704921a848/HSDRaw/Melee/Pl/SBM_Hurtbox.cs>`__,
  `environment collision <https://github.com/Ploaj/HSDLib/blob/85567e40797de3c820a55476eca54c704921a848/HSDRaw/Melee/Pl/SBM_EnvironmentCollision.cs>`__,
  and `articles <https://github.com/Ploaj/HSDLib/blob/85567e40797de3c820a55476eca54c704921a848/HSDRaw/Melee/Pl/SBM_ArticlePointer.cs>`__.
* HSDLib's pinned `fighter command schema <https://github.com/Ploaj/HSDLib/blob/85567e40797de3c820a55476eca54c704921a848/HSDRawViewer/Scripts/command_fighter.yml>`__,
  `control command schema <https://github.com/Ploaj/HSDLib/blob/85567e40797de3c820a55476eca54c704921a848/HSDRawViewer/Scripts/command_controls.yml>`__,
  and `item command schema <https://github.com/Ploaj/HSDLib/blob/85567e40797de3c820a55476eca54c704921a848/HSDRawViewer/Scripts/command_item.yml>`__.
* HSDLib's pinned `FigaTree <https://github.com/Ploaj/HSDLib/blob/85567e40797de3c820a55476eca54c704921a848/HSDRaw/Common/Animation/HSD_FigaTree.cs>`__
  and `track decoder model <https://github.com/Ploaj/HSDLib/blob/85567e40797de3c820a55476eca54c704921a848/HSDRaw/Common/Animation/HSD_Track.cs>`__.
* `doldecomp/melee <https://github.com/doldecomp/melee>`__ at the inspected
  revision, especially `fighter command execution <https://github.com/doldecomp/melee/blob/d15c9cffe939611627b3a7a77a446705d2998f5f/src/melee/ft/ftaction.c>`__,
  `collision and command structures <https://github.com/doldecomp/melee/blob/d15c9cffe939611627b3a7a77a446705d2998f5f/src/melee/lb/types.h>`__,
  `generic command execution <https://github.com/doldecomp/melee/blob/d15c9cffe939611627b3a7a77a446705d2998f5f/src/melee/lb/lbcommand.c>`__,
  and `fighter animation behavior <https://github.com/doldecomp/melee/blob/d15c9cffe939611627b3a7a77a446705d2998f5f/src/melee/ft/ftanim.c>`__.
* `meleeDat2Json <https://github.com/pfirsich/meleeDat2Json>`__ and
  `meleeFrameDataExtractor <https://github.com/pfirsich/meleeFrameDataExtractor>`__.
* `Melee Subaction Unpacker <https://github.com/Adjective-Object/melee_subaction_unpacker>`__.
* `m-ex <https://github.com/akaneia/m-ex>`__ and
  `MexTK <https://github.com/akaneia/MexTK>`__.
* `DAT Texture Wizard <https://github.com/DRGN-DRC/DAT-Texture-Wizard>`__.
