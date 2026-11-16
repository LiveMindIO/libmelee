# Full-roster sweetspot audit

Seven disjoint fighter shards cover the catalog's 27 internal character
contexts: 26 selectable fighters, with Popo and Nana checked separately.
`group-a.json` through `group-g.json` record one disposition for every catalog
action, separate extraction failures, source provenance and out-of-catalog gaps.
Companion Markdown files explain each shard's findings. `boundaries.md` and
`boundaries.json` separately examine what this static catalog cannot establish.

## Dispositions

- `existing_labels_reviewed`: existing exact-signature annotations were checked
  against source evidence. This is not live collision-priority certification.
- `excluded_with_evidence`: source evidence supports leaving the represented
  phases unlabeled, for example separate strikes rather than power decay.
  This does not prove that every runtime context lacks a useful sweetspot.
- `unresolved_source`: the available evidence does not establish the named
  variant or exact mapping. Absence of a source description is not an exclusion.
- `runtime_or_article_limited`: fighter-owned static hitboxes cannot establish
  the relevant projectile, copied, partner, charge or other runtime behavior.

Proposed labels are research findings, not active annotations. They require
independent source/signature review and regression tests before CSV changes.
Damage maxima, earliest frames, another fighter's aliases and raw enumeration
names do not establish a selection.

## Inventory check

From the libmelee checkout:

```sh
python scripts/check_sweetspot_roster_audit.py --self-test
```

The checker rejects omitted/duplicate actions, missing roster shards, undefined
sources, unaccounted extraction failures and proposals for nonexistent phases.
Source-backed dispositions require retrieved evidence with a content digest.
Its receipt reports catalog and label-resource hashes plus per-character counts.
Negative controls test that malformed inventories fail closed.

Passing proves **inventory accounting**, not that source interpretations are
correct, all moves were extracted, or engine behavior was verified. Unresolved
and runtime-limited entries remain open work even when every row is accounted
for. No count of reviewed rows, candidate actions or labels certifies complete
sweetspot coverage.

## Compatibility boundary

This audit does not alter numerical catalog bytes, historical framedata, geometry,
frame origins, controller behavior, Hold APIs or original labels. Static poses
cannot prove actual collision order, target contact or combo/evasion success.
Projectile/article objects, runtime scaling and missing extraction need their
own evidence; an absent fighter hitbox is not proof of an absent attack.
