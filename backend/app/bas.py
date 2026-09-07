"""Mapping of the Swedish BAS chart of accounts to plain-language English
groups. This is the analytical backbone: every P&L line, cost category and
explanation derives from account-number ranges — no manual tagging.

Sign convention (from SIE): debit > 0, credit < 0. Revenue accounts therefore
sum negative; cost accounts positive. `sign` flips values so that revenue and
profit read positive and costs read as positive spend.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Group:
    key: str
    name: str
    lo: int
    hi: int
    sign: int  # multiply summed ledger amounts by this for display


# Income-statement groups, in presentation order
PNL_GROUPS: list[Group] = [
    Group("revenue", "Revenue — what clients paid you", 3000, 3999, -1),
    Group("direct", "Direct costs — subcontractors & goods", 4000, 4999, 1),
    Group("external", "Other external costs — everything you buy", 5000, 6999, 1),
    Group("personnel", "Personnel — salaries, employer tax, pension", 7000, 7699, 1),
    Group("depreciation", "Depreciation & write-downs", 7700, 7899, 1),
    Group("other_op", "Other operating items", 7900, 7999, 1),
    Group("financial", "Financial items — interest", 8000, 8899, -1),
    Group("tax", "Corporate tax", 8900, 8999, 1),
]

BALANCE_GROUPS: list[Group] = [
    Group("assets", "Assets", 1000, 1999, 1),
    Group("equity_liabilities", "Equity & liabilities", 2000, 2999, -1),
]


def pnl_group_for(account: int) -> Group | None:
    for g in PNL_GROUPS:
        if g.lo <= account <= g.hi:
            return g
    return None


def is_pnl_account(account: int) -> bool:
    return 3000 <= account <= 8999


# Plain-language descriptions for accounts common in a small consulting AB.
# Fallback: the account's own Swedish description from the ledger.
ACCOUNT_EXPLAIN: dict[int, str] = {
    1510: "Accounts receivable — invoices you've sent that aren't paid yet",
    1630: "Tax account (skattekonto) — your balance at Skatteverket",
    1930: "Company bank account",
    2081: "Share capital",
    2091: "Retained earnings from previous years",
    2099: "This year's profit or loss",
    2440: "Accounts payable — supplier invoices not yet paid",
    2510: "Corporate tax owed",
    2610: "Output VAT — moms you've charged clients and owe Skatteverket",
    2640: "Input VAT — moms you've paid and get back",
    2641: "Input VAT — moms you've paid and get back",
    2650: "VAT settlement — net moms to pay or receive",
    2710: "Employees' withheld income tax, to be forwarded to Skatteverket",
    2731: "Employer contributions owed (arbetsgivaravgifter)",
    2941: "Accrued social charges",
    3001: "Sales of services within Sweden",
    3041: "Consulting services, 25% VAT",
    3308: "Sales of services to other EU countries",
    5410: "Equipment & supplies — computers, furniture, small purchases",
    5810: "Travel — tickets, hotels, per diems",
    5910: "Advertising & marketing",
    6070: "Client entertainment (representation)",
    6212: "Phone & internet",
    6230: "Data & IT communication",
    6310: "Business insurance",
    6530: "Accounting & bookkeeping services",
    6540: "IT services — software, cloud, subscriptions",
    6570: "Bank charges",
    6991: "Other external costs, deductible",
    7210: "Salaries to white-collar employees",
    7220: "Salaries to company directors",
    7410: "Occupational pension premiums",
    7412: "Occupational pension premiums",
    7510: "Employer contributions (arbetsgivaravgifter) — 31.42% on top of gross salary",
    7533: "Special payroll tax on pension premiums",
    7690: "Other personnel costs",
    8310: "Interest income",
    8410: "Interest costs",
    8423: "Interest on tax account",
    8910: "Corporate income tax (bolagsskatt)",
    8999: "Year-end result booked to the balance sheet",
}


def explain(account: int) -> str | None:
    return ACCOUNT_EXPLAIN.get(account)
