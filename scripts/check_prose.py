"""Runs the tighten sweep over this repository's prose, exempting citations.

The sweep bans semicolons in prose. A reference list uses them as the standard
separator between works, so the paper's bibliography fails a rule that was
written for sentences. Rather than rewrite citations into something a reader of
papers would find odd, or leave a gate permanently red until nobody reads it,
the reference list is skipped and everything above it is checked as normal.

Nothing else is exempt. The exemption is per section, not per file, so prose
that happens to sit near a citation is still checked.

Usage: python scripts/check_prose.py
"""

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SWEEP = Path.home() / ".claude" / "skills" / "tighten" / "scripts" / "sweep.py"

# file, and the heading whose section is skipped (None checks the whole file)
TARGETS = [
    (ROOT / "paper" / "paper.md", "## References"),
    (ROOT / "README.md", None),
    (ROOT / "ONE_PAGER.md", None),
    (ROOT / "HYPOTHESIS.md", None),
]


def body_of(path, cut_at):
    text = path.read_text()
    if cut_at and cut_at in text:
        # rstrip, or the cut leaves trailing blanks the sweep then reports as a
        # fault in a file that does not have one
        return text.split(cut_at)[0].rstrip() + "\n", True
    return text, False


def main():
    if not SWEEP.exists():
        sys.exit(f"sweep not found at {SWEEP}")

    failed = []
    for path, cut_at in TARGETS:
        if not path.exists():
            continue

        body, trimmed = body_of(path, cut_at)
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write(body)
            temp = handle.name

        result = subprocess.run([sys.executable, str(SWEEP), temp],
                                capture_output=True, text=True)
        Path(temp).unlink()

        verdict = result.stdout.strip().splitlines()[-1] if result.stdout else "no output"
        note = "  (references skipped)" if trimmed else ""
        print(f"{path.relative_to(ROOT)}{note}")
        print(f"  {verdict}")
        if result.returncode != 0:
            failed.append(path.relative_to(ROOT))
            for line in result.stdout.splitlines():
                if "line " in line:
                    print(f"    {line.strip()}")

    if failed:
        print(f"\n{len(failed)} file(s) failed: {', '.join(str(f) for f in failed)}")
        sys.exit(1)
    print("\nall prose clean")


if __name__ == "__main__":
    main()
