# Group C: sword fighters

Inventory accounting is complete for Marth (18), Roy (26), Link (6), and
Young Link (20): **126 catalog actions, six unavailable entries, 21 gaps**.
This is not complete sweetspot, extraction, runtime, or collision certification.
Exact action decisions and source receipts are in [group-c.json](group-c.json).

## Dispositions

| Fighter | Actions | Existing reviewed | Excluded | Unresolved | Runtime/article limited | Proposed phases |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Marth | 42 | 14 | 5 | 20 | 3 | 0 |
| Roy | 40 | 9 | 4 | 24 | 3 | 0 |
| Link | 22 | 2 | 11 | 8 | 1 | 6 |
| Young Link | 22 | 3 | 10 | 9 | 0 | 8 |
| Total | 126 | 28 | 30 | 61 | 7 | 14 |

The assigned 146 existing label rows remain unchanged: Marth72, Roy44,
Link12, Young Link18. Marth45's existing labels are preserved but its exact
timing remains unresolved, rather than counted as independently confirmed.

## Proposals: research only

- **Link69 down aerial:** three clean phases13-15, damage22/20/20, sweet;
  three late phases16-64, damage19/19/19, sour. Sources `l` and `l-dair`
  name the clean/late roles and match these windows. Select every clean zone,
  not only the maximum22% zone. Runtime bounce6/8% is outside these signatures.
- **Young Link66 forward aerial:** four clean phases14-16,
  damage12/11/9/9 at361 degrees, sweet; four late phases17-33,
  damage8/7/7/5 at76 degrees, sour. Sources `y` and `y-fair` establish a
  single-hit move with named clean/late roles, unlike Link's two-hit fair.
  Late launch utility is retained; spatial ranking remains unresolved.

All 14 proposal IDs exist in the catalog and are currently unlabeled.
No CSV changes are made. Independent review and lead-owned regression tests
must precede adoption.

## Unresolved evidence

- **Marth45:** move-page Timing5-9 conflicts with catalog4-8. Spatial tipper
  role agrees; do not silently shift frames or remove existing labels.
- **Sword-dance branches:** first-branch timing agrees, but later Wiki windows
  are generally one frame later. Keep every ground/air branch separate;
  do not infer a universal frame correction or hilt/tip label.
  Marth354/363 catalog12% meteor also conflicts with character summary10%.
- **Roy65:** explicit finisher-base sweetspot wording does not reconcile the
  character summary's tip5% with table/catalog6%. Preserve opener/finisher
  separation; no new labels. Blazer's reverse opener and multihit roles do
  not justify importing Marth's startup sweetspot.
- **Young Link53:** Wiki IDs1/2 damage10/11 conflicts with catalog11/10.
- **Young Link56:** Timing9-15 agrees, but the embedded strip has12 lag,
  three hit,26 lag frames. No timing correction is proposed.
- **Young Link57:** character prose calls the tip a meteor; table/catalog
  outerID3 is angle70 while innerIDs0/1/2 are angle280. Do not label tip meteor.
- **Young Link67:** Clean/Late table headings describe two kicks according to
  the same page's Hit1/Hit2 timing and moveset. Exclude temporal power labels.
- **Link356:** catalog IDs0-2 change15% to5% at14; Wiki says16 and prior
  FightCore evidence says15. ID3 remains15% through8-41. Existing label-doc
  prose saying persistentID3 is8% is inconsistent with catalog15%; not edited.
- **Young Link356:** thirteen grounded strikes, not five aerial strikes.
  Wiki repeatsID0 for other root zones and gives finisher1%; catalog and
  character summary give3%. Do not flatten pulses into clean/late phases.

## Gaps and boundaries

- Roy dash attack50 and down aerial69 have named sweetspot evidence but no
  catalog entries. Marth slow ledge attack256 is also missing. Missing
  extraction is not proof of absent hitboxes.
- Marth/Roy full-charge aerial348 and Counter retaliations370/372 are absent.
  Charge scaling, recoil, conditional counter power, and copied owner behavior
  require separate runtime evidence; stance states are not retaliation hits.
- Link/Young Link capture212/214 and Z-air360 fail on fighter bone139.
  Character-relative identifiers override misleading generic enum names.
- Rapid jabs, arrows, boomerangs, bombs, pummels, throws, and down-air bounce
  behavior have explicit gap records. Article/item or throw-owner hitboxes
  cannot be inferred from fighter-owned static poses.
- Reviewed Young Link69 labels cover both early and stronger late fire meteor
  signatures, not runtime bounce8/9%. Front/back swings, successive multihits,
  target flags, and situational trajectories are not generic early-best rules.

## Provenance and validation

The JSON records 75 sources with URLs, revisions, SHA-256 digests, scope, and
retrieval flags: four local resources, four raw character articles with HTML
receipts, and 63 move pages. Character revisions are Marth2067346,
Roy2067101, Link2062902, and Young Link2062463. Local-resource URLs identify
commit6aa09c70cd97e1665d3870fa53927fbfbd05f638; bytes were read locally,
not fetched over HTTP. Temporary fetch-output paths are not durable evidence;
essential findings and digests are retained in the JSON.

Read-only checks verify exact once-only assigned action/unavailable coverage,
defined source references, local-resource hashes, proposal phase existence,
and absence of proposal labels from the current CSV. These checks do not
independently certify source interpretation, collision priority, actual target
contact, all-move extraction, or runtime behavior. Numerical resources,
historical frame values, and all569 existing labels remain untouched by this shard.
