"""Prior probability that an Austin 311 request resolves slower than the median.

No timing data was used. The estimates come from how municipal work actually
gets closed, and the reference point is the median across *all* requests in the
catalogue, which is pulled down by the very high volume of routed, same-cycle
work (missed collections, dispatched officers, dead animal pickup). So a type
only needs to be moderately involved to land above that median.

What makes a request fast:
  - A crew or officer is already routed past the address on a fixed cycle, so
    the work is appended to tomorrow's run (missed garbage, recycling, compost).
  - One visit closes it, with no second party to satisfy: patrol answers a noise
    call, a dead animal is collected, a scooter is moved, a locate is painted.
  - It is closed by contact rather than by work: information requests,
    call-back requests, and miscategorised tickets that get transferred.
  - A statutory clock forces speed (utility locates) or a safety SLA does
    (signal outage, debris blocking a lane).

What makes a request slow:
  - Legal process. Code enforcement runs inspect, notice, cure period,
    re-inspect, and sometimes citation or court. Vehicle abatement has a
    statutory tag-and-wait before a tow. These are weeks to months by design.
  - A third party has to act. Private property graffiti needs owner consent,
    conservation violations need the customer to fix a controller, short term
    rental cases need a registrant to respond.
  - Design or engineering precedes the work. New signs, new signals, speed
    mitigation, sidewalk and ramp construction, drainage work all queue behind
    a study, a design, a budget line, and a contractor.
  - The work is batched into a cycle longer than a week: mowing rounds, bulk
    and brush set-outs, tree crews, storm debris passes.
  - The ticket stays open for the life of the thing it tracks: a lane closure
    notification closes when the closure ends.
  - An observation period is built in: bite quarantine, cruelty follow-up,
    stray hold, foster placement.

Keyword groups derived from that, roughly high to low:
  legal/compliance (code officer, compliance, short term rental, abatement,
  violation, follow-up), capital and design (new sign, new signal, sidewalk,
  ramp, study, drainage, construction, closure, permit), cyclical field work
  (tree, mowing, park grounds, bulk, brush, storm debris), third-party and
  asset repair (graffiti, street light, parking machine, meter, water waste),
  observation-bound animal cases (bite, proper care, cruelty, keep, wildlife),
  single-visit dispatch (loose dog, injured animal, dead animal, debris,
  pothole, micromobility, signal maintenance), routed collection (missed,
  garbage, recycling, compost, yard trimmings), and contact-only work
  (information, contact request, assistance request, other).

Departments give the fallback when nothing matches, and nudge the keyword
estimate slightly, since the owning department says a lot about process weight:
code and development services are slow by construction, resource recovery,
animal services and police close on a route or a shift.
"""

import re
from typing import Dict, Pattern as RePattern, Sequence, Tuple

DEFAULT_PRIOR = 0.5
FLOOR, CEILING = 0.05, 0.95

# Weight given to the owning department when a service keyword already matched.
DEPARTMENT_BLEND = 0.15
MODIFIER_STEP = 0.04
MODIFIER_CAP = 0.10

Pattern = Tuple[str, ...]
Rule = Tuple[float, Tuple[Pattern, ...]]

DEPARTMENT_PRIORS: Tuple[Rule, ...] = (
    (0.80, (("code",),)),                     # Austin Code, Code Compliance
    (0.75, (("development services",),)),
    (0.70, (("economic development",),)),
    (0.65, (("watershed",),)),
    (0.62, (("public works",),)),
    (0.60, (("parks",), ("recreation",))),
    (0.55, (("energy",),)),
    (0.55, (("public health",), ("health",))),
    (0.52, (("water",),)),
    (0.50, (("transportation",),)),
    (0.40, (("311",), ("command center",))),
    (0.35, (("resource recovery",),)),
    (0.35, (("animal",),)),
    (0.32, (("police",),)),
)

# Ordered most specific first. The first rule whose pattern matches wins, so
# "storm debris" must precede "debris", "dead animal" must precede "animal".
SERVICE_RULES: Tuple[Rule, ...] = (
    # Legal and compliance process: inspect, notice, cure period, re-inspect.
    (0.86, (("request code officer",), ("code officer",), ("code inspect",))),
    (0.84, (("short term rental",), ("str complaint",))),
    (0.82, (("code compliance",), ("code enforcement",), ("zoning",),
            ("substandard",), ("nuisance abatement",))),
    (0.80, (("follow up",), ("re inspect",), ("reinspect",), ("case follow",))),
    (0.78, (("land use",), ("occupancy",), ("building permit",),
            ("permit issue",), ("license",))),

    # Capital, design and engineering work, queued behind study and budget.
    (0.84, (("sidewalk",), ("curb ramp",), ("ada ramp",), ("curb repair",))),
    (0.84, (("sign", "new"), ("signal", "new"), ("street light", "new"))),
    (0.82, (("traffic study",), ("speed",), ("traffic calming",),
            ("crosswalk",), ("bike lane",), ("striping",))),
    (0.80, (("closure",), ("lane road",), ("detour",))),
    (0.78, (("drainage",), ("flood",), ("erosion",), ("creek",),
            ("storm drain",), ("water quality",), ("channel",))),
    (0.76, (("construction",), ("capital",), ("design",), ("engineering",),
            ("right of way permit",), ("excavation",))),

    # Third-party dependency or statutory waiting period.
    (0.74, (("vehicle abatement",), ("abandoned vehicle",),
            ("junked vehicle",), ("inoperable vehicle",))),
    (0.72, (("obstruction",), ("encroach",), ("illegal dumping",))),
    (0.70, (("storm debris",), ("debris collection",))),

    # Cyclical field work batched into rounds longer than a week.
    (0.72, (("tree",), ("arborist",), ("brush trim",), ("vegetation",))),
    (0.66, (("bulk",), ("brush",), ("large item",))),
    (0.62, (("park maintenance",), ("grounds",), ("mow",), ("playground",),
            ("trail",), ("athletic field",))),

    # Asset repair that needs parts, a contractor, or an owner's consent.
    (0.62, (("graffiti",),)),
    (0.60, (("parking machine",), ("meter repair",), ("kiosk",))),
    (0.60, (("street light",), ("streetlight",), ("light issue",),
            ("pole",), ("outage",))),
    (0.58, (("water waste",), ("conservation violation",),
            ("irrigation",), ("backflow",))),
    (0.56, (("guardrail",), ("fence",), ("bench",), ("bridge",))),
    # Venue noise: repeat visits, sound readings, permit conditions, not one
    # patrol response like a residential noise call.
    (0.48, (("commercial music",), ("amplified",), ("sound permit",),
            ("entertainment",))),

    # Animal cases with a built-in observation or holding period.
    (0.70, (("bite",), ("quarantine",), ("rabies",))),
    (0.68, (("proper care",), ("cruelty",), ("neglect",), ("welfare check",))),
    (0.66, (("report", "keep"), ("foster",), ("adopt",), ("surrender",))),
    (0.58, (("wildlife",), ("snake",), ("coyote",), ("raccoon",))),
    (0.55, (("aggressive",), ("bark",), ("tether",), ("at large investigat",))),

    # Routed collection: appended to the next scheduled run.
    (0.18, (("missed",),)),
    (0.20, (("dead animal",),)),
    (0.28, (("garbage",), ("recycling",), ("compost",), ("yard trimmings",),
            ("trash",), ("cart",), ("collection",))),

    # Single-visit dispatch that one crew or officer closes on the spot.
    (0.22, (("parking violation",), ("enforcement",), ("tow request",))),
    (0.22, (("noise",), ("alarm",), ("loud",))),
    (0.26, (("non emergency",), ("collision",), ("accident report",))),
    (0.28, (("dig tess",), ("locate",), ("utility locate",))),
    (0.30, (("traffic signal",), ("signal maintenance",), ("signal timing",),
            ("flashing",))),
    (0.32, (("debris",), ("spill",), ("blocked",))),
    (0.34, (("pothole",), ("pavement repair",), ("street repair",))),
    (0.34, (("loose dog",), ("stray",), ("injured",), ("sick animal",),
            ("pick up",), ("trapped",))),
    (0.40, (("micromobility",), ("scooter",), ("dockless",), ("bike share",))),
    (0.42, (("sign maintenance",), ("sign repair",), ("marking",))),
    (0.45, (("leak",), ("water pressure",), ("sewer",), ("manhole",))),

    # Closed by contact rather than by work.
    (0.32, (("contact request",), ("information",), ("inquiry",),
            ("resource center",), ("question",))),
    (0.38, (("assistance request",), ("other",), ("general",),
            ("referral",), ("complaint only",))),
)

# Small nudges layered on top, capped so they cannot flip a confident estimate.
MODIFIERS: Tuple[Tuple[float, Pattern], ...] = (
    (+1, ("investigat",)),
    (+1, ("violation",)),
    (+1, ("abatement",)),
    (+1, ("review",)),
    (+1, ("request for",)),
    (+1, ("install",)),
    (+1, ("replace",)),
    (-1, ("emergency",)),
    (-1, ("urgent",)),
    (-1, ("missed",)),
    (-1, ("report",)),
    (-1, ("notification",)),
)


def _normalise(text: object) -> str:
    """Lowercase, flatten punctuation to spaces, collapse whitespace."""
    raw = str(text if text is not None else "").lower()
    for char in "-/_,.()[]&:;'\"":
        raw = raw.replace(char, " ")
    return " ".join(raw.split())


_TOKEN_CACHE: Dict[str, RePattern] = {}


def _token_regex(token: str) -> RePattern:
    """Token must start on a word boundary, but may run on ("inspect" hits
    "inspection"). Without the leading boundary, "street" would match "tree"."""
    cached = _TOKEN_CACHE.get(token)
    if cached is None:
        cached = _TOKEN_CACHE[token] = re.compile(r"\b" + re.escape(token))
    return cached


def _matches(haystack: str, patterns: Tuple[Pattern, ...]) -> bool:
    return any(
        all(_token_regex(token).search(haystack) for token in pattern)
        for pattern in patterns
    )


def _first_match(haystack: str, rules: Sequence[Rule]) -> float:
    for value, patterns in rules:
        if _matches(haystack, patterns):
            return value
    return DEFAULT_PRIOR


def prior_slow_probability(service_type: str, department: str) -> float:
    """Probability this request runs slower than the median."""
    service = _normalise(service_type)
    dept = _normalise(department)

    dept_prior = _first_match(dept, DEPARTMENT_PRIORS) if dept else DEFAULT_PRIOR

    matched = None
    for value, patterns in SERVICE_RULES:
        if _matches(service, patterns) or (not service and _matches(dept, patterns)):
            matched = value
            break

    if matched is None:
        probability = dept_prior
    else:
        probability = (1 - DEPARTMENT_BLEND) * matched + DEPARTMENT_BLEND * dept_prior

    nudge = 0.0
    for direction, pattern in MODIFIERS:
        if _matches(service, (pattern,)):
            nudge += direction * MODIFIER_STEP
    probability += max(-MODIFIER_CAP, min(MODIFIER_CAP, nudge))

    return float(max(FLOOR, min(CEILING, probability)))


# Recorded before evaluation, by the experimenter rather than the author.
#
# This author reasoned more carefully than the human one did: it identified
# statutory holds, third-party consent, design-before-work queues, and tickets
# that stay open for the life of the thing they track. None of that came from
# timing data, which it never saw.
#
# Prediction: AUC 0.52 to 0.62. Better than the human blind prior because the
# reasoning is better, but still far short of the 0.883 those columns support.
#
# Unlike the human blind prior, this prediction is NOT itself blind. The
# experimenter already knew the first blind result when writing it, so treat
# the band as an informed guess and the author's rules as the blind artefact.
PREDICTED_RANGE = (0.52, 0.62)
