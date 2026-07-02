#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["simpleobsws"]
# ///
"""Push one scene from an OBS scene-collection JSON export into a LIVE OBS over
obs-websocket (v5), flattening any groups into their child sources.

    python3 push_scene_ws.py --collection Untitled            # simplest: no-auth OBS
    python3 push_scene_ws.py --scene scoreboard --collection Untitled --replace
    python3 push_scene_ws.py --dry-run                        # preview, no connection

Defaults: --scenes = bundled robocup-2026/scenes.json, --scene = scoreboard,
--password = "" (no auth), --collection = none (uses OBS's currently-active collection).

Why flatten: obs-websocket has no "create group" request, so each group's children
are placed directly in the target scene, their positions offset by the group's
position. (In this collection the groups are translate-only — scale 1, no rotation —
so the offset is exact; a scaled/rotated group would only be approximate and is warned.)

Easiest way to run (no install, no sudo) — uv reads the inline deps above:
    uv run obs-template/push_scene_ws.py --collection Untitled
Or with plain python if simpleobsws is already available:  pip install --user simpleobsws
--dry-run prints the plan and needs no dependencies at all.
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

# OBS bounds_type int (file) -> obs-websocket enum string
BOUNDS = {
    0: "OBS_BOUNDS_NONE", 1: "OBS_BOUNDS_STRETCH", 2: "OBS_BOUNDS_SCALE_INNER",
    3: "OBS_BOUNDS_SCALE_OUTER", 4: "OBS_BOUNDS_SCALE_TO_WIDTH",
    5: "OBS_BOUNDS_SCALE_TO_HEIGHT", 6: "OBS_BOUNDS_MAX_ONLY",
}


def load_collection(path):
    d = json.loads(Path(path).read_text())
    sources = {s["name"]: s for s in d["sources"]}
    groups = {g["name"]: g for g in d.get("groups", [])}
    return sources, groups


def transform(it, dx=0.0, dy=0.0):
    t = {
        "positionX": it["pos"]["x"] + dx, "positionY": it["pos"]["y"] + dy,
        "rotation": it.get("rot", 0.0),
        "scaleX": it["scale"]["x"], "scaleY": it["scale"]["y"],
        "alignment": it.get("align", 5),
        "cropLeft": it.get("crop_left", 0), "cropRight": it.get("crop_right", 0),
        "cropTop": it.get("crop_top", 0), "cropBottom": it.get("crop_bottom", 0),
    }
    bt = it.get("bounds_type", 0)
    if bt:  # only send bounds fields when bounds are actually enabled
        t["boundsType"] = BOUNDS.get(bt, "OBS_BOUNDS_NONE")
        t["boundsAlignment"] = it.get("bounds_align", 0)
        t["boundsWidth"] = it["bounds"]["x"]
        t["boundsHeight"] = it["bounds"]["y"]
    return t


def mk(src, tf):
    settings = {k: v for k, v in src.get("settings", {}).items() if k != "undo_suuid"}
    return {"name": src["name"], "kind": src.get("versioned_id") or src["id"],
            "settings": settings, "transform": tf}


def build_plan(scene_name, sources, groups):
    scene = sources.get(scene_name)
    if not scene or scene.get("id") != "scene":
        sys.exit(f"error: scene {scene_name!r} not found in export")
    plan = []
    for it in scene["settings"]["items"]:
        nm = it["name"]
        # group_item_backup items are OBS's internal ungroup-restore copies of a group's
        # members; the real placement comes from the group definition, so skip these.
        if it.get("group_item_backup"):
            continue
        if nm in groups:
            if it["scale"]["x"] != 1.0 or it["scale"]["y"] != 1.0 or it.get("rot", 0):
                print(f"  ! group {nm} is scaled/rotated - flatten is approximate", file=sys.stderr)
            gx, gy = it["pos"]["x"], it["pos"]["y"]
            for ch in groups[nm]["settings"]["items"]:
                src = sources.get(ch["name"])
                if src:
                    plan.append(mk(src, transform(ch, gx, gy)))
                else:
                    print(f"  ! group child missing: {ch['name']}", file=sys.stderr)
        elif nm in sources:
            src = sources[nm]
            if src.get("id") == "scene":
                print(f"  ! skipping nested scene: {nm}", file=sys.stderr)
            else:
                plan.append(mk(src, transform(it)))
        else:
            print(f"  ! item source missing: {nm}", file=sys.stderr)
    return plan


async def push(args, plan):
    import simpleobsws
    ws = simpleobsws.WebSocketClient(url=f"ws://{args.host}:{args.port}", password=args.password)
    await ws.connect()
    await ws.wait_until_identified()

    async def req(t, d=None):
        r = await ws.call(simpleobsws.Request(t, d or {}))
        if not r.ok():
            raise RuntimeError(f"{t} failed: {r.requestStatus}")
        return r.responseData

    if args.collection:
        await req("SetCurrentSceneCollection", {"sceneCollectionName": args.collection})
        await asyncio.sleep(1.0)  # let OBS load the collection

    have = {s["sceneName"] for s in (await req("GetSceneList"))["scenes"]}
    if args.scene in have:
        if args.replace:
            await req("RemoveScene", {"sceneName": args.scene})
            await req("CreateScene", {"sceneName": args.scene})
        else:
            print(f"scene {args.scene!r} already exists - adding into it (use --replace to reset)")
    else:
        await req("CreateScene", {"sceneName": args.scene})

    existing = {i["inputName"] for i in (await req("GetInputList"))["inputs"]}
    ok = 0
    for p in plan:
        try:
            if p["name"] in existing:
                print(f"  ~ {p['name']}: input already exists in collection - referencing it")
                r = await req("CreateSceneItem", {"sceneName": args.scene, "sourceName": p["name"]})
            else:
                r = await req("CreateInput", {
                    "sceneName": args.scene, "inputName": p["name"],
                    "inputKind": p["kind"], "inputSettings": p["settings"],
                    "sceneItemEnabled": True})
            await req("SetSceneItemTransform", {
                "sceneName": args.scene, "sceneItemId": r["sceneItemId"],
                "sceneItemTransform": p["transform"]})
            print(f"  + {p['name']} ({p['kind']})")
            ok += 1
        except Exception as e:
            print(f"  ! {p['name']}: {e}", file=sys.stderr)
    await ws.disconnect()
    print(f"\ndone: {ok}/{len(plan)} sources pushed into scene {args.scene!r}")


def main():
    default_scenes = Path(__file__).resolve().parent / "robocup-2026" / "scenes.json"
    ap = argparse.ArgumentParser(description="Push a scene from a scenes.json export into live OBS via websocket.")
    ap.add_argument("--scenes", default=str(default_scenes),
                    help="scene-collection JSON to read from (default: bundled robocup-2026/scenes.json)")
    ap.add_argument("--scene", default="scoreboard", help="scene name to copy (default: scoreboard)")
    ap.add_argument("--collection", default=None, help="target scene collection to switch to first")
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=4455)
    ap.add_argument("--password", default="", help="OBS websocket password (default: empty = no auth)")
    ap.add_argument("--replace", action="store_true", help="delete the target scene first if it exists")
    ap.add_argument("--dry-run", action="store_true", help="print the plan; do not connect")
    args = ap.parse_args()

    sources, groups = load_collection(args.scenes)
    plan = build_plan(args.scene, sources, groups)
    print(f"scene {args.scene!r}: {len(plan)} flattened sources")
    if args.dry_run:
        for p in plan:
            t = p["transform"]
            print(f"  {p['name']:22} {p['kind']:20} pos=({t['positionX']:.0f},{t['positionY']:.0f}) "
                  f"scale=({t['scaleX']:.3f},{t['scaleY']:.3f}) align={t['alignment']}")
        return
    asyncio.run(push(args, plan))


if __name__ == "__main__":
    main()
