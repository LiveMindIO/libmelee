# Additional reviewed sweetspot labels

These annotations extend the original 19 signatures by 523, for 542 labeled
phases across 121 character/action pairs. Successive batches cover eight, 34,
31, six, 16, 13, two, one, two, two and one character/action pairs, listed below.
They do not modify the NTSC-U 1.02 numerical catalog, geometry or frame indexing.

## Evidence

Each row below was checked against `melee/hitbox_catalog.json` and the listed
public sources. IDs are engine hitbox IDs, not historical CSV geometry slots.
Frame intervals are inclusive. Damage is uncharged, before gameplay modifiers.

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

Forward air remains unlabeled for both characters. The static catalog's ID 0
reports angle 270, while leader/partner rules affect its actual meteor behavior.
A shared character article and equal script records do not prove equal runtime
behavior. Partner damage scaling and forward-air angle adjustment require a
separate runtime audit; no catalog values are rewritten to simulate them here.

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
Both remain unlabeled; their damage gradients alone do not resolve that question.
