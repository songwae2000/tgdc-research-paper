# Hypothesis, fixed before the experiment was run

## Question

Real operational records are produced by a process with hard constraints: a
housing agency does not receive noise complaints, a police precinct does not
repair boilers. A generator fitted to summary statistics sees those constraints
as strong correlations rather than as rules, and will happily emit a record
that the real process could never have produced.

## Hypothesis

**H.** Generated records matching real data to low-order fidelity (every
marginal, plus pairwise association: the bar SDV's Quality Score and the
NIST differential-privacy winners optimise) still contain a substantial
fraction of combinations that never occur in reality. An agent trained on
those records learns from relationships that cannot exist, and its accuracy on
real records falls as that impossible-combination rate rises.

## How it could fail

Three ways, any of which kills it:

1. Low-order fidelity might already produce almost no impossible combinations,
   in which case there is nothing to measure.
2. Impossible records might be harmless. A model can simply place little weight
   on combinations that never appear in the real test set, so the rate could
   rise with no loss of accuracy at all.
3. The loss might track something else entirely, such as how well the label
   conditional was preserved, with the impossible rate along for the ride.

Outcome 2 is the one worth watching. It would mean the thing real data
uniquely supplies here is not constraint structure, and that a generator is
free to emit nonsense records as long as its conditionals hold up.

## What this deliberately does not claim

That fidelity fails to imply downstream utility. That is established (Karr et
al. 2006; Snoke et al. 2018; Hansen et al. 2023) and is not the question here.
This asks a narrower one: *which* property of real data is doing the work.

## Design commitments, made in advance

- Every generator synthesises its own feature rows. No arm inherits real rows,
  because modelling co-occurrence is the thing under test.
- Train on synthetic, test on real (TSTR), with train-on-real (TRTR) as the
  ceiling.
- Train and test windows are complete, separate calendar weeks.
- Tickets still open are kept and treated as known-slow, since they are older
  than any threshold used here. Dropping them removes the slowest work.
- Every number is reported over 10 seeds with a bootstrap confidence interval.
  An arm whose skill is zero by construction is reported as zero.
