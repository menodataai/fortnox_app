# Swedish tax & accounting reference (for the AI assistant)

*On-demand reference for the F8/F9 assistant. Compiled 2026-07-31, with each
section's current-year values verified online against authoritative Swedish
sources (skatteverket.se, regeringen.se, riksdagen.se, riksgalden.se,
bolagsverket.se) at compile time. Companion to
[COMPANY_CONTEXT.example.md](COMPANY_CONTEXT.example.md) — that file holds the
company's own verified numbers and known data-quality issues; **this** file holds the general
Swedish rules, formulas, and structures those numbers plug into.*

## How to use this file

- **Concepts and formulas here are stable; the numbers are not.** Every
  year-specific value is tagged **`(2026 — ⚠ verify at use)`** (a few sections
  write it `(2026 — ⚠ verify)` — same meaning). When such a value carries a
  conclusion, **re-verify it online against a primary source and cite it**
  (Hard rule 3 / the parameter-enumeration rule). The structural rules — how a
  bracket works, what is in a benefit basis, how reverse charge flows — change
  rarely and can be relied on.
- **Prefer the ledger for facts about *this* company**; use this file for the
  *rules*. The worked numbers in this file are **illustrative** (a fictional
  EV, round lease figures); the company's own verified values live in
  `COMPANY_CONTEXT.md` and, where present, the local audit case studies —
  always prefer those for facts about this company.
- **The single most-load-bearing rule** (the assistant has gotten it wrong):
  §1.2 — the 20 % statlig inkomstskatt applies **only to the slice of income
  above the brytpunkt**, never to a whole amount.
- Swedish terms are glossed in English on first use; the full bilingual
  glossary is in `swedish_english_financial_glossary.md`.

## Contents

1. **Personal income tax** — kommunalskatt, statlig skatt, skiktgräns/brytpunkt,
   grundavdrag, jobbskatteavdrag, marginalskatt, the `tax(FI)` formula, PGI/SGI.
2. **Employer & benefit taxes** — arbetsgivaravgifter (31.42 %), särskild
   löneskatt, the **bilförmån** förmånsvärde formula (full derivation), other
   förmåner incl. **friskvård** (bidrag vs naturaförmån).
3. **Fåmansföretag & the 3:12 rules** — gränsbelopp, förenklings-/huvudregeln,
   lönebaserat utrymme, the 2026 reform (löneuttagskrav abolished), K10, dividends.
4. **Corporate income tax & untaxed reserves** — bolagsskatt 20.6 %,
   periodiseringsfond, schablonintäkt, dividend at company level.
5. **Moms (VAT)** — rates, input/output, the **50 % car-lease rule**, reverse
   charge, zero-rated vs exempt, momsdeklaration periods, gross vs net.
6. **Skattekonto, F-skatt & the tax calendar** — the running tax account, PAYE/AGI,
   preliminärskatt, filing & payment deadlines, the ledger tax-account map.

> **Not tax advice.** Every tax-adjacent conclusion the assistant draws from this
> reference must carry the "estimate — confirm with your accountant" framing.

---

## 1. Personal income tax (inkomstskatt för privatpersoner)

*Scope: tax on an individual's employment income (tjänst) — salary plus taxable benefits (förmåner) such as a company car. This is the **driver's** tax, entirely separate from the company's arbetsgivaravgifter (AGA) and bolagsskatt. The worked example below combines an illustrative **49,000 kr/mo salary** with an illustrative **6,650 kr/mo bilförmån** — take the actual values from COMPANY_CONTEXT / the ledger.*

### 1.1 The two layers

Employment income is taxed in two stacked layers on the **beskattningsbar förvärvsinkomst** (taxable earned income = gross income − grundavdrag):

| Layer | Swedish term | Rate | Applies to |
|---|---|---|---|
| Municipal | **kommunalskatt** (municipal income tax, flat) | ~29–35% depending on municipality; **32.4%** used in the worked examples **(2026 — ⚠ verify at use)** | *All* taxable earned income (flat, from the first krona above grundavdrag) |
| State | **statlig inkomstskatt** (state income tax) | **+20%** | **Only** the slice of taxable income **above the skiktgräns** |

- Kommunalskatt is set per municipality (kommun + region); it does **not** change with income — it is a flat percentage. 32.4% is an illustrative mid-range rate; verify the individual's registered kommun at use.
- Statlig inkomstskatt is a single 20% bracket (the former top "värnskatt"/5% tier was abolished in 2020). There is only **one** state bracket in 2026.

### 1.2 THE KEY RULE — state tax is marginal, not average

> **The 20% statlig inkomstskatt applies ONLY to the portion of income ABOVE the brytpunkt — never to the whole income.**

This is the mistake to avoid: raising someone past the brytpunkt does **not** retroactively tax their entire salary at +20%. Only the krona-for-krona excess above the line is hit. A benefit that pushes income from just below to just above the line costs 20% on the **overshoot only**.

**Worked example (illustrative car-benefit tax effect):**
- Salary **49,000 kr/mo = 588,000 kr/yr** → *below* the brytpunkt (660,400) on its own.
- Add bilförmån **6,650 kr/mo = 79,800 kr/yr** → total förvärvsinkomst = **667,800 kr/yr**.
- Amount poking above the brytpunkt = 667,800 − 660,400 = **7,400 kr**.
- State-tax effect of the benefit = 20% × 7,400 = **1,480 kr/yr ≈ 123 kr/mo**.
- The *rest* of the benefit (79,800 − 7,400 = 72,400 kr) is taxed only at kommunal 32.4%.
- ✗ WRONG: "the benefit is taxed at 18 pp (52.4% − 34.4%) extra" applied to the *whole* 79,800 kr. That would claim ~14,364 kr/yr of state-tax cost — nearly 10× the true 1,480 kr.

### 1.3 Skiktgräns vs. brytpunkt

Two different reference points — do not conflate them:

| Term | Measured on | 2026 value (under-66) | Meaning |
|---|---|---|---|
| **Skiktgräns** (bracket threshold) | *Taxable* income (after grundavdrag) | **643,000 kr/yr** **(2026 — ⚠ verify at use)** | Above this, +20% state tax kicks in |
| **Brytpunkt** (breakpoint) | *Gross* income (before grundavdrag) | **660,400 kr/yr ≈ 55,033 kr/mo** **(2026 — ⚠ verify at use)** | The gross salary+benefit level at which you cross the skiktgräns |

- Relationship: **brytpunkt = skiktgräns + grundavdrag** at that income level → 643,000 + **17,400** ≈ 660,400 kr **(2026 — ⚠ verify at use)**. The 17,400 kr is the grundavdrag applicable at the breakpoint.
- Practical use: compare a person's **gross annual income** (salary + förmåner) to the **brytpunkt**. If below, no state tax at all.
- Note there is a *higher* brytpunkt for those who have turned **66 by the start of the year** (≈ 760,500 kr/yr in 2026 **— ⚠ verify at use**), because their grundavdrag is larger. For working-age employees use the standard 660,400.

### 1.4 Grundavdrag (basic allowance)

- **Grundavdrag** = a basic allowance deducted from gross earned income before tax; you pay *no* income tax on this slice.
- It is **not flat** — it rises then falls with income along a statutory schedule (a function of prisbasbelopp), reaching a **minimum floor of ~17,400 kr** at higher incomes (which is why it equals the skiktgräns→brytpunkt gap). At low incomes it is much larger (up to ~ several tens of thousands of kr), which is what makes low earnings lightly taxed.
- For incomes in the worked example's range (600k–700k/yr), grundavdrag sits at its **floor (~17,400 kr)** and is effectively constant — so it can be treated as a fixed ~17,400 kr in marginal reasoning at this income level. **(2026 — ⚠ verify at use)**
- Because grundavdrag shrinks toward this floor as income rises, **brytpunkt > skiktgräns** always.

### 1.5 Jobbskatteavdrag (JSA — earned-income tax credit)

- **Jobbskatteavdrag** = a *tax reduction* (skattereduktion), subtracted from computed tax, that rewards earned income (only work income qualifies — not pensions or benefits-in-lieu). It lowers effective tax on wages.
- **Strengthened for 2026** (~17 bn kr reform): the ordinary JSA was raised for work incomes above ~192,000 kr/yr.
- **2026 shape (load-bearing):**
  - Rises with income, reaching its **maximum at ≈ 478,336 kr/yr (≈ 40,000 kr/mo)** **(2026 — ⚠ verify at use)**.
  - **Maximum ≈ 52,400 kr/yr (4,366 kr/mo)** **(2026 — ⚠ verify at use)**.
  - **Phase-out (avtrappning) abolished** (since 2025): JSA no longer tapers off at high incomes.
- **Consequence the assistant must use:** for any income **at or above the plateau (~478,336 kr/yr)**, JSA is a **constant ~52,400 kr/yr** — it does **not** vary with income. Therefore in a **salary comparison between two figures both above the plateau, JSA CANCELS** and can be dropped entirely. (This simplification was previously missed. In the worked examples, both salaries compared are well above the plateau, so JSA is constant across every scenario compared.)
- Note: förmåner (the car benefit) **do** count as earned income for JSA purposes, but since the driver is already on the plateau, JSA is maxed and flat regardless.

### 1.6 Marginalskatt (marginal tax rate) by bracket, 2026

Marginal rate = tax on the *next* krona of gross income. Assuming kommunal 32.4% and JSA on its flat plateau (so JSA adds 0 pp at the margin in the relevant range):

| Gross income band (under-66) | Layers at the margin | Approx. marginalskatt |
|---|---|---|
| 0 → grundavdrag floor region | none (covered by grundavdrag) | ~0% |
| grundavdrag → **660,400 kr/yr** (brytpunkt) | kommunal only | **≈ 32.4%** **(2026 — ⚠ verify at use)** |
| **above 660,400 kr/yr** | kommunal + statlig 20% | **≈ 52.4%** **(2026 — ⚠ verify at use)** |

- (Below the JSA plateau, ~192k–478k/yr, the *effective* marginal rate is a few pp lower because JSA is still rising — not relevant at the worked-example salary levels, but note it exists.)
- **The car benefit is taxed as ordinary income:** the bilförmån (6,650 kr/mo in the worked example) is added to taxable förvärvsinkomst and taxed at the driver's marginal rate for that slice. It is **not cash** — the driver pays income tax on an amount they never receive as money; the company separately pays AGA (31.42%) on it (see COMPANY_CONTEXT). Keep the three views distinct: (1) driver income-tax effect, (2) company AGA, (3) zero P&L cash effect (7390 nets against 7399).

### 1.7 Compact tax(FI) formula for computation

For an individual with total **förvärvsinkomst FI** (= salary + all taxable förmåner, kr/yr), the annual income tax is well-approximated by:

```
tax(FI) ≈ 0.324 × (FI − grundavdrag) + 0.20 × max(0, FI − brytpunkt) − JSA

where (2026 — ⚠ verify each at use):
  grundavdrag ≈ 17,400 kr   (floor value, valid for FI in the ~430k–700k range)
  brytpunkt   ≈ 660,400 kr
  JSA         ≈ 52,400 kr    (constant for FI ≥ ~478,336 kr/yr; CANCELS in comparisons in this range)
  kommunal    = 0.324        (illustrative mid-range rate; use the driver's actual kommun rate)
```

- **kyrkoavgift (church fee, ~1–1.5%) is IGNORED** — it applies only to members of a religious community and is not an income tax; state it as excluded.
- For a **marginal** question (effect of one more krona / one benefit), skip the formula and apply §1.2: kommunal on the whole added slice, +20% only on the part above brytpunkt, JSA unchanged.
- Sanity check with the worked example: the *marginal* effect of the 79,800 kr/yr car benefit = 0.324 × 79,800 + 0.20 × 7,400 ≈ 25,855 + 1,480 ≈ **27,335 kr/yr** total income tax on the benefit (of which the state-tax part is the 1,480/yr ≈ 123/mo highlighted above).

### 1.8 The non-tax price of a low salary

Minimizing salary to cut tax has costs that are **not** in the tax formula — flag these whenever advising on salary level:

- **PGI (pensionsgrundande inkomst)** — pension-qualifying income. Public pension accrues at **18.5%** of PGI, but only up to a ceiling of **7.5 inkomstbasbelopp (IBB)**. IBB 2026 = **80,600 kr** → PGI ceiling ≈ **604,500 kr/yr** **(2026 — ⚠ verify at use)**. Salary above this earns no extra public pension; salary far below it permanently lowers pension accrual.
- **SGI (sjukpenninggrundande inkomst)** — the base for **sjukpenning** (sick pay) and **föräldrapenning** (parental pay). Capped at **~8 prisbasbelopp (pbb)** for sjukpenning / **10 pbb** for föräldrapenning. pbb 2026 = **59,200 kr** → sjukpenning SGI ceiling ≈ **473,600 kr/yr** **(2026 — ⚠ verify at use)**. A very low salary can cut sick-pay and parental-benefit entitlement to near zero.
- Bilförmån and other **förmåner do count** toward PGI/SGI (they are förvärvsinkomst), partially offsetting a low cash salary — but pension/benefit planning should be raised explicitly, not buried.

### Sources

- Skatteverket — *När ska man betala statlig inkomstskatt och hur hög är den?* (skiktgräns/brytpunkt 2026): https://www.skatteverket.se/privat/etjansterochblanketter/svarpavanligafragor/inkomstavtjanst/privattjansteinkomsterfaq/narskamanbetalastatliginkomstskattochhurhogarden.5.10010ec103545f243e8000166.html
- Skatteverket — *Skiktgränser, brytpunkter, prisbasbelopp m.m. 2020 till 2026* (PDF): https://www.skatteverket.se/download/18.1522bf3f19aea8075ba4a0/1765193942058/tabell-skiktgranser-2020-2026.pdf
- Skatteverket — *Belopp och procentsatser för inkomståret 2026* (PDF): https://www.skatteverket.se/download/18.1522bf3f19aea8075ba3285/1767885159120/belopp-och-procentsatser-for-inkomstaret-2026.pdf
- Sveriges riksdag — *Förordning (2025:1050) om skiktgräns för statlig inkomstskatt för beskattningsåret 2026*: https://www.riksdagen.se/sv/dokument-och-lagar/dokument/svensk-forfattningssamling/forordning-20251050-om-skiktgrans-for-statlig_sfs-2025-1050/
- Ekonomifakta — *Jobbskatteavdraget* (max belopp, avtrappning slopad): https://www.ekonomifakta.se/sakomraden/skatt/skatt-pa-arbete/jobbskatteavdraget_1212612.html
- Regeringen — *Beräkningskonventioner 2026* (PDF): https://www.regeringen.se/contentassets/1ed01e00001b42e5ad8d47433db63ece/berakningskonventioner_2026.pdf

---

## 2. Employer & benefit taxes (arbetsgivaravgifter och förmåner)

*How the company pays tax on what it pays its people — cash wages and benefits alike. The centerpiece is the **bilförmån** (company-car benefit); the worked-example numbers below are **illustrative** (a fictional EV) — take the company's actual registered values from payroll / COMPANY_CONTEXT. Re-verify every year-tagged number online at the moment it carries a conclusion.*

### 2.1 Arbetsgivaravgifter (AGA) — employer social contributions

**Arbetsgivaravgifter** (employer social-security contributions) are paid by the employer *on top of* gross pay — they are not withheld from the employee. The full rate is **31.42 % (2026 — ⚠ verify at use)** and has been stable for several years.

**What it is levied on:** the sum of **kontant lön** (cash wage) **+ skattepliktiga förmåner** (taxable benefits) per employee per month. A taxable benefit — the car benefit, a taxable perk — is *förmånsgrundande*: it enlarges the AGA base exactly as if it were cash, even though no cash changes hands.

**Ledger formula (ties to the öre):**

```
account 7510 AGA  =  31.42 %  ×  (kontant lön + skattepliktiga förmåner)
                     per employee, per month
```

This identity should reconcile payroll to the ledger: when `7510` = **31.42 % (2026 — ⚠ verify)** × (wage + benefits) matches every month to the öre, the AGI-declared amounts agree with the books.

**Sub-components** (the 31.42 % is a bundle of statutory avgifter; **2026 — ⚠ verify at use**):

| Component | Rate |
|---|---|
| Ålderspensionsavgift (old-age pension) | 10.21 % |
| Efterlevandepensionsavgift (survivor's pension) | 0.60 % |
| Sjukförsäkringsavgift (health insurance) | 3.55 % |
| Föräldraförsäkringsavgift (parental insurance) | 2.60 % |
| Arbetsskadeavgift (work-injury) | 0.20 % |
| Arbetsmarknadsavgift (labour market) | 2.64 % |
| Allmän löneavgift (general payroll levy) | 11.62 % |
| **Total** | **31.42 %** |

Only the **ålderspensionsavgift (10.21 %)** is a genuine pension contribution; the large **allmän löneavgift (11.62 %)** is effectively a tax, not an insurance premium.

**Reduced rates (edge cases — flag if any employee qualifies):**
- **Older employees:** for those who have reached the higher age (66+; born **1959 or earlier for 2026 — ⚠ verify age threshold**), only the ålderspensionsavgift **10.21 % (2026 — ⚠ verify)** is levied. Born **1938 or earlier → 0 %**.
- **Young employees / växa-stöd:** temporary reliefs on the first employee or for the young exist year to year; **verify current eligibility and caps at use (2026 — ⚠ verify)**.

### 2.2 Särskild löneskatt (SLF) — special payroll tax

**Särskild löneskatt på pensionskostnader** (special payroll tax on pension costs) is **24.26 % (2026 — ⚠ verify at use)**, levied on the company's **avsättning till pension** (pension provision / premiums paid), e.g. tjänstepension premiums booked on `7410`.

**Why pension escapes ordinary AGA:** an occupational-pension premium is *not* salary and confers no immediate PGI/SGI, so it is **not** part of the AGA base above. Instead the state levies SLF on it — a lighter charge (**24.26 %** vs **31.42 %**) that broadly stands in for the social-fee element. In the ledger this appears as `7530` (cost) with the liability on `2514 särskild löneskatt`. SLF also applies to a few other items (e.g. certain foreign-pension and profit-sharing-foundation contributions) — rare here.

### 2.3 Bilförmån (company-car benefit) — the centerpiece

A **bilförmån** arises when an employee may use a company car privately. Its **förmånsvärde** (benefit value) is a statutory *schablon* (standard formula), taxed as the driver's income and swept into the AGA base — it is **not** based on actual private mileage.

**The formula (current "bonus-malus"-era rules, post-2021 reform per prop. 2020/21:156):**

```
Yearly förmånsvärde =
    prisbasbeloppsdelen        0.29 × prisbasbelopp
  + ränterelaterat belopp      (0.7 × SLR + 1 pp) × förmånsgrundande nybilspris
  + prisrelaterat belopp       13 % of nybilspris up to 7.5 pbb
                             +  20 % of the part above 7.5 pbb
  + fordonsskatt               actual vehicle tax for the year
  ( + extrautrustning is inside the nybilspris basis, see below )
```

**2026 parameters (⚠ verify at use):**

| Parameter | 2026 value | Source |
|---|---|---|
| Prisbasbelopp (pbb) | **59,200 kr (2026 — ⚠ verify)** | regeringen.se / SCB |
| Prisbasbeloppsdelen = 0.29 × pbb | **17,168 kr (2026 — ⚠ verify)** | 0.29 × 59,200 |
| Statslåneränta (SLR) 30 Nov 2025 | **2.55 % (2026 — ⚠ verify)** | Riksgälden |
| Räntedel coefficient = 0.7 × SLR + 1 pp | **2.785 % (2026 — ⚠ verify)** | 0.7 × 2.55 + 1.00; SLR floored at 0.50 % |
| Prisrelaterat, below 7.5 pbb | **13 % (2026 — ⚠ verify)** | prop. 2020/21:156 |
| Prisrelaterat, above 7.5 pbb | **20 % (2026 — ⚠ verify)** | prop. 2020/21:156 |
| 7.5 × pbb threshold | **444,000 kr (2026 — ⚠ verify)** | 7.5 × 59,200 |
| EV nedsättning (electric/hydrogen) | **350,000 kr (2026 — ⚠ verify)** | Skatteverket |
| Lägsta förmånsvärde (≈ 40 % pbb) | **23,680 kr (2026 — ⚠ verify)** | Skatteverket |

Because both worked-example bases fall **below** the 7.5-pbb threshold (444,000), the räntedel and prisdel combine into a single coefficient on the whole basis: **2.785 % + 13 % = 15.785 % (2026 — ⚠ verify)**.

**Worked derivation — as a payroll system might (wrongly) register it (illustrative, 6,650 kr/mo):**

```
nybilspris basis (as registered = order total)   744,500
  − EV reduction                                 −350,000  (2026 — ⚠ verify)
  = förmånsgrundande basis                         394,500
    × 15.785 %                                  =   62,271.83
  + prisbasbeloppsdelen (0.29 × 59,200)         =   17,168
  + fordonsskatt                                =      360
  = yearly förmånsvärde                         ≈   79,800  /12
  = 6,650.00 kr/mo   (2026 — ⚠ verify at use)
```

**Worked derivation — the CORRECT basis (should be 6,301.40 kr/mo):**

```
fastställt nybilspris (from the billista)        612,000
  + extrautrustning incl. winter wheels          = 106,000
  = correct nybilspris                             718,000
  − EV reduction                                 −350,000  (2026 — ⚠ verify)
  = förmånsgrundande basis                         368,000
    × 15.785 %  + 17,168 + 360                  ≈   75,617  /12
  = 6,301.40 kr/mo   (2026 — ⚠ verify at use)
```

The gap (**≈ 349 kr/mo** in the illustration) is a **basis** error, not a missing EV reduction: payroll used the order total **744,500** (including a **9,500 kr delivery fee** and **no discount deducted**) instead of the **fastställt nybilspris 612,000** from Skatteverket's *billista* plus extrautrustning. This error pattern occurs in real payrolls — when found, **flag for the accountant, do not "fix" the books.**

**What IS and IS NOT in the basis (structural — no year tag):**
- **IN:** the **fastställt nybilspris** (Skatteverket's list price for the exact model/year — look up the model code in the *billista*), plus **extrautrustning** at market value — **winter tyres (vinterdäck) are extrautrustning** per Skatteverket and belong in the basis.
- **NOT IN:** **leveransavgift / delivery fees**, and **rabatter** — discounts never lower the basis because the list price, not the paid price, is used. (A calculator run that omits the winter wheels will come out too *low*.)

**EV / miljöbil reduction (nedsättning):** for cars first taxable after **2022-06-30**, the förmånsgrundande nybilspris is reduced by a fixed amount by environmental technology — **electric & hydrogen: 350,000 kr (2026 — ⚠ verify)** (plug-in hybrid and gas cars get smaller reductions). The reduction is **capped at 50 % of the nybilspris**. In the illustration 50 % × 718,000 = 359,000 > 350,000, so the full **350,000 (2026 — ⚠ verify)** applies. Whether payroll actually applied it can be proven by reverse-engineering the registered value from the monthly benefit rows.

**How the benefit flows in the ledger (nets to zero in the P&L):**

| Account | Entry | Effect |
|---|---|---|
| `7390` Förmåner | +6,650.00 (debit, cost) | books the benefit as a personnel cost |
| `7399` Motkontering | −6,650.00 (credit) | grosses it back out |
| **Net P&L impact** | **0** | the benefit is the **driver's** taxable income, not a company cash cost |
| `7510` AGA | 31.42 % × 6,650.00 = **2,089.43 kr/mo (2026 — ⚠ verify)** | the company's **only** real cost of the benefit |

So the employer's cost of the car benefit is **exactly the AGA on it** — **2,089.43 kr/mo (2026 — ⚠ verify)** in the illustration (or ≈ 1,980 kr/mo on the correct basis). Keep three views distinct: (a) the P&L-neutral 7390/7399 pair, (b) the AGA on `7510` (employer cost), (c) the driver's own income-tax effect (a separate number; see §1 for the state-tax slice).

**Drivmedelsförmån (fuel/charging benefit):** paying for the driver's **private** fuel or charging is a **separate** taxable benefit from the car benefit itself, generally valued at market cost **× 1.2**. Note the current carve-out: **free charging at the workplace** has been temporarily **tax-free** — **verify the rule and its expiry at use (2026 — ⚠ verify)**; employer-paid **home/public** private charging is normally a taxable drivmedelsförmån.

### 2.4 Övriga förmåner & skattefria förmåner (other and tax-free perks)

- **Övriga skattepliktiga förmåner** (other taxable benefits) — e.g. small recurring benefit lines of a few hundred kr/mo on `7390/7399` (meals, minor perks) — flow exactly like the car benefit: into the AGA base and the driver's income.
- **Sjukvårdsförsäkring** (private health-care insurance) is **taxable — it is not friskvård**: Skatteverket's schablon values **60 % of the premium (⚠ verify)** as the förmånsvärde (the rest is deemed tax-free rehab/prevention). The premium is a cost on `7621`; the 60 % value flows through `7390/7399` into the AGA base like any benefit.
- **Skattefria förmåner** (tax-free perks — structural, but the caps are year-specific): **arbetsredskap** (work tools) of limited private value, workplace refreshments, certain safety/health items — and **motion & friskvård**, which has enough structure to get its own block below.

**Motion & friskvård — one perk, two independent tax-free forms** (personalvårdsförmån):

| | **Friskvårdsbidrag** (allowance) | **Naturaförmån** (employer-provided) |
|---|---|---|
| Who picks & pays | Employee picks the activity and pays; employer reimburses | **Employer decides and holds the agreement**; pays the supplier directly |
| Cap | **5,000 kr/yr per employee incl. moms (2026 — ⚠ verify)**; non-exercise activities (massage etc.) also ≤ **1,000 kr/occasion** | No kronor cap — must instead be **"enklare slag och av mindre värde"** (a normal-standard gym membership qualifies) |
| If exceeded | **The entire allowance becomes taxable**, not just the excess — a cliff, not marginal | The benefit becomes taxable when it is no longer "modest" |
| Ledger shape | Reimbursement to the employee; cost on a `7699`-type account; **no** `7390/7399` rows | Supplier invoice paid by the company; cost on a `7699`-type account; **no** `7390/7399` rows |

- Both forms require **equal terms for all staff**, and they **combine freely**: a company-paid gym arrangement does *not* consume the 5,000 kr bidrag headroom.
- **Substance over form:** if employees in practice choose their own activities and the employer just pays invoices exceeding 5,000 kr/person, Skatteverket can recharacterize the arrangement as an over-cap friskvårdsbidrag → fully taxable. Keep the contract/invoice showing the **company** as the purchasing party.
- **VAT tell:** sports/gym services carry **6 % moms** — a supplier invoice at 6 % is consistent with a motion/friskvård service.
- **Not to be confused with personalfest:** one-off staff events (julbord, kickoff) are **intern representation** (`7631/7632`) — a separate regime, not friskvård.

### 2.5 PGI / SGI consequence (cross-reference to §1)

Only **kontant lön + skattepliktiga förmåner** build **PGI** (pensionsgrundande inkomst) and **SGI** (sjukpenninggrundande inkomst); pension premiums (SLF-taxed) do **not**. A taxable **förmån** therefore *does* raise PGI/SGI, but only up to the statutory ceilings (SGI ≈ 8 pbb; PGI ≈ 7.5 IBB). A salary in the 45–55k/mo range plus a car benefit typically sits near those ceilings — the detailed brytpunkt / ceiling analysis is in **§1**.

### Sources

- Skatteverket — Belopp och procent inkomstår 2026: https://www.skatteverket.se/privat/skatter/beloppochprocent/2026.4.1522bf3f19aea8075ba21.html
- Skatteverket — Belopp och procentsatser för inkomståret 2026 (PDF): https://www.skatteverket.se/download/18.1522bf3f19aea8075ba3285/1767885159120/belopp-och-procentsatser-for-inkomstaret-2026.pdf
- Skatteverket — Arbetsgivaravgifter: https://www.skatteverket.se/foretag/arbetsgivare/arbetsgivaravgifterochskatteavdrag/arbetsgivaravgifter.4.233f91f71260075abe8800020817.html
- Skatteverket — Särskild löneskatt: https://www.skatteverket.se/foretag/drivaforetag/foretagsformer/aktiebolag/sarskildloneskatt.4.6e8a1495181dad540843a8.html
- Skatteverket — Personalvårdsförmån, motion och friskvård: https://www.skatteverket.se/foretag/arbetsgivare/formaner/personalvardsformanmotionochfriskvard.4.7459477810df5bccdd4800014540.html
- Skatteverket — Bilförmån (arbetsgivare): https://www.skatteverket.se/foretag/arbetsgivare/lonochersattning/formaner/bilforman.4.3016b5d91791bf546791919.html
- Skatteverket — Bilförmånsberäkning (e-tjänst): https://www7.skatteverket.se/portal/bilformansberakning/
- Skatteverket — Beräkna bilförmånsvärde (Rättslig vägledning): https://www4.skatteverket.se/rattsligvagledning/321424.html
- Skatteverket — Förmånsvärde miljöbilar: https://www.skatteverket.se/privat/skatter/arbeteochinkomst/formaner/bilforman/miljobilar.4.3f4496fd14864cc5ac9e89a.html
- Skatteverket — Drivmedelsförmån: https://www.skatteverket.se/foretag/arbetsgivare/lonochersattning/formaner/bilforman/drivmedelsforman.4.3016b5d91791bf546791a89.html
- Prop. 2020/21:156 Justerad beräkning av bilförmån: https://www.riksdagen.se/sv/dokument-och-lagar/dokument/proposition/justerad-berakning-av-bilforman_h803156/html/
- Regeringen — Prisbasbelopp för 2026 fastställt: https://www.regeringen.se/artiklar/2025/09/prisbasbelopp-for-2026-faststallt/
- Riksgälden / statslåneränta 30 Nov 2025 = 2.55 %

---

## 3. Fåmansföretag & the 3:12 rules (utdelning och K10)

*Reference for dividend planning at a small fåmansföretag. The 3:12 rules were **reformed effective income year 2026** (return filed 2027) — the förenklingsregel and huvudregel were merged into one calculation. Everything below reflects the **new** regime. Year-specific figures are tagged; re-verify before any conclusion.*

### 3.1 What "3:12" and fåmansföretag mean

- **Fåmansföretag** (closely-held company): an AB where ≤4 persons control >50% of the votes. A one-person AB with a sole owner holding 100% of the shares is a textbook fåmansföretag.
- **"3:12"** = the nickname for the special rules (originally chapter 57 IL, historically §3:12 of the old lag) governing how an **aktiv delägare** is taxed on dividends (utdelning) and capital gains (kapitalvinst) on their shares.
- **Aktiv delägare** = owner (or close relative, närstående) whose work in the company is "av betydelse" (significant) — i.e. the profit is really their labour, not passive capital. When a family member (närstående) of the owner also works actively in the company, both count as active, and the owner's shares are **kvalificerade andelar** (qualified shares) — which is what triggers 3:12 — via either person's activity.
- **The point of 3:12**: it splits dividend income into a lightly-taxed capital slice and a heavily-taxed labour slice, so owners can't dress up salary as dividends.

### 3.2 How a dividend is taxed — the three tiers

For a qualified share, a dividend is taxed against the owner's **gränsbelopp** (dividend allowance):

| Slice of dividend | Taxed as | Rate |
|---|---|---|
| Up to the **gränsbelopp** | Kapital (capital) | flat **20%** (= 2/3 of the 30% kapitalskatt; only 2/3 of the amount is taken up) |
| Above gränsbelopp, up to the **takbelopp** | Tjänst (earned income) | marginal, up to ≈ **55%** (incl. statlig skatt) — no employer AGA, no pension right |
| Above the takbelopp | Kapital | **30%** |

- **Takbelopp** (ceiling) for dividends = **90 inkomstbasbelopp (IBB)** of dividend in the year, counted across the whole närståendekrets **(2026 — ⚠ verify at use)** (≈ 7.25 Mkr at IBB 80,600). Above it, the tjänst tier stops and the flat 30% applies. Irrelevant at a small AB's scale, but structurally important.
- The **20% tier is the prize**: on money already inside the AB, paying it out as dividend within gränsbelopp costs ~20%, versus a ~50%+ marginal on salary above the brytpunkt (see §3.8).

### 3.3 Gränsbelopp 2026 — the merged rule

From 2026 the gränsbelopp for the year = **grundbelopp + lönebaserat utrymme + interest on omkostnadsbelopp**, plus any **sparat utdelningsutrymme** carried in. You no longer choose "förenklingsregeln OR huvudregeln" — it is one formula.

**Grundbelopp** (base amount) = **4 IBB = 322,400 kr (2026 — ⚠ verify at use)**.
- IBB used is the prior year's: income year 2026 uses **IBB 2025 = 80,600 kr (2026 — ⚠ verify at use)** → 4 × 80,600 = 322,400.
- Granted **once per person across all their companies** — if you own several fåmansföretag you get the grundbelopp in only one. (One company here, so no conflict.)
- Split **by ownership share**. A sole owner holding 100% gets the full 322,400; a family member who works in the company but owns 0% of the shares gets no grundbelopp of their own (their 3:12 room would come only from shares they actually hold).

> Planning note: to give a närstående co-worker their own grundbelopp, they would need to **own qualified shares** (e.g. a share transfer). That is an accountant/lawyer question, not something to assume.

### 3.4 The 2026 reform — what actually changed (decision-critical)

The reform is **in force** (träder i kraft 1 Jan 2026, first applied to beskattningsår beginning after 31 Dec 2025). Confirmed changes:

1. **Löneuttagskravet is abolished.** Under **pre-2026** rules, to use the wage-based space (lönebaserat utrymme) the owner had to personally draw a minimum salary (roughly the lower of 6 IBB + 5% of total wages, or 9.6 IBB). A low owner salary — e.g. a 40k/mo scenario — would **forfeit the entire lönebaserat utrymme**. **From 2026 there is no personal salary-withdrawal requirement**: any active owner can access wage-based space regardless of their own salary. *This timing fact can flip a salary-vs-dividend analysis — see §3.9.*
2. **The 4% capital-share rule (4%-spärren) is abolished.** Previously an owner needed ≥4% of the capital to use wage-based space at all; now even sub-4% owners qualify.
3. **A single schematic wage deduction replaces both requirements**: lönebaserat utrymme is now **50% of (the owner's share of the löneunderlag − 8 IBB)** (see §3.5).
4. **Interest on omkostnadsbelopp is curtailed** — only the part of the omkostnadsbelopp **above 100,000 kr (2026 — ⚠ verify at use)** earns the klyvningsränta (see §3.6).
5. **Sparat utdelningsutrymme no longer grows with interest** (see §3.7).

Uncertain / to watch: implementation regulations and Skatteverket's detailed guidance (SKV 292, utgåva 34) were still settling as the reform bedded in; some transitional edges (exact treatment of pre-2026 saved room, K10 line changes) should be **verified against the current SKV 292 and the K10 for income year 2026** before relying on a figure. Treat any single blog restatement as secondary to Skatteverket/regeringen.

### 3.5 Lönebaserat utrymme (wage-based space)

- **Löneunderlag** = the total **cash gross wages** (kontanta bruttolöner) paid by the company (and subsidiaries) in the year before — benefits (e.g. the car benefit) and pension do **not** count.
- New formula: **lönebaserat utrymme = 50% × (delägarens andel av löneunderlaget − 8 IBB)**, i.e. minus **8 IBB = 644,800 kr (2026 — ⚠ verify at use)** per owner.
- Capped at **50 × the owner's (or a close relative's) own cash salary** — a residual "you must pay some wages" brake, but no longer a personal minimum to *qualify*.

**Worked example (illustrative).** A two-person AB paying total cash wages of **1,200,000 kr/yr** company-wide: with the **8 IBB (644,800) floor**, only the excess feeds the 50% — 1,200,000 − 644,800 = 555,200 → **× 50% ≈ 277,600 kr** of lönebaserat utrymme (recompute from the actual year's L-series wage total). At this wage level the wage-based space is **real but modest**, and it stacks on top of the 322,400 grundbelopp. Under the **old** rules owner salaries in the 40k–50k/mo range risked failing the personal löneuttagskrav and losing this entirely; **from 2026 that risk is gone.**

### 3.6 Omkostnadsbelopp & the capital base

- **Omkostnadsbelopp** = the owner's acquisition cost of the shares (aktiekapital paid in / purchase price), adjusted per the rules. For a typical small AB started with the statutory-minimum 25,000 kr aktiekapital, this contributes little.
- The old huvudregel "capital base" survives as the **interest on omkostnadsbelopp**: **klyvningsränta = statslåneränta + 9 percentage points**, applied **only to the omkostnadsbelopp above 100,000 kr (2026 — ⚠ verify at use)**. With a small omkostnadsbelopp this term is ~0 here — the grundbelopp and lönebaserat utrymme do all the work.

### 3.7 Sparat utdelningsutrymme (carried-forward allowance)

- Any gränsbelopp **not used** in a year is saved as **sparat utdelningsutrymme** and carries forward indefinitely while the shares stay qualified. It can be used for a later dividend **or** to shield a future kapitalvinst on a sale — a major reason to "take the gränsbelopp" (compute and record it on the K10) even in years you pay no dividend.
- **Reform change:** under pre-2026 rules saved room was **uplifted each year by statslåneränta + 3 percentage points** (an uppräkningsränta ≈ 5–6%/yr). **From 2026 this uplift is abolished** — saved room carries forward but **no longer grows (2026 — ⚠ verify at use)**. Consequence: less benefit to "banking" unused room for its own sake; use-it-or-park-it math has changed.

### 3.8 K10 — what it reports

The owner files a **K10** (Blankett K10) as an appendix to the personal inkomstdeklaration for **each** fåmansföretag with qualified shares. It:
- computes the year's **gränsbelopp** (grundbelopp + lönebaserat utrymme + omkostnadsbelopp interest) and any **sparat utdelningsutrymme** brought in;
- reports the **utdelning** actually received and splits it into the kapital (20%) slice and any tjänst slice;
- rolls forward the **new sparat utdelningsutrymme**.
- File it **even in zero-dividend years** to accrue saved room. A dividend decided at the årsstämma (see COMPANY_CONTEXT for the company's own history) lands on the owner's K10 for that income year and is measured against their gränsbelopp there.

### 3.9 Worked comparison — routing a saving out as dividend (illustrative)

**Illustrative, with 2026 parameters — recompute at use:**

- Suppose a salary reduction frees **~300,000 kr/yr** inside the AB (gross salary + AGA no longer paid).
- Routed out as a **3:12 dividend within gränsbelopp**: 300,000 × (1 − 20.6% bolagsskatt) × (1 − 20% kapitalskatt) ≈ **190,600 kr** to the household.
- Kept as **salary** instead: the same employer cost buys ≈ 228,300 kr gross (÷ 1.3142), which — if it all sits above the brytpunkt — nets ≈ **108,700 kr** at a ~52.4% marginal rate (though it also builds pension/SGI).
- Net effect at these levels: on the order of **+80,000 kr/yr** for the household by the dividend route — smaller when part of the salary slice would fall below the brytpunkt, so compute the bracket placement per person (§1.2). And (post-reform) a low salary **no longer forfeits** the dividend room it would have cost under pre-2026 rules.

This is the core 3:12 lever for a profitable small AB: pay enough salary to be sensible (pension, SGI, and the 50× wage cap), then take the profit as 20% dividend within gränsbelopp.

**Caveat — always confirm with the accountant.** Dividend routing trades away pension/sjukpenning/föräldrapenning-grundande income (lower PGI/SGI), assumes the profit and free equity exist under försiktighetsregeln (ABL 17:3), and depends on year-specific IBB/SLR and the still-settling 2026 guidance. Any dividend-planning conclusion here is **indicative — verify the current figures and confirm with your accountant before acting.**

### Sources

- Skatteverket — Ändrade regler för delägare i fåmansföretag inför inkomstdeklarationen 2027: https://www.skatteverket.se/foretag/drivaforetag/foretagsformer/famansforetag/andradereglerinforinkomstdeklarationen2027.4.4a54dc8b19aa6175a152359.html
- Skatteverket — SKV 292 utgåva 34, Skatteregler för delägare i fåmansföretag: https://www.skatteverket.se/download/18.1522bf3f19aea8075ba4f3e/1768831040199/skatteregler-for-delagare-i-famansforetag-skv292-utgava34.pdf
- Regeringen — Lagrådsremiss, Enklare och bättre skatteregler för delägare i fåmansföretag: https://www.regeringen.se/contentassets/67f037536bf7415c80559c5cab8a4b79/enklare-och-battre-skatteregler-for-delagare-i-famansforetag.pdf
- Regeringen — Inkomstbasbelopp och inkomstindex för år 2026 fastställt: https://www.regeringen.se/artiklar/2025/11/inkomstbasbelopp-och-inkomstindex-for-ar-2026-faststallt/
- PwC Tax Matters — Nya 3:12-regler träder i kraft 1 januari 2026: https://blogg.pwc.se/taxmatters/nya-312-regler
- Företagarna — Nya 3:12-reglerna från 2026: https://www.foretagarna.se/driva-eget-foretag/handbocker-och-guider/handbok-312-reglerna/nya-312-reglerna-fran-2026/

---

## 4. Corporate income tax & untaxed reserves (bolagsskatt och obeskattade reserver)

*How an AB's profit becomes a tax bill, and how periodiseringsfonder (tax allocation reserves) on the balance sheet defer that bill. The examples assume a K2, calendar-fiscal-year AB — check COMPANY_CONTEXT for the company's own conventions. Re-verify every tagged number against skatteverket.se at the moment it carries a conclusion.*

### 4.1 Bolagsskatt: the rate and its base

Corporate income tax (**bolagsskatt**) is **20.6 %** *(2026 — ⚠ verify at use)*, unchanged since fiscal years beginning after 2020-12-31. It is levied on the **skattemässigt resultat** (taxable profit), *not* on the **bokfört resultat** (book profit) in the P&L.

The bridge from book profit to taxable profit is a set of adjustments. Structurally:

```
skattemässigt resultat
  = resultat före bokslutsdispositioner (book result before appropriations)
  − avsättning till periodiseringsfond          (this year's new reserve)
  + återföring av periodiseringsfond            (reversed reserves, if any)
  + schablonintäkt på periodiseringsfonder      (§4.3 — a tax-only add-back)
  + ej avdragsgilla kostnader                    (non-deductible costs, added back)
  − ej skattepliktiga intäkter                   (non-taxable income, removed)
```

**bokfört vs skattemässigt** — the recurring traps for this company:

| Item | In the books | Tax effect |
|---|---|---|
| Bilförmån gross-up (`7390`/`7399`) | Nets to **zero** in P&L | Zero — it is the *driver's* taxable income, not a company deduction (COMPANY_CONTEXT §3) |
| Ej avdragsgill representation (`6072`) | Booked as cost | Added back — non-deductible above the schablon |
| Non-deductible fines/penalties, some interest | Booked as cost | Added back |
| Skattefria ränteintäkter (`8314`) | Booked as income | Removed — not taxable |
| Skatt på årets resultat (`8910`) | Booked as cost | Added back — corporate tax itself is never deductible |

Everything else in the K2 P&L is generally both booked and tax-effective, so for a clean consulting company the book/tax gap is usually small and dominated by the bokslutsdispositioner in §4.2.

### 4.2 Periodiseringsfond (tax allocation reserve)

A periodiseringsfond lets an AB move up to **25 %** *(2026 — ⚠ verify at use)* of the profit before this appropriation into an untaxed reserve, deferring — not eliminating — tax on that slice. Mechanics:

- **Avsättning (set-aside):** max 25 % of *överskottet före avsättning* (the profit base before this reserve). Booked as a bokslutsdisposition (debit `88xx`, credit the `212x` reserve).
- **Återföring (reversal):** each year's fund **must be reversed back into taxable income no later than the sixth tax year after the set-aside year**. Reversal is **FIFO** — the oldest fund is always released first.
- Purpose: smooths tax across years and finances working capital interest-free, but it is a *timing* tool, not a saving — the tax lands when the fund reverses.

Illustration — a company holding **600 000 kr** of periodiseringsfonder at 2026-01-01, across three accounts:

| Account | Set aside for | Amount | Latest reversal (year + 6) |
|---|---|---:|---|
| `2125` | FY2025 bokslut | **300 000 kr** | FY2031 |
| `2124` | FY2024 bokslut | **200 000 kr** | FY2030 |
| `2123` | FY2023 bokslut | **100 000 kr** | FY2029 |

Data-quality pattern worth checking: the `212x` account *labels* (which often carry a fund year in the name) sometimes don't match the actual set-aside year. Trust the årsredovisning's movements over the account label — and flag mismatches to the accountant rather than "correcting" them.

### 4.3 Schablonintäkt on periodiseringsfonder

Holding periodiseringsfonder is not free: each year a **standardized income (schablonintäkt)** is added to taxable profit (a tax-only add-back — nothing is booked in the ledger):

```
schablonintäkt = SLR(30 Nov of year before the calendar year the tax year ends)
                 × opening balance of all periodiseringsfonder
```

- The rate is the **statslåneränta (SLR)** on 30 Nov of the prior year, with a **floor of 0.5 %** *(2026 — ⚠ verify at use)* if the actual SLR is lower.
- **SLR at 2025-11-30 = 2.55 %** *(2026 — ⚠ verify at use)* → the rate for tax year FY2026.
- Base = the reserves at the **start** of the tax year (600 000 kr in the illustration).

For FY2026: **2.55 % × 600 000 = 15 300 kr** *(2026 — ⚠ verify at use)* of extra taxable income → roughly **20.6 % × 15 300 ≈ 3 152 kr** *(2026 — ⚠ verify at use)* of actual tax. Small, but it is the standing "rent" on the deferral.

### 4.4 Other obeskattade reserver

Other untaxed reserves an AB can carry — **överavskrivningar** (accelerated depreciation booked as *ackumulerade avskrivningar utöver plan*, account group `215x`) and reserves like ersättningsfond — work the same way: a bokslutsdisposition that defers tax. A small consulting AB typically has none of these — often the only obeskattade reserver are periodiseringsfonder, with inventarier (`1220`) written off within plan and no untaxed excess. Check the `215x` accounts and COMPANY_CONTEXT to confirm.

### 4.5 Estimating corporate tax for a projection

For a forward estimate — never a substitute for the accountant's bokslut:

```
tax ≈ 20.6 % × ( resultat före bokslutsdispositioner
                 − new periodiseringsfond avsättning
                 + any periodiseringsfond återföring
                 + schablonintäkt
                 + ej avdragsgilla poster )
```

> **Estimate only — the accountant's bokslut is the truth.** This ignores loss carry-forwards, prior-year true-ups, and the exact non-deductible split. Present a range, cite the drivers, and defer the final figure to the bokslut.

Sanity anchor: the filed *skatt på årets resultat* typically lands slightly **above** 20.6 % of the post-appropriation book result — the schablonintäkt and non-deductible add-backs explain the wedge. Check the company's own bokslut figures (COMPANY_CONTEXT) when anchoring a projection.

### 4.6 Utdelning (dividend) at the company level

A dividend is paid from **fritt eget kapital** (distributable equity: balanserat resultat + årets resultat, net of restrictions) and is decided by the **bolagsstämma** (AGM), typically on the board's proposal. Two gates:

- **Beloppsspärren** — you may not distribute more than free equity allows.
- **Försiktighetsregeln (ABL 17:3)** — even within free equity, the distribution must be *defensible* given the company's consolidation needs, liquidity, and risk. The board must justify it.

Illustration (årsstämma): available profit **500 000 kr** → **200 000 kr** dividend to the shareholder, **300 000 kr** carried forward, with the board expressly citing försiktighetsregeln in its statement. The dividend is booked in the following year's equity movement (2091/2898).

The **personal-side taxation** of that dividend (the 3:12 / fåmansföretag rules, gränsbelopp, 20 % vs marginal tax) is a *shareholder* matter and lives in **§3** — cross-reference it, do not duplicate here.

### Sources

- Bolagsskatt & taxable result: https://www.skatteverket.se/foretag/drivaforetag/foretagsformer/aktiebolag.4.5c13cb6b1198121ee8580002546.html
- Periodiseringsfond (25 %, 6-year FIFO reversal): https://www.skatteverket.se/foretag/drivaforetag/foretagsformer/aktiebolag/periodiseringsfond.4.4887341d16e1e2b8ddf30e.html
- Återföring av periodiseringsfond: https://www4.skatteverket.se/rattsligvagledning/edition/2025.1/329552.html
- Schablonintäkt (SLR 30 Nov, 0.5 % floor, opening balance): https://www4.skatteverket.se/rattsligvagledning/edition/2025.1/329554.html
- Belopp och procent 2026: https://www.skatteverket.se/foretag/skatterochavdrag/beloppochprocent/2025.106.262c54c219391f2e963502f.html
- Utdelning / försiktighetsregeln (ABL 17:3), riksdagen: https://www.riksdagen.se/sv/dokument-lagar/dokument/svensk-forfattningssamling/aktiebolagslag-2005551_sfs-2005-551

---

## 5. Moms (VAT)

*Moms (mervärdesskatt) = Swedish value-added tax. This section lets the assistant read the ledger correctly: what a cost figure includes, why some foreign costs look "gross," and where VAT is a real, non-recoverable expense for the company. Rates and rules verified against Skatteverket; see Sources.*

### 5.1 Rates

Sweden has one standard rate and two reduced rates. The rate lives on the sale, not the buyer.

| Rate | Applies to (typical) | Example-company relevance |
|---|---|---|
| **25 %** *(2026 — ⚠ verify at use)* | Default for almost all goods & services — incl. **consulting services** | The company's own sales (account `3001`, "sales SE 25 % moms") and most of its purchases |
| **12 %** *(2026 — ⚠ verify at use)* | Food & restaurant/catering, hotel accommodation, some repairs | Hotel *lodging* portion of travel; restaurant meals |
| **6 %** *(2026 — ⚠ verify at use)* | Passenger transport (domestic), books, newspapers, cultural events | Domestic train/taxi; not the company's core |

Consulting — the company's entire revenue line — is **standard-rated at 25 %**. There is no reduced or exempt treatment for technical/AI consulting sold domestically.

### 5.2 Ingående vs utgående moms — why the ledger is already net

- **Utgående moms** (output VAT) = VAT the company *charges* customers on its sales. A liability owed to Skatteverket. Booked on `2610`/`2611`.
- **Ingående moms** (input VAT) = VAT the company *pays* suppliers. Reclaimable to the extent the purchase serves the VAT-liable business. Booked on `2640`/`2641`.
- Each period the two net off on `2650` (momsredovisning) and the balance is paid to, or refunded by, Skatteverket.

**The key fact for reading costs:** because deductible input VAT is reclaimed, it is **never** left in the expense account. **P&L cost accounts are booked NET of deductible VAT** — the figure you see *is* the true economic cost. Do not "add VAT" to a cost line to estimate the real burden; for fully deductible purchases the cost line already is the real burden. The exceptions — where VAT is *not* recoverable and therefore *does* sit inside the cost — are the car (5.3) and anything zero-rated/exempt (5.5).

| Account | Meaning |
|---|---|
| `2610` / `2611` | Utgående moms (output VAT on sales) |
| `2640` / `2641` | Ingående moms (input VAT on purchases) |
| `2650` | Momsredovisning — the settlement/clearing account |

### 5.3 The 50 % leasing rule (personbil) — a real, non-recoverable cost

**This is the rule the assistant has hedged on before. Do not hedge — it is settled by law and by the voucher.**

For a **personbil** (passenger car) that is *hyrd/leased*, only **50 % of the input VAT on the leasing fee is deductible** (the *avdragsbegränsning*). This is a flat *schablon* rule from Skatteverket: it applies to **all** leased passenger cars used more than *ringa* (> 1,000 km/year) in VAT-liable business — **even if the car is used 100 % for business**. The other half of the VAT is **not recoverable** and is therefore absorbed **into the booked lease cost** on `5615`. (Narrow exceptions where 100 % is deductible: taxi, driving-school, hearse — none apply here.)

**Worked proof — a monthly car-lease voucher (illustrative round numbers):**

| Account | Amount | What it is |
|---|---:|---|
| `2440` (leverantörsskuld) | **−8 000,00** | Gross invoice paid |
| `2641` (ingående moms) | **+800,00** | VAT reclaimed = *half* |
| `5615` (leasing cost) | **7 200,00** | Cost booked = net base + the *other* half of the VAT |

Full VAT on the lease = 1 600 (25 % of the 6 400 net base); exactly **half (800 kr/mo)** is reclaimed and **half (800 kr/mo) is a non-recoverable cost living inside the 7 200 kr lease figure**. So when the assistant reports the lease cost, part of it is irrecoverable VAT, not service value — but it *is* a genuine cash cost to the company. No need to "confirm with the accountant": the voucher's own 2440/2641/5615 rows prove the treatment.

**Purchase & running costs — even stricter.** For *buying* a personbil, input VAT is generally **100 % non-deductible** (the car is capitalised VAT-inclusive). Most *running costs* of a personbil (service, repairs) are likewise non-deductible, with narrow exceptions. The **50 % rule is specific to the leasing fee.** (Fuel/charging follows its own rules; electricity charging typically sits on `5611`/`5619`.)

### 5.4 Reverse charge — omvänd skattskyldighet (foreign purchases)

When the company buys **services from a business in another EU country** (`4535`) or **from a non-EU/utland supplier** (`4531`), the supplier invoices **without VAT** and the **buyer self-accounts** for the tax: it books **both** output VAT (`2610`-series) **and** input VAT (`2640`-series) on the same purchase. If the purchase is fully deductible, the two **net to zero** — no cash cost — but Swedish moms entries still appear on the voucher.

- This is why such cost lines can look **"gross" of any foreign VAT** (the foreign supplier charged none) yet still carry Swedish moms postings.
- **EU goods** (`4515`) work the same way (unionsinternt förvärv).
- Requires the **counterparty's VAT number**, validated via **VIES**; EU service/goods sales *by* the company must be reported on the periodisk sammanställning (5.6).
- Net effect on true cost: **zero** where fully deductible — so the reverse-charge mechanism does not change the economic cost figure, it just moves the VAT accounting to the buyer.

| Account | Purchase type | VAT mechanism |
|---|---|---|
| `4515` | EU goods | Reverse charge (förvärvsmoms) |
| `4531` | Non-EU / utland services | Reverse charge |
| `4535` | EU services | Reverse charge |

### 5.5 Zero-rated (0 %) vs exempt (undantaget)

These look similar in the ledger — no VAT charged — but differ in a way that matters:

- **0 % / zero-rated** — still *momspliktig* (VAT-liable), so the seller **keeps the right to deduct** input VAT. **International passenger transport (utrikes persontransport) — e.g. cross-border flights — is zero-rated.** In the cost trace, air tickets were **booked with no VAT** and there is **no reclaimable VAT** on them (the cost is the whole ticket). Export of services outside the EU is likewise outside Swedish VAT.
- **Undantaget / exempt** — outside VAT with **no right to deduct** input VAT: e.g. financial services, insurance, healthcare, education. VAT paid on related purchases is lost.

**Practical read:** for a flight, do not look for a reclaimable-VAT sliver — there isn't one. For an insurance premium (e.g. the car's insurance cover), the invoice carries no deductible VAT either.

### 5.6 Momsdeklaration — periods & deadlines

The **redovisningsperiod** depends on *beskattningsunderlag* (taxable base ≈ annual turnover subject to VAT):

| Beskattningsunderlag / year | Period | May opt for |
|---|---|---|
| Over **40 MSEK** *(2026 — ⚠ verify at use)* | Monthly (mandatory) | — |
| **1 – 40 MSEK** *(2026 — ⚠ verify at use)* | Quarterly | Monthly |
| Up to **1 MSEK** *(2026 — ⚠ verify at use)* | Yearly | Monthly or quarterly |

A small consulting AB with net sales in the **1–40 MSEK** band files **quarterly** by default (may elect monthly). With mainly domestic sales (25 %), the mechanics are ordinary output VAT, not cross-border. Check COMPANY_CONTEXT / the ledger for the company's own period.

**Deadlines (structural):**
- **≤ 40 MSEK filers** (monthly *or* quarterly): the **12th** of the *second* month after the period — except **17th** in January and August.
- **> 40 MSEK filers** (monthly): the **26th** of the month after the period (**27th** in December).

**Periodisk sammanställning** (EC sales list): required when the company **sells** goods/services to VAT-registered businesses in **other EU countries** — reports those sales by counterparty VAT number. Services-only sellers may report **quarterly**; selling goods pushes it **monthly**. Due by the **25th** of the month after the period (e-service). No sales in a period → nothing to file. Late filing risks a **1 250 kr** *(2026 — ⚠ verify at use)* fee. This is separate from the momsdeklaration and is *not* triggered by purchases (those are the buyer's reverse charge in 5.4).

### 5.7 Gross (cash) vs net (P&L) — keep them distinct

A cost's **P&L figure is net** of deductible VAT; the **cash that left the bank is gross** (incl. VAT), even when that VAT is later reclaimed. The assistant must not conflate the two:

- **Hotel (illustrative):** **8 000 kr** hits the P&L (net) while **8 960 kr** actually leaves the bank (gross) — the 960 kr difference is input VAT (12 % on lodging), reclaimed later via `2640`.
- So "what did this cost us?" (P&L, net) and "what left the account?" (cash, gross) are **different numbers** whenever deductible VAT is involved. For a cash-flow / liquidity question, use gross; for true-cost / profitability, use net.
- The car lease is the instructive hybrid: gross **8 000** paid, **7 200** in the P&L — but here the gap is only *half* the VAT, because the other half (5.3) is non-deductible and stays in the cost.

### Sources

- Bilar och moms (50 % leasing rule): https://www.skatteverket.se/foretag/moms/sarskildamomsregler/bilarochmoms.4.58d555751259e4d6616800010628.html
- Rätt till avdrag för ingående skatt vid leasing av personbil (Rättslig vägledning): https://www4.skatteverket.se/rattsligvagledning/edition/2025.1/26381.html
- Inköp eller hyra av personbil eller motorcykel (Rättslig vägledning): https://www4.skatteverket.se/rattsligvagledning/edition/2026.12/407504.html
- När ska jag deklarera moms (periods & deadlines): https://www.skatteverket.se/foretag/moms/deklareramoms/narskajagdeklareramoms.4.6d02084411db6e252fe80008988.html
- Köpa varor eller tjänster till företaget (input VAT deduction): https://www.skatteverket.se/foretag/moms/kopavarorochtjanster/kopavarorellertjanstertillforetaget.4.7459477810df5bccdd480005156.html
- Periodisk sammanställning för varor och tjänster (EC sales list): https://www.skatteverket.se/foretag/moms/deklareramoms/periodisksammanstallningforvarorochtjanster.4.58d555751259e4d661680001093.html

---

## 6. Skattekonto, F-skatt & the tax calendar

*How every tax the company owes flows through one running account at Skatteverket, how the ledger mirrors it, and when each declaration and payment is due for a calendar-year AB. Deadlines and rates change — re-verify tagged values at use (COMPANY_CONTEXT §7).*

### 6.1 Skattekonto (the tax account at Skatteverket)

The **skattekonto** is a single running account at Skatteverket into which *all* of the company's taxes settle: preliminär F-skatt, employee tax (personalskatt), arbetsgivaravgifter (AGA), and moms. There is one balance, not one per tax.

- **Debits** (charges): declared taxes, debiterad F-skatt, corrections. **Credits** (payments): money you transfer in, plus refunds/reductions. The account nets to a single **saldo**.
- Skatteverket runs a monthly **avstämning** (reconciliation). A negative saldo (underskott) accrues **kostnadsränta** (cost interest); a surplus historically accrued **intäktsränta** (credit interest), currently **0 %** *(2026 — ⚠ verify at use)*. Both are pegged to the **basränta** (verify the current basränta — it moves with the SLR); kostnadsränta has a low tier and a high tier (basränta + 15 pp on established deficits).
- Interest on the skattekonto is **not deductible** (cost) and **not taxable** (credit).
- **Ledger mirror:** account **`1630 Skattekonto`** mirrors the skattekonto balance in the books — its movements should tie to Skatteverket's statement (COMPANY_CONTEXT §6).

### 6.2 F-skatt / preliminärskatt (the company's own income tax)

The AB is registered for **F-skatt** and pays its corporate income tax *in advance*, monthly, across the year:

- The monthly charge (**debiterad F-skatt**) is one-twelfth of the tax Skatteverket has assessed from the company's **preliminär inkomstdeklaration** (a forecast). If profit is trending well above forecast, the company files a *new* preliminär deklaration to raise the F-skatt and avoid a deficit + kostnadsränta.
- Preliminär F-skatt is due on the **12th of each month (17th in January)** *(2026 — ⚠ verify at use)*.
- After the year, the **slutlig skatt** on the filed Inkomstdeklaration 2 is compared to F-skatt paid; the difference (kvarskatt or återbetalning) settles on the skattekonto at the **slutskattebesked**.
- **Ledger accounts:** `2510` skatteskuld (accrued corporate tax liability), `2518` betald F-skatt (F-skatt paid in). At bokslut, `8910` books the tax cost against `2510`; `2518` offsets what was already paid (COMPANY_CONTEXT §2, §6).

### 6.3 Arbetsgivardeklaration (AGI) — monthly PAYE

Each month the company reports payroll on an **arbetsgivardeklaration på individnivå (AGI)** — per-employee wage, benefit, and withheld-tax rows — covering:

- **Personalskatt** — preliminary tax withheld from employees' wages (ledger `2710`).
- **Arbetsgivaravgifter (AGA)** — employer social contributions at **31.42 %** *(2026 — ⚠ verify at use)* of gross wage + taxable benefits (ledger `2731`/`2730`).

Both the **declaration and the payment** are due the month *after* payroll, on the **12th (17th in January)** *(2026 — ⚠ verify at use)*, for a company with turnover ≤ 40 msek (virtually every small AB qualifies). Example: March wages → declared and paid by **12 April**. Note also `2514` särskild löneskatt on pension premiums (`7530`) at **24.26 %** *(2026 — ⚠ verify at use)*, settled the same way (COMPANY_CONTEXT §4, §6).

### 6.4 Moms (VAT) — cross-reference

Moms is declared and paid on its own **momsdeklaration**; the **deadline depends on the company's momsperiod** (monthly vs quarterly) and turnover, and both flow through the skattekonto. Representative dates appear in the calendar below, but the **mechanics, the 50 % lease-VAT rule, and per-voucher treatment are in §5** — cross-reference there for anything moms-specific. Ledger: `2610`–`2650` moms accounts, netting to `2650 Momsredovisning`.

### 6.5 Filing & payment calendar — calendar-year AB (turnover ≤ 40 msek)

| Obligation | Frequency | Deadline *(all 2026 — ⚠ verify at use)* |
|---|---|---|
| AGI + PAYE (personalskatt `2710` + AGA `2730`) declare **and** pay | Monthly | 12th of month after payroll (17 Jan) |
| Preliminär F-skatt (1/12 of debiterad) | Monthly | 12th of each month (17 Jan) |
| Moms — if **monthly** momsperiod | Monthly | 12th of 2nd month after period (17 Jan/Aug) — see §5 |
| Moms — if **quarterly** momsperiod | Quarterly | 12th of 2nd month after quarter (e.g. Q1 → 12 May) — see §5 |
| **Inkomstdeklaration 2** (FY end 31 Dec) | Annual | 1 July (paper) / **1 Aug → 3 Aug 2026** if filed digitally |
| **Årsredovisning** to Bolagsverket | Annual | Within **7 months** of year-end → 31 July |
| **Årsstämma (AGM)** | Annual | Within **6 months** of year-end → 30 June |

Notes:
- **Inkomstdeklaration 2 deadline is driven by the fiscal-year-end month.** For an AB whose year ends Sep–Dec, the paper deadline is 1 July and digital filing buys one extra month to 1 August; 1 Aug 2026 falls on a weekend, so the effective digital deadline is **3 Aug 2026** *(2026 — ⚠ verify at use)*. Late filing costs **6 250 kr** *(2026 — ⚠ verify at use)*, up to three times.
- **Årsredovisning** must reach Bolagsverket within 7 months of year-end; late filing triggers a **förseningsavgift of 7 500 kr** *(2026 — ⚠ verify at use)* (rising in steps). With no auditor the report must be finalised ≥ 2 weeks before the AGM; if the company has an auditor (mandatory or voluntary — check COMPANY_CONTEXT), ≥ 6 weeks applies.
- The AGM (within 6 months) is where the dividend and profit disposition are decided (§4.6).

### 6.6 Ledger tax-account map

So the assistant can tie any declaration back to the books:

| Tax / declaration | Ledger accounts | Skattekonto? |
|---|---|---|
| Moms (VAT) | `2610`–`2650` (net `2650`) | Yes — via `1630` |
| PAYE: employee tax + AGA | `2710` personalskatt, `2730`/`2731` sociala avgifter | Yes — via `1630` |
| Särskild löneskatt (pension) | `2514` | Yes — via `1630` |
| Corporate income tax / F-skatt | `2510` skatteskuld, `2518` betald F-skatt, `8910` skattekostnad | Yes — via `1630` |
| Running tax account itself | `1630 Skattekonto` (mirror of the skattekonto) | — |

Every declaration debits the skattekonto; every payment credits it; `1630` is the ledger's copy of that single balance. Reconcile `1630` to Skatteverket's kontoutdrag, and tie each period's `2650`/`2710`/`2730`/`2510` movement to the matching declaration.

### Sources

- Skattekonto (running account, ränta): https://www.skatteverket.se/foretag/skatterochavdrag/skattekonto.4.18e1b10334ebe8bc80005221.html
- Arbetsgivardeklaration — när ska jag lämna: https://www.skatteverket.se/foretag/arbetsgivare/lamnaarbetsgivardeklaration/narskajaglamnaarbetsgivardeklaration.4.361dc8c15312eff6fd13c11.html
- Betala arbetsgivaravgifter och skatt (12th, ≤40 msek): https://www.skatteverket.se/foretag/arbetsgivare/arbetsgivaravgifterochskatteavdrag/betalaarbetsgivaravgifterochskatt.4.361dc8c15312eff6fd13d2d.html
- Inkomstdeklaration 2 deadlines by fiscal-year-end: https://www.skatteverket.se/foretag/inkomstdeklaration/deklareraatettaktiebolagellerenekonomiskforening.4.46ae6b26141980f1e2d1261.html
- Årsredovisning & förseningsavgift (7 months): https://bolagsverket.se/foretag/aktiebolag/arsredovisningforaktiebolag/taframenarsredovisning.793.html
- Bolagsstämma (AGM within 6 months): https://bolagsverket.se/en/foretag/aktiebolag/drivaaktiebolag/tabeslutiaktiebolaget/bolagsstamma.551.html

---

## See also

- **[COMPANY_CONTEXT.example.md](COMPANY_CONTEXT.example.md)** — template for the loaded company's verified numbers and known data-quality issues.
- **`CASE_STUDY_BILFORMAN.md`** — the bilförmån derivation these formulas reproduce (local/gitignored; not in the public repo).
- **`CASE_STUDY_COST_ANALYSIS_TRACE.md`** — the Q1–Q4 benchmark (FCF, salary optimization, VAT) these rules answer (local/gitignored).
- **`swedish_english_financial_glossary.md`** — full bilingual glossary for any term used above.
- **Bookmark for verification:** Skatteverket *"Belopp och procent"* (per year) is the single best hub for confirming almost every tagged number here.
