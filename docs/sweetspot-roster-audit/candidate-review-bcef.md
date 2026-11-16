# Independent candidate adjudication: B, C, E, F

2026-11-16. **40 ACCEPT, 0 REJECT, 9 UNRESOLVED**, across all 49 proposed
signatures / 11 actions. ACCEPT permits a static annotation, not runtime or
collision certification. UNRESOLVED means insufficient evidence for the proposed
role, not proof of an incorrect numerical phase or of absent sweet/sour behavior.
No annotations, catalog values, tests, or runtime code were edited by this review.
A/G candidates are outside this report.

## Independent checks

- Read libmelee `AGENTS.md`, `docs/sweetspot-labels.md`, all four JSON/Markdown
  shards, the numerical catalog, label CSV, `melee/bot/hitbox_phases.py`, query
  integration, `docs/hitbox-phases.md`, and relevant phase tests.
- Independently fetched all 15 sources below at their exact revisions. All raw
  byte hashes matched the shard receipts. Read source text/tables, not just shard
  interpretations. Move pages explicitly identify SSBM; general Punch/Kick pages
  were restricted to their Melee passages, including the Melee Kirby comparison.
- Matched every proposal uniquely to its own catalog hitbox/bone/phase and exact
  frame/damage/angle/element signature; also inspected knockback and target flags.
  All 49 were absent from the CSV at inspection. No clone, maximum-damage,
  chronological-first, or successive-hit inference was used.
- Exact-signature lookup leaves unknown phases unlabeled. Selectors filter only
  explicitly labeled phases; partial sweet-only/sour-only coverage is supported.
  No complementary annotation is required for a successful partial selection.
- `../../.venv/bin/python -m unittest test_hitbox_phases`: **44 passed**.
  These are existing tests, not regressions for adopting these candidates.

Local catalog SHA-256:
`ad1c7a27d10da8c0ad0b4fd3d558ba104dabca634e5353077d84a8fb998a6940`.
Historical framedata SHA-256:
`8e0d811290b511902076c0011db1a0116356a7ddaa68dfa369ea4f5dcdc93777`.
The CSV was concurrently advanced by other work from the shard baseline 569 to
577 rows; observed SHA-256
`600be54b7ec7f3bcecf8c62ae8069f1199c2af88b6a84c98b0d1d794a20080a2`.
This reviewer did not modify it or adjudicate that concurrent addition.

## Exact decisions

Each phase ID is `hitbox:bone:sequence`, scoped by character/action in its
heading. Columns F/D/A/E mean inclusive frames / damage / angle / element.
Together with the heading and phase ID these identify each exact CSV signature.
`361` is the preserved Sakurai-angle sentinel. Unless noted, both ground and air
targets are enabled. S-number references resolve to pinned source receipts below.

### B: Fox up tilt, 1:56 — 1 ACCEPT, 3 UNRESOLVED

S1 explicitly names the **ground-only sweetspot** and records all four zones.
It does not name the other three zones sour. A target-mask distinction or being
outside the named sweetspot does not independently adjudicate their role.

| Phase | F | D | A | E | Proposed role | Decision |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `0:15:1` | 5–11 | 12 | 110 | 0 | sweet | ACCEPT |
| `1:15:1` | 5–11 | 9 | 84 | 0 | sour | UNRESOLVED |
| `2:13:1` | 5–11 | 9 | 80 | 0 | sour | UNRESOLVED |
| `3:12:1` | 5–11 | 9 | 80 | 0 | sour | UNRESOLVED |

ID0 hits **grounded targets only**; ID1 hits **aerial targets only**. IDs2/3
hit both. All retain base18/growth140. Do not advertise sweet ID0 as an aerial
hit or label the other three sour merely to complete a partition.

### B: Falco up air, 22:68 — 1 ACCEPT, 2 UNRESOLVED

S2 explicitly calls the second hit's low-scaling zone a **sourspot**. ID2 uniquely
matches growth20 versus growth120 for IDs0/1. It does not explicitly adjudicate
IDs0/1 as sweet; retaining them unlabeled avoids a reverse-complement inference.

| Phase | F | D | A | E | Proposed role | Decision |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `0:13:1` | 11–14 | 10 | 70 | 0 | sweet | UNRESOLVED |
| `1:15:1` | 11–14 | 10 | 70 | 0 | sweet | UNRESOLVED |
| `2:4:2` | 11–14 | 10 | 90 | 3 | sour | ACCEPT |

ID2 retains base30/growth20/slash; the kicks retain base22/growth120/normal.
The 8–9 opener is a separate strike, not sour by omission. Equal 10% damage
does not erase the named second-hit body role.

### B: Falcon Gentleman, 2:46 — 4 ACCEPT

S3 explicitly separates clean/late within **Hit 3**, with matching 5–8/9–11
windows. This is temporal decay of one Gentleman, not ranking jabs or a finisher
against its linkers. Clean body is included, not only the leg zone.

| Phase | F | D | A | E | Proposed role | Decision |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `0:13:1` | 5–8 | 8 | 361 | 0 | sweet | ACCEPT |
| `1:4:1` | 5–8 | 8 | 361 | 0 | sweet | ACCEPT |
| `0:13:2` | 9–11 | 6 | 361 | 0 | sour | ACCEPT |
| `1:4:2` | 9–11 | 6 | 361 | 0 | sour | ACCEPT |

Base knockback changes20→0; growth100 remains. These are action-local frames,
not cumulative time from jab1.

### B: Falcon Punch ground/air, 2:347 / 2:348 — 2 ACCEPT, 4 UNRESOLVED

S4 maps independent ground/air zones; S5's **Melee** Kirby comparison explicitly
places Falcon's sweetspot closer to his body. This supports each close27% zone.
The reference to differing sweet/sour positions does not uniquely map both the
middle25% and far23% Falcon zones to sour. Do not fill both complements from
damage order or from a two-zone Kirby comparison.

| Action | Phase | F | D | A | E | Proposed role | Decision |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| 347 | `0:45:1` | 52–56 | 27 | 361 | 1 | sweet | ACCEPT |
| 347 | `1:45:1` | 52–56 | 25 | 361 | 1 | sour | UNRESOLVED |
| 347 | `2:47:1` | 52–56 | 23 | 361 | 1 | sour | UNRESOLVED |
| 348 | `0:45:1` | 52–56 | 27 | 361 | 1 | sweet | ACCEPT |
| 348 | `1:45:1` | 52–56 | 25 | 361 | 1 | sour | UNRESOLVED |
| 348 | `2:47:1` | 52–56 | 23 | 361 | 1 | sour | UNRESOLVED |

Growth102; ground base30 versus air40. Aerial close/middle geometry differs;
both actions were matched independently. S4's tables say Normal while its prose
calls the punch flaming and the catalog has element1: preserve/disclose this
table conflict, not silently change element. No reverse punch, charge mechanic,
or copied Kirby hitbox is imported from another game/context.

### B: Falcon Kick ground/air, 2:357 / 2:359 — 12 ACCEPT

S6 explicitly names continuous clean/mid/late phases for each version; S7's Melee
section specifically describes the clean first active frames. Named decay, not
three different strikes or an unqualified early-best rule, supports these roles.

| Action | Phase | F | D | A | E | Proposed role | Decision |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| 357 | `0:14:1` | 14–16 | 15 | 361 | 1 | sweet | ACCEPT |
| 357 | `1:13:1` | 14–16 | 15 | 361 | 1 | sweet | ACCEPT |
| 357 | `0:14:2` | 17–24 | 12 | 80 | 1 | sour | ACCEPT |
| 357 | `1:13:2` | 17–24 | 12 | 80 | 1 | sour | ACCEPT |
| 357 | `0:14:3` | 25–32 | 9 | 90 | 1 | sour | ACCEPT |
| 357 | `1:13:3` | 25–32 | 9 | 90 | 1 | sour | ACCEPT |
| 359 | `1:14:1` | 15–17 | 15 | 361 | 1 | sweet | ACCEPT |
| 359 | `2:13:1` | 15–17 | 15 | 361 | 1 | sweet | ACCEPT |
| 359 | `1:14:2` | 18–25 | 13 | 361 | 1 | sour | ACCEPT |
| 359 | `2:13:2` | 18–25 | 13 | 361 | 1 | sour | ACCEPT |
| 359 | `1:14:3` | 26–29 | 11 | 361 | 1 | sour | ACCEPT |
| 359 | `2:13:3` | 26–29 | 11 | 361 | 1 | sour | ACCEPT |

Ground base50/growth70→60→50; air base40/growth70→65→60. Ground mid12% is
supported by S6 despite the character-summary13% discrepancy. S6 explicitly
explains the air script's26–33 interval truncating at29; retain the catalog's29,
without claiming an independent engine-execution proof. Its animation-length
prose/table/trivia also differ; no animation-timing repair is certified here.
The noted noninteractive ground ID2 and separate landing hits are not added.
Wall collisions, travel speed, landing, and jump refresh are runtime boundaries.

### C: Link down air, 6:69 — 6 ACCEPT

S8/S9 identify clean/late and the exact windows, independently of Young Link.
Select all three clean zones, including both20% zones. These are base pre-bounce
signatures; S8's6/8% bounce behavior is not represented by these static phases.

| Phase | F | D | A | E | Proposed role | Decision |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `0:0:1` | 13–15 | 22 | 65 | 3 | sweet | ACCEPT |
| `1:0:1` | 13–15 | 20 | 65 | 3 | sweet | ACCEPT |
| `2:0:1` | 13–15 | 20 | 65 | 3 | sweet | ACCEPT |
| `0:0:2` | 16–64 | 19 | 65 | 3 | sour | ACCEPT |
| `1:0:2` | 16–64 | 19 | 65 | 3 | sour | ACCEPT |
| `2:0:2` | 16–64 | 19 | 65 | 3 | sour | ACCEPT |

ID0 retains base50; IDs1/2 base40; growth80 throughout. Bone0 is a common root,
not evidence that all three offsets share anatomy. Bounce/re-hit and landing
termination remain unmodeled; the label is not a guaranteed64-frame live hit.

### C: Young Link forward air, 20:66 — 8 ACCEPT

S10 explicitly states **one continuous hit despite two visual slashes**. S11
names clean/late, resolving the potential multihit confusion. All clean zones
are selected, not just12%; this adjudicates temporal roles, not spatial ranking.

| Phase | F | D | A | E | Proposed role | Decision |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `0:28:1` | 14–16 | 12 | 361 | 3 | sweet | ACCEPT |
| `1:25:1` | 14–16 | 11 | 361 | 3 | sweet | ACCEPT |
| `2:19:1` | 14–16 | 9 | 361 | 3 | sweet | ACCEPT |
| `3:28:1` | 14–16 | 9 | 361 | 3 | sweet | ACCEPT |
| `0:28:2` | 17–33 | 8 | 76 | 3 | sour | ACCEPT |
| `1:25:2` | 17–33 | 7 | 76 | 3 | sour | ACCEPT |
| `2:19:2` | 17–33 | 7 | 76 | 3 | sour | ACCEPT |
| `3:28:2` | 17–33 | 5 | 76 | 3 | sour | ACCEPT |

Base5/growth100 becomes base0/growth90. Late upward launch remains useful;
these labels do not say every clean zone dominates every late zone tactically.
No Link two-hit semantics or neighboring Young Link back-air timing is imported.

### E: Game & Watch down air, 24:69 — 3 ACCEPT

S12 explicitly names14% sweetspot /13% sourspot and describes the early meteor.
S13 maps those named roles to the exact IDs, angles and windows.

| Phase | F | D | A | E | Proposed role | Decision |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `0:0:1` | 12 | 14 | 270 | 0 | sweet | ACCEPT |
| `0:0:2` | 13–38 | 13 | 60 | 0 | sour | ACCEPT |
| `1:0:1` | 12–38 | 13 | 60 | 0 | sour | ACCEPT |

Base20/growth100 throughout. ID1 is already13%/60 at frame12: preserve its one
unbroken phase, rather than split it to mirror source table headings. The
separate6% landing attack is not a sour phase. No Judgment RNG or article power
is relevant to these fighter-owned key signatures.

### F: Peach down tilt, 9:57 — 3 ACCEPT (partial)

S14 explicitly distinguishes the forearm meteor from hand non-meteor and names
sweet/sour outcomes. S15 maps both-target meteor IDs2/3 and air-only launcherID1.
Equal12% damage is deliberately not the selection rule. Bone97's precise anatomy
is not established: retain the proposed neutral label **inner meteor**.

| Phase | F | D | A | E | Proposed role | Decision |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `2:72:1` | 12–13 | 12 | 270 | 0 | sweet | ACCEPT |
| `3:97:1` | 12–13 | 12 | 270 | 0 | sweet | ACCEPT |
| `1:74:1` | 12–13 | 12 | 80 | 0 | sour | ACCEPT |

Meteor zones base60/growth100; air-only launcher base15/growth100. Unproposed
ground-only meteor `0:74:1` shares the launcher's bone/geometry but is not an
adjudicated anatomical sweet/sour role; leave it unlabeled. Do not imply that
every grounded meteor contact selects one of the two accepted sweet phases.
These are not float variants, vegetable RNG, or a guarantee of ledge connectivity.

## Independently retrieved source receipts

Each link retrieves raw bytes at the listed exact revision; SHA-256 covers those
bytes. All retrievals succeeded and matched the respective shard receipt. General
Punch/Kick pages contain other games; only the specified Melee text supports this
report. The extra sweet-spot overview revision2059342 was also checked but supplies
no additional candidate-specific evidence and is not used for adoption.

| ID | Pinned raw source / revision | SHA-256 |
| --- | --- | --- |
| S1 | [Fox up tilt1655106](https://www.ssbwiki.com/index.php?title=Fox_(SSBM)/Up_tilt&action=raw&oldid=1655106) | `02eeb4a1600b552a2f880eb1e3c8ee52935bc11c87060109f85399f1ef7b0c1b` |
| S2 | [Falco up air2031216](https://www.ssbwiki.com/index.php?title=Falco_(SSBM)/Up_aerial&action=raw&oldid=2031216) | `d2288f9ee166211618e8ede4b5be6be9c316552210406eb90734e1c08177f7dc` |
| S3 | [Falcon Gentleman1915179](https://www.ssbwiki.com/index.php?title=Captain_Falcon_(SSBM)/Neutral_attack/Hit_3&action=raw&oldid=1915179) | `2214ad20a49e82222aa05ad57fca664568e7a242178f50cc7e01a3e31b3a5dae` |
| S4 | [Falcon neutral special1930502](https://www.ssbwiki.com/index.php?title=Captain_Falcon_(SSBM)/Neutral_special&action=raw&oldid=1930502) | `2764230fac590075b2069b4dad76846350e10d7a12e40c87cdb455fc1d46d7ed` |
| S5 | [Falcon Punch2067832](https://www.ssbwiki.com/index.php?title=Falcon_Punch&action=raw&oldid=2067832) | `6129e36937db2be987a75bde1a61ed7ae68352f2e6f6dde0fd4c30e1ee8680cb` |
| S6 | [Falcon down special2056712](https://www.ssbwiki.com/index.php?title=Captain_Falcon_(SSBM)/Down_special&action=raw&oldid=2056712) | `8880783d09b5c450543d27bdffb58cbdacc353ac0b37b609ef070f63cc6892db` |
| S7 | [Falcon Kick2012692](https://www.ssbwiki.com/index.php?title=Falcon_Kick&action=raw&oldid=2012692) | `bd604b7c17436543d1e8edb16e8b5b6f8320a0e7c4de698902cb9a6305942f3e` |
| S8 | [Link2062902](https://www.ssbwiki.com/index.php?title=Link_(SSBM)&action=raw&oldid=2062902) | `dd26db3fd234a97087b0b6ae0bcf4048524ff0580077f17a06dea3adf94873c5` |
| S9 | [Link down air2002902](https://www.ssbwiki.com/index.php?title=Link_(SSBM)/Down_aerial&action=raw&oldid=2002902) | `133cee3b78a71c3b29da90ca34354169a05c573d1431f2c499836c881e4abe87` |
| S10 | [Young Link2062463](https://www.ssbwiki.com/index.php?title=Young_Link_(SSBM)&action=raw&oldid=2062463) | `1a1be48c05bfcf0e01ebbfc985f4ac5c15e6bcdc1117dab044e93b1c51db6706` |
| S11 | [Young Link forward air1389928](https://www.ssbwiki.com/index.php?title=Young_Link_(SSBM)/Forward_aerial&action=raw&oldid=1389928) | `22f9ad49c41cb5a4973c94123f7747521e6dbe455fd0dcf47478212b21a29826` |
| S12 | [Game & Watch2062479](https://www.ssbwiki.com/index.php?title=Mr._Game_%26_Watch_%28SSBM%29&action=raw&oldid=2062479) | `ae5f283816a038ad9df8cd68d82890cbfe858b58d812c7d5fe21ad9c1aa8195f` |
| S13 | [Game & Watch down air1938699](https://www.ssbwiki.com/index.php?title=Mr._Game_%26_Watch_%28SSBM%29%2FDown_aerial&action=raw&oldid=1938699) | `3e5b321f621f71c452534c89938044a6cc3d08def31a26f2dfc08478a2ec47b8` |
| S14 | [Peach2062455](https://www.ssbwiki.com/index.php?title=Peach_(SSBM)&action=raw&oldid=2062455) | `11f7af01d20ded882ea24acfd0c3b96efe31ac29d4154afbd92cf376feecc064` |
| S15 | [Peach down tilt1939197](https://www.ssbwiki.com/index.php?title=Peach_(SSBM)/Down_tilt&action=raw&oldid=1939197) | `90982cb5c2712a608b7c180ab2248c24a9093057452dd3dffff7b0888886d456` |

## Adoption boundary

| Shard | Proposed | ACCEPT | REJECT | UNRESOLVED |
| --- | ---: | ---: | ---: | ---: |
| B | 29 | 20 | 0 | 9 |
| C | 14 | 14 | 0 | 0 |
| E | 3 | 3 | 0 | 0 |
| F | 3 | 3 | 0 | 0 |
| Total | 49 | 40 | 0 | 9 |

Seven proposed sour complements (Fox3, Punch4) overreach the inspected named
evidence; two Falco sweet complements likewise need independent adjudication.
Leave all nine unlabeled pending stronger evidence. ACCEPT rows still require
lead-owned integration and exact-signature/partial-selection regressions.
No runtime, full-roster source, extraction completeness, overlap priority,
vulnerability, contact guarantee, or live-emulator signoff is given.
