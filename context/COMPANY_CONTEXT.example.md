# Company context & verified reference values — TEMPLATE

*Copy this file to `COMPANY_CONTEXT.md` (gitignored) and fill it in for your
company. It is the AI assistant's grounding file: the agent reads it via
`read_reference` before answering company-specific questions, so everything in
it should be **verified** — from your annual report, your accountant, or a
completed audit session — not guessed. A filled-in example for the fictional
demo company is in `context-demo/COMPANY_CONTEXT.md`.*

*Why this file exists: the ledger shows numbers, not context. The assistant
can see that account 7385 carries 6,650 kr/month; it cannot know that this is
the company car's förmånsvärde, which car, or that you already audited it.
Facts recorded here stop the agent from re-deriving them — possibly wrong —
on every question.*

## 1. Who they are

- Company name, org.nr, location.
- What the business does; number of employees and who is who in the payroll
  rows (`anställd: N`), including start dates.
- Fiscal year, VAT period (monthly/quarterly), who does the bookkeeping.
- Things that DON'T apply (no company car, no inventory, ...) — negative
  facts prevent hallucinated analysis.

## 2. Clients & revenue model

- Main clients/engagements and their approximate levels — lets the assistant
  sanity-check revenue questions without re-deriving from invoices.
- Known risks (client concentration, seasonality).
- Known open items (disputed/overdue invoices).

## 3. People & payroll (verified values)

- Gross salaries per employee and year, withheld-tax levels, pension premiums
  and provider.
- Benefits (company car with the verified förmånsvärde, insurance, ...) and
  which accounts they're booked on.
- Anything payroll-related you have already audited, with the verified
  numbers and a pointer to the audit notes.

## 4. Balance-sheet facts

- Fixed assets and their depreciation schedules.
- Last closed year's result, tax, and how the result was disposed
  (dividend, retained earnings).
- Loans, credit lines, anything unusual.

## 5. Known data-quality issues

- Misbookings you know about and how to treat them.
- Mirror limitations (years with balances only, missing scopes).

## 6. Evidence classes

State the rule the assistant must follow: facts in this file are verified;
everything else must be pulled from the mirror or verified online at the
moment of use.
