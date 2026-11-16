# Marth jab 2 and Yoshi neutral-air timing

Read-only investigation, 2026-11-16. Baseline libmelee
`e90926abf144cadeb93ba5032e27fe272a6c1baa`; numerical catalog and labels unchanged.
Read the complete `sweetspot-labels.md`, group C/F reports and source receipts,
catalog generator, pinned extractor, historical CSVs and Console normalization.

## Findings

| Action | Disposition | Evidence-backed explanation |
| --- | --- | --- |
| Marth 18:45 | Resolved at script/public-index boundary; live confirmation outstanding | DAT creates at animation time 4 and clears at 9. Catalog preserves raw 4–8, but Console adds one for this exact action. Its public-frame counterpart is 5–9, agreeing with Wiki. The pinned generator's compatibility offset is zero here. |
| Yoshi 14:65 | Resolved against the pinned Wiki timing table at static-script level; live confirmation outstanding | DAT creates clean at absolute time 3, waits **four relative frames**, recreates late at 7, and clears at absolute 34. Native timer semantics and an independent bounded stepper give clean 3–6/late 7–33. Console does not add one. Wiki's clean 3–5/late 6–33 is inconsistent with that script, not a blanket offset. |

These are different defects in the compared sources/contracts, not one global
index correction. No numerical resource, signature, label, runtime code, Wiki
page or other audit report was edited. Named spatial/clean roles were not
re-adjudicated. This report does not certify live connectivity or collision order.

## Fresh disc evidence

Used the existing legally supplied local ISO, without downloading or extracting
members to disk. Header is GALE01/revision 2; DOL offset `0x1E800`, FST offset
`0x456E00`, FST size 29,993. These match catalog provenance. This is not a new
whole-ISO checksum certification. Member SHA-256 values were freshly computed:

| Member | SHA-256 |
| --- | --- |
| `PlMs.dat` | `0c4b7e49c8d18bfb3f5fd8c463d7c00b70292fa971b1ee94caf99548ba5b45b2` |
| `PlMsAJ.dat` | `a9560b7fdfca328dd3deeb6e999edc7ea1e89abe837c3846afdd46972b2ca308` |
| `PlYs.dat` | `95649bbf535503832190c9f34f400f27ad9c17523cebed88c1925bad1884f52b` |
| `PlYsAJ.dat` | `3282abc5431952243958af60e1d06e5aac6e3c185e02e2433d0c247581c1b3fd` |

Reopened these through the **catalog's exact extractor**,
`d255abefd162cfb63aabe875fb99aec4b62726ef`, loaded from Git objects into memory.
No checkout, environment file, extractor file or generated artifact was changed.
Also independently reopened the FST/member bytes with `struct`, and stepped the
two straight-line scripts without importing the extractor interpreter.

### Row mapping: not a neighboring animation

| Field | Marth jab 2 | Yoshi neutral air |
| --- | --- | --- |
| Runtime action | 45 / `NEUTRAL_ATTACK_2` | 65 / `NAIR` |
| DOL common MotionState address | `0x803C2DA0` | `0x803C3020` |
| DAT action-table index | 47 | 68 |
| Animation symbol | `PlyMars5K_Share_ACTION_Attack12_figatree` | `PlyYoshi5K_Share_ACTION_AttackAirN_figatree` |
| Animation frame count | 28 | 48 |
| Script file offset, including DAT header | `0x4B38` | `0x47C8` |
| DAT flags | `0x08000012` | `0x0000000E` |
| Animation callback | `0x8008B040`, `ftCo_Attack12_Anim` | `0x8008D010`, `ftCo_AttackAir_Anim` |
| Input callback | `0x8008B07C` | `0x8008D08C` |

The common table is `0x803C2800 + runtime_action * 0x20`. Its first word is
the DAT animation index, not the runtime action. Both rows resolve to the
expected named move. No character-relative action alias or slot substitution is
needed. Neither script branches, changes playback speed, or uses animation-timer
opcode 8. These findings do not cover interruption, landing, hitlag or blending.

### Marth 18:45: first-active and clear commands

DAT file offsets and command meanings:

- `0x4B38`: opcode 2, absolute timer 3.
- `0x4B3C`: opcode 49; then `0x4B40`: opcode 2, absolute timer 4.
- `0x4B54/0x4B68/0x4B7C/0x4B90`: opcode 11 creates IDs 0–3 at time 4.
  Bones 76/71/25/76, damage 4/4/4/6. No next-frame delay is encoded by create.
- `0x4BA4`: opcode 2, absolute timer 9.
- `0x4BA8`: opcode 16, clears all hitboxes at time 9.
- `0x4BC8`: opcode 23 enables interrupt at time 26.

Thus the raw script interval is `[4,9)`, or inclusive raw 4–8. Catalog values
faithfully reproduce this. However:

- `melee/actiondata.csv` records exactly `18,45,True` for `zeroindex`.
- `Console.__fixframeindexing` adds one to this action's raw post-frame counter.
- Historical `framedata.csv` stores active rows 4–8; `FrameData` reads its frame
  keys directly, without applying `actiondata.csv` normalization.
- Pinned `FrameData._disc_hitbox_frame_offset` returns **0** for Marth jab 2.
  The generator uses `frame.local_frame + offset`. `_subaction._frame(time)`
  is `max(1, ceil(time))`, not `time + 1`.
- `doAttack12Normal` in `ftCo_Attack1.c` enters `Attack12` at start 0/rate 1,
  without the extra `ftAnim_8006EBA4` immediately after the motion change that
  the common aerial entry has. This independently supports treating entry
  indexing as action-specific, not assigning the same origin to both moves.

The public-counter interval corresponding to raw 4–8 is therefore **5–9**.
The interrupt counter similarly maps raw 26 to public 27, agreeing with Wiki's
27. This corroborates an indexing-boundary omission in the catalog/facade's
public-frame interpretation, not a misdecoded hitbox command or wrong DAT row.
It does not authorize changing established numerical/signature compatibility.

### Yoshi 14:65: relative wait is decisive

- `0x47C8`: opcode 2, absolute timer 3.
- `0x47E0/0x47F4/0x4808`: opcode 11 creates clean IDs 0–2, bones 14/7/4,
  damage 14/base knockback 15, at time 3.
- `0x481C`: opcode **1**, relative timer **4**, not absolute frame 6.
- `0x4820/0x4834/0x4848`: opcode 11 recreates those IDs with damage 10/base
  knockback 0 after the wait, at time **7**.
- `0x485C`: opcode 2, absolute timer 34; `0x4860`: opcode 16 clears all.
- `0x4868`: opcode 19 clears the landing-lag flag at time 36.
- `0x4870`: opcode 23 enables interrupt at time 45.

`actiondata.csv` records `14,65,False`. Common aerial entry in
`ftCo_AttackAir.c:129–138` changes motion at start 0/rate 1 and immediately calls
`ftAnim_8006EBA4`. There is no additional Console increment. At unit rate,
native relative-timer arithmetic gives four clean frames **3,4,5,6**, then
late frames **7–33**. Absolute clear at 34 prevents a whole-action ±1 shift
from reconciling the Wiki: its startup and end already agree.

The pinned Wiki independently matches all three bones, offsets, sizes, damage,
angles and base/growth knockback, but its clean/late division is one frame
early. Its animation length 47 versus DAT endpoint 48 is separately consistent
with snapshot/endpoint accounting; that cannot move only the mid-attack damage
transition. The source provides no command dump or cited execution trace to
justify a three-frame wait. Classify its transition as contradicted by the
retail script/native-timer evidence, not a reason to rewrite catalog frames.

## Native timer branch check

Independently fetched doldecomp revision
`d15c9cffe939611627b3a7a77a446705d2998f5f`:

- [`lbcommand.c:19–30`](https://github.com/doldecomp/melee/blob/d15c9cffe939611627b3a7a77a446705d2998f5f/src/melee/lb/lbcommand.c#L19-L30):
  `Command_01` does `timer += value`; `Command_02` does
  `timer = value - frame_count`.
- [`ftaction.c:1321–1350`](https://github.com/doldecomp/melee/blob/d15c9cffe939611627b3a7a77a446705d2998f5f/src/melee/ft/ftaction.c#L1321-L1350):
  `ftAction_80073240` subtracts playback rate once per invocation and continues
  executing until timer is **strictly positive**, or the script ends. Zero
  does not defer to the following tick. Same-invocation effects are retained.
- [`ftaction.c:289–365`](https://github.com/doldecomp/melee/blob/d15c9cffe939611627b3a7a77a446705d2998f5f/src/melee/ft/ftaction.c#L289-L365):
  `ftAction_8007121C` writes the hitbox values immediately.
- [`fighter.c:1217–1345`](https://github.com/doldecomp/melee/blob/d15c9cffe939611627b3a7a77a446705d2998f5f/src/melee/ft/fighter.c#L1217-L1345):
  motion change initializes `cur_anim_frame = anim_start - frame_speed_mul`,
  uses timer zero at start zero, then runs the command path.
- [`ftCo_Attack1.c:185–209`](https://github.com/doldecomp/melee/blob/d15c9cffe939611627b3a7a77a446705d2998f5f/src/melee/ft/chara/ftCommon/ftCo_Attack1.c#L185-L209):
  non-Pikachu/Pichu second-jab entry (`doAttack12Normal`).
- [`ftCo_AttackAir.c:129–138`](https://github.com/doldecomp/melee/blob/d15c9cffe939611627b3a7a77a446705d2998f5f/src/melee/ft/chara/ftCommon/ftCo_AttackAir.c#L129-L138):
  common aerial entry's immediate animation/script advance.

Fresh ISO DOL reads, disassembled in memory with `llvm-mc --disassemble
--triple=powerpc`, confirm the relevant native arithmetic/strict-positive gate:

| Address / byte length | SHA-256 of native bytes | Witness |
| --- | --- | --- |
| `0x8000594C` / `0x48` | `0c3da173069bcfe62c6e009f630bcfcdf55fcacf153af97bb77c9232581169aa` | relative timer `fadds`, store at `CommandInfo+0` |
| `0x80005994` / `0x48` | `8bba8b9eb48a5ec78b0b211bd4ce0bda8548f2371d9835e7ba3e25e800eb07e6` | absolute value minus `CommandInfo+4` frame count |
| `0x80073240` / `0x114` | `bf0faf8f72c1ad88c63c015885a5f1e222f2c6f443e73b996cf9970970173d31` | timer minus `Fighter+0x89C` rate; strict-positive exit; repeated dispatch |

Addresses and sizes match the pinned
[`config/GALE01/symbols.txt`](https://github.com/doldecomp/melee/blob/d15c9cffe939611627b3a7a77a446705d2998f5f/config/GALE01/symbols.txt).
This is bounded binary corroboration, not execution of the entire native game.

## Geometry and artifact preservation

Fresh pinned-extractor static poses equal **every stored geometry row exactly**:
20 Marth rows (four hitboxes × five frames), 93 Yoshi rows (three × 31).
Both generator compatibility offsets are zero. No bone mismatch, geometry-slot
remap or animation substitution explains either timing conflict.

Important distinction: `DiscFrameData.posed_frame` samples animation time equal
to its supplied local frame. Moving a catalog frame key without preserving the
corresponding pose sample would alter geometry semantics. A future public-frame
normalization must convert between public frame and native pose time, not merely
shift query numbers and resample the next pose.

Catalog first appeared in commit
`a8d3e6eb58563a2e7d20571adf79ac1c01b78419`. Current numerical catalog SHA-256 is
`ad1c7a27d10da8c0ad0b4fd3d558ba104dabca634e5353077d84a8fb998a6940`.
Its frame values were not introduced by the later label-only additions.

## Source receipts

Complete response/file-byte SHA-256 values, independently checked in this task:

| Source | Revision / SHA-256 |
| --- | --- |
| [Marth jab 2 raw](https://www.ssbwiki.com/index.php?title=Marth_(SSBM)/Neutral_attack/Hit_2&action=raw&oldid=1934835) | 1934835 / `1bd3d27a2023e30aac78af35766727ee48c2b60206ad0823dfaeb95227423e1b` |
| [Yoshi nair raw](https://www.ssbwiki.com/index.php?title=Yoshi_(SSBM)/Neutral_aerial&action=raw&oldid=1394994) | 1394994 / `d564b1c251e102108c07ade3925ce70fdb660089f0fc924acc03637184c44183` |
| Pinned decomp `src/melee/lb/lbcommand.c` | d15c9cff / `266aec976cad2cdbf561a736c238592994cf5b3a651f91906c45652233bbd587` |
| Pinned decomp `src/melee/ft/ftaction.c` | d15c9cff / `5a0c443cab5ea538197279ff45889f1744389d556223d2b08462c24081157b07` |
| Pinned decomp `src/melee/ft/fighter.c` | d15c9cff / `39bfefd52e86cf37d604c090507dc23f553909766bcd316618e758a3c14af3d0` |
| Pinned decomp `src/melee/ft/chara/ftCommon/ftCo_Attack1.c` | d15c9cff / `d1b85194e7c434ffed9178fe94394a643e579aa74f527e5af80d6a298c188c22` |
| Pinned decomp `src/melee/ft/chara/ftCommon/ftCo_AttackAir.c` | d15c9cff / `8f11b9030d8a0f2f13de25cfd34d613cead89f500610bff870c8c4a31b932bfa` |
| Pinned decomp `config/GALE01/symbols.txt` | d15c9cff / `52959f0e13a6a1269051496e105fad51e9faac9d9dc0120b2bb20959d8a72b25` |
| [Extractor `melee/_subaction.py`](https://git.jacoby6000.com/LiveMindIO/libmelee/src/commit/d255abefd162cfb63aabe875fb99aec4b62726ef/melee/_subaction.py) | d255abe / `2b82ee5e4256373bdfea1394542ae615f99fb3b1e8052e50d699d42dd34a2527` |
| [Extractor `melee/disc_framedata.py`](https://git.jacoby6000.com/LiveMindIO/libmelee/src/commit/d255abefd162cfb63aabe875fb99aec4b62726ef/melee/disc_framedata.py) | d255abe / `275fc8ba6dfd2ce5f79eaef5d8135270de3f8b21687d64ab82836fa509c2f5c8` |
| [Extractor `melee/framedata.py`](https://git.jacoby6000.com/LiveMindIO/libmelee/src/commit/d255abefd162cfb63aabe875fb99aec4b62726ef/melee/framedata.py) | d255abe / `ef7ef3de410a742d4b879d2430d979bfcb6ef87ea247b693296cf284d131fb4a` |
| Baseline `scripts/build-hitbox-catalog.py` | e90926ab / `0b72dad22192b89098669e02f3a1a6ce1f939a84c76caf08b15cffc0f805bff2` |
| Baseline `melee/actiondata.csv` | e90926ab / `af329461b27b19e83f3a491f512e09873c53623f9d3eaba52825a4b844596137` |
| Baseline `melee/framedata.csv` | e90926ab / `8e0d811290b511902076c0011db1a0116356a7ddaa68dfa369ea4f5dcdc93777` |
| Baseline `melee/console.py` | e90926ab / `0054b078cb13079372c8d82528bd65efa35d6884ce60b1c065c25d55541a2bc4` |

Baseline file URLs use
`https://git.jacoby6000.com/LiveMindIO/libmelee/src/commit/e90926abf144cadeb93ba5032e27fe272a6c1baa/`
plus the listed relative path. Decomp short revisions in the table mean the
full revision linked above. Remote retrieval failures of guessed filenames
were discarded, never treated as evidence.

## Reproducible independent timing probe

Run from the libmelee root with an explicit legal ISO argument. This reads FST
and script words directly, without the extractor, writes nothing, and models
only these verified straight-line, unit-rate command streams. It is not a
general engine interpreter. Native semantics are the three witnessed functions
above; both scripts begin with an absolute timer, so no residual initial timer
is imported. Reported frames use the independently recorded per-action Console
normalization, not an inferred global origin.

```python
import hashlib
import struct
import sys

with open(sys.argv[1], "rb") as disc:
    disc.seek(0x424)
    offset, size = struct.unpack(">II", disc.read(8))
    disc.seek(offset)
    fst = disc.read(size)
    count = struct.unpack_from(">I", fst, 8)[0]

    def read_member(name):
        for i in range(1, count):
            tag, offset, size = struct.unpack_from(">III", fst, 12 * i)
            start = count * 12 + (tag & 0xFFFFFF)
            end = fst.index(0, start)
            if not tag >> 24 and fst[start:end].decode() == name:
                disc.seek(offset)
                return disc.read(size)
        raise AssertionError(name)

    lengths = {0: 1, 1: 1, 2: 1, 11: 5, 16: 1, 17: 3,
               19: 1, 23: 1, 29: 1, 43: 1, 49: 1}
    for name, pc, increment in [
        ("PlMs.dat", 0x4B38, 1), ("PlYs.dat", 0x47C8, 0)
    ]:
        data = read_member(name)
        timer, active, windows = 0, {}, {}
        for raw_frame in range(40):
            timer -= 1
            while pc is not None and timer <= 0:
                word = struct.unpack_from(">I", data, pc)[0]
                opcode = word >> 26
                assert opcode in lengths, opcode
                pc += 4 * lengths[opcode]
                if opcode == 0:
                    pc = None
                elif opcode == 1:
                    timer += word & 0x3FFFFFF
                elif opcode == 2:
                    timer = (word & 0x3FFFFFF) - raw_frame
                elif opcode == 11:
                    active[(word >> 23) & 7] = word & 0x1FF
                elif opcode == 16:
                    active.clear()
            for damage in set(active.values()):
                windows.setdefault(damage, []).append(raw_frame + increment)
        print(name, hashlib.sha256(data).hexdigest(),
              {d: (min(fs), max(fs), len(fs)) for d, fs in windows.items()})
```

Observed output intervals/counts: Marth damage 4 and 6 each `(5, 9, 5)`;
Yoshi damage 14 `(3, 6, 4)` and damage 10 `(7, 33, 27)`.

## Next testable actions and remaining boundary

- **Marth:** add a separately authorized public-frame/pose-origin regression,
  not a label-only edit. With an isolated diagnostic game, capture raw action
  frame, normalized action frame, command PC and hitbox enabled state around
  raw 3/4/8/9. Expected public boundaries are 5 and 10. Any proposed migration
  must preserve old signatures or version the compatibility contract explicitly.
- **Yoshi:** capture command PC, timer, damage and raw action frame at 5/6/7
  without hitlag. Expected damage is 14 at frame 6 and 10 at 7. If the game
  instead switches at 6, identify the extra timer invocation or rate/frame
  change; that specific missing runtime mechanism would overturn this bounded
  conclusion. A Wiki correction needs independent execution evidence, not an
  automatic edit based only on this report.
- No live game, DAP session, replay capture, whole-engine callback audit or
  collision-priority experiment was performed. The isolated native timer
  disassembly is corroboration, not engine/live certification.
