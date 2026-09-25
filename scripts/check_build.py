"""Fails if the committed PDF is older than the source it claims to be built from.

The paper once shipped seven commits behind its own LaTeX. It was three pages
where the source was four, it had no reference list, and it asserted a result
the current draft retracts. Nothing caught it, because the source and the build
lived in different repositories and neither knew about the other.

This compares what git has recorded for each file, not what is on disk, since
the working copy is always fresh on the machine that just ran pdflatex and never
on anyone else's.

Usage: python scripts/check_build.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = "paper/paper.md"
TEX = "main.tex"
PDF = "main.pdf"


def committed_at(path):
    """Unix time of the last commit touching this path, or None if untracked."""
    out = subprocess.run(
        ["git", "log", "-1", "--format=%ct", "--", path],
        cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return int(out) if out else None


def dirty(path):
    out = subprocess.run(["git", "status", "--porcelain", "--", path],
                         cwd=ROOT, capture_output=True, text=True).stdout
    return bool(out.strip())


def main():
    times = {p: committed_at(p) for p in (SOURCE, TEX, PDF)}
    missing = [p for p, t in times.items() if t is None]
    if missing:
        sys.exit(f"not tracked: {', '.join(missing)}")

    problems = []
    if times[TEX] < times[SOURCE]:
        problems.append(f"{TEX} was committed before {SOURCE}. "
                        f"Run scripts/make_paper.py and commit the result.")
    if times[PDF] < times[TEX]:
        problems.append(f"{PDF} was committed before {TEX}. "
                        f"Rebuild with pdflatex and commit the result.")
    for path in (SOURCE, TEX, PDF):
        if dirty(path):
            problems.append(f"{path} has uncommitted changes, so what a reader "
                            f"clones is not what you are looking at.")

    if problems:
        print("the published paper does not match its source:")
        for line in problems:
            print(f"  {line}")
        sys.exit(1)

    print(f"{PDF} is newer than {TEX}, which is newer than {SOURCE}")


if __name__ == "__main__":
    main()
