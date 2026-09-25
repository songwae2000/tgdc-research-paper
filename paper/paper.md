# What a domain prior can and cannot replace

## Abstract

Whether hand-written rules can stand in for a client's operational records when generating enterprise data is tested here on 311 tickets from four cities. Blind rules clear a structural null in San Francisco (p 0.0015) and
not in Austin (p 0.110), and a conditional fitted on the real data exceeds them
in both. Two cheaper references carry most of the signal: category volume alone scores 0.672 against 0.676 for the author-written rules, and a city's published service target recovers 79% of the achievable margin with no records at all. An agent benchmark built on generated tickets therefore tests a much weaker problem than it appears to.

## Introduction

Generated enterprise data is built from a description of a business rather than
from anyone's real records: an org chart, a list of the work, and hand-written
rules for how that work behaves. The appeal is that a client unable to share data
can still be served, and the open question is what that substitution costs.
Distributional fidelity is readily measured but is already established as a poor
guide to downstream usefulness, so the operative question is which properties of
real records the rules can supply and which must come from the client.

This study draws on public 311 service request feeds from four cities. Each
ticket is treated as a unit of work and the outcome of interest is time to
closure. A service catalogue lists job types and the departments that own them
with no timings attached, so it stands in for the description of a business,
while the recorded durations stand in for the client records a generator does
without.

## Hypothesis

The hypothesis under test is that rules reasoned from the nature of the work,
written without sight of any outcome, predict time to closure at an AUC between
0.60 and 0.72, and that any value below 0.55 would indicate that the reasoning
contributes nothing.

## Related work

That fidelity and utility can come apart is established. Karr et al. (2006) and Snoke et al. (2018) set out utility measures that rank generators differently [1, 2]; Hansen et al. (2023) report high fidelity
alongside poor downstream performance [3]; van Breugel et al. (2023) show that
models trained on synthetic data without care do not carry back to real data [4];
and Du and Li (2025) argue that the standard metrics may not measure the right thing [5]. That divergence is taken as given here rather than demonstrated.

The nearer literature treats language models as priors over tabular problems, of
which this study is a small instance. Knauer et al. (2025) induce a decision tree
from the target and the column names alone, with no rows and no labels [6], the move the model-written rules make here; Hegselmann et al. (2023) show with
TabLLM that column names carry zero-shot signal before any label [7]; and Capstick et al. (2025) score an elicited prior by marginal likelihood in AutoElicit, choosing between priors by Bayes factor [8], which needs no test split and is the procedure this study would adopt next time. Previous work is confined to classification where the target here is duration, and the first three require descriptive feature names, a precondition Knauer et al. state explicitly. A 311 taxonomy is unusually kind on that point;
an enterprise schema of coded columns would not be.

## Method

The records are written by the people who do the work. Each feed reports the work
type, the owning department, the intake channel, and the opening and closing
timestamps. The full weeks of 4 May and 8 June 2026 were taken from each city
(Table 1).

Caption: the four feeds, two complete weeks from each.
| city | train | test | median resolution | categories |
| --- | --- | --- | --- | --- |
| New York | 72,206 | 78,296 | 5.4h | 164 |
| Chicago | 17,291 | 38,671 | 118.0h | 92 |
| Austin | 5,968 | 6,029 | 23.8h | 117 |
| San Francisco | 17,723 | 17,007 | 15.1h | 37 |

Tickets still open at the time of extraction were retained and coded as slow,
since all lie months beyond any threshold; Chicago closes most of its feed within
a second of creation, and those rows were dropped as records rather than work.

The task is to predict, at the moment a ticket opens, whether closure will take
longer than the median. Let `A` denote the AUC attained by an arm and `C` the
ceiling AUC available from the same columns; recovered skill, reported alongside
AUC, is then `S = (A - 0.5) / (C - 0.5)`. The null tested is that the rules carry
no information about which work runs slow, so that any score they reach is
available from carving up the same taxonomy at random.

A ceiling is required for the denominator. Since a prior reads two columns, the
service category and the owning department, the conditional rate was fitted from
those same two to establish what they support. It is a taxonomy ceiling rather
than a general limit on skill, and it separates a weak rule from weak features.
The estimator was settled on after the first Austin arm had been scored against a
different one, so the AUCs reported here are pre-registered and the denominator
is not; every percentage sits beside its raw AUC.

Two kinds of interval are reported. Resampling tickets treats 17,007 San
Francisco rows as independent when the rules were written per category, so
categories were resampled as well [9]. That second unit carries two warnings. A
score is constant within a category only where the category has one owning
department, which holds throughout Austin but fails for 22 of San Francisco's 37
categories, 99.6% of its rows. Clustered resampling is also asymptotic in the
number of clusters and assumes rough balance, where one San Francisco category
holds 34% of the rows and the effective count is 5.3 against 37 categories,
Austin 22.3 against 117. Almost nothing could clear an interval that wide, so the
category intervals are read as descriptive rather than as tests; where a result
is described below as not established, the meaning is that this design cannot
establish it [10].

Each catalogue was pulled with the query limited to category names and row
counts, so no duration, rate or outcome reached the author. The rules were
written from that alone, committed with a prediction, and only then evaluated.
One San Francisco file was amended 27 seconds after commit, to match on word
boundaries rather than substrings, before that city's data existed on disk.

The principal risk is that the result describes the reasoning of a single author,
so Austin and San Francisco each carry two rule sets under the same blind
condition, one written by the author and one by a language model from the same
catalogue. New York serves as the contrast, written under sight of the real
rates, and Chicago as the transfer target for those rules.

## Results

### Blind prior recovery

Caption: what blind rules recover, by city and by author. Ticket intervals are 1,000 resamples, category intervals 2,000.
| city | rules | AUC | by ticket | by category | ceiling | recovered |
| --- | --- | --- | --- | --- | --- | --- |
| Austin | author | 0.494 | [0.481, 0.508] | [0.331, 0.649] | 0.883 | -1% |
| Austin | model | 0.611 | [0.598, 0.626] | [0.442, 0.770] | 0.883 | 29% |
| San Francisco | author | 0.676 | [0.670, 0.684] | [0.515, 0.815] | 0.886 | 46% |
| San Francisco | model | 0.777 | [0.770, 0.784] | [0.529, 0.859] | 0.886 | 72% |

The answer is not categorical (Table 2). The best blind rules recover 72% of the
taxonomy ceiling in San Francisco and the weakest recover nothing in Austin; a
single-city design would have supported a confident conclusion in either
direction, the city deciding which.

The two intervals disagree. By ticket, three of the four arms exceed chance; by
category, only the two San Francisco arms do, and Austin's model-written set
spans [0.442, 0.770], which is not distinguishable from guessing. The 72% spans
roughly 7% to 93% on that unit, and every claim below should be read at that
width.

### Gain over structure

A rule set may score well because it encodes reasoning, or because almost any
sensible cut of a lopsided taxonomy would; two controls separate the cases.

Caption: blind rules against two baselines built from structure alone, with category intervals and the permutation test of the null.
| city | arm | AUC | [95% CI] | recovered | p vs H0 |
| --- | --- | --- | --- | --- | --- |
| Austin | blind rules, per ticket | 0.611 | | 29% | |
| Austin | blind rules, per category | 0.617 | | | 0.110 |
| Austin | category frequency alone | 0.516 | [0.351, 0.726] | 4% | |
| Austin | same rules, verdicts shuffled | 0.501 | [0.322, 0.674] | 0% | |
| SF | blind rules, per ticket | 0.777 | | 72% | |
| SF | blind rules, per category | 0.741 | | | 0.0015 |
| SF | category frequency alone | 0.672 | [0.441, 0.785] | 45% | |
| SF | same rules, verdicts shuffled | 0.499 | [0.312, 0.690] | 0% | |

Shuffling the verdicts across categories preserves the taxonomy, the row counts
and the set of scores, and breaks only which category received which score; it
therefore draws from the null directly, so the share of shuffles reaching the
observed AUC is a permutation p-value (Table 3). The null assigns one verdict per
category, so the arm is scored on that unit as well, which is why the table
carries a second AUC for it. The rules reach 0.741 in San Francisco with 2 of
2,000 shuffles matching, p of 0.0015, and 0.617 in Austin with 220 matching, p of
0.110. The null is therefore rejected in San Francisco and not in Austin: the
reasoning does real work in one city and is not distinguishable from a lucky cut
of the taxonomy in the other.

Frequency is the harder baseline, because the pull supplied row counts and those
are themselves real operational data. Scored rarer-is-slower it reaches 0.672
against 0.676 for the author-written San Francisco rules, which therefore add
almost nothing beyond volume; the model-written rules clear it by 0.105. The
direction of that baseline is one bit the catalogue did not supply, so the
comparison is generous to it if anything.

### The author effect

The model-written rules exceed the author-written rules by 0.116 in Austin and
0.101 in San Francisco, the same direction at a similar magnitude in both cities.
By ticket, both differences exclude zero, at [0.104, 0.131] and [0.095, 0.107];
by category, neither does, at [-0.036, 0.288] and [-0.021, 0.174]. Two cities are
not sufficient, and an earlier draft reported these differences with no interval
at all.

### Pre-registered predictions

| arm | predicted | observed | in band |
| --- | --- | --- | --- |
| Austin, author | 0.60 to 0.72 | 0.494 | no |
| Austin, model | 0.52 to 0.62 | 0.611 | yes |
| SF, author | 0.55 to 0.68 | 0.676 | yes |
| SF, model | none | 0.777 | - |

The first band was set before the project had produced any result, and it was
wrong. The next two were set after Austin had been observed, so the expected
range was already known, a weaker achievement and counted as one. The fourth arm
produces the headline 72% and carries no prediction at all. The only prediction
made in genuine ignorance is the one that failed.

### One department

Caption: dropping the highest-volume categories in each city, for both sets of rules. The same operation run both ways.
| subset | rules | n | prior | ceiling | recovered |
| --- | --- | --- | --- | --- | --- |
| Austin, all | author | 6,029 | 0.494 | 0.883 | -1% |
| Austin, all | model | 6,029 | 0.611 | 0.883 | 29% |
| Austin, minus ARR | author | 4,008 | 0.644 | 0.881 | 38% |
| Austin, minus ARR | model | 4,008 | 0.766 | 0.881 | 70% |
| SF, all | author | 17,007 | 0.676 | 0.886 | 46% |
| SF, all | model | 17,007 | 0.777 | 0.886 | 72% |
| SF, minus top 2 | author | 7,255 | 0.571 | 0.851 | 20% |
| SF, minus top 2 | model | 7,255 | 0.595 | 0.851 | 27% |

Austin Resource Recovery (Table 4) accounts for 34% of the city's volume and 70%
of its work runs slow, yet both rule sets classify it as fast, 0.37 for the model
and 0.05 for the author. With the department removed, the model reaches 70%
against San Francisco's 72% and the author 38% against 46%, so the gap closes for
both. A missed collection remains open until the next scheduled route, a week
away: the work is routine while the ticket is not, and nothing in the phrase
ARR - Compost conveys this.

Applied to San Francisco, the same operation cuts the other way, which is the
more important half of the table. Its two largest categories are 57% of test
volume, both fast and both called fast. With them removed the ceiling barely
moves, 0.886 to 0.851, while the model falls from 72% to 27% and the author from
46% to 20%. A two-line rule calling those two fast and the rest slow scores 0.699
by itself, so the 72% rests on a few high-volume decisions rather than on 37
categories of reasoning.

ARR is a department prefix rather than a category called waste, so removing it
also takes out fast work it owns, such as ARR - Dead Animal Collection at 0.0%
slow. Graffiti Public accounts for 8.2% of San Francisco volume and is 85.1%
slow, yet is priced at 0.37 by the model; the failure ARR shows in Austin is
therefore present there too, and no subset here removes it.

### The real-data comparator

Given the same two columns, a conditional fitted on the real data exceeds the
blind rules by 0.108 in San Francisco and 0.272 in Austin, so real records win on
this task in both cities. Against a conditional using the category column alone
the rules appear level, 0.777 to 0.771, but that comparator lacks the department
column the rules read, which is worth 0.115 in San Francisco, and the 0.0067
margin has a paired interval of [-0.201, +0.108].

### The finding

The finding is stated as an ordering rather than a level, because the level moves
with the categories in the subset and the interval on it is wide. Blind rules
exceed chance in San Francisco and not in Austin; the model-written rules exceed
the author-written rules in both cities; and removing one administratively
clocked department closes most of the gap between the cities for both authors.

The explanation offered for that ordering, that a blind prior holds where
duration follows from the job and fails where the clock is an administrative
cycle, is a hypothesis rather than a result. The partition was derived from the
categories the author-written rules got wrong, in one city, so it cannot fail
against the data that produced it. The test that would settle it is set out in
the closing section.

### Value of the real rates

Caption: rules written with the rates in hand, those rules carried to another city, and the city's own published service target.
| rules | tested on | threshold | AUC | ceiling | recovered |
| --- | --- | --- | --- | --- | --- |
| New York | New York | 5.4h | 0.840 | 0.918 | 81% |
| NY rules carried | Chicago | 118.0h | 0.496 | 0.717 | -2% |
| NY rules carried | Chicago | 5.4h | 0.581 | 0.717 | 37% |
| published target | New York | 5.4h | 0.830 | 0.918 | 79% |

Rules written with a city's rates in hand reach 81% there, above the 72% a blind
author obtained in San Francisco but not by much.

The last row was not expected. New York publishes the target it holds itself to,
in days, per complaint type. Ranking tickets by that alone reaches 0.830, or 79%, matching rules written under sight of the real outcomes and needing no reasoning, no language model and no client records. Where a client publishes what they intend to take, that document is worth about as much as the exercise this paper measures, and is the first thing to ask for.

It bears on contamination too, since a language model may be recalling published material rather than reasoning. No equivalent dataset was found for Austin or San
Francisco, which narrows that concern without settling it.

Carried to Chicago at Chicago's own median the rules score 0.496, which an
earlier draft called actively misleading. That does not hold (Table 5): the
medians are 5.4h and 118.0h, so the carried row poses a question the rules were
not written for. At New York's own threshold they reach 0.581, or 37%. The
remaining shortfall is mechanical, since they fire on 17.1% of Chicago rows,
being New York acronyms.

### Distribution fidelity

The first recorded hypothesis, fixed in `HYPOTHESIS.md` before any run, was that
generated records matching real data to low-order fidelity would still hold
combinations the real process could never produce, and that accuracy would fall
as those rose. It was tested by fitting generators on real New York records,
sampling, training on the sample and testing on real records [11]. It failed, for
a structural reason. The pairwise generator draws department conditional on
category, so it cannot emit a pair it never saw and its 0.0% impossible rate is
an identity; the learner is additive over one-hot columns with no interaction
terms, so a wrong combination could not have hurt it either. Both were settled by
the design before any data was touched. The work moved to the narrower question
this paper answers, which is why the stated hypothesis and the pre-registration
are not the same sentence.

The ladder still shows the one thing it is here for. Marginals alone lose almost
everything, 0.511 against a 0.918 ceiling, while adding pairwise dependence
recovers all of it at 0.917. A generator clearing the column shapes and column
pair trends a quality report scores [12] is indistinguishable from real records
here, so a distribution-level check cannot see the effect this paper measures.
The generators used here are conditional probability tables with no privacy
noise, so they are not PrivBayes or MST, but the order of structure they keep is
the order those methods fit [13, 14].

## Limits

The design covers four cities, one domain and one task, of which only two are blind. New York is a contamination control and Chicago its transfer target,
so neither replicates anything, and what does replicate is an author effect whose
category intervals cross zero. A 311 feed offers three usable columns, no documents that must agree and no prices, so it is a thin stand-in for enterprise data.

The second author is a language model, which is the largest weakness. These feeds are widely mirrored, so blind here means the session was shown no durations, not that the weights hold none: language models memorise
popular tabular datasets and score better on ones they have seen [15], the exact
failure this arm admits, and it produces every headline number. Neither the
prompt nor the model version was recorded, so it cannot be rerun.

The Austin arm also has an ordering problem. The commit that evaluated the author-written rules names compost at 96%, traffic signal maintenance at 8% and vehicle abatement at 94%, all three called the wrong way. The model wrote its Austin rules twelve hours later, using the author's own phrasing as keyword strings, and got two of the three right. Compost it still called fast, which argues against wholesale transfer, but the prompt was not recorded and this cannot be settled. The blind condition covers the catalogue pull, not what had already been written down.

The San Francisco rules were written in knowledge of what Austin had shown, and the ARR result is a subset selected after observing which family the author-written rules got wrong, so it fits the numbers and nothing has tested it. New York carries known artefacts too, including a department that closes most tickets at exactly midnight.

## The general question

The first step is to make the rules generate. The arms reported here score rule
sets against a conditional fitted on real data, which measures how much of a conditional a person can guess, not what generated data costs. Sampling rows from the taxonomy and volume counts, labelling them with the
prior, then training on those and testing on real records would answer it
directly. The second is to predict the failures in advance: any category whose clock is an administrative cycle should break a blind prior, so such categories would be named in a fifth city from the taxonomy
alone, the list recorded, and the measurement taken after.

This bears on the evaluation of agents. Where a taxonomy and a published target
reach most of the achievable skill, an agent scored on tickets generated from that taxonomy is scored on the easiest part of the problem to reconstruct. The categories where a blind prior fails are invisible in the taxonomy the benchmark was built from, so a high score there is evidence about the generator rather than the agent.

A prior can be evaluated as a prior only once per dataset, before any outcome has
been seen, and the prediction must come first. Of the predictions recorded here,
the only one made in genuine ignorance is the one that proved wrong.

## References

[1] A. F. Karr, C. N. Kohnen, A. Oganian et al. A
framework for evaluating the utility of data altered to protect confidentiality.
*The American Statistician*, 60(3):224-232, 2006.



[2] J. Snoke, G. M. Raab, B. Nowok et al. General and
specific utility measures for synthetic data. *J. R. Stat. Soc. A*,
181(3):663-688, 2018.



[3] L. Hansen, N. Seedat, M. van der Schaar et al. Reimagining synthetic tabular
data generation through data-centric AI. In *NeurIPS Datasets and Benchmarks*,
2023.



[4] B. van Breugel, Z. Qian and M. van der Schaar. Synthetic data, real errors: how
(not) to publish and use synthetic data. In *ICML*, PMLR 202, 2023.



[5] Y. Du and N. Li. Systematic assessment of tabular data synthesis. In *ACM
CCS*, 2025.



[6] R. Knauer, M. Koddenbrock, R. Wallsberger et al. Zero-shot decision tree
induction and embedding with large language models. In *KDD*, 2025.



[7] S. Hegselmann, A. Buendia, H. Lang et al. TabLLM: few-shot classification of
tabular data with large language models. In *AISTATS*, PMLR 206, 2023.



[8] A. Capstick, R. G. Krishnan and P. Barnaghi. AutoElicit: LLMs for expert prior
elicitation in predictive modelling. In *ICML*, PMLR vol. 267, 2025.

[9] C. A. Field and A. H. Welsh. Bootstrapping clustered data. *J. R. Stat. Soc.
B*, 69(3):369-390, 2007.



[10] A. C. Cameron, J. B. Gelbach and D. L. Miller. Bootstrap-based improvements for
inference with clustered errors. *Rev. Econ. Stat.*, 90(3):414-427, 2008.



[11] C. Esteban, S. L. Hyland and G. Rätsch. Real-valued (medical) time series
generation with recurrent conditional GANs. arXiv:1706.02633, 2017.



[12] SDV Team. Quality report: column shapes and column pair trends. SDMetrics
docs.sdv.dev/sdmetrics, accessed 24 Sep 2026.



[13] J. Zhang, G. Cormode, C. M. Procopiuc et al. PrivBayes: private data release
via Bayesian networks. *ACM Trans. Database Syst.*, 42(4):25, 2017.



[14] R. McKenna, G. Miklau and D. Sheldon. Winning the NIST contest. *J. Privacy and
Confidentiality*, 11(3), 2021.



[15] S. Bordt, H. Nori, V. Rodrigues et al. Elephants never forget: memorization of
tabular data in large language models. In *COLM*, 2024.
