"""Builds the LaTeX paper from paper/paper.md, so the two cannot diverge.

paper.md is the source of record and its figures are checked against
run_all.py's output. This turns it into the main.tex at the repository root,
which is what Overleaf syncs and compiles. Writing it here rather than into a
sibling repository is deliberate: the previous arrangement let the committed PDF
fall seven commits behind its own source without anything noticing.

Usage: python scripts/make_paper.py [output.tex]
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "paper" / "paper.md"
DEFAULT_OUT = ROOT / "main.tex"

PREAMBLE = r"""\documentclass[10pt,a4paper,twocolumn]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[british]{babel}
\usepackage[margin=1.5cm]{geometry}
\setlength{\columnsep}{0.6cm}
\setcounter{topnumber}{3}
\setcounter{totalnumber}{4}
\renewcommand{\topfraction}{0.9}
\renewcommand{\textfraction}{0.08}
\renewcommand{\floatpagefraction}{0.8}
\usepackage{booktabs}
\usepackage{microtype}
\usepackage{titlesec}
\usepackage[hidelinks]{hyperref}
\titlespacing*{\section}{0pt}{0.5em}{0.2em}
\titlespacing*{\subsection}{0pt}{0.5em}{0.15em}
\setlength{\parskip}{0pt}
\setlength{\parindent}{1.2em}
\title{\vspace{-1.0em}\textbf{%s}\vspace{-0.4em}}
\author{\textbf{Cajetan Songwae} \\
  \small{\href{mailto:songwae2000@gmail.com}{songwae2000@gmail.com}} \\
  \small{TGDC case study, research track}}
\date{}
\begin{document}
\twocolumn[
  \begin{@twocolumnfalse}
  \maketitle
  \vspace{-2.2em}
  \end{@twocolumnfalse}
]
"""


SPECIALS = {"<": r"\textless{}", ">": r"\textgreater{}",
            "#": r"\#", "$": r"\$"}


def escape(text):
    # a leading minus on a percentage becomes a real minus sign, and this has
    # to happen before the percent sign is escaped or the pattern stops matching
    text = re.sub(r"(?<![\d\w])-(\d+%)", r"MINUS\1", text)
    text = text.replace("%", r"\%").replace("&", r"\&")
    for raw, safe in SPECIALS.items():
        text = text.replace(raw, safe)
    text = re.sub(r"MINUS([\d.]+\\%)", r"$-\1$", text)

    text = re.sub(r"`([^`]+)`",
                  lambda m: r"\texttt{" + m.group(1).replace("_", r"\_") + "}", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\\textbf{\1}", text)
    return re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\\textit{\1}", text)


def table(rows, caption=None):
    header = [c.strip() for c in rows[0].strip("|").split("|")]
    body = [[c.strip() for c in r.strip("|").split("|")] for r in rows[2:]]
    # a column is right-aligned when its values are numbers, which is most of
    # them. Left-aligning a numeric column wastes width the column cannot spare.
    def numeric(index):
        cells = [row[index] for row in body if index < len(row)]
        return all(re.fullmatch(r"[-$\\%\d.,\[\] a-z]*\d[-$\\%\d.,\[\] a-z]*",
                                c.replace("**", "").strip()) for c in cells if c)

    align = "l" + "".join("r" if numeric(i) else "l"
                          for i in range(1, len(header)))

    wide = len(header) > 4
    size = r"\footnotesize"

    # narrow tables stay exactly where the text puts them. Wider ones have to
    # span both columns, which means floating, so they carry a caption.
    if wide:
        out = [r"\begin{table*}[t]", r"\centering", size]
    else:
        # inline tables have only one column of width to live in, so the
        # padding between cells is tightened rather than the content cut
        out = [r"\begin{center}", size, r"\setlength{\tabcolsep}{4pt}"]
    out += [
           r"\begin{tabular}{" + align + "}", r"\toprule",
           " & ".join(escape(h) for h in header) + r" \\", r"\midrule"]
    out += [" & ".join(escape(c) for c in row) + r" \\" for row in body]
    out += [r"\bottomrule", r"\end{tabular}"]
    if wide:
        out += [r"\caption{" + escape(caption) + "}" if caption else "",
                r"\end{table*}"]
    else:
        out += [r"\end{center}"]
    return [line for line in out if line]


def unwrap_emphasis(markdown):
    """Pulls bold and italic runs onto one line.

    escape() works a line at a time, so a marker pair split across a line break
    never reaches it as a pair. Collapsing the run here keeps that conversion in
    markdown, before any LaTeX command exists for a stray asterisk to pair with.
    """
    def flatten(match):
        marker = "**" if match.group(0).startswith("**") else "*"
        return marker + " ".join(match.group(1).split()) + marker

    markdown = re.sub(r"\*\*([^*]+?)\*\*", flatten, markdown, flags=re.DOTALL)
    return re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", flatten, markdown, flags=re.DOTALL)


def convert(markdown):
    lines = unwrap_emphasis(markdown).splitlines()
    title = lines[0].lstrip("# ").strip()

    out, i, pending_caption = [], 1, None
    while i < len(lines):
        line = lines[i]
        if line.startswith("### "):
            out.append(r"\subsection*{" + escape(line[4:]) + "}")
        elif line.startswith("## "):
            out.append(r"\section*{" + escape(line[3:]) + "}")
            # the reference list drops a size and loses its paragraph indent
            # and spacing. Conventional, and it is what holds the paper to four
            # pages: at body size the last three entries spill onto a fifth.
            if line[3:].strip().lower() == "references":
                out.append(r"\footnotesize\setlength{\parindent}{0pt}"
                           r"\setlength{\parskip}{0.05em}")
        elif line.startswith("    ") and line.strip():
            block = []
            while i < len(lines) and (lines[i].startswith("    ") or not lines[i].strip()):
                block.append(lines[i][4:])
                i += 1
            while block and not block[-1].strip():
                block.pop()
            out += [r"\begin{quote}\small\begin{verbatim}"] + block + \
                   [r"\end{verbatim}\end{quote}"]
            continue
        elif line.startswith("Caption: "):
            pending_caption = line[len("Caption: "):]
        elif line.startswith("|"):
            block = []
            while i < len(lines) and lines[i].startswith("|"):
                block.append(lines[i])
                i += 1
            out += table(block, pending_caption)
            pending_caption = None
            continue
        else:
            out.append(escape(line) if line.strip() else "")
        i += 1

    return (PREAMBLE % title) + "\n".join(out) + "\n\n\\end{document}\n"


if __name__ == "__main__":
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    destination.write_text(convert(SOURCE.read_text()))
    print(f"wrote {destination}")
