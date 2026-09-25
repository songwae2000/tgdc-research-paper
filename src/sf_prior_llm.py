"""Prior probability that a San Francisco 311 request resolves slower than the median.

No timing data was used. The estimates come from how municipal work actually
gets closed, and the reference point is the median across *all* requests in
this catalogue. That matters a lot here: the SF feed is dominated by routed
street work (Street and Sidewalk Cleaning, Recology bin pickups, graffiti
abatement, dispatched parking officers), all of which closes on the next crew
pass. The median is therefore pulled down to roughly a day, so a request only
has to involve a second visit, a second party or a second department to land
above it. Most of the catalogue does, which is why few rules sit near 0.5.

What makes a request fast:
  - A crew is already routed past the address on a daily cycle and the job is
    appended to tomorrow's run: street cleaning, abandoned material pickup,
    overflowing receptacles, illegal postings, public graffiti abatement.
  - An officer closes it on the spot in one shift. Parking enforcement is the
    clearest case: drive out, cite or clear, close.
  - A safety SLA forces a same-day pass: a blocked sidewalk or lane.
  - The work is a scheduled sweep that the ticket simply joins. Encampment and
    homeless-concern cases go to HSOC, which works a posted route, so they
    close on a cycle rather than waiting on anyone.

What makes a request slow:
  - A statutory clock. An abandoned vehicle must be marked, left for 72 hours,
    re-inspected and only then towed. That floor alone puts it above a median
    set by same-day cleaning.
  - Private property. In SF the owner is responsible for the sidewalk and for
    graffiti on their own building, so the case becomes notice of violation,
    a cure period, then re-inspection. Weeks by design.
  - A second agency or a jointly owned asset. Streetlights split between the
    PUC and PG&E and need pole ownership resolved first. External requests are
    handed to Caltrans, BART or the state, where the city cannot close them.
  - Fabrication, design or excavation before the work: sign shops, sign permits,
    pavement reconstruction, sewer main repair, curb ramps.
  - Investigation with a person at the end of it. Transit feedback is routed to
    operations for a response, and employee feedback adds a supervisor
    interview and a labour process.
  - Batched or seasonal crews: tree maintenance behind an arborist inspection,
    park grounds work behind a rounds schedule.
  - Chronic backlog and access constraints: housing authority work orders wait
    on a trade, a part and a tenant being home.
  - Catch-all buckets. A "General Request" is usually misrouted at least once,
    and every reassignment restarts the clock.

Keyword groups derived from that, roughly high to low:
  private-property compliance (private, curb, sidewalk owner, damage),
  batched or seasonal crews (tree, park, rec), asset work needing parts or a
  second owner (streetlight, sign, meter, defect, pavement), statutory holds
  (abandoned vehicle), people processes (muni, employee, feedback, housing,
  sfha, tenant, residential building), hand-offs (external, general request,
  duplicate, supervisor), utility response (sewer, manhole), complaint-on-
  contact (noise), scheduled sweeps (encampment, homeless, hsoc), routed
  collection and abatement (cleaning, recology, overflow, receptacle, posting,
  public graffiti), and single-shift dispatch (parking enforcement, blocked).

The agency queue gives the fallback when nothing matches and nudges the keyword
estimate slightly, since the owning queue carries its own process weight: BSM
is permits and encroachments, the MUNI queue is investigation, the Housing
Authority queue is a maintenance backlog, while Recology and the enforcement
dispatch queues are next-pass work.
"""

import re
from typing import Dict, Pattern as RePattern, Sequence, Tuple

DEFAULT_PRIOR = 0.5
FLOOR, CEILING = 0.05, 0.95

# Weight given to the owning queue when a service keyword already matched.
AGENCY_BLEND = 0.15
MODIFIER_STEP = 0.04
MODIFIER_CAP = 0.10

Pattern = Tuple[str, ...]
Rule = Tuple[float, Tuple[Pattern, ...]]

# Ordered most specific first. "recology" must precede "abandoned", or the
# Recology_Abandoned queue inherits the abandoned-vehicle tow clock.
AGENCY_PRIORS: Tuple[Rule, ...] = (
    (0.85, (("housing authority",), ("sfha",))),
    (0.78, (("muni",),)),
    (0.72, (("bsm",), ("street use",), ("mapping",))),
    (0.65, (("meter",), ("bike",))),
    (0.60, (("supervisor",),)),
    (0.55, (("duplicate",), ("hold",))),
    (0.80, (("abandoned", "vehicle"), ("dpt abandoned",))),
    (0.45, (("sewer",), ("puc",))),
    (0.42, (("hsoc",), ("healthy streets",))),
    (0.35, (("environmental services",), ("pw ",))),
    (0.32, (("dpw",), ("public works",))),
    (0.25, (("recology",),)),
    (0.15, (("parking enforcement",), ("dispatch",), ("dpt",), ("mta",))),
)

# Ordered most specific first. The first rule whose pattern matches wins, so
# "graffiti private" must precede "graffiti", and "cleaning" must precede
# "sidewalk", or Street and Sidewalk Cleaning is priced as curb repair.
SERVICE_RULES: Tuple[Rule, ...] = (
    # Private property: notice of violation, cure period, re-inspection.
    (0.90, (("graffiti", "private"), ("private property",))),
    (0.86, (("curb",), ("curb ramp",), ("sidewalk defect",),
            ("sidewalk repair",))),
    (0.75, (("damage",), ("property damage",), ("claim",))),

    # Batched and seasonal crews, gated by an inspection first.
    (0.88, (("tree",), ("arborist",), ("limb",), ("stump",))),
    (0.65, (("rec and park",), ("rpd",), ("park maintenance",),
            ("recreation",), ("playground",), ("trail",))),

    # Statutory hold before the work can even start.
    (0.85, (("abandoned", "vehicle"), ("vehicle",), ("tow",))),

    # People processes: investigation, a response, sometimes a labour process.
    (0.86, (("employee",), ("operator",), ("driver",), ("discourteous",))),
    (0.85, (("sfha",), ("housing authority",), ("residential building",),
            ("tenant",), ("habitability",))),
    (0.78, (("muni",), ("transit",), ("bus",), ("rail",), ("streetcar",))),

    # Assets needing fabrication, parts, or a second owner to agree.
    (0.82, (("streetlight",), ("street light",), ("light",), ("pole",),
            ("outage",))),
    (0.80, (("temporary sign",), ("sign request",), ("new sign",))),
    (0.76, (("sign",), ("signal",), ("marking",), ("striping",))),
    (0.72, (("street defect",), ("defect",), ("pothole",), ("pavement",),
            ("roadway",))),
    (0.70, (("meter",), ("bike rack",), ("kiosk",), ("parking machine",))),
    (0.72, (("permit",), ("encroach",), ("construction",), ("excavat",))),

    # Hand-offs. The city does not control the closing clock.
    (0.75, (("external",), ("other agency",), ("referral",), ("caltrans",),
            ("state",))),
    (0.55, (("duplicate",),)),

    # Utility response: hours for a backup, weeks for a main.
    (0.45, (("sewer",), ("manhole",), ("catch basin",), ("clogged drain",),
            ("water",))),

    # Closed on contact, or referred straight back out.
    (0.48, (("noise",), ("loud",), ("alarm",))),

    # Scheduled sweeps. The ticket joins a posted route, not a queue.
    (0.42, (("encampment",), ("homeless",), ("hsoc",), ("healthy streets",))),

    # Routed collection and abatement: appended to the next crew pass.
    (0.44, (("posting",), ("poster",), ("flyer",), ("handbill",))),
    (0.36, (("graffiti", "public"),)),
    (0.55, (("graffiti",),)),
    (0.30, (("receptacle",), ("overflow",), ("trash can",), ("garbage can",),
            ("bin",), ("recology",))),
    (0.28, (("cleaning",), ("sweep",), ("litter",),
            ("dumping",), ("debris",), ("spill",), ("human waste",),
            ("needle",))),

    # Single-shift dispatch: one officer, one visit, closed on the spot.
    (0.12, (("parking enforcement",), ("parking violation",))),
    (0.20, (("enforcement",), ("citation",), ("blocked driveway",))),
    (0.30, (("blocked",), ("obstruct",), ("lane",))),
    (0.25, (("parking",),)),

    # Catch-all buckets, which get misrouted at least once.
    (0.72, (("general", "mta"), ("general", "dpt"))),
    (0.70, (("general", "dph"), ("general", "health"))),
    (0.58, (("general", "puc"), ("general", "public works"),
            ("general", "pw"))),
    (0.75, (("feedback",), ("complaint",), ("comment",))),
    (0.65, (("general",), ("miscellaneous",), ("other",))),
    (0.60, (("request",), ("inquiry",), ("service",))),
    (0.45, (("report",), ("concern",), ("issue",))),
)

# Small nudges layered on top, capped so they cannot flip a confident estimate.
# "request" against "report" is the useful axis: asking the city to build or
# supply something is slower than flagging something that is already broken.
MODIFIERS: Tuple[Tuple[float, Pattern], ...] = (
    (+1, ("private",)),
    (+1, ("investigat",)),
    (+1, ("permit",)),
    (+1, ("install",)),
    (+1, ("replace",)),
    (+1, ("request",)),
    (+1, ("maintenance",)),
    (-1, ("report",)),
    (-1, ("clean",)),
    (-1, ("overflow",)),
    (-1, ("emergency",)),
    (-1, ("dispatch",)),
    (-1, ("pickup",)),
)


def _normalise(text: object) -> str:
    """Lowercase, flatten punctuation to spaces, collapse whitespace."""
    raw = str(text if text is not None else "").lower()
    for char in "-/_,.()[]&:;'\"":
        raw = raw.replace(char, " ")
    return " ".join(raw.split())


_TOKEN_CACHE: Dict[str, RePattern] = {}


def _token_regex(token: str) -> RePattern:
    """Token must start on a word boundary, but may run on ("defect" hits
    "defects"). Without the leading boundary, "sign" would match "design"."""
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


def prior_slow_probability(service_type: str, agency: str) -> float:
    """Probability this request runs slower than the median."""
    service = _normalise(service_type)
    queue = _normalise(agency)

    agency_prior = _first_match(queue, AGENCY_PRIORS) if queue else DEFAULT_PRIOR

    matched = None
    for value, patterns in SERVICE_RULES:
        if _matches(service, patterns) or (not service and _matches(queue, patterns)):
            matched = value
            break

    if matched is None:
        probability = agency_prior
    else:
        probability = (1 - AGENCY_BLEND) * matched + AGENCY_BLEND * agency_prior

    nudge = 0.0
    for direction, pattern in MODIFIERS:
        if _matches(service, (pattern,)):
            nudge += direction * MODIFIER_STEP
    probability += max(-MODIFIER_CAP, min(MODIFIER_CAP, nudge))

    return float(max(FLOOR, min(CEILING, probability)))
