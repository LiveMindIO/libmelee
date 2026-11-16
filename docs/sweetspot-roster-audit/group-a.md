# Group A: Mario, Dr. Mario, Luigi, Donkey Kong

Report-only audit at libmelee `6aa09c70cd97e1665d3870fa53927fbfbd05f638`.
Every assigned numerical-catalog action is recorded once in `group-a.json`.
No runtime, numerical catalog, frame, label, test, or other report file changed.
Six sour-only label signatures proposed for two full-charge Giant Punch actions;
none applied. Existing 569 signatures/129 actions remain intact.

| Character | Actions | Existing reviewed | Excluded candidate | Unresolved | Runtime limited |
| --- | ---: | ---: | ---: | ---: | ---: |
| Mario0 |30|5|20|5|0|
| Dr. Mario21 |26|6|16|4|0|
| Luigi17 |33|4|23|2|4|
| Donkey Kong3 |30|5|17|4|4|
| Total |119|20|76|15|8|

No assigned `catalog.unavailable` entries. Sixteen separately recorded gaps.

## Scope and status semantics

- `existing_labels_reviewed`: exact existing physical signatures and cited
  interpretation rechecked; qualifications remain in individual rows.
- `excluded_with_evidence`: the specific numerical candidate is explained by
  uniform coverage, successive strikes, capture geometry, or separate actions.
  This does **not** prove the move lacks every useful spacing or runtime variant.
- `unresolved_source`: useful differentiation exists, but named semantics,
  independent timing, target identity, or source adjudication remains incomplete.
- `runtime_or_article_limited`: charge, random outcomes, or timing ownership
  prevents certifying a static sweetspot selection.

The JSON records all action decisions, external raw/HTML source revisions and
SHA-256 digests, local input digests, failed retrieval, and uncatalogued gaps.
It is the authoritative row inventory; sources are evidence, not instructions.

## Findings

- Mario: fire-blast versus arm roles independently checked for all three
  available smash angles. Neutral/back air retain named clean/late distinctions.
  Forward air explicitly has **no sourspot** in both character and move pages.
- Dr. Mario: late neutral air remains stronger; do not impose early-best.
  Slide ID1 stays strong through frame25, unlike ID0's frame10 decay.
  Up-smash grounded-only spike and aerial launcher are independent target
  filters; both clean variants remain selected.
- Luigi: down-air meteor and nonmeteor all deal16%; damage ranking fails.
  Ground/air Fire Jump Punch frame5 sweetspots deal25%/20%, respectively.
  Green Missile charge and random misfire are not spatial sweetspot variants.
- DK: named forward-smash elbow and down-smash hand roles confirmed.
  Forward air remains unresolved: early launcher and late meteor both deal16%,
  with the early hit preferred for particular confirms, not every situation.
  Character changes explicitly names down-air's body sourspot, independently
  strengthening the existing foot/body labels. Later-game horizontal
  chest-sourspot descriptions must not be backported to Melee.

## Bounded proposal: full-charge Giant Punch rear sourspot

DK's own Melee changes section explicitly calls the rear80-degree hit a sourspot:
18% grounded,16% aerial. The dedicated move tables independently match all three
early frame17 signatures on bones30/31/4, engine IDs0/1/2. JSON proposes those
six exact phases as `sour`, label `full-charge rear vertical sourspot`:

- Ground action373: `0:30:1`, `1:31:1`, `2:4:1`,18%,80 degrees, frame17.
- Air action378: same phase IDs,16%,80 degrees, frame17.

No complementary `sweet` label is proposed merely because the later hit has
more damage. No proposal covers partial-charge372/377. General Giant Punch's
explicit uncharged-elbow sweetspot sentence is under **Brawl** stages, not Melee;
copying it would be a cross-game inference. Runtime power, collision priority,
and execution-origin coverage remain unverified. Status stays runtime-limited
despite the source-backed bounded sour proposal.

## Source-backed exclusions and unresolved candidates

- Separate opposite-side down-smash/getup strikes are not clean/late phases.
  Mario's changes introduction mentions down-smash sourspots without assigning
  them to exact foot/leg phases. Mario/Doc back-strike gradients remain unresolved;
  Luigi's two kicks
  have equal17% damage and are excluded as a decay hypothesis.
- Cape/Super Sheet close/far or offset-zone damage differences are real, but
  retrieved descriptions do not name a sweet/sour choice. Reflection is an
  independent capability, not proof of stronger fighter-contact selection.
- Mario and Doc up/down specials contain successive linkers and finishers.
  Luigi Cyclone explicitly has two medium-strength strikes. DK Spinning Kong
  has six/eight successive strikes; selecting only its strongest opener would
  conflate hit role with sweetspot. Aerial Spinning Kong arm/body loop power
  remains separately unresolved.
- Mario down tilt8% foot/9% leg and DK up tilt9/10/11% are not automatically
  highest-damage sweetspots. Their dedicated move overviews are empty.
- Mario/Doc/Luigi quick ledge attacks have8% legs/6% body without named sweet
  interpretation. Other assigned getups/ledge attacks have separately checked
  uniform combat values, not assumed clone equivalence.
- Standing/running grabs are zero-damage capture volumes. Pummels, throws,
  cargo victim damage and back-throw collateral remain uncatalogued gaps,
  not verified absent attacks.
- DK grounded Headbutt bury and aerial Headbutt meteor belong to different
  actions; their5/10% difference does not define an in-action sweetspot.
- DK Hand Slap only hits grounded targets. Inability to reach a grounded foe
  with up smash, by contrast, is source geometry commentary and does not prove
  an aerial-only target flag.

## Timing and source discrepancies

No frame or numerical corrections were made.

| Move | Catalog | Retrieved move source | Consequence |
| --- | --- | --- | --- |
| DK up tilt |6-11|6-13, revision1395243|Unresolved lifetime; no blanket shift.|
| Luigi taunt |45|46, revision1930503|Single meteor, unresolved indexing origin.|
| Luigi Green Missile |takeoff-local4-43|global22-61, revision2059219|Different action origin; source misfire ID1 versus catalog ID0 also unresolved.|
| DK partial Giant Punch |local17/18-21|no-charge24/25-29, revision2058001|Do not reuse full-charge timing or infer global origin.|
| DK full Giant Punch |17/18-21|17/18-21, same revision|Timing agreement does not resolve charge/trajectory selection.|
| DK Hand Slap |loop-local5-6/16-17|global19-20/30-31, revision2056127|Startup offset plausible, unproved; second-hit base/radius also differs.|
| Doc down smash |back IDs0/1|back ID0 repeated twice, revision1949675|Source table typo/conflict; no engine-ID overwrite.|

## Persisted source evidence

All four character pages were fetched as actual HTML and pinned raw source;
current revisions match the prior reviewed character revisions. JSON hashes
refer to complete retrieved payloads, not reformatted snippets. Move-page raw
payloads were also fetched after identifying their current HTML revision.

Key raw-source excerpts/observations retained here and in JSON scopes:

- Mario2062453 `fsmashdesc`: "Its sweetspot is the fire blast"; sourspot at
  arm. `fairdesc`: meteor "with no sourspot". Move1936259 repeats no sourspot.
- Doc2062457 `fsmashdesc`: "it has no sourspot". `fairdmg`:17% sweetspot,
  16% sourspot; `fairdesc` names weaker hand. `nairdesc`: "power increases the
  longer it's out". Move1952263 timing explicitly retains `Hitbox 1 |6-25`.
- Luigi2062454 `usdesc`: "1-frame sweetspot right at the beginning";
  `usdmg`:25 ground clean,20 air clean,1 late. Move2054418 independently lists
  `Sweetspot |5` and `Sourspot |6-23`. Move1983582 explicitly maps ID2/bone54
  to270 while IDs0/1 use361, all16%.
- DK2062459 changes-from-Smash-64 names arm/hand smash sweetspots;
  move1930258 explicitly locates forward-smash sweetspot on elbows.
  The same character changes section explicitly names down-air's body sourspot
  and full-charge Giant Punch's rear80-degree sourspot18% ground/16% air.
  Move2030297 names early launcher and late meteor and prefers early for
  specified confirms. It does not supply a universal sweet/sour partition.
- DK2058001 distinguishes `Uncharged`, `Max charge (Ground)` and `Max charge
  (Aerial)`; partial damage gets `+2% damage per arm swing (max 10)`.
  Full-charge ground rises18->30, air16->27: strongest-first is false.
  Character changes source, not this numerical ordering, justifies the six
  early-sour proposals. Mario/Doc comparison text also explicitly states Doc
  down tilt has consistent damage without a sourspot; it is not used to infer
  exact Mario down-tilt labels from another fighter.
- Luigi1934581 explicitly contrasts Cyclone's "two medium-strength hits"
  with several weak Mario hits. DK2058395 explicitly separates first hit,
  hits2-3 and hits4-6 on ground, and eight-hit aerial behavior.
- Sweet-spot definition2059342 independently names Mario flame and Luigi Fire
  Jump Punch. Its DK chest-sourspot example explicitly begins in SSB4, not Melee.

One attempted dedicated source failed: `Mario_(SSBM)/Edge_attack` returned
HTTP404. It supplies no evidence. Character moveset leg/body ledge damage
remains available, but this is not a replacement per-move adjudication.
There were no character raw/HTML fetch failures in this shard.

## Gaps and remaining work

- Historical CSV/catalog omit Mario, Luigi and DK dash attacks; omit Doc jab2/3,
  up-angled tilt and angled smashes. These are inventory gaps, not no-hit claims.
- Mario down-air landing hit is expected and missing; Doc's move explicitly has
  no landing hit, so the gap must not be generalized across clones.
- Fireballs/pills have CSV action records but no fighter-owned catalog groups.
  Projectile/article phases require their own extraction and collision review.
- Pummels, ordinary throws, cargo releases/breakout and thrown-owner collateral
  require independent conditional/runtime ownership review.
- Charge, RNG, reflection, collision priority, animation blending, actual live
  connectivity and target vulnerability are not certified by this static audit.
- Intermediate angled actions cannot be synthesized from adjacent catalog IDs.
- No source, data or model says every remaining unlabeled action lacks sweetspots.

## Validation

Validated with root `python/.venv/bin/python`:

- 119 action rows match assigned `catalog.actions` exactly once each.
- 49 unique source IDs:48 retrieved, one explicit404; all references resolve.
- All43 successful external raw/HTML payloads were fetched again; every recorded
  SHA-256 matched, with zero remote mismatches. Five local input hashes match.
- 74 existing assigned label signatures match catalog frames, ID, bone, damage,
  angle and element exactly. Global CSV remains569 labels/129 actions.
- Six proposed phase IDs resolve to the exact full-charge early signatures;
  no existing labeled signature is overwritten.
- Zero assigned unavailable entries;16 separately recorded gaps.

Report-only validation does not certify runtime gameplay completeness.
