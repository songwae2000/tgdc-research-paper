"""New York's published service level agreements, as a cold-start prior.

The blind priors in this repository are written by reasoning about what a job
involves. A published service target needs no reasoning at all: the city says
how long it intends to take, and you rank categories by that. If the target
predicts duration as well as reasoning does, then the useful prior for a new
client is a document they already have, not an exercise someone has to perform.

This also bears on contamination. A language model asked to reason about
municipal work may be recalling published performance material rather than
reasoning, and this measures how much such a document is worth on its own.
New York publishes these targets. I could not find an equivalent open dataset
for Austin or San Francisco, which are the two cities carrying the blind result,
so this narrows that worry without settling it.

Source: NYC Open Data, 311 Service Level Agreements, dataset cs9t-e3x8.
"""

import json
import os
import re
import subprocess

import numpy as np

ENDPOINT = "https://data.cityofnewyork.us/resource/cs9t-e3x8.json"
PATH = "data/nyc_sla.json"
UNMANAGED = "sla not managed by 311"

# "4 days", "8 hours", "1 day". Anything else, including the 761 rows that say
# the target is not managed by 311, carries no number and is dropped.
DURATION = re.compile(r"(\d+(?:\.\d+)?)\s*(day|hour|week|month)s?", re.I)
IN_HOURS = {"hour": 1.0, "day": 24.0, "week": 168.0, "month": 720.0}


def ensure():
    if os.path.exists(PATH):
        return
    print("  fetching New York service level agreements...", flush=True)
    result = subprocess.run(
        ["curl", "-s", "--max-time", "120", "--retry", "2", "-G", ENDPOINT,
         "--data-urlencode", "$limit=10000"],
        capture_output=True, text=True)
    rows = json.loads(result.stdout)
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("service level agreement feed came back empty")
    os.makedirs("data", exist_ok=True)
    json.dump(rows, open(PATH, "w"))


def target_hours():
    """Published target per complaint type, in hours.

    A complaint type can carry several targets, one per sub-problem, and they
    disagree. The median is taken, since the question asked of it here is how
    long this kind of work is meant to take, not which of its variants is
    slowest.
    """
    ensure()
    by_problem = {}
    for row in json.load(open(PATH)):
        problem = (row.get("problem") or "").strip().lower()
        raw = (row.get("sla_days") or "").strip()
        if not problem or raw.lower() == UNMANAGED:
            continue
        match = DURATION.search(raw)
        if not match:
            continue
        hours = float(match.group(1)) * IN_HOURS[match.group(2).lower()]
        by_problem.setdefault(problem, []).append(hours)

    return {p: float(np.median(v)) for p, v in by_problem.items()}


def score(features, targets, fallback=None):
    """Ranks tickets by their category's published target, slowest first.

    A category with no published target is scored at the median of the ones
    that have, which is the least informative thing available rather than a
    guess in either direction.
    """
    if fallback is None:
        fallback = float(np.median(list(targets.values())))
    return [targets.get(f["category"].strip().lower(), fallback)
            for f in features]


def coverage(features, targets):
    hit = sum(1 for f in features
              if f["category"].strip().lower() in targets)
    return hit / len(features)
