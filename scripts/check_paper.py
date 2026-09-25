"""Checks that every figure in the paper is one run_all.py actually prints.

Two numbers reached a draft of the paper without ever being computed. They
looked plausible and nobody would have caught them by reading. This walks every
table cell, pulls out each number, and fails if the run output does not contain
it.

The feeds are live and backfill in place, so a reviewer who re-downloads gets
bootstrap bounds that move in the third decimal. An exact match would fail for
every such reviewer, which would make the check noise rather than a guard.
Numbers therefore match within a tolerance, and the tolerance is reported so a
reviewer can see how much drift was absorbed. Anything that moves further than
that is a real disagreement and still fails.

Usage: python run_all.py > out.txt && python scripts/check_paper.py out.txt
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAPER = ROOT / "paper" / "paper.md"
NUMBER = re.compile(r"-?\d[\d,]*\.?\d*%?")
TOLERANCE = 0.002    # absolute, on the decimal figures the run prints
# Percentages match exactly. A tolerance here defeats the check: a paper
# percentage is two digits, the run prints dozens of them, and anything within a
# point of any of them passes. That let 72% be changed to 92% and still pass,
# because the run prints 93% elsewhere. Third-decimal drift on a live feed can
# still move a rounded percentage across a boundary, and when it does this fails
# loudly and a reviewer compares the two numbers by eye, which is the right
# trade against silently accepting a figure nobody computed.
PERCENT_TOLERANCE = 0.0


CITATION = re.compile(r"\[\d+(?:, *\d+)*\]")
TABLE_REF = re.compile(r"\bTables?\s+\d+")
# things that are numbers but not findings: a year, the name of the feed, a
# figure of speech with a digit in it. None of these are ever printed by a run
# and none of them are claims, so checking them would only train the reader to
# ignore the checker.
NOT_A_FINDING = {"311", "2026", "2025", "2024", "2023", "2018", "2017",
                 "2016", "2008", "2007", "2006", "0.5", "95", "1,000",
                 "2,000", "4", "8"}


def figures_in(markdown):
    """Every number in a table row or in prose, with the line it came from.

    Prose is included because the two figures that once reached a draft
    uncomputed were in prose, and a later review found two more there. A checker
    that walks only table cells teaches you to trust the tables and nothing
    else, which is worse than no checker.
    """
    found = []
    body = markdown.split("## References")[0]
    for line in body.splitlines():
        if set(line) <= set("|- ") or line.startswith("#"):
            continue
        text = line
        if not line.startswith("|"):
            text = CITATION.sub(" ", TABLE_REF.sub(" ", text))
        for token in NUMBER.findall(text):
            if token in NOT_A_FINDING:
                continue
            found.append((token, line.strip()))
    return found


def as_number(token):
    try:
        if token.endswith("%"):
            return float(token[:-1].replace(",", "")), True
        return float(token.replace(",", "")), False
    except ValueError:
        return None, False


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: check_paper.py <run_all output file>")

    run = Path(sys.argv[1]).read_text()
    haystack = run + "\n" + run.replace(",", "")
    printed = [as_number(t) for t in NUMBER.findall(haystack)]

    missing, approximate = [], []
    for token, row in figures_in(PAPER.read_text()):
        if token in haystack or token.replace(",", "") in haystack:
            continue

        want, is_percent = as_number(token)
        if want is None:
            missing.append((token, row, None))
            continue

        tolerance = PERCENT_TOLERANCE if is_percent else TOLERANCE
        nearest = None
        for value, same_kind in printed:
            if value is None or same_kind != is_percent:
                continue
            if nearest is None or abs(value - want) < abs(nearest - want):
                nearest = value

        if nearest is not None and abs(nearest - want) <= tolerance:
            approximate.append((token, nearest, abs(nearest - want)))
        else:
            missing.append((token, row, nearest))

    if missing:
        print(f"{len(missing)} figure(s) in the paper that run_all.py never printed:")
        for token, row, nearest in missing:
            near = f"nearest printed {nearest}" if nearest is not None else "no match"
            print(f"  {token:>10}   {near:<28}{row[:60]}")
        sys.exit(1)

    total = len(figures_in(PAPER.read_text()))
    print(f"all {total} table figures are present in the run output")
    if approximate:
        worst = max(d for _, _, d in approximate)
        print(f"  {len(approximate)} matched within tolerance, largest drift {worst:.4f}")
        print("  the feeds backfill in place, so this is the data moving under you")


if __name__ == "__main__":
    main()
