"""The contaminated prior: rules for New York, written after reading its rates.

This is the control condition, and the thing the paper is about. The author
had seen New York's conditional resolution rates by department and complaint
type before writing these rules, so they cannot be read as domain knowledge.
Compare src/austin_prior.py, which was written blind and committed before any
outcome was observed.

Kept verbatim as first written. Tuning them after the fact would destroy the
comparison.
"""

SLOW_WORK = ("PAINT", "PLASTER", "WATER", "LEAK", "HEAT", "ELECTRIC", "PLUMBING",
             "DOOR", "WINDOW", "FLOORING", "APPLIANCE", "GENERAL", "SAFETY",
             "Mold", "Asbestos", "Rodent", "Sewer", "Street Condition",
             "Sidewalk", "Damaged Tree", "Graffiti")
FAST_WORK = ("Noise", "Illegal Parking", "Blocked Driveway", "Derelict Vehicle",
             "Drug Activity", "Disorderly", "Traffic", "Vendor")
SLOW_DEPT = ("HPD", "DOHMH", "DEP", "DSNY", "DPR", "DOB")
FAST_DEPT = ("NYPD",)


def prior_slow_probability(category: str, department: str) -> float:
    score = 0.5
    if any(k.lower() in category.lower() for k in SLOW_WORK):
        score = 0.85
    elif any(k.lower() in category.lower() for k in FAST_WORK):
        score = 0.15

    if department in SLOW_DEPT:
        score = min(0.95, score + 0.25)
    elif department in FAST_DEPT:
        score = max(0.05, score - 0.25)
    return score
