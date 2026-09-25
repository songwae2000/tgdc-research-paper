# One pager: decisions, results, limits, next step

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
catalogue requesting only names and row counts, wrote the rules from that alone,
committed them with a prediction, then evaluated. Austin and San Francisco have
two rule sets each, mine and a language model's, because the first version had
one author and the result was about me as much as the method.

## Results

| rule set | Austin | San Francisco |
| --- | --- | --- |
| mine | -1% | 46% |
| the model | 29% | 72% |

Shuffling the rules' verdicts across categories tests the null that they carry
no information. San Francisco gives p 0.0015 and Austin 0.110, so the reasoning
does real work in one city and not in the other.

Given the same two columns, real records win in both cities, by 0.108 in San
Francisco and 0.272 in Austin. I withdrew an earlier claim that the rules drew
level: that comparator read one column where the rules read two.

The cheapest baseline is the one that matters. New York publishes the target it
holds itself to, per complaint type. Ranking tickets by that alone reaches 79%,
matching rules written while looking at the real outcomes, with no reasoning and
no records. If a client publishes what they intend to take, ask for that first.

The only prediction I made in genuine ignorance is the one that failed.

## Limits

Five of these cost me a finding.

No table here trains on generated data. Every arm scores hand-written rules
against a conditional fitted on real records, and that conditional reads the
same two columns the rules read. The rules are a coarse version of what it fits
properly, so real records were always going to win. The one arm that does use
generated rows is null by construction.

The 72% comes from the weakest arm. The model recorded no prediction, no prompt
and no version, on feeds it has very likely seen. Its own file puts the San
Francisco median at "roughly a day" when it is 15.1h, a number it should not
have had a view on at all. It also wrote its Austin rules twelve hours after I
wrote three slow rates down in my own phrasing, and got two of the three right.

Two categories, 57% of San Francisco volume, carry that 72%. Drop them and the
model falls to 27%, I fall to 20%, and the permutation test stops rejecting, at
p 0.1374 against 0.0015 for the whole city. Resampling categories rather than
tickets puts the headline between 7% and 93%.

Frequency alone scores 0.672 against my 0.676. The Chicago transfer failure was
mostly a 22-fold threshold gap, and at New York's own threshold the carried
rules reach 37%, not the -2% I first reported. The fidelity ladder's one
discriminating arm reversed when I fixed a labelling bug, so it is gone. ARR is
a subset I picked after seeing the gap, though on that subset the null does
reject, at p 0.0025.

## Next step

Make the rules generate. Sample rows from the taxonomy and the volume counts,
label them with the rules, train on that and test on real records. Nothing here
measures that, and it is the number the question actually asks for.

Then two things, both a day. Re-run the model arm with the prompt and version
recorded, because every headline number rests on an arm nobody can reproduce.
And re-score with category names replaced by opaque IDs, which separates
structural reasoning from label recall.
