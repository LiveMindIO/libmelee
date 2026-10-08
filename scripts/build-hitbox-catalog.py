"""Generate numerical phase data with the audited d255abe disc extractor.

Run with that checkout on PYTHONPATH and a legally supplied NTSC 1.02 ISO.
No disc bytes, animation tracks, local paths, or credentials enter the output.
"""

import argparse
import csv
import hashlib
import json
import subprocess
from dataclasses import asdict
from pathlib import Path

from melee.disc_framedata import DiscFrameData, DiscFrameDataError

import melee
from melee.enums import Action, Character
from melee.framedata import FrameData


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path)
    parser.add_argument("csv", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    extractor = Path(melee.__file__).resolve().parent.parent
    revision = subprocess.check_output(["git", "-C", str(extractor), "rev-parse", "HEAD"], text=True).strip()
    if revision != "d255abefd162cfb63aabe875fb99aec4b62726ef":
        raise ValueError("catalog extraction requires the reviewed d255abe checkout")
    if subprocess.check_output(["git", "-C", str(extractor), "status", "--porcelain"], text=True).strip():
        raise ValueError("catalog extraction requires an unmodified extractor checkout")
    disc = DiscFrameData(args.iso)
    facade = FrameData(iso_path=args.iso, _warn_deprecated=False)
    with args.csv.open() as stream:
        pairs = sorted({(int(r["character"]), int(r["action"])) for r in csv.DictReader(stream)})
    actions = {}
    unavailable = {}
    for char_id, action_id in pairs:
        char, action = Character(char_id), Action(action_id)
        key = f"{char_id}:{action_id}"
        try:
            record = disc.action_for_state(char, action)
            if record is None:
                continue
            offset = facade._disc_hitbox_frame_offset(char, action)
            groups = {}
            current = {}
            for frame in record.timeline.frames:
                number = frame.local_frame + offset
                if number < 1:
                    continue
                boxes = frame.active_hitboxes
                if not boxes:
                    current.clear()
                    continue
                posed = {p.hitbox.hitbox_id: p for p in disc.posed_frame(char, action, frame.local_frame).hitboxes}
                next_current = {}
                for box in boxes:
                    # Conditional/thrown-owner and non-fighter hitboxes cannot
                    # be treated as unconditional normal attack predictions.
                    if (
                        box.bugged_only_hit_grabbed_fighter_flag
                        or box.requires_thrown_hitbox_owner
                        or not box.fighter_interaction
                    ):
                        continue
                    identity = (box.hitbox_id, box.bone_id)
                    group = groups.setdefault(
                        identity, {"hitbox_id": box.hitbox_id, "bone_id": box.bone_id, "phases": []}
                    )
                    combat = asdict(box)
                    geometry = posed[box.hitbox_id]
                    previous = current.get(identity)
                    recreated = any(
                        e.change.value == "create"
                        and e.hitbox_id == box.hitbox_id
                        and e.local_frame == frame.local_frame
                        for e in record.timeline.hitbox_events
                    )
                    if (
                        previous is not None
                        and not recreated
                        and previous["combat"] == combat
                        and previous["end_frame"] == number - 1
                    ):
                        phase = previous
                    else:
                        phase = {
                            "phase_id": f"{box.hitbox_id}:{box.bone_id}:{len(group['phases']) + 1}",
                            "start_frame": number,
                            "end_frame": number,
                            "combat": combat,
                            "frames": [],
                        }
                        group["phases"].append(phase)
                    phase["end_frame"] = number
                    phase["frames"].append([number, geometry.x, geometry.y, geometry.z, geometry.size])
                    next_current[identity] = phase
                current = next_current
            if groups:
                actions[key] = list(groups.values())
        except DiscFrameDataError as exc:
            # Explicit absence, never fallback to unrelated CSV slot geometry.
            unavailable[key] = str(exc)
    build = asdict(disc.build)
    build.pop("iso_path")
    args.output.write_text(
        json.dumps(
            {
                "schema": 1,
                "extractor_commit": revision,
                "build": build,
                "csv_sha256": hashlib.sha256(args.csv.read_bytes()).hexdigest(),
                "geometry": "static unblended unit-rate fighter-root pose; scale=1; facing=right",
                "actions": actions,
                "unavailable": unavailable,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )
    print(f"Generated {len(actions)} actions; {len(unavailable)} actions unavailable")


if __name__ == "__main__":
    main()
