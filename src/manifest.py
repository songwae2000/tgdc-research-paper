"""Records exactly which rows this paper's figures were computed from.

The four feeds are live. A city can backfill a late closure or correct a
category months after the fact, so a reviewer pulling the same two weeks later
may not receive the same rows we did. The raw files are too large to keep in
the repository, so instead we keep their fingerprints. If a rerun disagrees
with the paper, this says immediately whether the data moved or the code did.
"""

import hashlib
import json
from pathlib import Path

from src import cities, tickets

MANIFEST = Path("data/MANIFEST.json")


def fingerprint(path):
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    rows = len(json.loads(Path(path).read_text()))
    return {"sha256": digest[:16], "rows": rows}


def build():
    return {
        f"{city.name}/{which}": fingerprint(tickets.path_for(city, which))
        for city in cities.ALL
        for which in ("train", "test")
    }


def write():
    MANIFEST.parent.mkdir(exist_ok=True)
    MANIFEST.write_text(json.dumps(build(), indent=2, sort_keys=True) + "\n")


def check():
    """Compares the data on disk against the manifest the paper was built from.

    Returns a list of human-readable differences, empty when they agree.
    """
    if not MANIFEST.exists():
        return ["no manifest recorded"]

    expected = json.loads(MANIFEST.read_text())
    actual = build()
    notes = []
    for key, want in sorted(expected.items()):
        got = actual.get(key)
        if got is None:
            notes.append(f"{key}: missing locally")
        elif got["sha256"] != want["sha256"]:
            # the branch is on content, so say which kind of difference it is.
            # Identical row counts with a different hash means the feed
            # backfilled a field in place, which moves figures in the third
            # decimal without changing what was pulled.
            if got["rows"] == want["rows"]:
                notes.append(f"{key}: same {want['rows']} rows, but the file "
                             f"contents changed, so a field was edited in place")
            else:
                notes.append(f"{key}: {want['rows']} rows in the paper, "
                             f"{got['rows']} rows here")
    return notes


if __name__ == "__main__":
    write()
    print(f"wrote {MANIFEST}")
