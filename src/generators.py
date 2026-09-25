"""Generators at three levels of fidelity to the real data.

Each one synthesises its own feature rows and its own labels. None of them
copies a real row, because reproducing which combinations can occur is the
thing being measured.

  marginal  every column drawn independently from its own distribution
  lowdim    every marginal, plus a tree of the strongest pairwise dependencies
            (the shape PrivBayes and the NIST winners optimise, and what
            SDV's Column Pair Trends scores)
  joint     feature tuples drawn from the empirical joint, which knows every
            combination that really occurs. An upper bound, not a contender.
"""

import math
import random
from collections import Counter, defaultdict

FEATURES = ("category", "department", "channel")


def _weighted(rng, items, weights, total):
    pick = rng.random() * total
    running = 0.0
    for item, weight in zip(items, weights):
        running += weight
        if pick <= running:
            return item
    return items[-1]


class MarginalGenerator:
    """Independent columns. Every marginal is exact, every dependency is gone."""

    name = "marginal only"

    def fit(self, features, labels):
        self.columns = {}
        for column in FEATURES:
            counts = Counter(row[column] for row in features)
            self.columns[column] = (list(counts), list(counts.values()), sum(counts.values()))
        self.rate = sum(labels) / len(labels)
        return self

    def sample(self, n, rng):
        rows, labels = [], []
        for _ in range(n):
            rows.append({c: _weighted(rng, *self.columns[c]) for c in FEATURES})
            labels.append(rng.random() < self.rate)
        return rows, labels


def _mutual_information(features, a, b):
    joint = Counter((row[a], row[b]) for row in features)
    left = Counter(row[a] for row in features)
    right = Counter(row[b] for row in features)
    n = len(features)
    total = 0.0
    for (x, y), count in joint.items():
        p_xy = count / n
        total += p_xy * math.log(p_xy / ((left[x] / n) * (right[y] / n)))
    return total


class LowOrderGenerator:
    """Marginals plus a maximum-spanning tree of pairwise dependencies.

    A Chow-Liu tree: each column is drawn conditional on one parent, so every
    pairwise association along the tree is preserved and nothing higher is.
    """

    name = "marginals + pairwise"

    def fit(self, features, labels):
        scores = {}
        for i, a in enumerate(FEATURES):
            for b in FEATURES[i + 1:]:
                scores[(a, b)] = _mutual_information(features, a, b)

        # greedy maximum spanning tree over the columns
        root = FEATURES[0]
        in_tree, self.parents = {root}, {root: None}
        while len(in_tree) < len(FEATURES):
            best, best_score = None, -1.0
            for (a, b), score in scores.items():
                for x, y in ((a, b), (b, a)):
                    if x in in_tree and y not in in_tree and score > best_score:
                        best, best_score = (y, x), score
            child, parent = best
            self.parents[child] = parent
            in_tree.add(child)

        self.order = [c for c in FEATURES if self.parents[c] is None]
        while len(self.order) < len(FEATURES):
            for column in FEATURES:
                if column not in self.order and self.parents[column] in self.order:
                    self.order.append(column)

        self.tables = {}
        for column, parent in self.parents.items():
            if parent is None:
                counts = Counter(row[column] for row in features)
                self.tables[column] = (list(counts), list(counts.values()),
                                       sum(counts.values()))
            else:
                by_parent = defaultdict(Counter)
                for row in features:
                    by_parent[row[parent]][row[column]] += 1
                self.tables[column] = {
                    value: (list(c), list(c.values()), sum(c.values()))
                    for value, c in by_parent.items()
                }

        # the label also gets pairwise treatment: conditioned on its single
        # most informative column, and nothing else
        self.label_on = max(FEATURES,
                            key=lambda c: _mutual_information(
                                [{**r, "_y": y} for r, y in zip(features, labels)], c, "_y"))
        by_value = defaultdict(list)
        for row, y in zip(features, labels):
            by_value[row[self.label_on]].append(y)
        self.label_rate = {v: sum(ys) / len(ys) for v, ys in by_value.items()}
        self.fallback = sum(labels) / len(labels)
        return self

    def sample(self, n, rng):
        rows, labels = [], []
        for _ in range(n):
            row = {}
            for column in self.order:
                parent = self.parents[column]
                if parent is None:
                    row[column] = _weighted(rng, *self.tables[column])
                else:
                    table = self.tables[column].get(row[parent])
                    row[column] = (_weighted(rng, *table) if table
                                   else _weighted(rng, *self.tables[self.order[0]]))
            rows.append(row)
            labels.append(rng.random() < self.label_rate.get(row[self.label_on],
                                                             self.fallback))
        return rows, labels


class JointGenerator:
    """Draws whole feature tuples that really occurred. The ceiling."""

    name = "empirical joint"

    def fit(self, features, labels):
        combos = defaultdict(list)
        for row, y in zip(features, labels):
            combos[tuple(row[c] for c in FEATURES)].append(y)
        self.keys = list(combos)
        self.weights = [len(v) for v in combos.values()]
        self.total = sum(self.weights)
        self.rates = {k: sum(v) / len(v) for k, v in combos.items()}
        return self

    def sample(self, n, rng):
        rows, labels = [], []
        for _ in range(n):
            key = _weighted(rng, self.keys, self.weights, self.total)
            rows.append(dict(zip(FEATURES, key)))
            labels.append(rng.random() < self.rates[key])
        return rows, labels


GENERATORS = (MarginalGenerator, LowOrderGenerator, JointGenerator)
