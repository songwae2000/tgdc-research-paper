"""Reproduces every number in paper/paper.md.

Usage: python run_all.py

Downloads four 311 feeds on first run, then reruns from disk.
"""

import random

import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from src import cities, manifest, sla, stats, tickets
from src.austin_prior import PREDICTED_RANGE as AUSTIN_HUMAN_BAND
from src.austin_prior import prior_slow_probability as austin_human
from src.austin_prior_llm import PREDICTED_RANGE as AUSTIN_LLM_BAND
from src.austin_prior_llm import prior_slow_probability as austin_llm
from src.generators import GENERATORS
from src.nyc_prior import prior_slow_probability as nyc_prior
from src.sf_prior import PREDICTED_RANGE as SF_HUMAN_BAND
from src.sf_prior import prior_slow_probability as sf_human
from src.sf_prior_llm import prior_slow_probability as sf_llm

# Austin Resource Recovery, the department that owns kerbside collection. This
# is a department prefix on the category name, not a category called "waste",
# so excluding it removes everything ARR owns, fast work included.
ARR = "ARR"
COLUMNS = ("category", "department")


def heading(text):
    print(f"\n\n{text}\n{'=' * len(text)}\n")


def prepared(city):
    train, test = tickets.load(city, "train"), tickets.load(city, "test")
    threshold = tickets.median_hours(train)
    train_f, train_y = tickets.split(train, threshold)
    test_f, test_y = tickets.split(test, threshold)
    return train_f, train_y, test_f, test_y, threshold


def ceiling_from_columns(train_f, train_y, test_f, test_y):
    """A strong reference for what these two columns support.

    The conditional rate fitted on train and applied to test. Not a proved upper
    bound: it is one unregularised estimator, and a rule can beat it.
    """
    return roc_auc_score(test_y, stats.conditional_lookup(train_f, train_y,
                                                          test_f, COLUMNS))


def score_prior(prior, test_f):
    return [prior(f["category"], f["department"]) for f in test_f]


def categories_of(test_f):
    return [f["category"] for f in test_f]


def prior_by_category(prior, test_f):
    """The verdict the rules hand each category, averaged over its rows."""
    by = {}
    for f, p in zip(test_f, score_prior(prior, test_f)):
        by.setdefault(f["category"], []).append(p)
    return {c: float(np.mean(v)) for c, v in by.items()}


def recovered(auc, top):
    return (auc - 0.5) / (top - 0.5)


def main():
    print("data")
    for city in cities.ALL:
        tickets.ensure(city)

    drift = manifest.check()
    if drift:
        print("\n  WARNING: the feeds have moved since the paper was written.")
        for note in drift:
            print(f"    {note}")
        print("  Figures below will differ from the paper by that much.")
    else:
        print("  data matches the manifest the paper was computed from")

    loaded = {city.name: prepared(city) for city in cities.ALL}
    print(f"\n  {'city':<16}{'train':>8}{'test':>8}{'median':>9}{'categories':>12}")
    for city in cities.ALL:
        train_f, _, test_f, _, threshold = loaded[city.name]
        cats = len({f["category"] for f in test_f})
        print(f"  {city.name:<16}{len(train_f):>8}{len(test_f):>8}"
              f"{threshold:>8.1f}h{cats:>12}")

    heading("TABLE 1: blind priors, two authors, two cities")
    print(f"  {'city':<16}{'author':<14}{'AUC':>7}{'by ticket':>18}"
          f"{'by category':>18}{'ceiling':>9}{'recovered':>11}{'vs chance':>20}")

    blind = ((cities.AUSTIN, "human", austin_human),
             (cities.AUSTIN, "independent", austin_llm),
             (cities.SF, "human", sf_human),
             (cities.SF, "independent", sf_llm))
    observed = {}
    for city, author, prior in blind:
        train_f, train_y, test_f, test_y, _ = loaded[city.name]
        top = ceiling_from_columns(train_f, train_y, test_f, test_y)
        scores = score_prior(prior, test_f)
        auc, lo, hi = stats.auc_interval(test_y, scores)
        _, clo, chi = stats.auc_interval_clustered(test_y, scores,
                                                   categories_of(test_f))
        observed[(city.name, author)] = (auc, recovered(auc, top), top, scores)
        print(f"  {city.name:<16}{author:<14}{auc:>7.3f}"
              f"{f'[{lo:.3f}, {hi:.3f}]':>18}{f'[{clo:.3f}, {chi:.3f}]':>18}"
              f"{top:>9.3f}{recovered(auc, top):>10.0%}"
              f"{stats.versus_chance(clo, chi):>20}")

    print("\n  Two resampling units. By ticket is 1,000 draws over rows. By")
    print("  category is 2,000 draws over whole categories, which is the unit a")
    print("  rule set is constant within, and the one the verdict column uses.")
    print("  Under clustering the headline 72% spans roughly 7% to 93%.")

    heading("TABLE 2: what the rules add over structure alone")
    print(f"  {'city':<16}{'arm':<26}{'AUC':>7}{'[95% CI]':>18}{'recovered':>11}")
    for city, author in ((cities.AUSTIN, "independent"), (cities.SF, "independent")):
        train_f, train_y, test_f, test_y, _ = loaded[city.name]
        auc, _, top, _ = observed[(city.name, author)]
        cats = categories_of(test_f)

        counts = {}
        for f in train_f:
            counts[f["category"]] = counts.get(f["category"], 0) + 1
        rare = [-counts.get(c, 0) for c in cats]
        f_auc, f_lo, f_hi = stats.auc_interval_clustered(test_y, rare, cats)

        rules = austin_llm if city is cities.AUSTIN else sf_llm
        verdicts = prior_by_category(rules, test_f)
        # the null shuffles one verdict per category, so the observed arm has
        # to be scored on that same per-category vector. Passing the per-ticket
        # AUC would compare two different statistics, and the prior also reads
        # department, so the two are not equal.
        observed_by_cat = roc_auc_score(test_y, [verdicts[c] for c in cats])
        p_auc, p_lo, p_hi, pval = stats.permutation_test(verdicts, cats,
                                                         test_y, observed_by_cat)

        for label, a, lo, hi in (
                ("blind rules, independent", auc, None, None),
                ("category frequency alone", f_auc, f_lo, f_hi),
                ("same rules, verdicts shuffled", p_auc, p_lo, p_hi)):
            span = f"[{lo:.3f}, {hi:.3f}]" if lo is not None else ""
            print(f"  {city.name:<16}{label:<26}{a:>7.3f}{span:>18}"
                  f"{recovered(a, top):>11.0%}")
        print(f"  {'':<16}permutation test of H0: p {'<' if pval <= 1/2001 else '='} "
              f"{max(pval, 1/2001):.4f}  "
              f"({int(round(pval * 2001)) - 1} of 2,000 shuffles reached "
              f"{observed_by_cat:.3f}, the arm scored per category)")
        print()

    print("  H0: the rules carry no information about which category runs slow.")
    print("  Shuffling verdicts across categories draws from that null directly,")
    print("  holding the taxonomy, the row counts and the exact multiset of")
    print("  verdicts, and breaking only which category got which verdict.")
    print("  Frequency alone uses only the row counts the blind pull supplied,")
    print("  scored rarer-is-slower. Choosing that direction is one bit the")
    print("  catalogue did not give, so the baseline is if anything generous.")

    heading("TABLE 3: the author effect, as a paired difference")
    print(f"  {'city':<16}{'independent minus human':>24}{'by ticket':>20}"
          f"{'by category':>20}")
    crosses = []
    for city in (cities.AUSTIN, cities.SF):
        _, _, test_f, test_y, _ = loaded[city.name]
        _, _, _, human = observed[(city.name, "human")]
        _, _, _, indep = observed[(city.name, "independent")]
        cats = categories_of(test_f)
        diff, lo, hi = stats.auc_difference(test_y, indep, human)
        _, clo, chi = stats.auc_difference_clustered(test_y, indep, human, cats)
        crosses.append(clo <= 0 <= chi)
        print(f"  {city.name:<16}{diff:>+24.3f}{f'[{lo:+.3f}, {hi:+.3f}]':>20}"
              f"{f'[{clo:+.3f}, {chi:+.3f}]':>20}")

    print("\n  Paired on the same resample, so the two arms share noise.")
    if all(crosses):
        print("  By category both differences cross zero, so the author effect is")
        print("  suggestive and not established by two cities.")
    elif any(crosses):
        print("  By category one difference crosses zero and one does not, so the")
        print("  author effect holds in one city and is not established in both.")
    else:
        print("  By category both differences still exclude zero, so the author")
        print("  effect survives the resampling unit that the arms are constant in.")

    heading("TABLE 4: predictions recorded before evaluation")
    print(f"  {'arm':<34}{'predicted':>14}{'observed':>10}{'inside band':>14}")
    for label, band, auc in (
            ("Austin, human", AUSTIN_HUMAN_BAND, observed[("Austin", "human")][0]),
            ("Austin, independent", AUSTIN_LLM_BAND, observed[("Austin", "independent")][0]),
            ("San Francisco, human", SF_HUMAN_BAND, observed[("San Francisco", "human")][0])):
        inside = "yes" if band[0] <= auc <= band[1] else "NO"
        print(f"  {label:<34}{f'{band[0]:.2f} to {band[1]:.2f}':>14}"
              f"{auc:>10.3f}{inside:>14}")
    print(f"  {'San Francisco, independent':<34}{'none recorded':>14}"
          f"{observed[('San Francisco', 'independent')][0]:>10.3f}{'-':>14}")

    print("\n  The fourth arm produces the headline 72% and carries no recorded")
    print("  prediction. The first was set before the project had any result.")

    heading("TABLE 4b: what the prior beats, and what carries it")
    print(f"  {'city':<16}{'reference':<40}{'AUC':>8}")
    for city, rules_h, rules_m in ((cities.AUSTIN, austin_human, austin_llm),
                                   (cities.SF, sf_human, sf_llm)):
        tr_f, tr_y, te_f, te_y, _ = loaded[city.name]
        cat_only = roc_auc_score(te_y, stats.conditional_lookup(
            tr_f, tr_y, te_f, ("category",)))
        both = ceiling_from_columns(tr_f, tr_y, te_f, te_y)
        print(f"  {city.name:<16}{'conditional fitted on real data, category only':<40}"
              f"{cat_only:>8.3f}")
        print(f"  {city.name:<16}{'conditional on real data, both columns':<40}"
              f"{both:>8.3f}")
        print(f"  {city.name:<16}{'blind rules, the model':<40}"
              f"{observed[(city.name, 'independent')][0]:>8.3f}")
        print(f"  {city.name:<16}{'blind rules, mine':<40}"
              f"{observed[(city.name, 'human')][0]:>8.3f}")
        eff = stats.effective_clusters(categories_of(te_f))
        print(f"  {city.name:<16}{'categories / effective clusters':<40}"
              f"{len({f['category'] for f in te_f}):>4} /{eff:>4.1f}")
        print()

    print("  The category-only row is not a fair comparator for the rules, which")
    print("  read the department too. Like for like, against the two-column")
    print("  conditional, the fitted model wins in both cities:")
    for city, rules in ((cities.AUSTIN, austin_llm), (cities.SF, sf_llm)):
        tr_f, tr_y, te_f, te_y, _ = loaded[city.name]
        cats = categories_of(te_f)
        cat_only = stats.conditional_lookup(tr_f, tr_y, te_f, ("category",))
        both = ceiling_from_columns(tr_f, tr_y, te_f, te_y)
        arm = score_prior(rules, te_f)
        gap = both - roc_auc_score(te_y, arm)
        d, lo, hi = stats.auc_difference_clustered(te_y, arm, cat_only, cats)
        print(f"    {city.name:<16}two-column conditional beats the rules by "
              f"{gap:+.3f}")
        print(f"    {'':<16}rules minus category-only {d:+.4f} "
              f"[{lo:+.3f}, {hi:+.3f}] by category")
    print("\n  The effective cluster count is what the category bootstrap is")
    print("  really working with, and it is far below the number of categories,")
    print("  so those intervals are descriptive and not tests.")

    heading("TABLE 4c: is a prior constant within a category?")
    print("  The category bootstrap assumes it is. A prior also reads the")
    print("  department, so it holds only where a category has one owner.")
    print(f"  {'city':<16}{'rules':<10}{'multi-valued':>14}{'of rows':>10}")
    for city, pair in ((cities.AUSTIN, (("mine", austin_human), ("the model", austin_llm))),
                       (cities.SF, (("mine", sf_human), ("the model", sf_llm)))):
        _, _, te_f, _, _ = loaded[city.name]
        for who, prior in pair:
            by, rows = {}, {}
            for f in te_f:
                by.setdefault(f["category"], set()).add(
                    prior(f["category"], f["department"]))
                rows[f["category"]] = rows.get(f["category"], 0) + 1
            multi = [c for c, v in by.items() if len(v) > 1]
            share = sum(rows[c] for c in multi) / len(te_f)
            print(f"  {city.name:<16}{who:<10}{f'{len(multi)} of {len(by)}':>14}"
                  f"{share:>9.1%}")
    print("\n  It holds throughout Austin and fails for most of San Francisco,")
    print("  which is where the headline sits. The clustered interval is still")
    print("  the better of the two units, but it is an approximation.")

    heading("TABLE 4d: the three Austin categories named before the model wrote")
    print("  Commit 4400226 evaluated my own Austin rules and named these three")
    print("  with their measured rates. The model's rules came twelve hours on.")
    train_f, train_y, test_f, test_y, _ = loaded["Austin"]
    named = ("Compost", "Signal - Maintenance", "Vehicle Abatement Report")
    print(f"  {'category':<38}{'n':>6}{'slow':>7}{'mine':>7}{'model':>7}")
    for needle in named:
        rows = [(f, y) for f, y in zip(test_f, test_y) if needle.lower() in f["category"].lower()]
        if not rows:
            continue
        cat = rows[0][0]["category"]
        slow = np.mean([y for _, y in rows])
        h = np.mean([austin_human(f["category"], f["department"]) for f, _ in rows])
        m = np.mean([austin_llm(f["category"], f["department"]) for f, _ in rows])
        print(f"  {cat:<38}{len(rows):>6}{slow:>6.0%}{h:>7.2f}{m:>7.2f}")

    heading("TABLE 5: removing the highest-volume categories, both cities")
    for city, prior_h, prior_m, drop_n in ((cities.AUSTIN, austin_human, austin_llm, None),
                                           (cities.SF, sf_human, sf_llm, 2)):
        tr_f, tr_y, te_f, te_y, _ = loaded[city.name]
        counts = {}
        for f in te_f:
            counts[f["category"]] = counts.get(f["category"], 0) + 1
        if drop_n is None:
            drop = {c for c in counts if c.upper().startswith(ARR)}
            label = "excluding all ARR categories"
        else:
            drop = {c for c, _ in sorted(counts.items(), key=lambda kv: -kv[1])[:drop_n]}
            label = f"excluding the top {drop_n} categories"
        keep_f = [f for f in te_f if f["category"] not in drop]
        keep_y = [y for f, y in zip(te_f, te_y) if f["category"] not in drop]
        share = 1 - len(keep_f) / len(te_f)
        print(f"  {city.name}: {label}, {share:.0%} of volume")
        print(f"    {'subset':<34}{'rules':<10}{'n':>7}{'prior':>8}"
              f"{'ceiling':>9}{'recovered':>11}")
        for sub_label, feats, ys in (("all tickets", te_f, te_y),
                                     (label, keep_f, keep_y)):
            top = ceiling_from_columns(tr_f, tr_y, feats, ys)
            for who, prior in (("mine", prior_h), ("the model", prior_m)):
                a = roc_auc_score(ys, score_prior(prior, feats))
                print(f"    {sub_label:<34}{who:<10}{len(feats):>7}{a:>8.3f}"
                      f"{top:>9.3f}{recovered(a, top):>11.0%}")
        print()

    print("  Austin loses the department whose clock is administrative and the")
    print("  prior improves. San Francisco loses its two largest categories and")
    print("  the prior collapses. The same operation, run both ways, because")
    print("  running it only where it helps is not an analysis.")
    simple = {}
    for city, prior in ((cities.SF, sf_llm),):
        _, _, te_f, te_y, _ = loaded[city.name]
        counts = {}
        for f in te_f:
            counts[f["category"]] = counts.get(f["category"], 0) + 1
        top2 = {c for c, _ in sorted(counts.items(), key=lambda kv: -kv[1])[:2]}
        rule = [0.0 if f["category"] in top2 else 1.0 for f in te_f]
        simple[city.name] = roc_auc_score(te_y, rule)
        print(f"  A two-line rule, '{' and '.join(sorted(top2))} are fast,")
        print(f"  everything else slow', scores {simple[city.name]:.3f} in San Francisco")
        print("  on its own.")

    heading("TABLE 5c: what sits inside those subsets")
    train_f, train_y, test_f, test_y, _ = loaded["Austin"]
    owned = [f["category"].upper().startswith(ARR) for f in test_f]
    owned_y = [y for y, w in zip(test_y, owned) if w]
    print(f"  ARR is {sum(owned) / len(test_f):.0%} of Austin volume and "
          f"{np.mean(owned_y):.0%} of it runs slow.")
    for who, prior in (("mine", austin_human), ("the model", austin_llm)):
        vals = [p for p, w in zip(score_prior(prior, test_f), owned) if w]
        print(f"    mean prediction on ARR, {who:<12}{np.mean(vals):>6.2f}")

    print("\n  ARR is a department, so this removes fast work it owns as well as")
    print("  slow. The three fastest ARR categories, by slow rate:")
    by_cat = {}
    for f, y in zip(test_f, test_y):
        if f["category"].upper().startswith(ARR):
            by_cat.setdefault(f["category"], []).append(y)
    for cat, ys in sorted(by_cat.items(), key=lambda kv: np.mean(kv[1]))[:3]:
        print(f"    {cat:<38}n={len(ys):>5}  slow {np.mean(ys):>5.1%}")

    sf_train_f, sf_train_y, sf_test_f, sf_test_y, _ = loaded["San Francisco"]
    print("\n  San Francisco categories over 2% of volume, by how far the rules")
    print("  underprice them:")
    sf_by = {}
    for f, y in zip(sf_test_f, sf_test_y):
        sf_by.setdefault(f["category"], []).append(y)
    priced_m = prior_by_category(sf_llm, sf_test_f)
    priced_h = prior_by_category(sf_human, sf_test_f)
    gaps = [(c, len(v) / len(sf_test_f), float(np.mean(v)), priced_m[c], priced_h[c])
            for c, v in sf_by.items() if len(v) / len(sf_test_f) > 0.02]
    print(f"    {'category':<26}{'volume':>8}{'slow':>8}{'model':>8}{'mine':>8}")
    for cat, share, slow, pm, ph in sorted(gaps, key=lambda g: g[3] - g[2])[:2]:
        print(f"    {cat:<26}{share:>7.1%}{slow:>8.1%}{pm:>8.2f}{ph:>8.2f}")

    heading("TABLE 6: how concentrated each city is, and where the prior misreads it")
    print(f"  {'city':<16}{'categories':>12}{'top 5 share':>13}"
          f"{'volume in wrong-direction categories':>38}")
    for city, prior in ((cities.AUSTIN, austin_llm), (cities.SF, sf_llm)):
        _, _, feats, ys, _ = loaded[city.name]
        by = {}
        for f, y in zip(feats, ys):
            by.setdefault(f["category"], []).append(
                (y, prior(f["category"], f["department"])))
        ranked = sorted(by.values(), key=len, reverse=True)
        top5 = sum(len(v) for v in ranked[:5]) / len(feats)
        wrong = sum(len(v) for v in by.values()
                    if (np.mean([p for _, p in v]) > 0.5)
                    != (np.mean([y for y, _ in v]) > 0.5))
        print(f"  {city.name:<16}{len(by):>12}{top5:>12.0%}{wrong / len(feats):>37.0%}")

    print("\n  Wrong-direction compares mean prediction against mean outcome, so")
    print("  it is a calibration count. AUC depends on ranking, and a category")
    print("  can be miscalibrated and still ranked correctly.")

    heading("TABLE 7: the same procedure with the site's rates in hand")
    print(f"  {'prior':<18}{'tested on':<14}{'threshold':>11}{'AUC':>7}"
          f"{'[95% CI]':>18}{'ceiling':>9}{'recovered':>11}")
    for tested in ("New York", "Chicago"):
        train_f, train_y, test_f, test_y, threshold = loaded[tested]
        top = ceiling_from_columns(train_f, train_y, test_f, test_y)
        scores = score_prior(nyc_prior, test_f)
        auc, lo, hi = stats.auc_interval(test_y, scores)
        label = "New York" if tested == "New York" else "NY rules carried"
        print(f"  {label:<18}{tested:<14}{threshold:>10.1f}h{auc:>7.3f}"
              f"{f'[{lo:.3f}, {hi:.3f}]':>18}{top:>9.3f}{recovered(auc, top):>11.0%}")

    ny_threshold = loaded["New York"][4]
    chi_rows = tickets.load(cities.CHICAGO, "test")
    chi_f, chi_y = tickets.split(chi_rows, ny_threshold)
    chi_train_f, chi_train_y = tickets.split(
        tickets.load(cities.CHICAGO, "train"), ny_threshold)
    top = ceiling_from_columns(chi_train_f, chi_train_y, chi_f, chi_y)
    auc = roc_auc_score(chi_y, score_prior(nyc_prior, chi_f))
    matched_share = recovered(auc, top)
    print(f"  {'NY rules carried':<18}{'Chicago':<14}{ny_threshold:>10.1f}h"
          f"{auc:>7.3f}{'':>18}{top:>9.3f}{matched_share:>11.0%}")

    targets = sla.target_hours()
    ny_train_f, ny_train_y, ny_test_f, ny_test_y, _ = loaded["New York"]
    ny_top = ceiling_from_columns(ny_train_f, ny_train_y, ny_test_f, ny_test_y)
    sla_auc = roc_auc_score(ny_test_y, sla.score(ny_test_f, targets))
    print(f"  {'published target':<18}{'New York':<14}{'':>11}{sla_auc:>7.3f}"
          f"{'':>18}{ny_top:>9.3f}{recovered(sla_auc, ny_top):>11.0%}")

    matched = np.mean([abs(nyc_prior(f["category"], f["department"]) - 0.5) > 1e-9
                       for f in loaded["Chicago"][2]])
    print("\n  The two cities' medians differ 22-fold: 5.4h against 118.0h. The")
    print("  carried row at Chicago's own threshold therefore asks the rules a")
    print("  question they were never written for, and most of the apparent")
    print("  transfer failure is that change of question rather than the move")
    print("  between cities. Held at New York's own threshold the same rules")
    print(f"  reach {auc:.3f}, or {matched_share:.0%} of what Chicago's columns support.")
    print(f"  They still fire on only {matched:.1%} of Chicago rows, so what is left")
    print("  is largely string overlap between two taxonomies.")

    print(f"\n  The published target is New York's own service level agreement,")
    print(f"  {len(targets)} complaint types covering "
          f"{sla.coverage(ny_test_f, targets):.0%} of test volume, ranked")
    print("  slowest first. It needs no reasoning and no client records, and it")
    print("  very nearly matches rules written with the real rates in hand. I")
    print("  could not find an equivalent published dataset for Austin or San")
    print("  Francisco, the two cities carrying the blind result, so this")
    print("  narrows the worry that a language model is reading published")
    print("  performance material rather than reasoning, without settling it.")

    heading("TABLE 8: fidelity ladder, trained on generated New York records")
    train_f, train_y, test_f, test_y, _ = loaded["New York"]
    # the thresholds come from train and are applied to test, as everywhere
    # else here. Fitting them on test would let the label see its own split.
    ny_train_rows = tickets.load(cities.NYC, "train")
    medians, total_cats = tickets.category_medians(ny_train_rows)
    strat_train_f, strat_train_y = tickets.stratified_split(ny_train_rows, medians)
    strat_test_f, strat_test_y = tickets.stratified_split(
        tickets.load(cities.NYC, "test"), medians)
    print(f"\n  within-category keeps {len(medians)} of {total_cats} New York "
          f"categories, those with at least 400 training rows")

    tasks = (("city median", train_f, train_y, test_f, test_y),
             ("within category", strat_train_f, strat_train_y,
              strat_test_f, strat_test_y))

    for task, tr_f, tr_y, te_f, te_y in tasks:
        vec = DictVectorizer(sparse=True).fit(tr_f)
        x_test = vec.transform(te_f)
        top = roc_auc_score(te_y, LogisticRegression(max_iter=1000)
                            .fit(vec.transform(tr_f), tr_y)
                            .predict_proba(x_test)[:, 1])
        # what is possible is defined by train alone. Including test would let
        # the metric see the split it is supposed to be blind to.
        allowed = {(f["department"], f["category"]) for f in tr_f}

        print(f"\n  task: {task}   n_train={len(tr_f)}  n_test={len(te_f)}")
        print(f"  {'generator':<24}{'AUC':>8}{'recovered':>12}{'impossible':>13}")
        print(f"  {'real records (ceiling)':<24}{top:>8.3f}{'100%':>12}{'0.0%':>13}")
        for generator_class in GENERATORS:
            generator = generator_class().fit(tr_f, tr_y)
            aucs, invented = [], []
            for seed in range(10):
                rows, labels = generator.sample(len(tr_f), random.Random(1000 + seed))
                model = LogisticRegression(max_iter=1000).fit(vec.transform(rows), labels)
                aucs.append(roc_auc_score(te_y, model.predict_proba(x_test)[:, 1]))
                invented.append(np.mean([(r["department"], r["category"]) not in allowed
                                         for r in rows]))
            mean = float(np.mean(aucs))
            lo, hi = np.percentile(aucs, [2.5, 97.5])
            print(f"  {generator.name:<24}{mean:>8.3f}{recovered(mean, top):>11.0%}"
                  f"{np.mean(invented):>13.1%}   [{lo:.3f}, {hi:.3f}]")

    print("\n  The pairwise generator draws department conditional on category,")
    print("  so it cannot emit a pair it never saw and 0.0% impossible is an")
    print("  identity, not a measurement. The learner is additive in one-hot")
    print("  columns and carries no interaction terms, so it cannot be harmed by")
    print("  a wrong combination either. On the city-median task the label is")
    print("  nearly a function of one column, which is why pairwise ties the")
    print("  joint. The within-category task removes that column, and the two")
    print("  fidelity orders separate.")


if __name__ == "__main__":
    main()
