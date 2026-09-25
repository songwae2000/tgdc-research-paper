"""Bootstrap intervals, so every figure carries its own uncertainty.

A bare AUC of 0.494 invites the obvious question of whether it differs from
chance at all. These answer it. Comparisons between two arms resample the test
set once and score both on the same resample, because the two scores are
measured on the same tickets and are not independent.

Two resampling units are available and they do not agree. Resampling tickets
treats every row as an independent observation, which they are not, because the
rules were written per category and a category's rows share whatever the author
got right or wrong about it. San Francisco has 37 categories against 17,007 test
rows, so the difference is not cosmetic: the ticket interval is far too narrow
for any claim about work a rule set has not seen. Both are reported.

The category is not a perfect unit either, and the paper says so. A prior here
reads the department as well, so its score is constant within a category only
when that category has one owning department. That holds throughout Austin and
fails for most of San Francisco, where 22 of 37 categories carry more than one
value and those categories are 99.6% of the rows. Clustering on category is still
the better of the two available units, since the dependence it removes is the
larger one, but it is an approximation rather than the exact design.
"""

import collections

import numpy as np
from sklearn.metrics import roc_auc_score

RESAMPLES = 1000
CLUSTER_RESAMPLES = 2000
SEED = 20260924


def _resample_indices(n, rng, draws):
    return rng.integers(0, n, size=(draws, n))


def _cluster_draw(groups, rng):
    """One resample that draws whole categories with replacement."""
    keys = np.unique(groups)
    where = {k: np.flatnonzero(groups == k) for k in keys}
    picked = rng.choice(keys, size=len(keys), replace=True)
    return np.concatenate([where[k] for k in picked])


def auc_interval(y_true, scores, draws=RESAMPLES):
    """Point estimate and a 95% percentile interval for one arm."""
    y = np.asarray(y_true)
    s = np.asarray(scores, dtype=float)
    rng = np.random.default_rng(SEED)

    point = roc_auc_score(y, s)
    boot = []
    for idx in _resample_indices(len(y), rng, draws):
        if len(np.unique(y[idx])) < 2:
            continue
        boot.append(roc_auc_score(y[idx], s[idx]))

    lo, hi = np.percentile(boot, [2.5, 97.5])
    return point, lo, hi


def auc_difference(y_true, scores_a, scores_b, draws=RESAMPLES):
    """Paired interval for (A minus B), both scored on the same resample."""
    y = np.asarray(y_true)
    a = np.asarray(scores_a, dtype=float)
    b = np.asarray(scores_b, dtype=float)
    rng = np.random.default_rng(SEED)

    point = roc_auc_score(y, a) - roc_auc_score(y, b)
    boot = []
    for idx in _resample_indices(len(y), rng, draws):
        if len(np.unique(y[idx])) < 2:
            continue
        boot.append(roc_auc_score(y[idx], a[idx]) - roc_auc_score(y[idx], b[idx]))

    lo, hi = np.percentile(boot, [2.5, 97.5])
    return point, lo, hi


def auc_interval_clustered(y_true, scores, groups, draws=CLUSTER_RESAMPLES):
    """Point estimate and interval resampling whole categories.

    The honest unit when the scores under test are constant within a category.
    """
    y = np.asarray(y_true)
    s = np.asarray(scores, dtype=float)
    g = np.asarray(groups)
    rng = np.random.default_rng(SEED)

    point = roc_auc_score(y, s)
    boot = []
    for _ in range(draws):
        idx = _cluster_draw(g, rng)
        if len(np.unique(y[idx])) < 2:
            continue
        boot.append(roc_auc_score(y[idx], s[idx]))

    lo, hi = np.percentile(boot, [2.5, 97.5])
    return point, lo, hi


def auc_difference_clustered(y_true, scores_a, scores_b, groups,
                             draws=CLUSTER_RESAMPLES):
    """Paired difference resampling whole categories rather than tickets."""
    y = np.asarray(y_true)
    a = np.asarray(scores_a, dtype=float)
    b = np.asarray(scores_b, dtype=float)
    g = np.asarray(groups)
    rng = np.random.default_rng(SEED)

    point = roc_auc_score(y, a) - roc_auc_score(y, b)
    boot = []
    for _ in range(draws):
        idx = _cluster_draw(g, rng)
        if len(np.unique(y[idx])) < 2:
            continue
        boot.append(roc_auc_score(y[idx], a[idx]) - roc_auc_score(y[idx], b[idx]))

    lo, hi = np.percentile(boot, [2.5, 97.5])
    return point, lo, hi


def permutation_test(values_by_group, groups, y_true, observed,
                     draws=CLUSTER_RESAMPLES):
    """Tests H0: the rules carry no information about which category is slow.

    Holds everything structural: the number of categories, how many rows sit in
    each, and the exact multiset of scores the rules hand out. Only the pairing
    of verdict to category is destroyed, so shuffling draws directly from the
    distribution of AUCs available under H0. Whatever that reaches is available
    from partitioning a taxonomy at all, with no domain reasoning in it.

    Returns the null mean, its 95% range, and a one-sided p-value: the share of
    shuffles reaching the observed AUC or better. The +1 in both terms counts
    the observed arrangement itself, which keeps the p-value from ever being
    zero on a finite number of draws.
    """
    y = np.asarray(y_true)
    g = np.asarray(groups)
    keys = sorted(values_by_group)
    values = np.array([values_by_group[k] for k in keys], dtype=float)
    rng = np.random.default_rng(SEED)

    null = []
    for _ in range(draws):
        shuffled = dict(zip(keys, rng.permutation(values)))
        scores = np.array([shuffled[k] for k in g], dtype=float)
        null.append(roc_auc_score(y, scores))

    null = np.asarray(null)
    lo, hi = np.percentile(null, [2.5, 97.5])
    p = (1 + int(np.sum(null >= observed))) / (1 + len(null))
    return float(np.mean(null)), lo, hi, p


def effective_clusters(groups):
    """Kish effective number of clusters, given how uneven they are.

    A count of categories overstates the evidence when one of them holds a
    third of the rows. This is the count the cluster bootstrap is really
    working with, and it is what decides whether an interval from it can be
    read as a test at all.
    """
    sizes = np.array(list(collections.Counter(groups).values()), dtype=float)
    return float(sizes.sum() ** 2 / np.square(sizes).sum())


def versus_chance(lo, hi):
    """Where the interval sits relative to 0.5, with direction.

    An interval that excludes 0.5 from below is significantly worse than
    guessing, which is a different finding from being better than it.
    """
    if lo > 0.5:
        return "above"
    if hi < 0.5:
        return "below"
    return "indistinguishable"


def conditional_lookup(train_features, train_labels, test_features, columns):
    """Best achievable using only these columns: the fitted conditional rate.

    This is the information ceiling for any rule that reasons over those
    columns, so it separates "the columns are weak" from "the rule is weak".
    """
    table, counts = {}, {}
    for row, y in zip(train_features, train_labels):
        key = tuple(row[c] for c in columns)
        table[key] = table.get(key, 0) + int(y)
        counts[key] = counts.get(key, 0) + 1

    overall = float(np.mean(train_labels))
    rates = {k: table[k] / counts[k] for k in counts}
    return [rates.get(tuple(row[c] for c in columns), overall) for row in test_features]
