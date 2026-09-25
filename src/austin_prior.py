"""Pre-registered domain prior for Austin 311. Written before any outcome was seen.

PROCEDURE. Austin's service-type and department vocabulary was pulled with
`$select` restricted to category names and row counts. No date, no duration,
no resolution rate, and no per-category outcome of any kind was requested or
displayed before these rules were written and committed.

This is the control the NYC rules lacked. Those were written after reading
NYC's conditional rates, scored 0.822 there, and scored 0.435 on Chicago.
The open question is how much of that 0.822 was knowledge and how much was
memory. A blind prior, authored and committed before evaluation, measures it.

THE PRINCIPLES. Four claims about municipal service work, not about Austin:

  1. One person attending once clears it        -> fast
     Patrol response, collection, pick-up, impound.
  2. Inspection opening a process               -> slow
     Code enforcement, permits, investigations. The visit starts the clock,
     it does not stop it.
  3. A crew, materials or capital scheduling    -> slow
     Repair, construction, installation. Queued against budget and crews.
  4. A fixed-cycle routine service              -> fast
     Waste and recycling run on a published schedule, so the worst case is
     the next cycle.

PREDICTION, recorded before evaluation. If domain knowledge is real and
transferable, a blind prior should beat chance clearly: AUC 0.60 to 0.72.
Below 0.55 means the NYC 0.822 was essentially all contamination. Above 0.80
means the priors were genuine knowledge all along and Chicago failed for some
other reason, which would refute the contamination reading.
"""

# principle 1: dispatched, resolved on the visit
ATTEND_ONCE = ("noise", "alarm", "loud", "music", "collision", "parking violation",
               "vehicle abatement", "loose dog", "found animal", "dead animal",
               "injured", "sick animal", "animal bite", "pick up", "assistance request",
               "contact request", "wildlife")

# principle 4: published collection cycle
ROUTINE_CYCLE = ("arr -", "arr missed", "garbage", "recycling", "compost",
                 "yard trimmings", "organics", "brush", "bulk", "storm debris")

# principle 2: an inspection that opens a process
OPENS_PROCESS = ("code officer", "code compliance", "short term rental", "follow-up",
                 "violation report", "water waste", "conservation violation",
                 "proper care", "obstruction", "closure notification")

# principle 3: crew, materials, capital scheduling
NEEDS_CREW = ("repair", "maintenance", "pothole", "sidewalk", "street light",
              "tree issue", "sign - new", "sign -", "graffiti", "debris in street",
              "park maintenance", "grounds", "parking machine")

# departments that mostly run on dispatch or on a collection round
FAST_DEPT = ("police", "animal", "resource recovery", "pet resource", "311")

# departments that mostly run on inspection or on capital works
SLOW_DEPT = ("code", "development services", "watershed", "public works",
             "parks", "energy", "water", "transportation")


def _hit(text, keywords):
    lowered = text.lower()
    return any(k in lowered for k in keywords)


def prior_slow_probability(service_type: str, department: str) -> float:
    """Chance this ticket runs slow, from the nature of the work alone."""
    score = 0.5

    if _hit(service_type, ROUTINE_CYCLE):
        score = 0.2
    elif _hit(service_type, ATTEND_ONCE):
        score = 0.15
    elif _hit(service_type, OPENS_PROCESS):
        score = 0.85
    elif _hit(service_type, NEEDS_CREW):
        score = 0.75

    if _hit(department, FAST_DEPT):
        score = max(0.05, score - 0.15)
    elif _hit(department, SLOW_DEPT):
        score = min(0.95, score + 0.15)

    return score


# Transcribed from the docstring above, which was committed in 8973439 before
# any outcome was observed. The band is not new, only machine readable.
PREDICTED_RANGE = (0.60, 0.72)
