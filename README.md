# What a domain prior can and cannot replace

Can hand-written domain rules replace a client's operational records when
generating enterprise data? This tests it on 311 service tickets from four
cities, and the answer turns out to depend on the client.

Written for the TGDC case study, research track. The paper is `main.pdf`, four
pages. Everything it reports is printed by `python run_all.py` in this
repository.

## Run it

    pip install -r requirements.txt
    python run_all.py

Four public 311 feeds, no key, no account, no cost. numpy and scikit-learn are
the only dependencies. The first run downloads about 60MB. Later runs read from
disk and take under two minutes, most of it bootstrap resampling.

It prints every table the paper quotes, in order.

## The result

Priors written blind, from a city's service catalogue alone, recover this much
of the achievable skill:

| author | Austin | San Francisco |
| --- | --- | --- |
| the experimenter | -1% | 46% |
| a language model | 29% | 72% |

Both authors score far lower in Austin, and one department's work accounts for
most of the gap. Austin Resource Recovery is a third of the city's volume and
70% of its work runs slow, because a missed collection stays open until the next
scheduled route. The work is routine. The ticket is not.

So a blind prior works on work whose duration follows from the job, and fails on
work whose clock is an administrative cycle. Which of those a client has is not
visible in their taxonomy.

Two controls decide how much of that is reasoning. Shuffling the same rules'
verdicts across categories, which holds the taxonomy and the row counts and
destroys only the reasoning, scores 0.501: the reasoning is doing the work.
Scoring by category row count alone reaches 0.672 in San Francisco against the
experimenter's 0.676, so that arm adds almost nothing beyond volume.

The cheapest baseline is the most useful one. New York publishes the target it
holds itself to, per complaint type. Ranking tickets by that alone recovers 79%,
matching rules written while looking at the real outcomes, with no reasoning and
no records at all. If a client publishes what they intend to take, ask for that
first.

Intervals resampled by category rather than by ticket are wide. The 72% spans
roughly 7% to 93%, and the author effect crosses zero in both cities.

## How blindness was enforced

Each city's taxonomy was pulled with the query restricted to category names and
row counts, so no duration, rate or outcome was available to the author. Rules
were written, committed with a recorded prediction, and only then evaluated.

Austin and San Francisco each have two authors under that condition, because the
first draft of this work had one and the result turned out to be partly about
him. The second author is a language model, which is disclosed in the paper and
is the design's largest uncontrolled channel: these feeds are widely mirrored,
so blind means it was shown no durations, not that it holds none. New York has a
single, deliberately non-blind prior, and Chicago has none.

## Layout

- `run_all.py` prints every figure in the paper.
- `paper/paper.md` is the source of record for the text. `main.tex` is generated
  from it and `main.pdf` is built from that.
- `src/*_prior.py` and `src/*_prior_llm.py` are the blind priors, one file per
  author per city. Each carries its reasoning and its recorded prediction.
- `src/nyc_prior.py` is the contrast case, written with the site's rates in hand.
- `src/sla.py` is the published service target baseline.
- `src/tickets.py` loads any of the four feeds into one shape.
- `src/generators.py` is the fidelity ladder: marginal, pairwise, joint.
- `src/stats.py` is bootstrap intervals and the information ceiling.
- `HYPOTHESIS.md` is the hypothesis as fixed before the first experiment ran,
  including the three ways it could fail. One of them happened.
- `ONE_PAGER.md` is the one-page note: decisions, results, limits, next step.

## Checks

    python scripts/check_paper.py <(python run_all.py)
    python scripts/check_build.py

`check_paper.py` walks every table cell in the paper and fails if a number
appears there that the run did not print. It exists because two figures once
reached a draft without being computed.

`check_build.py` fails if the committed PDF is older than the LaTeX, or the
LaTeX older than the markdown. It exists because the paper once shipped seven
commits behind its own source, back when the text and the experiment lived in
separate repositories. They no longer do.

`data/MANIFEST.json` records the row count and hash of each file the paper was
computed from. The feeds are live, so `run_all.py` reports any disagreement
before printing a figure, and a reviewer whose numbers differ can tell whether
the data moved or the code did.
