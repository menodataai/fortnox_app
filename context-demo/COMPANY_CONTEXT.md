# Company context & verified reference values — DEMO

*Grounding file for **Nordvind Konsult AB** — the **fictional** company in the
demo dataset (`DEMO_MODE=1`, seeded by `backend/scripts/seed_demo.py`). Every
number below matches the seeded ledger by construction. Read this before
answering any question about the company; do not re-derive these facts and get
them wrong. This file plays the role that a real deployment's
`context/COMPANY_CONTEXT.md` plays — see `COMPANY_CONTEXT.example.md` for how
to write one for a real company.*

## 1. Who they are

- **Nordvind Konsult AB**, org.nr 559012-3456 (fictional), Storgatan 24, Umeå.
- AI/data consulting for Nordic mid-size companies. Founded 2023.
- **Two people**: the founder/CEO (anställd: 1 in payroll rows) and one senior
  consultant (anställd: 2, **employed since March 2025** — payroll before that
  is founder-only).
- Fiscal year = calendar year. Bookkeeping is done by an external accountant
  in Fortnox. VAT is reported **quarterly**.
- **No company car** — bilförmån questions do not apply to this company.

## 2. Clients (verified from the invoice ledger)

| Client | Engagement | Level |
|---|---|---|
| Fjällström Energi AB | Monthly retainer, AI-platform work | 120,000 kr/mo 2025 → 135,000 kr/mo 2026 |
| Nordic Health Partners AB | ML forecasting project | 65,000 kr/mo Sep–Dec 2025; 70,000 kr/mo Mar–Jul 2026 |
| Kranholm Logistik AB | One-off workshops | 18,000 kr each |
| Baltika Retail AB | Data-platform sprints Feb–Jun 2025 | 55,000 kr/mo (2025 only) |

- **Client concentration is the known business risk**: Fjällström ≈ 74% of
  2026 revenue. Flag it when relevant.
- **Known open item**: invoice 1035 to Kranholm (22,500 kr incl. VAT, workshop
  follow-up) was due 2026-07-10 and is **overdue**.

## 3. People & payroll (verified values)

| | 2025 | 2026 |
|---|---|---|
| Founder gross (7220) | 48,000 kr/mo | 52,000 kr/mo |
| Consultant gross (7210) | 38,000 kr/mo (from Mar) | 42,000 kr/mo |
| Withheld tax (2710) | 14,400 + 10,100 | 15,900 + 11,400 |
| Pension premiums (7412, SPP) | 3,120 + 2,280/mo | same |

- AGA (7510/2731) is booked at **31.42%** of gross; särskild löneskatt on
  pension (7533/2941) at **24.26%** — both reconcile to the öre.
- Payroll is booked on the 25th (L series); withheld tax + AGA are paid to
  Skatteverket on the 12th of the following month.

## 4. Balance-sheet facts

- **Fixed assets** (register synced): two MacBook Pros (28,000 kr each,
  36-month straight line) and desks/furniture (12,000 kr, 60 months), all
  acquired 2025-02-04, depreciated from March 2025 at **1,755.56 kr/month**
  (7830 → 1229).
- **2025 result**: revenue 2,011,000 kr; profit before tax 312,615 kr;
  bolagsskatt 64,400 kr (8910/2510, paid 2026-03-12); net result 248,215 kr.
- **Årsstämma 2026-04-21**: 120,000 kr dividend decided (2898), paid
  2026-05-05; remainder to retained earnings (2091).
- Opening 2025 items (December-2024 invoice 81,250 kr, supplier debts, payroll
  taxes, 2024 corporate tax 31,000 kr) were all cleared January–March 2025.

## 5. Known data-quality notes

- The mirror ends **at the seed date** — the current month is partial
  (supplier invoices arrive early-month; revenue is invoiced month-end, so the
  current month can show costs but no revenue yet).
- Voucher numbers restart each financial year (A and L series).
- The demo has no 1630 skattekonto flows — tax payments go straight from the
  bank account (a deliberate simplification; say so if asked).

## 6. Evidence classes

Facts here are (a) verified against the seeded ledger by construction. For
anything else: pull vouchers from the mirror, and verify year-specific tax
parameters online at the moment of use, per the hard rules.
