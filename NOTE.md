# Note

Paper: `main.pdf`. This repository is the experiment as well, and `python
run_all.py` prints every figure the paper quotes.

## Decisions

"When does real operational data beat generated data" is too big for a week, so
I took the part a generator has to solve. If you build a client's data from a
taxonomy and hand-written rules, how much of the behaviour do the rules supply?
Behaviour here is one property, how long a job takes.

I used public 311 feeds from four cities. A service catalogue lists job types
and owners with no timings, which is what a procedural generator starts from.
The recorded durations are the client records it does without. I pulled each
catalogue requesting only names and row counts, wrote rules from that alone,
committed them with a recorded prediction, then evaluated. Austin and San
Francisco have two rule sets each, mine and a language model's, because the
first version had one author and the result turned out to be about me as much as
the method.

## Results

| rule set | Austin | San Francisco |
| --- | --- | --- |
| mine | -1% | 46% |
| the model | 29% | 72% |

Shuffling the rules' verdicts across categories tests the null that they carry
no information. San Francisco gives p of 0.0015 and Austin 0.110, so the
reasoning does real work in one city and not in the other.

An earlier draft claimed something sharper: blind rules at 0.777 against 0.771
for a conditional fitted on the real data. I withdrew it. That comparator read
one column where the rules read two, and the department is worth 0.115 in San
Francisco. Given the same two columns real records win in both cities, by 0.108
here and 0.272 in Austin.

The cheapest baseline is the one that matters. New York publishes the target it
holds itself to, per complaint type. Ranking tickets by that alone reaches 79%,
matching rules written while looking at the real outcomes, with no reasoning and
no records. If a client publishes what they intend to take, ask for that first.

Three of the four rule sets carry a prediction recorded before scoring. The one
producing the 72% does not, and the only prediction made in genuine ignorance is
the one that failed.

## Limits

Four of these cost me a finding.

The 72% is carried by two categories, 57% of San Francisco volume, both fast and
both called fast. Drop them and the model falls to 27% and I fall to 20% against
a ceiling that barely moves. Resampling categories rather than tickets widens
the headline to 7% to 93%, on an effective cluster count of 5.3, so those
intervals are too wide to read as tests. The Chicago transfer failure was mostly
a 22-fold threshold gap, and at New York's own threshold the carried rules reach
37%, not the -2% I first reported. The fidelity ladder's one discriminating arm
reversed when I fixed a labelling bug, so it is gone.

The row counts the pull supplied are themselves real operational data, and
scoring by them alone reaches 0.672 against my 0.676. The language model cannot
be blind to feeds this widely mirrored, and I recorded no prompt or version. The
ARR explanation is a subset chosen after seeing the gap, so it cannot fail
against the data that produced it. And I had written three Austin slow rates
down before the model was asked, and it got two of them right.

## Next step

Make the rules generate. Sample rows from the taxonomy and volume counts, label
them with the rules, train on that and test on real records. That turns a share
of a margin into the number the question asks for: how much of the training
value of real records does a generator built without them deliver?

Then one control, under a day. Replace category names with opaque IDs and
re-score, which separates structural reasoning from label recall. The other
control I planned is the 79% above.
