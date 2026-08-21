"""Single source of truth for one monthly AR run.

Everything month-specific, company-specific, or path-specific lives here.
The engine, workbook, dashboard, SOA and reminder modules read only from
this module — never edit constants inside them.

To run a new month: update AS_OF and the two input paths, nothing else.
"""
import calendar
import datetime as dt
from pathlib import Path

# ---------------------------------------------------------------------------
# Period
# ---------------------------------------------------------------------------
AS_OF = dt.date(2026, 7, 31)          # report date (month-end)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"              # put the two input files here
OUT_DIR = ROOT / "output"

# Current-month NetSuite extract: "A/R Aging Detail SO/Project ID".
# Layout expected: headers on row 7, data from row 8, customer name only on
# group-header rows, "Total - <customer>" rows closing each group.
EXTRACT_FILE = DATA_DIR / "ARAgingDetailSOProjectID.xlsx"
EXTRACT_SHEET = None                  # None = first sheet

# Prior-month workbook: the payment-terms master (terms live here, NOT in
# NetSuite). Sheet "SOA": customer col 1, terms col 7, open balance col 10,
# data from row 8. May be absent on a first run — everything then falls to
# derived / assumed terms and is flagged as such.
PRIOR_FILE = DATA_DIR / "prior_month.xlsx"
PRIOR_SHEET = "SOA"

ENGINE_JSON = OUT_DIR / "ar_engine.json"

# ---------------------------------------------------------------------------
# Company / letterhead
# ---------------------------------------------------------------------------
COMPANY_NAME = "Convergint Systems Integration L.L.C S.O.C"
COMPANY_SHORT = "Convergint"
CURRENCY = "AED"
PREPARED_BY = "Finance - Receivables"

# Statement-of-account letterhead. Replace the bracketed placeholders with
# the real details from the approved company letterhead before circulating
# statements externally. LOGO_FILE may be a PNG/SVG path or None.
LETTERHEAD = {
    "address_lines": ["[Street address]", "[PO Box, City, Country]"],
    "phone": "[Phone]",
    "email": "[AR contact email]",
    "trn": "[Tax Registration No.]",
    "bank_details": [
        "Bank: [Bank name]",
        "Account name: " + COMPANY_NAME,
        "IBAN: [IBAN]",
        "SWIFT: [SWIFT]",
    ],
    "logo_file": None,
}

# ---------------------------------------------------------------------------
# Intercompany identification (Trap 1)
# ---------------------------------------------------------------------------
IC_CONTAINS = ["(IC "]
IC_PREFIXES = ["MEA TECH GT", "MEA PROJECTS LLC (DUBAI)"]

# ---------------------------------------------------------------------------
# Payment terms (Trap 2 / Trap 3)
# ---------------------------------------------------------------------------
STANDARD_TERMS = [30, 45, 60, 90, 120]  # derived terms snap to nearest
DEFAULT_TERMS = 30                       # last-resort, always flagged ASSUMED

# ---------------------------------------------------------------------------
# Buckets, risk and priority
# ---------------------------------------------------------------------------
BUCKETS = ["Current", "0-30", "31-60", "61-90", "91-120", "Over 120"]

# Collection priority thresholds on the over-60 balance, in report currency.
PRIO_P1 = 1_000_000
PRIO_P2 = 250_000

# ---------------------------------------------------------------------------
# Entity mapping from document numbers (cosmetic slicer only)
# ---------------------------------------------------------------------------
ENTITY_PATTERNS = {"/AUH/": "Abu Dhabi", "/DXB/": "Dubai", "/IRQ/": "Iraq"}
ENTITY_DEFAULT = "Other"

# ---------------------------------------------------------------------------
# Forecast months (derived — do not edit)
# ---------------------------------------------------------------------------
def _add_months(d: dt.date, n: int) -> dt.date:
    y, m = divmod(d.month - 1 + n, 12)
    y, m = d.year + y, m + 1
    return dt.date(y, m, min(d.day, calendar.monthrange(y, m)[1]))

M1 = _add_months(AS_OF.replace(day=1), 1)   # first forecast month
M2 = _add_months(AS_OF.replace(day=1), 2)
M3 = _add_months(AS_OF.replace(day=1), 3)

MONTH_LABELS = {
    "M1": M1.strftime("%b %Y"),
    "M2": M2.strftime("%b %Y"),
    "M3": M3.strftime("%b %Y"),
    "Beyond": "Beyond " + M3.strftime("%b %Y"),
}

PRIOR_LABEL = _add_months(AS_OF.replace(day=1), -1).strftime("%b %Y")
ASOF_LABEL = AS_OF.strftime("%d %b %Y")
