# Additional reviewed sweetspot labels

These annotations extend the original 19 signatures by 601, for 620 labeled
phases across 144 character/action pairs. Successive batches cover eight, 34,
31, six, 16, 13, two, one, two, two, one, two, four, two, four and 11 character/action pairs, listed below.
A further three annotations reuse three of those actions.
They do not modify the NTSC-U 1.02 numerical catalog, geometry or frame indexing.

## Evidence

Each row below was checked against `melee/hitbox_catalog.json` and the listed
public sources. IDs are engine hitbox IDs, not historical CSV geometry slots.
Frame intervals are inclusive. Damage is before gameplay modifiers, uncharged
unless an explicitly full-charge action is identified below.

| Character/action | Frames | Sweet variant | Other labeled variant |
| --- | --- | --- | --- |
| Zelda back air, 19/67 | 5–8 | ID 2, bone 16: 20%, electric | IDs 0/1, bones 13/4: 10%, normal |
| Samus back air, 13/67 | 9–12 | ID 2, bone 18: 14%, foot | IDs 0/1, bone 14: 10%, leg |
| Mario forward smash up, 0/58 | 12–16 | ID 0, bone 0: 19%, fire | IDs 1/2, bones 0/29: 15%, normal |
| Mario forward smash level, 0/60 | 12–16 | ID 0, bone 0: 18%, fire | IDs 1/2, bones 0/29: 11%/10%, normal |
| Mario forward smash down, 0/62 | 12–16 | ID 0, bone 0: 17%, fire | IDs 1/2, bones 0/29: 13%, normal |
| Luigi down air, 17/69 | 10–14 | ID 2, bone 54: 16%, angle 270, meteor | IDs 0/1, bones 4/55: 16%, angle 361 |
| Falcon down air, 2/69 | 16–20 | ID 2, bone 4: 16%, angle 290, nipple spike | IDs 0/1, bones 14/13: 16%, angle 270, meteor |
| Young Link down air early, 20/69 | 13–15 | ID 2, bone 0: 16%, fire, angle 270 | IDs 0/1, bone 0: 14%, slash, angle 70 |
| Young Link down air late, 20/69 | 16–64 | ID 2, bone 0: 21%, fire, angle 270 | IDs 0/1, bone 0: 17%, slash, angle 70 |

### Source revisions

SmashWiki move descriptions establish the named spatial/trajectory variants.
FightCore supplies independent per-ID damage, angle, effect and frame tables
for the level forward smash and five aerials. Mario's angled damage values
are also recorded in the character moveset table and the extracted catalog.
FightCore pages are mutable; the pinned catalog and regression fixtures retain
the exact checked values rather than fetching web data at runtime.

- Zelda: [moveset, revision 2066384](https://www.ssbwiki.com/index.php?title=Zelda_(SSBM)&oldid=2066384#Moveset),
  [FightCore](https://data.fightcore.gg/characters/239/zelda).
- Samus: [moveset, revision 2062465](https://www.ssbwiki.com/index.php?title=Samus_(SSBM)&oldid=2062465#Moveset),
  [FightCore](https://data.fightcore.gg/characters/212/samus).
- Mario: [moveset, revision 2062453](https://www.ssbwiki.com/index.php?title=Mario_(SSBM)&oldid=2062453#Moveset),
  [FightCore](https://data.fightcore.gg/characters/236/mario).
- Luigi: [down air, revision 1983582](https://www.ssbwiki.com/index.php?title=Luigi_(SSBM)/Down_aerial&oldid=1983582),
  [FightCore](https://data.fightcore.gg/characters/213/luigi).
- Falcon: [down air, revision 2027556](https://www.ssbwiki.com/index.php?title=Captain_Falcon_(SSBM)/Down_aerial&oldid=2027556),
  [FightCore](https://data.fightcore.gg/characters/227/captainfalcon).
- Young Link: [down air, revision 2058960](https://www.ssbwiki.com/index.php?title=Young_Link_(SSBM)/Down_aerial&oldid=2058960),
  [FightCore](https://data.fightcore.gg/characters/220/younglink).

## Meaning and limits

`sweet` selects the named powerful hit or meteor/spike variant, not a universal
tactical ranking. Luigi's non-meteor can be preferable for horizontal knockback;
Falcon's ordinary meteor remains useful for grounded combos. Young Link's
non-meteor launches upward, and his late meteor is stronger than his early one.
Do not derive these labels by sorting damage or treating all late hits as sour.

The labels do not prove which overlapping hitbox wins collision priority, that
the target can be hit, or that a meteor/spike connects in a given position.
Selected prediction retains the documented static-pose limitations. Young Link
bounce/runtime changes are not new phases in this patch; only the exact catalog
signatures above are labeled. Changed signatures remain unmatched rather than
inheriting a label by character/action alone.

This is a bounded addition, not a complete all-roster audit. Other normals,
specials, copies, partner variants and projectile/article hitboxes still require
individual review. Maximum damage alone is insufficient evidence for labeling
other candidates, including Mewtwo's differing down-air damage zones.

## Roster continuation: 159 additional signatures

The following table defines the selected engine IDs and inclusive windows.
Other phases of each listed action are sour. Exact bone, damage, angle and
element values remain in the CSV and must match the numerical catalog.
No selection is calculated by ranking damage at runtime.

| Character | Raw action / move | Sweet engine IDs and frames |
| --- | --- | --- |
| Dr. Mario | 66 forward air | 0: 18–22, strong punch rather than hand |
| Dr. Mario | 65 neutral air | 0/1: 20–31, late strong kick |
| Sheik | 63 up smash | 0/1: 12, overhead rather than side swing |
| Sheik | 67 back air | 3: 4–7 and 8–19, foot in both phases |
| Ness | 341 forward smash | 3: 16–17, bat tip |
| Peach | 63 up smash | 1: 13–22, shoulder |
| Donkey Kong | 69 down air | 0: 18–23, foot meteor rather than body meteor |
| Game & Watch | 346 forward smash | 0/1: 13–16, early torch |
| Game & Watch | 64 down smash | 2/3: 15–19, hammer heads |
| Fox / Falco | 64 down smash | 0/1: 6–10, feet rather than legs |
| Fox / Falco | 67 back air | 0/1: 4–7, strong early kick |
| Luigi | 355 grounded / 356 aerial Super Jump Punch | 0: 5, fire punch rather than coins |
| Marth | 44 / 45 jabs | 3: 4–7 / 4–8, tipper |
| Marth | 53 forward tilt | 3: 7–10, tipper |
| Marth | 56 up tilt | 3: 6–8 and 9–12, tipper in both phases |
| Marth | 57 down tilt | 3: 7–9, tipper |
| Marth | 50 dash attack | 3: 12–15, tipper |
| Marth | 63 up smash | 3: 13–16, named tipper (not literal blade endpoint) |
| Marth | 64 down smash | 3: 5–7 and 20–22, both tipper swings |
| Marth | 67 back air | 3: 7–11, tipper |
| Marth | 68 up air | 0: 5–8, tipper |
| Marth | 69 down air | 0: 6–9, NTSC spike |
| Roy | 44 jab | 1/2: 4–7, inner strong zones |
| Roy | 53 forward tilt | 1/2: 9–13, inner strong zones |
| Roy | 56 up tilt | 2: 7–9 and 10–13, body |
| Roy | 57 down tilt | 1/2: 8–10, inner strong zones |
| Roy | 64 down smash | 0/1/2: 6–8 and 23–25, both inner swings |
| Roy | 66 forward air | 0/1/2: 5–7, inner zones |
| Roy | 67 back air | 0/1/2: 8–10, inner zones |
| Roy | 68 up air | 1/2/3: 5–10, inner zones |

### Continuation sources

Pinned SmashWiki character revisions supply the move descriptions and named
variants. FightCore supplies per-engine-ID combat values and timing. Each
character link below points to the moveset used in the audit:

The physical zones also have explicit bone/offset tables in
[Fox down smash, revision 2016028](https://www.ssbwiki.com/index.php?title=Fox_(SSBM)/Down_smash&oldid=2016028),
[DK down air, revision 1728388](https://www.ssbwiki.com/index.php?title=Donkey_Kong_(SSBM)/Down_aerial&oldid=1728388),
and [Marth up smash, revision 1436027](https://www.ssbwiki.com/index.php?title=Marth_(SSBM)/Up_smash&oldid=1436027).

| Character | SmashWiki revision | FightCore data |
| --- | --- | --- |
| Dr. Mario | [2062457](https://www.ssbwiki.com/index.php?title=Dr._Mario_(SSBM)&oldid=2062457#Moveset) | [215](https://data.fightcore.gg/characters/215/drmario) |
| Sheik | [2066385](https://www.ssbwiki.com/index.php?title=Sheik_(SSBM)&oldid=2066385#Moveset) | [260](https://data.fightcore.gg/characters/260/sheik) |
| Ness | [2062474](https://www.ssbwiki.com/index.php?title=Ness_(SSBM)&oldid=2062474#Moveset) | [243](https://data.fightcore.gg/characters/243/ness) |
| Peach | [2062455](https://www.ssbwiki.com/index.php?title=Peach_(SSBM)&oldid=2062455#Moveset) | [240](https://data.fightcore.gg/characters/240/peach) |
| Donkey Kong | [2062459](https://www.ssbwiki.com/index.php?title=Donkey_Kong_(SSBM)&oldid=2062459#Moveset) | [242](https://data.fightcore.gg/characters/242/donkeykong) |
| Game & Watch | [2062479](https://www.ssbwiki.com/index.php?title=Mr._Game_%26_Watch_(SSBM)&oldid=2062479#Moveset) | [219](https://data.fightcore.gg/characters/219/mrgame%26watch) |
| Fox | [2062523](https://www.ssbwiki.com/index.php?title=Fox_(SSBM)&oldid=2062523#Moveset) | [224](https://data.fightcore.gg/characters/224/fox) |
| Falco | [2062469](https://www.ssbwiki.com/index.php?title=Falco_(SSBM)&oldid=2062469#Moveset) | [218](https://data.fightcore.gg/characters/218/falco) |
| Luigi | [2062454](https://www.ssbwiki.com/index.php?title=Luigi_(SSBM)&oldid=2062454#Moveset) | [213](https://data.fightcore.gg/characters/213/luigi) |
| Marth | [2066242](https://www.ssbwiki.com/index.php?title=Marth_(SSBM)&oldid=2066242#Moveset) | [222](https://data.fightcore.gg/characters/222/marth) |
| Roy | [2062478](https://www.ssbwiki.com/index.php?title=Roy_(SSBM)&oldid=2062478#Moveset) | [223](https://data.fightcore.gg/characters/223/roy) |

### Conflicts, gaps and exclusions

- FightCore reports Fox/Falco back-air late hits starting at 7 while the catalog
  uses 8. Preserve catalog 4–7 / 8–19; do not merge overlapping source intervals
  or shift every action. The named early/late variants agree.
- Roy's Wiki up-tilt summary says 8% for blade/arm; FightCore and the catalog
  distinguish an 8% blade, 9% arm and 10% body. Only the body is labeled sweet;
  intermediate arm damage remains intact. This is not a catalog correction.
- Luigi's aerial FightCore table omits late coins; the catalog contains them.
  The character description explicitly distinguishes the aerial clean hit
  from the 1% late hit. Preserve both catalog coin hitboxes.
- Ness forward smash uses raw action 341, not generic `FSMASH_MID` (60).
  Game & Watch forward smash uses 346; use the numeric action to avoid a
  misleading generic name. Query resolution is unchanged by this addition.
- Marth neutral-air inner/tip zones have identical combat values apart from
  sound. Neither hit of that two-hit move is assigned sweet/sour here.
- Roy neutral air is a multihit attack with an unlabeled opener; do not label
  its finisher sweet merely because it deals more damage. Judge its spatial
  finisher variants separately before exposing a partial selection.
- Roy down air, Roy dash attack and Kirby Hammer are absent from the current
  numerical results despite independent evidence of hitboxes. Adding labels
  cannot repair extraction gaps. Game & Watch Judgment and Oil Panic remain
  unlabeled: RNG and absorbed-projectile power are not positional sweetspots.
- These annotations do not establish collision priority, charge behavior,
  copied or partner equivalence, article coverage, or complete roster coverage.

## Clean/late continuation: 150 additional signatures

This batch covers 31 actions. Unless noted, sweet selects the documented clean
hit across all engine IDs; every later phase is sour. These are named temporal
variants, not rankings between different moves, successive hits or charge levels.
The weaker late hit can still be preferable for combos or positioning.

| Character | Raw action / move | Sweet engine IDs and frames |
| --- | --- | --- |
| Mario | 65 neutral air | 0/1: 3–6 |
| Mario | 67 back air | 0/1: 6–8 |
| Luigi | 65 neutral air | 0/1: 3–6 |
| Peach | 65 neutral air | 0/1/2: 3–6 |
| Peach | 67 back air | 0: 6–9 |
| Bowser | 67 back air | 0: 9–10, shell semi-spike |
| Donkey Kong | 65 neutral air | 0/1/2: 10–13 |
| Donkey Kong | 67 back air | 0/1: 7–8 |
| Captain Falcon | 67 back air | 0/1/2: 10–13 |
| Captain Falcon | 50 dash attack | 0: 7–9 |
| Ganondorf | 50 dash attack | 0: 7–9 |
| Ness | 65 neutral air | 0/1/2: 5–12 |
| Ness | 67 back air | 0/1: 10–11, electric rather than normal |
| Kirby | 67 back air | 0/1: 6–8 |
| Kirby | 63 up smash | 0/1: 13, 14–15 and 16–23; stronger spatial zone in all three phases; ID 2 sour throughout |
| Samus | 50 dash attack | 0: 7–9 |
| Samus | 65 neutral air | 0/1: 5–8 |
| Sheik | 65 neutral air | 0/1/2: 3–6; weaker clean ID 3 and every late hit sour |
| Sheik | 68 up air | 0/1: 5–7; NTSC values |
| Pichu | 65 neutral air | 0/1/2: 3–10 |
| Pikachu | 65 neutral air | 0/1/2: 3–10 |
| Pikachu | 63 up smash | 0/1/2: 8–10; all three clean zones, not just the 19% zone |
| Jigglypuff | 65 neutral air | 0/1: 6–7 |
| Jigglypuff | 66 forward air | 0: 7–8, clean feet; clean body and both late zones sour |
| Mewtwo | 50 dash attack | 0/1/2: 10–14; both launch trajectories retained |
| Mewtwo | 60 forward smash | 1: 18–19, shadow blast; arms sour |
| Link | 65 neutral air | 1: 4–5, clean foot; clean back leg/hip and every late hit sour |
| Link | 68 up air | 0/1/2: 5–7 |
| Young Link | 65 neutral air | 0/1/2: 4–5 |
| Young Link | 68 up air | 0/1/2: 5–7 |
| Yoshi | 65 neutral air | 0/1/2: 3–6 |

### Sources and qualifications

Previously linked character revisions and FightCore datasets cover Mario,
Luigi, Peach, DK, Ness, Samus and Sheik. Falcon's clean/late descriptions use
[revision 2064399](https://www.ssbwiki.com/index.php?title=Captain_Falcon_(SSBM)&oldid=2064399#Moveset)
with the previously linked FightCore dataset. Additional character sources:

| Character | SmashWiki revision | FightCore data |
| --- | --- | --- |
| Bowser | [2062456](https://www.ssbwiki.com/index.php?title=Bowser_(SSBM)&oldid=2062456#Moveset) | [241](https://data.fightcore.gg/characters/241/bowser) |
| Ganondorf | [2063060](https://www.ssbwiki.com/index.php?title=Ganondorf_(SSBM)&oldid=2063060#Moveset) | [216](https://data.fightcore.gg/characters/216/ganondorf) |
| Kirby | [2064405](https://www.ssbwiki.com/index.php?title=Kirby_(SSBM)&oldid=2064405#Moveset) | [210](https://data.fightcore.gg/characters/210/kirby) |
| Pichu | [2062472](https://www.ssbwiki.com/index.php?title=Pichu_(SSBM)&oldid=2062472#Moveset) | [221](https://data.fightcore.gg/characters/221/pichu) |
| Pikachu | [2062470](https://www.ssbwiki.com/index.php?title=Pikachu_(SSBM)&oldid=2062470#Moveset) | [237](https://data.fightcore.gg/characters/237/pikachu) |
| Jigglypuff | [2064701](https://www.ssbwiki.com/index.php?title=Jigglypuff_(SSBM)&oldid=2064701#Moveset) | [214](https://data.fightcore.gg/characters/214/jigglypuff) |
| Mewtwo | [2062473](https://www.ssbwiki.com/index.php?title=Mewtwo_(SSBM)&oldid=2062473#Moveset) | [217](https://data.fightcore.gg/characters/217/mewtwo) |
| Link | [2062902](https://www.ssbwiki.com/index.php?title=Link_(SSBM)&oldid=2062902#Moveset) | [238](https://data.fightcore.gg/characters/238/link) |
| Young Link | [2062463](https://www.ssbwiki.com/index.php?title=Young_Link_(SSBM)&oldid=2062463#Moveset) | [220](https://data.fightcore.gg/characters/220/younglink) |
| Yoshi | [2062466](https://www.ssbwiki.com/index.php?title=Yoshi_(SSBM)&oldid=2062466#Moveset) | [211](https://data.fightcore.gg/characters/211/yoshi) |

- FightCore's DK back-air records use placeholder frame 0. The catalog's clean
  7–8 and late 9–15 intervals agree with
  [SmashWiki revision 1966076](https://www.ssbwiki.com/index.php?title=Donkey_Kong_(SSBM)/Back_aerial&oldid=1966076).
- FightCore omits Link neutral-air late hits. The catalog's 6–39 late interval
  agrees with [SmashWiki revision 1570758](https://www.ssbwiki.com/index.php?title=Link_(SSBM)/Neutral_aerial&oldid=1570758).
  Its activity through the animation end is a documented script quirk, not a
  reason to truncate or shift catalog frames.
- [Kirby up-smash revision 1875867](https://www.ssbwiki.com/index.php?title=Kirby_(SSBM)/Up_smash&oldid=1875867)
  independently records all three phases, bone IDs and offsets. The late sweet
  zones and clean sour zone both deal 13%; their damage equality does not merge
  the distinct spatial roles. Labels avoid inventing a bone-name mapping.
- Yoshi back air has four successive hits with decreasing damage, not four
  power-decay phases of one hit. It remains unlabeled. Ganondorf up air's useful
  reverse semi-spikes and Kirby neutral air's surviving clean phase are
  adjudicated separately below; neither uses a generic early-best rule.
- Zelda and Mewtwo down-air damage zones still lack an
  adjudicated sweet/sour interpretation; no labels are inferred from maxima.
- Ice Climbers leader/partner behavior and Peach float states are not covered
  merely by reviewing another fighter/state. The independently verified float
  neutral/back-air additions below do not imply coverage of other float attacks.

## Ice Climbers static hammer variants: 16 additional signatures

Popo (10) and Nana (11) each have independently matched catalog signatures for
the following selections. These are script-base values, not partner-adjusted
damage, the combined damage of two climbers, or a claim about either climber's
current runtime role. Labels do not derive one character's coverage by aliasing
the other. All listed sweet/sour differences remain within one action.

| Raw action | Sweet engine IDs and frames | Other phases |
| --- | --- | --- |
| 60 forward smash | 0, bone 15: 13–14, hammer head, 14% | 1, bone 10: hammer handle, 10% |
| 67 back air | 0, bone 15: 8–11, hammer head, 12% | 1, bone 11: hammer handle, 11% |
| 68 up air | 0/1, bones 15/11: 6–9, clean hammer reach, 9% | Same IDs/bones: 10–23, late reach, 7% |

Evidence: [character moveset revision 2062476](https://www.ssbwiki.com/index.php?title=Ice_Climbers_(SSBM)&oldid=2062476#Moveset)
and [FightCore 209](https://data.fightcore.gg/characters/209/iceclimbers).
Independent bone/offset tables agree for
[forward smash, revision 1394122](https://www.ssbwiki.com/index.php?title=Ice_Climbers_(SSBM)/Forward_smash&oldid=1394122)
and [back air, revision 1392758](https://www.ssbwiki.com/index.php?title=Ice_Climbers_(SSBM)/Back_aerial&oldid=1392758).

The later bounded forward-air adjudication below labels only each character's
exact aerial-target meteor signature. A shared character article and equal
script records do not prove equal runtime behavior. Partner damage scaling and
forward-air angle adjustment still require a separate runtime audit; no catalog
values are rewritten to simulate them here.

## Fox, Falco, Kirby and Dolphin Slash: 82 additional signatures

All engine IDs in each listed clean window are sweet, except Dolphin Slash,
which selects only the named startup tip. Remaining phases are sour. Exact
angle differences are preserved, including Falco's clean body forward-smash
angle and Kirby's front/back down-smash trajectories.

| Character | Raw action / move | Sweet engine IDs and frames |
| --- | --- | --- |
| Fox | 50 dash attack | 0/1: 4–7 |
| Fox | 60 forward smash | 0/1/2: 12–16 |
| Fox | 63 up smash | 0/1: 7–9, NTSC 18% |
| Fox | 65 neutral air | 0/1/2: 4–7 |
| Falco | 50 dash attack | 1: 4–7; no invented ID 0 |
| Falco | 60 forward smash | 0/1/2: 12–16 |
| Falco | 63 up smash | 0/1: 7–10 |
| Falco | 65 neutral air | 0/1/2: 4–7 |
| Kirby | 56 up tilt | 0/1: 4 |
| Kirby | 351 dash attack | 0: 9–15, NTSC 8% |
| Kirby | 58 / 60 / 62 angled forward smashes | 0/1/2: 13–15 in each action |
| Kirby | 64 down smash | 0/1/2/3: 7–9 |
| Marth | 367 grounded / 368 aerial Dolphin Slash | 0: 5, startup tip; non-tip startup and every leap hit sour |

Fox/Falco/Kirby descriptions and per-ID values use the previously linked
character revisions and FightCore datasets. Each action's independent catalog
signature is checked, including all three Kirby forward-smash angles.
Kirby's Wiki down-smash summary lists a 10% late hit, but FightCore and the
catalog retain 12% for IDs 0/1 and 10% for IDs 2/3; no values are flattened.

[Marth up-special revision 2056097](https://www.ssbwiki.com/index.php?title=Marth_(SSBM)/Up_special&oldid=2056097)
explicitly identifies the disjoint startup sweetspot and records the frame-5
13% tip, frame-5 10% non-tip hits, and frame-6–10 7%/6% leap hits. Both raw
catalog actions independently match these signatures. FightCore's ground/air
Dolphin Slash records have placeholder frame 0 and split startup/leap values
between entries; they do not establish different ground/air power here.
The public `up-b` query retains both action identities. Shield Breaker's charge
levels remain unlabeled, not treated as alternative sweetspots.

## Remaining clean hits and sustained slide: 57 additional signatures

The clean/early temporal selections below preserve all target flags, angle
variants and script phase boundaries. They do not select only maximum-damage
spatial zones: Peach/Zelda's weaker clean zones are included with their stronger
clean zones. Other phases are sour, except the sustained Dr. Mario slide noted
below. No new behavior is inferred from damage alone.

| Character | Raw action / move | Sweet engine IDs and frames |
| --- | --- | --- |
| Dr. Mario | 56 up tilt | 0/1/2: 4 |
| Dr. Mario | 63 up smash | 0/1: 9–10; both ground/air target variants retained |
| Dr. Mario | 67 back air | 0/1: 6–8, clean semi-spike |
| Dr. Mario | 50 dash attack | 0: 6–9 and 1: 6–25, strong slide |
| Peach | 53 forward tilt | 0/1/2: 6–7, all three clean zones |
| Peach | 50 dash attack | 0/1: 6–8 |
| Sheik | 50 dash attack | 0/1: 6 |
| Pikachu | 60 forward smash | 0: 16–18, early jolt; 19–21 and 22–23 phases sour |
| Pikachu | 67 back air | 0/1: 4–7; landing attack is a separate action |
| Jigglypuff | 56 up tilt | 0/1: 8–9 |
| Jigglypuff | 60 forward smash | 0/1: 12–15 |
| Game & Watch | 66 forward air | 0/1: 10–12 |
| Zelda | 50 dash attack | 0/1: 6–8 |

Evidence: the previously linked character moveset revisions and FightCore
datasets. [Dr. Mario dash attack, revision 1952263](https://www.ssbwiki.com/index.php?title=Dr._Mario_(SSBM)/Dash_attack&oldid=1952263)
independently confirms that only ID 0 weakens at frame 10: ID 1 remains at 9%
through frame 25. Its unchanged 6–25 phase remains sweet throughout; no synthetic
split is added merely to align its window with ID 0 or FightCore's row grouping.

[Sheik down smash, revision 1651635](https://www.ssbwiki.com/index.php?title=Sheik_(SSBM)/Down_smash&oldid=1651635)
identifies three separate strikes at 5–9, 16–19 and 22–24. It remains unlabeled:
the moveset summary's clean/late wording must not turn successive hit roles into
sweet/sour phases. Missing Mario, Bowser, DK and Jigglypuff dash-attack results
also remain gaps; nearby forward-tilt action IDs are not substitutes.

## Kirby spin and Ganondorf reverse kick: nine additional signatures

| Character | Raw action / move | Sweet engine IDs and frames | Sour phases |
| --- | --- | --- | --- |
| Kirby | 65 neutral air | 0, bone 4: 10–17, 10% clean spin | 18–29 mid 8%; 30–34 late 6% |
| Ganondorf | 68 up air | 0/1, bones 6/7: 6–10, clean kick | 11–13 mid 30-degree and 14–16 late zero-degree semi-spikes |

[Kirby neutral-air revision 2055946](https://www.ssbwiki.com/index.php?title=Kirby_(SSBM)/Neutral_aerial&oldid=2055946)
records the exact catalog windows and explains that the scripted 12% creation
is overwritten before an active game frame by an already-expired frame timer.
FightCore 210 instead lists a 12% frame-10 hit and starts 10% at frame 11.
That discrepancy is not repaired by shifting frames: annotations select only
the catalog's surviving 10% phase, consistent with the move-specific article.
No 12% hit, extra hitbox, or landing hit is synthesized. Independent engine
execution/creation-priority verification remains outside this label-only review.

[Ganondorf up-air revision 2035075](https://www.ssbwiki.com/index.php?title=Ganondorf_(SSBM)/Up_aerial&oldid=2035075)
and FightCore 216 independently match the clean/mid/late windows and both IDs.
The article explicitly calls the mid/late semi-spikes useful for reverse
edgeguards (the Tipman). `sweet` selects the named clean variant, not the best
edgeguard: the `sour` phases retain descriptive semi-spike labels and their
30/0-degree trajectories. Neither clean ID is discarded by damage ranking.

Zelda down-air revision 1393941 and Mewtwo down-air revision 1764236 confirm
the catalog's distinct zones but provide no named sweet/sour interpretation.
They remain unlabeled; numerical damage differences alone are insufficient.

## PK Thunder 2 and recovery-attack exclusions

Ness raw action 365, ID 0, bone 0 now labels the clean PK Thunder 2 body hit
at catalog frames 1–9 (25%, electric, angle 361) sweet, and the late body hit
at 10–36 (20%, electric, angle 361) sour. The
[Ness moveset revision 2062474](https://www.ssbwiki.com/index.php?title=Ness_(SSBM)&oldid=2062474#Moveset)
explicitly distinguishes these clean/late body hits. The catalog supplies the
exact phase windows; these are action-local frames, not time since starting the
steerable projectile. No projectile head/tail labels are implied. FightCore 243's
PK Thunder entries describe the 8% head and 1% tail with placeholder frame 0,
not the 25%/20% body collision, and cannot validate these body-hit windows.

Further recovery-attack review leaves these actions unlabeled:

- Link grounded Spin Attack (356): the catalog weakens IDs 0–2 at frame 14,
  FightCore 238 at frame 15, and
  [move revision 1930330](https://www.ssbwiki.com/index.php?title=Link_(SSBM)/Up_special&oldid=1930330)
  at frame 16. The move article also retains strong ID 3 throughout the late
  phase, matching the catalog's unbroken 8–41 phase, whereas FightCore omits it
  from the late row. Resolve the script timing independently before labeling;
  neither a blanket frame shift nor truncating ID 3 reconciles these accounts.
- Link aerial Spin Attack (357): five successive strikes with different linker
  and finisher properties, not one clean/late hit.
- Roy grounded/aerial Blazer (367/368): seven successive strikes, with separate
  blade/tip zones. Their spatial roles need per-strike adjudication; labeling
  only the higher-damage opener would conflate hit roles with sweetspots.
- Yoshi grounded Egg Roll actions 357/362: catalog base damage 4 does not
  represent the live speed-dependent 4–13% damage reported by the moveset.
  No static sweetspot is inferred from its runtime power range.

Regression controls require every listed excluded action to remain unlabeled.

## Peach float neutral and back air: eight additional signatures

The catalog independently contains neutral-air action 344 and back-air action
346, not merely the common 65/67 records. Each new label matches that alternate
action's own IDs, bones, combat signature and phase window:

| Raw action | Sweet phases | Sour phases |
| --- | --- | --- |
| 344 float neutral air | IDs 0/1/2, bones 100/74/4: 3–6, 14%, clean twirl | 7–23, 10%/10%/9%, late twirl |
| 346 float back air | ID 0, bone 4: 6–9, 14%, clean hip | 10–22, 10%, late hip |

The catalog-pinned doldecomp revision
[`d15c9cff` motion table](https://github.com/doldecomp/melee/blob/d15c9cffe939611627b3a7a77a446705d2998f5f/src/melee/ft/chara/ftPeach/ftPe_Init.c)
explicitly assigns 344/346 to `FloatAttackAirN`/`FloatAttackAirB`, with the same
common aerial submotions as neutral/back air. Its
[`ftPe_FloatAttack.c` callbacks](https://github.com/doldecomp/melee/blob/d15c9cffe939611627b3a7a77a446705d2998f5f/src/melee/ft/chara/ftPeach/ftPe_FloatAttack.c)
handle float continuation, movement and landing without replacing attack power.
The previously cited Peach clean/late move evidence therefore applies to these
independently matched records. Tests compare complete combat and geometry frames
between the common and float records, not just their maximum damage.

Float forward/up/down air (345/347/348) remain unlabeled, like their common
counterparts. This change does not infer sweetspots for equal-damage forward-air
zones, rank up-air zones by damage, or classify down-air multihit strikes as
decay phases. It does not change query aliases, float movement, landing lag,
or engine timing.

## Peach club and pan: seven additional signatures

| Raw action | Sweet zone at frames 15–18 | Sour zones at frames 15–18 |
| --- | --- | --- |
| 349 golf club | ID 3, bone 109, 17%, club tip | IDs 0/1, bone 109, 13%, shaft; ID 2, bone 86, 13%, inner hit |
| 350 frying pan | ID 0, bone 109, 17%, pan head | ID 1, bone 109, 15%, handle; ID 2, bone 86, 15%, inner hit |

[Peach moveset revision 2062455](https://www.ssbwiki.com/index.php?title=Peach_(SSBM)&oldid=2062455#Moveset)
explicitly names the club tip and pan head sweetspots. The
[forward-smash table revision 2012125](https://www.ssbwiki.com/index.php?title=Peach_(SSBM)/Forward_smash&oldid=2012125)
independently records their IDs, bones, weapon-local offsets and 15–18 timing.
FightCore 240 agrees with the catalog's per-weapon damage and angles but has
placeholder frame 0, so it is not used to establish timing. The pinned
`ftPe_Init.c` motion table linked above assigns 349/350/351 separately to club,
pan and racket submotions. No selected weapon or charge level is inferred.

Racket action 351 remains unlabeled. Its three zones all deal 12%, with ID 0
having higher base knockback than IDs 1/2; that difference alone does not
establish a named sweetspot. Club/pan inner hits retain their distinct Sakurai
angles instead of inheriting the weapon head's 45/80-degree trajectory.

Bowser forward-tilt revision 1434005 and forward-air revision 1643623 were also
checked. They confirm three spatial damage zones but do not adjudicate a named
sweet/sour selection. Those attacks remain unlabeled rather than treating the
largest damage value as sufficient evidence.

## Double-Edge Dance audit: no additional labels

All 18 Roy side-special actions (349–366) were reviewed without adding labels.
The [move table revision 2056103](https://www.ssbwiki.com/index.php?title=Roy_(SSBM)/Side_special&oldid=2056103)
records individual engine IDs and distinguishes successive down-branch hits
from the third-up branch's clean/late phases. Its timing agrees with catalog
action 349 at 6–8 but is one frame later for the subsequent listed branches
(for example, third-up clean 13–14 versus catalog 12–13). FightCore 223 has
placeholder frame 0 for these branches and cannot adjudicate that conflict.
No blanket offset is applied, and labels are deferred pending a script-timing
audit rather than making an unqualified exact-window claim.

There is also a substantive ground/air distinction: grounded third-up action
352 has clean ID 0/1/2 angles 280 and ID 3 angle 270, whereas aerial action
361 has clean angle 60 on every ID. Both have late angle 60. The catalog-pinned
[`ftFe_Init.c` motion table](https://github.com/doldecomp/melee/blob/d15c9cffe939611627b3a7a77a446705d2998f5f/src/melee/ft/chara/ftEmblem/ftFe_Init.c)
assigns these to distinct `SpecialS3Hi` and `SpecialAirS3Hi` submotions.
[Double-Edge Dance revision 2019055](https://www.ssbwiki.com/index.php?title=Double-Edge_Dance&oldid=2019055)
describes the Melee third-up meteor and its sourspot but does not establish
equivalent aerial behavior. Grounded meteor labels must not be copied into the
aerial branch merely because the damage values match.

Tests preserve both branches' different angles and the separate strike windows
of third-down and fourth-down, and require the current 18-action query to remain
unlabeled. No claim is made that those branches have no sweetspots; their exact
timing and per-strike spatial roles remain unresolved.

## Pikachu up-air semi-spike: six additional signatures

Pikachu action 68 selects the middle tail semi-spike, not the earliest phase
or a maximum-damage zone. Both IDs 0/1 (bones 47/50) retain 4% throughout:

| Frames | Angle | Selection |
| --- | --- | --- |
| 3–4 | 80 | sour, early tail launcher |
| 5–6 | 0 | sweet, mid tail semi-spike |
| 7–8 | 130 | sour, late tail launcher |

[Move revision 809680](https://www.ssbwiki.com/index.php?title=Pikachu_(SSBM)/Up_aerial&oldid=809680)
explicitly identifies the middle hit's edgeguard semi-spike and independently
records each ID, bone and timing window. FightCore 237 agrees with all three
angles and windows. `sweet` selects this specific edgeguard variant; the two
launching phases remain useful for juggling and are not universally inferior.
Equal damage is deliberately not used to merge or rank the phases.

Pichu action 68 independently has three 4% windows at 4–5, 6–7 and 8–9, but
every ID in every window uses angle 80. FightCore 221 agrees. No Pikachu
semi-spike label is copied onto the clone's different signatures.

Mewtwo up-air revision 1392909 and DK down-smash revision 1389252 also confirm
their numerical tail/limb zones without identifying a named sweet/sour variant.
That move-table-only review left both unlabeled. Mewtwo remains unresolved;
the additional named DK character evidence below supersedes its exclusion.

## Rechecked multihit exclusion and partner limits

[Roy neutral-air revision 1388991](https://www.ssbwiki.com/index.php?title=Roy_(SSBM)/Neutral_aerial&oldid=1388991)
independently agrees with the catalog's first strike at 7–8 and second strike
at 17–20. All four opener IDs deal 4%; the second strike has 8% inner zones
and a 6% outer zone. The second strike is not a late decay phase of the first.
Neither the stronger finisher nor its damage gradient alone establishes a named
sweetspot. Preserve the opener's distinct 100/90-degree angles and the finisher's
361 angles; keep this action unlabeled pending spatial-role adjudication.

[Ice Climbers forward-air revision 1392757](https://www.ssbwiki.com/index.php?title=Ice_Climbers_(SSBM)/Forward_aerial&oldid=1392757)
agrees with the 19–22 window, IDs 0/1/2, bones 15/15/11 and 11%/10%/9% base
damage. The static catalog independently records identical Popo/Nana signatures:
ID 0 angle 270 and IDs 1/2 angle 70. This shared script evidence does not resolve
leader/partner runtime adjustments or demonstrate which overlapping zone wins.
The earlier blanket forward-air exclusion is superseded only for the two exact
ID-0 signatures adjudicated below. Roy remains unlabeled; the four nonmeteor
IC signatures remain unlabeled. Static values are not replaced with inferred
live angles or partner-scaled damage.

## Warlock Punch shoulder: six additional signatures

Ground action 347 and aerial action 348 each select ID 2, bone 66, at 70–72:
the close shoulder sweetspot deals 34%. ID 1 on bone 66 deals 32% at the middle
offset; ID 0 on bone 69 deals 30% at the far end. Those two zones are sour.
Every zone retains angle 361, darkness element 13 and knockback growth 100.
Ground base knockback is 30; aerial base knockback is 40. Equal damage and
windows across the two actions do not erase that ground/air distinction.

[Sweet-spot revision 2059342](https://www.ssbwiki.com/index.php?title=Sweet_spot_(hitbox)&oldid=2059342)
explicitly identifies Warlock Punch's Melee shoulder sweetspot, including its
Home-Run Contest use. The
[move table revision 2059008](https://www.ssbwiki.com/index.php?title=Ganondorf_(SSBM)/Neutral_special&oldid=2059008)
records each ID, bone, offset, ground/air knockback and the 70–72 window.
[FightCore 216](https://data.fightcore.gg/characters/216/ganondorf) independently
agrees with the grounded damage, timing, angle, element and knockback values;
it does not establish the aerial base-knockback difference. The catalog-pinned
[`ftGn_Init.c` motion table](https://github.com/doldecomp/melee/blob/d15c9cffe939611627b3a7a77a446705d2998f5f/src/melee/ft/chara/ftGanon/ftGn_Init.c)
assigns 347/348 to distinct neutral-special ground/air submotions. Labels match
both catalog records independently; no charge, reverse-punch or later-game
variant is imported into Melee. Overlap priority and live connectivity remain
outside this static selection.

## Koopa Klaw: unresolved close/far roles

[Koopa Klaw revision 2054640](https://www.ssbwiki.com/index.php?title=Koopa_Klaw&oldid=2054640)
distinguishes the close command grab from the farther slash, bite and throws.
It describes a swipe at 17–18 followed by a grab, whereas the
[move table revision 2056108](https://www.ssbwiki.com/index.php?title=Bowser_(SSBM)/Side_special&oldid=2056108)
lists hitboxes and grabboxes together at 16–18. The catalog's ground/air swipe
actions 347/353 contain IDs 0/1 at 8%, angle 0, and IDs 2/3 at 12%/10%, angle
80, all at 16–18. These numerical records do not prove capture sequencing,
collision priority or which close/far role is preferable. Neither source names
a sweet/sour selection. Keep both actions unlabeled and preserve their exact
signatures; do not select ID 2 merely because it deals the most damage, or
advertise the 8% records as proof of an ordinary damaging grab connection.

## Falcon up air and Ganondorf forward tilt: 13 additional signatures

| Character / raw action | Sweet phases | Sour phases |
| --- | --- | --- |
| Falcon / 68 up air | IDs 0/1, bones 7/8: 6–10, 13%/12%, angle 361, clean kick | Same IDs/bones: 11–13, 12%/10%, angle 30, mid semi-spike |
| Ganondorf / 51 forward tilt up | ID 0, bone 13: 9–11, 14%, foot | IDs 1/2, bones 12/4: 13%/12%, leg/body |
| Ganondorf / 53 forward tilt level | ID 0, bone 13: 9–11, 13%, foot | IDs 1/2, bones 12/4: 12%/11%, leg/body |
| Ganondorf / 55 forward tilt down | ID 0, bone 13: 9–11, 12%, foot | IDs 1/2, bones 12/4: 11%/10%, leg/body |

[Falcon up-air revision 2034965](https://www.ssbwiki.com/index.php?title=Captain_Falcon_(SSBM)/Up_aerial&oldid=2034965)
records both IDs, bones and clean/mid windows. It explicitly describes the
semi-spike's gimping use and explains that the scripted late hit is deleted on
its creation frame, so no 14–16 phase survives. [FightCore 227](https://data.fightcore.gg/characters/227/captainfalcon)
independently agrees with the two surviving windows and their combat values.
Select both clean zones, including the 12% zone; do not rank equal 12% clean/mid
damage as equivalent. The mid semi-spike remains useful, not universally worse.
No absent late hit or Ganondorf zero-degree phase is copied into Falcon's data.
This agreement does not independently certify engine execution order.

[Ganondorf forward-tilt revision 2063293](https://www.ssbwiki.com/index.php?title=Ganondorf_(SSBM)/Forward_tilt&oldid=2063293)
explicitly names the foot sweetspot and records IDs, bones, offsets and the 9–11
window for all angles. [FightCore 216](https://data.fightcore.gg/characters/216/ganondorf)
independently agrees with up, level and down damage, timing and combat values.
Each catalog action is matched separately, preserving its own geometry and
damage; all three zones retain angle 361, base knockback 20 and growth 100.
The article's intermediate-angle tables do not justify synthesizing unavailable
catalog actions 52/54, and Falcon's different forward-tilt zones are not inferred
from these Ganondorf labels. Collision priority remains unverified.

## DK smash zones: eight additional signatures

| Raw action | Sweet phases | Sour phases |
| --- | --- | --- |
| 60 forward smash, 22–23 | ID 1, bone 0, 21%, arms | IDs 0/2/3, bone 0, 20%/19%/18%, hands/upper body/lower body |
| 64 down smash, 10–13 | IDs 0/1, bones 52/30, 16%, angle 115, hands | IDs 2/3, bones 51/29, 14%, angle 98, arms |

[DK character revision 2062459](https://www.ssbwiki.com/index.php?title=Donkey_Kong_(SSBM)&oldid=2062459)
explicitly identifies forward smash's arm sweetspot and down smash's hand
sweetspots in its changes-from-Smash-64 section, and maps their damage and
anatomical roles in the moveset. This is additional named evidence beyond the
down-smash numerical table previously reviewed; it supersedes that action's
unlabeled exclusion rather than inferring a sweetspot from maximum damage.

[Forward-smash revision 1930258](https://www.ssbwiki.com/index.php?title=Donkey_Kong_(SSBM)/Forward_smash&oldid=1930258)
also names the elbow sweetspot and records each root-relative offset, ID and
22–23 window. ID 0's hands and ID 1's arms retain base knockback 22/growth 94,
while IDs 2/3 retain base 18/growth 100. All four remain at angle 361. Bone 0
is the shared root, not a reason to collapse the four spatial zones or rename
the bone itself to an arm.

[Down-smash revision 1389252](https://www.ssbwiki.com/index.php?title=Donkey_Kong_(SSBM)/Down_smash&oldid=1389252)
independently records IDs, bones, offsets and 10–13 timing. Both hand zones are
selected; the two arm zones retain their different launch angle. [FightCore 242](https://data.fightcore.gg/characters/242/donkeykong)
agrees with both moves' per-ID damage, angles, knockback and windows. Labels
describe uncharged base signatures, not charge scaling or overlap priority.
## Unresolved trajectory, landing and combo roles

[DK forward-air revision 2030297](https://www.ssbwiki.com/index.php?title=Donkey_Kong_(SSBM)/Forward_aerial&oldid=2030297)
distinguishes the early launcher from the late meteor and prefers the early
hit for particular kill confirms, not every situation. All four catalog IDs
retain 16% in both windows: 25–26 uses angle 361, base knockback 20/growth 100;
27–29 uses angle 270, base 50/growth 80. IDs 2/3 also retain one extra shield
damage. Equal damage does not erase the trajectory change, and higher base
knockback alone does not make the meteor a sweetspot. No sweet/sour selection
is adjudicated here.

[Bowser up-smash revision 1666358](https://www.ssbwiki.com/index.php?title=Bowser_(SSBM)/Up_smash&oldid=1666358)
describes an overlapping 20% shell zone and a rarely connecting 17% inner zone
at 16–21, followed by a separate 12% landing hit at frame 30. The catalog keeps
both IDs on bone 1, shell angle 90/base 40/growth 86/slash element 3, and landing
angle 74/base 60/growth 100/normal element 0. Landing hits grounded targets only;
shell hits also target aerial opponents. A static overlap description does not
certify collision priority. Do not flatten the landing hit into ordinary damage
decay or label the largest shell zone solely from damage.

[Peach up-air revision 2060846](https://www.ssbwiki.com/index.php?title=Peach_(SSBM)/Up_aerial&oldid=2060846)
identifies different combo roles for heel and middle zones at different target
percents. IDs 0/1/2, bones 9/7/4, retain 14%/12%/11% at 7–11. Heel and middle
launch at 80; the inner zone uses 361. All retain base knockback zero/growth 120.
The source establishes spatial roles but not an adjudicated sweet/sour choice;
keep every zone unlabeled rather than promote maximum damage to a universal
selection. These three exclusions have exact-value and create/evolve tool
regressions. They add no labels and do not establish live connectivity.

## Mewtwo tail gradients and up-tilt timing: unresolved selections

The [character moveset revision 2062473](https://www.ssbwiki.com/index.php?title=Mewtwo_(SSBM)&oldid=2062473#Moveset)
describes near/middle/far damage for tilts and aerials, but names a sweetspot
only for forward smash's shadow blast. That existing forward-smash label does
not establish a general Mewtwo tail rule. Up air's highest-damage zone is far
on bone 25, while back air's is near on bone 21; their raw hitbox ID 2 therefore
does not identify the same anatomy. Neither gradient alone establishes labels.

| Actions | Catalog signatures (ID order) | Move evidence |
| --- | --- | --- |
| 51/53/55 forward tilt | 6–8, bones 21/23/25, 10%/8%/5%, angle 361, base 20/10/0, growth 100 | [2029922](https://www.ssbwiki.com/index.php?title=Mewtwo_(SSBM)/Forward_tilt&oldid=2029922), all three angles |
| 57 down tilt | 5–7, bones 21/23/25, 9%/8%/5%, angle 80, base 40, growth 80 | [1668339](https://www.ssbwiki.com/index.php?title=Mewtwo_(SSBM)/Down_tilt&oldid=1668339) |
| 67 back air | 12–15, bones 25/23/21, 9%/11%/13%, angle 361, base 0, growth 100 | [1392902](https://www.ssbwiki.com/index.php?title=Mewtwo_(SSBM)/Back_aerial&oldid=1392902) |
| 68 up air | 9–11, bones 21/23/25, 10%/12%/14%, angle 55, base 0, growth 100 | [1392909](https://www.ssbwiki.com/index.php?title=Mewtwo_(SSBM)/Up_aerial&oldid=1392909) |
| 69 down air | 18–21, bones 5/14/18, 14%/15%/16%, angle 270 throughout, base 10, growth 100 | [1764236](https://www.ssbwiki.com/index.php?title=Mewtwo_(SSBM)/Down_aerial&oldid=1764236) |

[Up-tilt revision 1394885](https://www.ssbwiki.com/index.php?title=Mewtwo_(SSBM)/Up_tilt&oldid=1394885)
distinguishes frame 6 from 7–11. Action 56 retains bones 5/21/23/25 and damage
10%/8%/6%/5% in both phases. Frame 6 angles are 110/110/110/361, base knockback
0/70/70/0 and growth 115/114/114/80. At 7–11 every angle is 78, bases are
60/60/50/40 and growth is 114 throughout. These are not simple damage-decay
phases: the tip's late knockback increases while other zones change differently.

[FightCore 217](https://data.fightcore.gg/characters/217/mewtwo) independently
matches these windows, per-ID damage, angles and knockback for the level tilt,
up/down tilts and three aerials. The move tables supply the bones and angled
tilt correspondence. Exact-value regressions cover all eight catalog actions;
create/evolve tools reject guessed selections through both structured APIs.
No labels, numerical values or frames change. These exclusions do not prove
that the moves lack sweetspots or certify collision priority in live play.

## Falcon angled tilts, Bowser claw and Yoshi regional control

[Falcon forward-tilt revision 1537370](https://www.ssbwiki.com/index.php?title=Captain_Falcon_(SSBM)/Forward_tilt&oldid=1537370)
records 9–11 for all three available angles (51/53/55), with IDs 0/1/2 on
bones 14/13/4. Up uses 12%/12%/11%, level uses 11% throughout, and down uses
10%/10%/11%. Base knockback is 10 except the down angle's IDs 0/1, which use
zero; angle 361 and growth 100 remain shared. The downward body zone is not
weaker than the foot, unlike Ganondorf's labeled foot selections. No Falcon
label is inferred from the related fighter or from each angle's maximum damage.

[Bowser forward-air revision 1643623](https://www.ssbwiki.com/index.php?title=Bowser_(SSBM)/Forward_aerial&oldid=1643623)
describes a claw swipe and several spacing/combo roles, but does not establish
a sweet/sour selection among its three zones. Action 66 retains 8–11, IDs
0/1/2 on bones 38/34/60, 14%/12%/11%, angle 361, base 50 and growth 80.
The largest damage zone is not automatically a reviewed sweetspot.

[Yoshi up-smash revision 2016021](https://www.ssbwiki.com/index.php?title=Yoshi_(SSBM)/Up_smash&oldid=2016021)
explicitly separates NTSC 14%/base 26 from PAL 15%/base 30. The NTSC-U 1.02
catalog's action 63 retains 14%/26 for both IDs, bones 38/37, at 11–15, angle
75 and growth 108. Different sphere geometry is not itself a sweetspot; do not
import the PAL buff or infer an intangibility window from numerical hitboxes.

Exact-value and both-mode authoring regressions cover these five actions.
All remain unlabeled; no numerical catalog, frame or existing label changes.

## Target filters, trapping pulses and two-sided strikes

These five actions remain unlabeled. Their differing damage, knockback or
timing does not alone establish sweet/sour variants. Exact-value regressions
and create/evolve tool checks retain the distinctions below, reject guessed
sweet and sour selections, and preserve the numerical resource unchanged.

- [Zelda down tilt, revision 1392811](https://www.ssbwiki.com/index.php?title=Zelda_(SSBM)/Down_tilt&oldid=1392811):
  action 57, frames 5–7. IDs 0/1 share bone 16 and 7% damage, but ID 0 hits
  grounded targets at 270 degrees and ID 1 hits aerial targets at 80 degrees.
  IDs 2/3 (bones 13/4) hit both target types at 270 degrees for 8%. All use
  base 20/growth 80. Do not describe both outer zones as meteor hits or use
  their identical geometry to merge target-specific launch behavior.
- [Zelda down air, revision 1393941](https://www.ssbwiki.com/index.php?title=Zelda_(SSBM)/Down_aerial&oldid=1393941):
  action 69, frames 14–17. IDs 0/1 on bones 7/10 deal 8%/7%, with base
  5/0 and growth 100/80; both hit grounded and aerial targets at 275 degrees.
  The empty move overview supplies no named sweet/sour adjudication; the
  largest damage or knockback is not sufficient evidence to invent one.
- [Zelda neutral air, revision 2061136](https://www.ssbwiki.com/index.php?title=Zelda_(SSBM)/Neutral_aerial&oldid=2061136):
  action 65 has five separate trapping pulses at 6–7, 10–11, 14–15, 18–19
  and 22–23, followed by a 26–27 finisher. IDs 0/1 use 2%, angle 130,
  weight-set knockback 70; IDs 2/3 use 3%, angle 90, weight-set 120/50.
  All four finishers use 5%, angle 361 and base 40, but growth remains
  130 for IDs 0/1 and 120 for IDs 2/3. Neither the finisher nor the 3%
  trapping zones become sweetspots merely because they deal more damage.
- [Samus down smash, revision 2040584](https://www.ssbwiki.com/index.php?title=Samus_(SSBM)/Down_smash&oldid=2040584):
  action 64 uses two strikes, not clean/late power decay. Both bone-14 zones
  deal 16% at 6–8 (base 110/growth 50), then 15% at 14–16 (base 90/growth
  40); angle 120 remains shared. These are uncharged script values.
- [Yoshi down smash, revision 1392005](https://www.ssbwiki.com/index.php?title=Yoshi_(SSBM)/Down_smash&oldid=1392005):
  action 64 uses 14% at 6–8 and 12% at 21–22, angle 30/base 50 throughout.
  IDs 0/1 retain growth 75; ID 2 changes from 60 to 80. Calling every
  second-strike zone weaker would lose that independent knockback distinction.
  The numerical table does not establish a named tail-tip sweetspot.

These checks do not prove absence of useful spacing, true combos, or live
collision priority. Article/projectile, partner and runtime modifications
remain separate research boundaries; no labels or timing corrections follow
from these exclusions.

## Independently adjudicated DK/IC variants: eight additional signatures

The [independent candidate review](sweetspot-roster-audit/candidate-review.md)
accepts six DK sour-only and two IC sweet-only signatures. This adds four
character/action pairs without inferring complementary labels. Earlier
full-roster audit reports describe the historical 569-label snapshot; their
prior-label counts and findings are not rewritten as current annotation counts.

| Character:action | IDs / bones | Frames | Base signature | Annotation |
| --- | --- | --- | --- | --- |
| DK 3:373, full-charge ground punch | 0/1/2, bones 30/31/4 | 17 | 18%, angle 80, base 40/growth 90 | sour: full-charge rear vertical sourspot |
| DK 3:378, full-charge air punch | 0/1/2, bones 30/31/4 | 17 | 16%, angle 80, base 40/growth 90 | sour: full-charge rear vertical sourspot |
| Popo 10:66, forward air | 0, bone 15 | 19–22 | 11%, angle 270, base 40/growth 100, aerial targets only | sweet: aerial-target meteor variant |
| Nana 11:66, forward air | 0, bone 15 | 19–22 | 11%, angle 270, base 40/growth 100, aerial targets only | sweet: aerial-target meteor variant |

All eight use normal element, zero set knockback and zero shield damage. DK's
six signatures hit grounded and aerial targets. The explicitly named Melee
rear vertical sourspot is established by
[DK revision 2062459](https://www.ssbwiki.com/index.php?title=Donkey_Kong_(SSBM)&oldid=2062459),
with IDs, bones, damage, knockback and timing independently supplied by
[neutral-special revision 2058001](https://www.ssbwiki.com/index.php?title=Donkey_Kong_(SSBM)/Neutral_special&oldid=2058001).
The existing action-state table independently identifies 373/378 as full-charge
punches. Their later 18–21 phases remain unlabeled at 30% ground/27% air,
angle 361 and base 10/growth 90. No front sweetspot or partial-charge 372/377
label follows. The elbow-sweetspot sentence in general Giant Punch revision
2064114 accompanies Brawl material, not Melee evidence.

[IC revision 2062476](https://www.ssbwiki.com/index.php?title=Ice_Climbers_(SSBM)&oldid=2062476)
explicitly names the forward-air meteor sweetspot;
[forward-air revision 1392757](https://www.ssbwiki.com/index.php?title=Ice_Climbers_(SSBM)/Forward_aerial&oldid=1392757)
uniquely maps its 270-degree aerial-only variant to ID 0/bone 15. Each context's
own catalog record matches independently. The label describes trajectory, not
hammer anatomy or current leader/follower role. IDs 1/2, bones 15/11, remain
unlabeled at 10%/9%, angle 70, both target types, base 40/growth 100. Neither
11% effective partner damage nor a grounded meteor is inferred.

The candidate review's complete-byte raw retrieval SHA-256 receipts are:

| Source revision | Raw SHA-256 |
| --- | --- |
| DK 2062459 | `057e70ea1a92335daf43c8743b2fc33bdd5dc3a9ae4777f1164b3e4f31abb3fe` |
| DK neutral special 2058001 | `13c4fa0c2871675b8803bf89db49d6ba7b4b0006f02c7c1a04d7ace27e6a6236` |
| IC 2062476 | `a3cd01b9027de5921bec60dccef8437360c304d06ef7a1505a2080d37d657dfb` |
| IC forward air 1392757 | `e5fbc3a6c9274ec78713ff52a159eb5e7a93e4187bc7094ca123d4626b97d8d0` |

The review also records separate canonical HTML hashes and the Brawl exclusion
witness. These are static annotations, not ISO re-extraction, charge/callback
proof, runtime partner transformation, live collision/priority certification or
full-roster signoff. Numerical resources, frame indexing and original labels
are unchanged. Explicit DK sweet and IC sour selectors fail instead of guessing.

## B/C/E/F adjudication: 40 additional signatures across 11 actions

The [independent B/C/E/F review](sweetspot-roster-audit/candidate-review-bcef.md)
accepts exactly 40 of 49 proposals at its 617-label checkpoint. Its S1–S15 source table pins each revision
and complete raw-byte SHA-256; the source references below use those receipts.
Nine proposed complements were then left unlabeled; three signatures receive
new source-backed roles in the follow-up below, including one reversed proposal.
The historical group reports retain their original 569-label snapshot. The
preceding DK/IC integration had 577 labels; neither snapshot is current coverage.

| Character:action | Accepted sweet phases | Accepted sour phases | Source receipts |
| --- | --- | --- | --- |
| Fox 1:56 up tilt | ID 0/bone 15, 5–11: 12%, 110, ground-only | None | S1, up tilt 1655106 |
| Falco 22:68 up air | None | ID 2/bone 4, 11–14: 10%, 90, slash, second-hit body | S2, up air 2031216 |
| Falcon 2:46 Gentleman | IDs 0/1, bones 13/4, 5–8: 8%, 361 | Same IDs/bones, 9–11: 6%, 361 | S3, Hit 3 1915179 |
| Falcon 2:347 ground Punch | ID 0/bone 45, 52–56: 27%, 361, fire | None | S4, neutral special 1930502; S5, Falcon Punch 2067832 |
| Falcon 2:348 air Punch | ID 0/bone 45, 52–56: 27%, 361, fire | None | S4/S5, independently matched air action |
| Falcon 2:357 ground Kick | IDs 0/1, bones 14/13, 14–16: 15%, 361 | Same IDs/bones, 17–24: 12%, 80; 25–32: 9%, 90 | S6, down special 2056712; S7, Falcon Kick 2012692 |
| Falcon 2:359 air Kick | IDs 1/2, bones 14/13, 15–17: 15%, 361 | Same IDs/bones, 18–25: 13%; 26–29: 11%, both 361 | S6/S7, independently matched air action |
| Link 6:69 down air | IDs 0/1/2, bone 0, 13–15: 22%/20%/20%, 65 | Same IDs/bone, 16–64: 19%, 65 | S8, Link 2062902; S9, down air 2002902 |
| Young Link 20:66 forward air | IDs 0/1/2/3, bones 28/25/19/28, 14–16: 12%/11%/9%/9%, 361 | Same IDs/bones, 17–33: 8%/7%/7%/5%, 76 | S10, Young Link 2062463; S11, forward air 1389928 |
| Game & Watch 24:69 down air | ID 0/bone 0, frame 12: 14%, 270 | ID 0, 13–38 and ID 1, 12–38, bone 0: 13%, 60 | S12, character 2062479; S13, down air 1938699 |
| Peach 9:57 down tilt | IDs 2/3, bones 72/97, 12–13: 12%, 270, both target types | ID 1/bone 74, 12–13: 12%, 80, aerial-only | S14, Peach 2062455; S15, down tilt 1939197 |

All windows are inclusive, action-local catalog frames. `361` is the Sakurai
angle sentinel. Gentleman, Fox and Peach use normal element; Kick/Punch use
fire; Link/Young Link use slash; the key uses normal. Every listed phase keeps
zero set knockback, shield damage and hit group. Except the explicit target
masks, grounded and aerial targets are both enabled.

### Partial selections and unresolved complements

- Fox's explicitly named ground-only sweetspot retains base 18/growth 140.
  ID 1 on the same bone is aerial-only, 9%/84; the separately reviewed character
  evidence below now labels it sweet too. IDs 2/3, bones 13/12, are both-target
  9%/80 and remain unresolved, not automatically sour. An explicit sour selector
  fails. Sweet selection retains both foot phases with their disjoint target masks.
- Falco's named second-hit sourspot retains base 30/growth 20 and slash element.
  The two normal-element second-hit kicks retain 10%/70, base 22/growth 120,
  unlabeled. All three 8–9 opener phases remain a separate unlabeled strike.
  No sweet selection is inferred from equal damage or reverse-complement logic.
- Punch selects the close zone in each action independently, based on S5's
  Melee Kirby comparison, not maximum damage. Middle 25% remains unlabeled;
  the newly reviewed character evidence below identifies only far 23% as sour.
  Ground base 30 and air base 40,
  growth 102 and differing ground/air geometry remain intact. S4's tables say
  Normal while its prose describes flames and the catalog retains fire element 1;
  this source conflict is disclosed, not repaired. No Kirby copy, reverse-punch
  or other-game charge behavior follows.
- Peach's equal-damage target variants are not ranked numerically. The named
  forearm/inner meteor zones retain base 60/growth 100; the aerial launcher
  retains base 15/growth 100. Ground-only meteor ID 0/bone 74 stays unlabeled,
  despite sharing the launcher's bone/geometry. Bone 97 is called `inner meteor`,
  not assigned unproven anatomy. Not every grounded meteor is a selected sweetspot.

### Temporal roles and runtime limits

- Gentleman clean/late is decay within Hit 3, not a ranking against jabs 1/2.
  Base knockback changes 20→0 with growth 100 throughout.
- Ground Kick retains base 50 and growth 70→60→50; air Kick retains base 40
  and growth 70→65→60. S6's ground mid 12% conflicts with the character summary's
  13%; the move table and catalog agree. S6 explains air activity ending at 29
  despite the script's 26–33 interval; preserve 29 without claiming independent
  engine-execution or animation-length proof. Noninteractive ground ID 2 and
  separate landing hits are not added. Travel, walls and jump refresh remain runtime concerns.
- Link's named clean/late phases include the two 20% clean zones, not just 22%.
  ID 0 retains base 50, IDs 1/2 base 40, growth 80 throughout. Bone 0 is a shared
  root, not anatomy. These are pre-bounce values, not the documented 6%/8% bounce
  behavior or a guarantee of a 64-frame live hit; landing/re-hit remain unmodeled.
- Young Link's S10 explicitly describes one continuous hit despite two visual
  slashes; S11 names clean/late. Clean base 5/growth 100 becomes late base 0/growth
  90. The useful late upward trajectory remains, without importing Link's two-hit
  forward-air semantics or ranking spatial zones by their damage.
- The key's named early meteor and later launcher retain base 20/growth 100.
  ID 1 already launches at frame 12 and keeps one unbroken 12–38 phase; do not
  split it to imitate source headings. The separate 6% landing hit is not added.

These exact static annotations do not certify runtime callbacks, partner/copy
transformations, extraction completeness, collision priority, vulnerability,
contact, or live-emulator behavior. No numerical resource or frame convention
changes, and no full-roster completion claim follows from this bounded batch.

## Complement follow-up: three additional signatures, no new actions

The latest independent receipt in the consumer workspace's
`.test-tmp/roster-annotations-review.md` ("Three exact annotation decisions")
accepts these three new roles after checking the
[complement follow-up](sweetspot-roster-audit/complement-followup.md):

| Character:action | Exact phase | Frames / damage / angle / element | Annotation | Targets / BKB / KBG |
| --- | --- | --- | --- | --- |
| Fox 1:56 | ID 1, bone 15, `1:15:1` | 5–11 / 9 / 84 / 0 | sweet: aerial-target foot | aerial-only / 18 / 140 |
| Falcon 2:347 | ID 2, bone 47, `2:47:1` | 52–56 / 23 / 361 / 1 | sour: far punch | ground and air / 30 / 102 |
| Falcon 2:348 | ID 2, bone 47, `2:47:1` | 52–56 / 23 / 361 / 1 | sour: far punch | ground and air / 40 / 102 |

All retain zero set knockback, shield damage and hit group. Existing 617 CSV
rows are unchanged; only these three signatures are appended. Original group
reports and candidate-review dispositions remain historical snapshots, not
rewritten evidence or current annotation totals.

[Fox character revision 2067316](https://www.ssbwiki.com/index.php?title=Fox_(SSBM)&action=raw&oldid=2067316)
explicitly says the aerial sweetspot retains its damage but changes from 80 to
84 degrees. The sole 84-degree phase independently matches ID 1/bone 15,
grounded=false/aerial=true. Its label is **sweet**, contradicting the earlier
proposed sour role; this is not an acceptance of that old proposal. The existing
12%/110 ground-only sweet ID 0 remains unchanged. IDs 2/3 remain unlabeled.

[Falcon character revision 2064399](https://www.ssbwiki.com/index.php?title=Captain_Falcon_(SSBM)&action=raw&oldid=2064399)
explicitly names the 23% sourspot, independently of its stronger close zone.
[Neutral-special revision 1930502](https://www.ssbwiki.com/index.php?title=Captain_Falcon_(SSBM)/Neutral_special&action=raw&oldid=1930502)
maps each ground/air 23% row to ID 2/bone 47 at 52–56. Both actions retain
growth 102, their different base knockback and their own geometry. The 25%
middle ID 1 remains unlabeled; plural sourspot wording does not establish its
role. The known Normal-table/fire-prose discrepancy remains disclosed and
catalog element 1 is preserved. Source priority wording is not certified here.

Complete raw-source SHA-256 receipts, independently matched by the review:

| Revision | SHA-256 |
| --- | --- |
| Fox 2067316 | `097773694ef943bdb99cf53420d39a7dc595b8cfb194d2a3e21ab970669ad784` |
| Falcon 2064399 | `a703faf75c286d8e7b046a41f0548ce5e2871b4e0555db88aba2ef53d44766d2` |
| Falcon neutral special 1930502 | `2764230fac590075b2069b4dad76846350e10d7a12e40c87cdb455fc1d46d7ed` |

Of the original nine proposals, two Falcon far sour roles are resolved; Fox's
aerial sour proposal is contradicted and replaced by a separately accepted sweet
role. Six original roles remain unresolved and unlabeled: two Fox inner-leg sour,
two Falco second-hit kick sweet, and two Falcon middle-punch sour proposals.
Falco's opener and Peach's unreviewed ground-only meteor also remain unlabeled.
No numerical, frame-indexing, Marth/Yoshi timing, runtime or collision-priority
change follows; no complete-roster or live-connectivity claim is made.
