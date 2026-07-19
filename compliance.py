"""
FilingDeck — Compliance Calendar Engine
Calculates upcoming filing deadlines for Indian businesses based on type,
registration date, and state. Covers GST, TDS, ROC, PT, ITR, and more.
"""

from datetime import datetime, date
from dateutil.relativedelta import relativedelta


# ── Business Type Definitions ────────────────────────────────────────────────

BUSINESS_TYPES = {
    "proprietorship": "Proprietorship / Individual",
    "partnership": "Partnership Firm",
    "llp": "Limited Liability Partnership (LLP)",
    "freelancer": "Freelancer / Self-Employed",
}

# ── Filing Definitions ───────────────────────────────────────────────────────
# Each filing has: name, description, frequency, due_day, due_month (for annual),
# applicable_to (list of business types), penalty info

FILINGS = [
    # ── GST Filings ──────────────────────────────────────────────────────────
    {
        "id": "gstr1",
        "name": "GSTR-1",
        "description": "Monthly return for outward supplies (sales)",
        "category": "GST",
        "frequency": "monthly",
        "due_day": 11,
        "applicable_to": ["proprietorship", "partnership", "llp", "pvt_ltd", "opc"],
        "penalty_per_day": 50,
        "max_penalty": 10000,
        "notes": "Due by 11th of following month. ₹50/day late fee (₹25 CGST + ₹25 SGST).",
    },
    {
        "id": "gstr3b",
        "name": "GSTR-3B",
        "description": "Monthly summary return with tax payment",
        "category": "GST",
        "frequency": "monthly",
        "due_day": 20,
        "applicable_to": ["proprietorship", "partnership", "llp", "pvt_ltd", "opc"],
        "penalty_per_day": 50,
        "max_penalty": 10000,
        "notes": "Due by 20th of following month. Interest at 18% p.a. on late tax payment.",
    },
    {
        "id": "gstr9",
        "name": "GSTR-9 (Annual Return)",
        "description": "Annual GST return summarizing all monthly filings",
        "category": "GST",
        "frequency": "annual",
        "due_month": 12,
        "due_day": 31,
        "applicable_to": ["proprietorship", "partnership", "llp", "pvt_ltd", "opc"],
        "penalty_per_day": 200,
        "max_penalty": None,
        "notes": "Due by 31st December. Late fee ₹200/day (₹100 CGST + ₹100 SGST), capped at 0.5% of turnover.",
    },
    {
        "id": "gstr3b_qrmp",
        "name": "GSTR-3B (QRMP Scheme)",
        "description": "Quarterly return for taxpayers opted into QRMP scheme",
        "category": "GST",
        "frequency": "quarterly",
        "due_dates": [
            {"quarter": "Q1 (Apr-Jun)", "due": "22nd July", "month": 7, "day": 22},
            {"quarter": "Q2 (Jul-Sep)", "due": "22nd October", "month": 10, "day": 22},
            {"quarter": "Q3 (Oct-Dec)", "due": "22nd January", "month": 1, "day": 22},
            {"quarter": "Q4 (Jan-Mar)", "due": "22nd April", "month": 4, "day": 22},
        ],
        "applicable_to": ["proprietorship", "partnership", "llp", "pvt_ltd", "opc"],
        "penalty_per_day": 50,
        "max_penalty": 10000,
        "notes": "Due by 22nd of the month following the quarter. Monthly Tax Payment (PMT-06) applies.",
    },

    # ── TDS Filings ──────────────────────────────────────────────────────────
    {
        "id": "tds_quarterly",
        "name": "TDS Return (Form 26Q/24Q)",
        "description": "Quarterly TDS return for tax deducted at source",
        "category": "TDS",
        "frequency": "quarterly",
        "due_dates": [
            {"quarter": "Q1 (Apr-Jun)", "due": "31st July", "month": 7, "day": 31},
            {"quarter": "Q2 (Jul-Sep)", "due": "31st October", "month": 10, "day": 31},
            {"quarter": "Q3 (Oct-Dec)", "due": "31st January", "month": 1, "day": 31},
            {"quarter": "Q4 (Jan-Mar)", "due": "31st May", "month": 5, "day": 31},
        ],
        "applicable_to": ["partnership", "llp", "pvt_ltd", "opc"],
        "penalty_per_day": 200,
        "max_penalty": None,
        "notes": "Late filing fee ₹200/day u/s 234E. Penalty up to ₹1 lakh u/s 271H.",
    },

    # ── Income Tax ───────────────────────────────────────────────────────────
    {
        "id": "itr",
        "name": "Income Tax Return (ITR)",
        "description": "Annual income tax return filing",
        "category": "Income Tax",
        "frequency": "annual",
        "due_month": 7,
        "due_day": 31,
        "applicable_to": ["proprietorship", "partnership", "llp", "pvt_ltd", "opc", "freelancer"],
        "penalty_per_day": None,
        "max_penalty": 10000,
        "notes": "Due 31st July (non-audit) / 31st October (audit). Late fee ₹5,000 u/s 234F (₹1,000 if income < ₹5L).",
    },
    {
        "id": "advance_tax",
        "name": "Advance Tax Installments",
        "description": "Quarterly advance tax payments if tax liability > ₹10,000",
        "category": "Income Tax",
        "frequency": "quarterly",
        "due_dates": [
            {"quarter": "1st Installment", "due": "15th June", "percentage": "15%", "month": 6, "day": 15},
            {"quarter": "2nd Installment", "due": "15th September", "percentage": "45%", "month": 9, "day": 15},
            {"quarter": "3rd Installment", "due": "15th December", "percentage": "75%", "month": 12, "day": 15},
            {"quarter": "4th Installment", "due": "15th March", "percentage": "100%", "month": 3, "day": 15},
        ],
        "applicable_to": ["proprietorship", "partnership", "llp", "pvt_ltd", "opc", "freelancer"],
        "penalty_per_day": None,
        "max_penalty": None,
        "notes": "Interest u/s 234B & 234C for non-payment or short payment.",
    },



    # ── Professional Tax (Maharashtra) ───────────────────────────────────────
    {
        "id": "pt_monthly",
        "name": "Professional Tax Return (PTRC)",
        "description": "Monthly PT return for employers deducting PT from employees",
        "category": "Professional Tax",
        "frequency": "monthly",
        "due_day": 15,  # Due by last date of the month, simplified
        "applicable_to": ["partnership", "llp", "pvt_ltd", "opc"],
        "penalty_per_day": None,
        "max_penalty": None,
        "notes": "Monthly return for employers in Maharashtra. Due by end of month following the salary month.",
    },


]


def get_applicable_filings(business_type):
    """Get all filings applicable to a given business type."""
    return [f for f in FILINGS if business_type in f["applicable_to"]]


def calculate_upcoming_deadlines(business_type, state="maharashtra", months_ahead=6):
    """
    Calculate upcoming filing deadlines for a business.
    
    Args:
        business_type: One of the keys from BUSINESS_TYPES
        state: State for state-specific compliance (default: maharashtra)
        months_ahead: How many months ahead to show deadlines
    
    Returns:
        List of upcoming deadlines sorted by due date
    """
    today = date.today()
    end_date = today + relativedelta(months=months_ahead)
    applicable = get_applicable_filings(business_type)
    deadlines = []

    for filing in applicable:
        freq = filing["frequency"]

        if freq == "monthly":
            # Generate monthly deadlines
            current = today.replace(day=1)
            for _ in range(months_ahead + 1):
                due_day = min(filing["due_day"], 28)  # Safe day
                # Monthly filings are for the previous month, due in current month
                try:
                    due_date = current.replace(day=due_day)
                except ValueError:
                    due_date = current.replace(day=28)

                if today <= due_date <= end_date:
                    # Filing period is the previous month
                    period_month = current - relativedelta(months=1)
                    deadlines.append({
                        "name": filing["name"],
                        "description": filing["description"],
                        "category": filing["category"],
                        "due_date": due_date,
                        "due_date_formatted": due_date.strftime("%d %b %Y"),
                        "period": period_month.strftime("%b %Y"),
                        "days_left": (due_date - today).days,
                        "status": _get_status(due_date, today),
                        "penalty_info": filing["notes"],
                    })
                current += relativedelta(months=1)

        elif freq == "quarterly":
            # For quarterly filings, show the specific dates
            if "due_dates" in filing:
                for qtr in filing["due_dates"]:
                    q_month = qtr.get("month")
                    q_day = qtr.get("day")
                    if q_month and q_day:
                        # Try this year and next year to see which falls in the window
                        try:
                            d1 = date(today.year, q_month, q_day)
                        except ValueError:
                            d1 = date(today.year, q_month, 28)
                            
                        try:
                            d2 = date(today.year + 1, q_month, q_day)
                        except ValueError:
                            d2 = date(today.year + 1, q_month, 28)
                            
                        for possible_date in (d1, d2):
                            if today <= possible_date <= end_date:
                                deadlines.append({
                                    "name": filing["name"],
                                    "description": filing["description"],
                                    "category": filing["category"],
                                    "due_date": possible_date,
                                    "due_date_formatted": possible_date.strftime("%d %b %Y"),
                                    "period": qtr["quarter"],
                                    "days_left": (possible_date - today).days,
                                    "status": _get_status(possible_date, today),
                                    "penalty_info": filing["notes"],
                                })

        elif freq == "annual":
            # Check if this year's deadline is upcoming
            if "due_month" in filing and "due_day" in filing:
                try:
                    due_this_year = date(today.year, filing["due_month"], filing["due_day"])
                except ValueError:
                    due_this_year = date(today.year, filing["due_month"], 28)

                if due_this_year < today:
                    # This year's already passed, show next year
                    try:
                        due_this_year = date(today.year + 1, filing["due_month"], filing["due_day"])
                    except ValueError:
                        due_this_year = date(today.year + 1, filing["due_month"], 28)

                if due_this_year <= end_date:
                    deadlines.append({
                        "name": filing["name"],
                        "description": filing["description"],
                        "category": filing["category"],
                        "due_date": due_this_year,
                        "due_date_formatted": due_this_year.strftime("%d %b %Y"),
                        "period": f"FY {today.year - 1}-{str(today.year)[2:]}",
                        "days_left": (due_this_year - today).days,
                        "status": _get_status(due_this_year, today),
                        "penalty_info": filing["notes"],
                    })

    # Sort by due date (soonest first), filtering out entries without real dates
    deadlines.sort(key=lambda x: x["due_date"])
    return deadlines


def _get_status(due_date, today):
    """Determine urgency status of a deadline."""
    days_left = (due_date - today).days
    if days_left < 0:
        return "overdue"
    elif days_left <= 3:
        return "critical"
    elif days_left <= 7:
        return "urgent"
    elif days_left <= 15:
        return "upcoming"
    else:
        return "safe"


def get_compliance_summary(business_type):
    """Get a summary of all compliance requirements for a business type."""
    applicable = get_applicable_filings(business_type)
    categories = {}
    for filing in applicable:
        cat = filing["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append({
            "name": filing["name"],
            "description": filing["description"],
            "frequency": filing["frequency"],
            "notes": filing["notes"],
        })
    return categories
