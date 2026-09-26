## Decisions

* **Scoping the Question:** The broader question of synthetic enterprise data is too broad for a single week, so I isolated the foundational component a generator relies on: *If you construct a business process from a taxonomy and hand-written rules, how much real operational behavior do those rules actually capture?.
* **The Proxy Setup:** Using public 311 service feeds from four cities, I treated the service catalogue (job types and owning departments, with no timings) as a procedural generator's description of a business, and recorded durations as the client records.
* **The Blind Condition:** I pulled catalogs requesting only names and row counts, wrote rules blind to outcomes, committed predictions, and evaluated them. Austin and San Francisco each contain two rule sets: one authored by me and one by Claude Opus 5, whose prompts are reproduced verbatim in `prompts/`.

## Results

| Rule Set | Austin | San Francisco |
| --- | --- | --- |
| Mine | -1% | 46% |
| The Model | 29% | 72% |

* **Blind Rule Performance:** Performance varied sharply by city. By ticket AUC, the model-written rules recovered **72%** of the taxonomy ceiling in San Francisco, but human-written rules in Austin dropped to **0.494** (-1% recovered).
* **Permutation Null Tests:** Shuffling verdicts across categories to test the null hypothesis yielded a significant **$p = 0.0015$** in San Francisco (confirming real reasoning), but failed in Austin (**$p = 0.110$**, indistinguishable from a random cut of the taxonomy).
* **Real Records Win:** Fitted conditionals on real data outperformed the rules in both cities (by 0.108 in San Francisco and 0.272 in Austin).
* **The Published Target Baseline:** In New York, ranking tickets solely by the city's **published service target** (official target days per complaint type) reached **79% of the achievable margin** (0.830 AUC) instantly, matching rules written with real outcomes in hand, requiring zero reasoning or records.

## Limits

* **Evaluative Proxy Gap:** Every arm scores rules against a conditional fitted on real records rather than training a downstream model on generated data. Because the rules are a coarse approximation of that conditional, real records were structurally guaranteed to win.
* **Category Skew:** Results are heavily sensitive to volume distribution. Dropping San Francisco's top two categories (57% of volume) drops the model's recovered score to 27% and causes the permutation test to lose significance ($p = 0.1374$).
* **Reproducibility & Contamination:** The model-written arm produces the headline numbers. Its prompts and model version are now recorded, so the arm is reproducible, but public feeds leave open the possibility of benchmark memorization: blind means the author was shown no durations, not that its weights hold none.

## Next step

* **Make the Rules Generate:** Close the loop by sampling rows from the taxonomy and volume counts, labelling them with the prior, training a model on that synthetic dataset, and testing on real records to directly measure the cost of generated data.
* **Isolate Structure from Recall:** Prompts and versions are now logged. Re-score using opaque category IDs to cleanly separate structural reasoning from label memorization.
