"""The three 311 feeds, and what each one calls its fields.

All three publish the same underlying object, a service request with an
opening time, a category, an owning department, an intake channel and a
closing time. Only the column names differ.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class City:
    name: str
    endpoint: str
    category: str      # what kind of work it is
    department: str    # who owns it
    channel: str       # how it was reported
    created: str
    closed: str
    # Chicago auto-closes most of its feed within a second of creation. Those
    # are informational records, not work, and leaving them in makes the task
    # "is this an auto-close record type" instead of "how long will this take".
    drop_instant_closes: bool = False


NYC = City(
    name="New York",
    endpoint="https://data.cityofnewyork.us/resource/erm2-nwe9.json",
    category="complaint_type", department="agency",
    channel="open_data_channel_type",
    created="created_date", closed="closed_date",
)

CHICAGO = City(
    name="Chicago",
    endpoint="https://data.cityofchicago.org/resource/v6vf-nfxy.json",
    category="sr_type", department="owner_department", channel="origin",
    created="created_date", closed="closed_date",
    drop_instant_closes=True,
)

AUSTIN = City(
    name="Austin",
    endpoint="https://data.austintexas.gov/resource/xwdj-i9he.json",
    category="sr_type_desc", department="sr_department_desc",
    channel="sr_method_received_desc",
    created="sr_created_date", closed="sr_closed_date",
)

SF = City(
    name="San Francisco",
    endpoint="https://data.sf.gov/resource/vw6y-z8j6.json",
    category="service_name", department="agency_responsible", channel="source",
    created="requested_datetime", closed="closed_date",
)

ALL = (NYC, CHICAGO, AUSTIN, SF)
