"""Pre-registered blind prior for San Francisco 311, by the human author.

PROCEDURE. Identical to the Austin one. San Francisco's service type and
agency queue vocabulary was pulled with the query restricted to names and row
counts. No duration, rate or per-category outcome was requested or displayed
before these rules were written and committed.

ONE HONEST DIFFERENCE FROM THE AUSTIN PRIOR. That one was written before
seeing any result. This one is written knowing what the Austin evaluation
showed: that duration tracks administrative process rather than the physical
nature of the work. The rules below are blind to San Francisco's rates, but the
author is no longer blind to the general lesson. That makes this a test of
whether the lesson transfers, which is a weaker claim than the Austin arm made
and is reported as such.

THE PRINCIPLES, revised in light of Austin:

  1. Routed work closes on the next pass          -> fast
     A crew or officer already passes the address on a cycle. Street cleaning,
     refuse collection, graffiti abatement, parking enforcement.
  2. A second party must act                      -> slow
     Private property owners, tenants, other utilities. Nothing moves until
     someone outside the department does something.
  3. A statutory clock runs before the work       -> slow
     Abandoned vehicles carry a tag-and-wait period before tow.
  4. The asset must be fabricated or excavated    -> slow
     Signs, streetlights, sewer, pavement. Design, parts, and a dig permit.
  5. The ticket tracks a process, not a task      -> slow
     Feedback about staff, housing authority casework, claims for damage.

PREDICTION, recorded before evaluation: AUC 0.55 to 0.68. Higher than the
Austin human prior because the principles have been corrected once, but still
well short of what the columns support.
"""

ROUTED = ("cleaning", "street and sidewalk", "recology", "litter", "receptacle",
          "overflow", "graffiti public", "illegal posting", "posting",
          "parking enforcement", "blocked street", "blocked sidewalk",
          "encampment", "homeless")

SECOND_PARTY = ("graffiti private", "private", "sidewalk or curb",
                "sidewalk and curb", "curb", "damaged property", "damage",
                "residential building", "sfha", "housing")

STATUTORY = ("abandoned vehicle", "abandoned")

FABRICATED = ("sign repair", "sign request", "temporary sign", "sign",
              "streetlight", "street light", "sewer", "street defect",
              "street defects", "tree maintenance", "tree", "meter")

PROCESS = ("muni feedback", "muni service", "muni employee", "employee",
           "feedback", "general request", "external request", "rec and park",
           "rpd general")

FAST_QUEUE = ("dpw ops", "recology", "street and environmental",
              "parking enforcement", "hsoc", "healthy streets")

SLOW_QUEUE = ("puc sewer", "housing authority", "muni work", "abandoned vehicles",
              "meter_bike", "supervisor queue", "duplicate case", "bsm")


def _hit(text, keywords):
    """Word-boundary match, because "street" contains "tree"."""
    padded = f" {(text or '').lower().replace('-', ' ')} "
    return any(f" {k} " in padded or padded.startswith(f" {k} ")
               or f" {k}s " in padded for k in keywords)


def prior_slow_probability(service_type: str, agency: str) -> float:
    """Chance this request runs slow, from the shape of the work alone."""
    score = 0.5

    # most specific first, since several groups overlap on substrings
    if _hit(service_type, STATUTORY):
        score = 0.80
    elif _hit(service_type, SECOND_PARTY):
        score = 0.80
    elif _hit(service_type, FABRICATED):
        score = 0.75
    elif _hit(service_type, PROCESS):
        score = 0.65
    elif _hit(service_type, ROUTED):
        score = 0.20

    if _hit(agency, SLOW_QUEUE):
        score = min(0.95, score + 0.15)
    elif _hit(agency, FAST_QUEUE):
        score = max(0.05, score - 0.15)

    return score


# AMENDMENT, made before any San Francisco outcome was observed.
#
# The first committed version matched keywords as bare substrings, so every
# "Street ..." type matched the tree-maintenance rule, since "street" contains
# "tree". That is an implementation error rather than a reasoning one, and
# evaluating it would have measured the coding rather than the prior. Matching
# is now on word boundaries. No outcome data was seen between the two commits.
PREDICTED_RANGE = (0.55, 0.68)
