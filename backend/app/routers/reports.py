"""Analytics endpoints — all served from the local mirror."""

from fastapi import APIRouter

from .. import analytics

router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/pnl")
async def profit_and_loss(year: int | None = None):
    return analytics.pnl(year)


@router.get("/balance")
async def balance_sheet(year: int | None = None, to_date: str | None = None):
    return analytics.balance_sheet(year, to_date)


@router.get("/years")
async def financial_years():
    return {"years": analytics.financial_years()}


@router.get("/accounts/{number}")
async def account(number: int, year: int | None = None):
    return analytics.account_detail(number, year)


@router.get("/vouchers/{series}/{number}")
async def voucher(series: str, number: int, year: int | None = None):
    return analytics.voucher_detail(series, number, year)


@router.get("/costs")
async def costs(year: int | None = None):
    return analytics.cost_structure(year)


@router.get("/clients")
async def clients(year: int | None = None):
    return analytics.clients_overview(year)


@router.get("/payroll")
async def payroll(year: int | None = None):
    return analytics.payroll(year)


@router.get("/projection")
async def projection(year: int | None = None):
    return analytics.projection_baseline(year)


@router.get("/invoices")
async def invoices():
    return {"invoices": analytics.invoices_list()}


@router.get("/company")
async def company():
    from .. import db

    with db.session() as conn:
        return db.get_meta_json(conn, "company", {})
