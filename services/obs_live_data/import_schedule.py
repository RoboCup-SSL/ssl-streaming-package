#!/usr/bin/env python3
"""Convert live/data/schedule.md -> live/data/schedule.json, validating as it goes.

Markdown shape:  '# <Day>'  ->  '## Field <X>'  ->  '### time | label | teamA | teamB'
Run: python live/import_schedule.py
"""
import difflib
import itertools
import json
import os
import re
from collections import defaultdict

HERE = os.path.dirname(__file__)
SRC = os.path.join(HERE, "data", "schedule.md")
OUT = os.path.join(HERE, "data", "schedule.json")
YEAR = 2026
MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], start=1)}

# Known corrections applied to team names (source markdown left untouched).
CORRECTIONS = {"TurtleRabbot": "TurtleRabbit"}


def parse_day(header):
    mm = re.search(r"(" + "|".join(MONTHS) + r")\s+(\d+)", header)
    return f"{YEAR}-{MONTHS[mm.group(1)]:02d}-{int(mm.group(2)):02d}"


def fix(name):
    return CORRECTIONS.get(name, name)


def parse(path):
    day = field = None
    out = []
    counters = defaultdict(int)
    for ln in open(path, encoding="utf-8"):
        ln = ln.rstrip()
        if ln.startswith("# "):
            day = parse_day(ln[2:])
        elif ln.startswith("## "):
            field = ln[3:].strip().replace("Field ", "")
        elif ln.startswith("### "):
            t, label, a, b = [p.strip() for p in ln[4:].split("|")]
            hh, mm = t.split(":")
            time = f"{int(hh):02d}:{int(mm):02d}"
            counters[(day, field)] += 1
            n = counters[(day, field)]
            out.append({
                "id": f"{day}-{field}-{n}",
                "day": day,
                "division": "A" if field == "A" else "B",
                "field": field,
                "time": time,
                "label": label,
                "teamA": fix(a),
                "teamB": fix(b),
            })
    return out


def validate(schedule):
    groups = defaultdict(list)
    teams = set()
    for m in schedule:
        if re.fullmatch(r"G\d", m["label"]):  # pure group-stage match
            groups[(m["division"], m["label"])].append((m["teamA"], m["teamB"]))
            teams.update([m["teamA"], m["teamB"]])
    print("=== round-robin check ===")
    ok = True
    for (d, g), pairs in sorted(groups.items()):
        ts = sorted({x for p in pairs for x in p})
        expected = len(ts) * (len(ts) - 1) // 2
        seen = defaultdict(int)
        for a, b in pairs:
            seen[frozenset((a, b))] += 1
        missing = [c for c in itertools.combinations(ts, 2) if frozenset(c) not in seen]
        dups = [tuple(k) for k, v in seen.items() if v > 1]
        good = len(pairs) == expected and not missing and not dups
        ok = ok and good
        print(f"Div {d} {g}: {len(ts)} teams, {len(pairs)}/{expected} [{'OK' if good else 'CHECK'}]")
        if missing:
            print(f"   missing: {missing}")
        if dups:
            print(f"   duplicate: {dups}")
    print(f"distinct group-stage teams: {len(teams)}")
    tl = sorted(teams)
    for i, a in enumerate(tl):
        for b in tl[i + 1:]:
            if a.lower() != b.lower() and difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio() > 0.85:
                print(f"   WARNING near-duplicate names: {a!r} ~ {b!r}")
                ok = False
    return ok


def seed_live(schedule):
    """currentId per field = earliest match on that field."""
    by_field = defaultdict(list)
    for m in schedule:
        by_field[m["field"]].append(m)
    live = {}
    for f, ms in by_field.items():
        ms.sort(key=lambda m: (m["day"], m["time"]))
        live[f] = {"currentId": ms[0]["id"]}
    return live


def main():
    schedule = parse(SRC)
    ok = validate(schedule)
    data = {"schedule": schedule, "live": seed_live(schedule)}
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    print(f"\nWrote {OUT}: {len(schedule)} matches, fields {sorted(data['live'])}")
    print("VALIDATION:", "OK" if ok else "PROBLEMS ABOVE")


if __name__ == "__main__":
    main()
