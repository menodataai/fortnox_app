# Proposal — Automated receipt pipeline ("F11")

*Research synthesized 2026-08-03. Problem: monthly receipt collection is manual
(download from SaaS portals, photograph paper receipts, email to the accountant /
the company's Fortnox intake address `inbox.ver.NNNNNNN@arkivplats.se`), and
foreign-currency receipts (USD/EUR) can't be matched by Fortnox or the
accountant against the SEK bank/card charge.*

---

## 1. What the research established

### The Fortnox API fully supports an ingestion pipeline

| Capability | Endpoint / fact | Status |
|---|---|---|
| Upload receipt file | `POST /3/inbox?path=Inbox_v` (voucher/receipt inbox) or `Inbox_s` (supplier invoices) | Verified, official best-practice guide |
| File types | PDF, TIFF, JPEG only (both API and email intake) | Verified |
| Attach file to voucher / supplier invoice | `POST /3/voucherfileconnections`, `POST /3/supplierinvoicefileconnections` (file must have been uploaded to `Inbox_v` for vouchers) | Verified |
| Foreign-currency supplier invoice | `POST /3/supplierinvoices` with writable `Currency`, `CurrencyRate`, `CurrencyUnit`; created **unbooked** (`Booked` is read-only; requires explicit `PUT …/bookkeep` or the attest flow) — i.e. a draft the accountant approves | Verified via Fortnox's own C# SDK |
| Vouchers | SEK-only (no currency fields), no draft state, no delete | Verified |
| Realized FX diffs | Fortnox auto-posts to 3960 (gains) / 7960 (losses) on payment of foreign-currency supplier invoices | Verified (support docs) |
| Scopes needed | `inbox`, `connectfile` (+ existing `supplierinvoice`, `bookkeeping`) — our token currently lacks `inbox`/`connectfile`, so re-consent is needed | Verified scope list |
| Private integration | Explicitly supported: keep the developer-portal app unpublished, activate by Client-Id — no marketplace review | Verified |
| Rate limit | 25 requests / 5-second window per client+tenant | Verified |

Email intake (`@arkivplats.se`) constraints: attachments must be PDF/TIFF/JPEG;
a **trusted-sender gate** holds mail from unknown senders until a human approves
the address/domain once in the Fortnox UI. HTML-body-only receipts (Stripe,
GitHub style) don't survive email forwarding usefully — they need PDF conversion
first. Sources: support.fortnox.se "ta emot e-postfaktura direkt i Fortnox",
"skicka in kvitton direkt till programmet".

### The currency "mismatch" is a workflow problem, not a compliance problem

- **BFNAR 2013:2 punkt 2.6**: companies may translate using **the rate at which
  payment was actually made** — i.e. the SEK amount on the card/bank statement
  (which already embeds the card network's rate + markup) *is* the correct
  booking amount. Attach the original USD/EUR receipt as underlag.
- No rule requires the exchange rate to be written on the verifikation; the SEK
  amount must merely be derivable/documented — the statement line does that.
- So the accountant's real pain is **pairing** (which SEK charge belongs to which
  USD receipt), not translation. Anything that hands them the pairing
  pre-computed solves the problem.
- Matching-engine practice (Midday, open source — midday.ai): score =
  embedding similarity 50% + amount 35% + currency 10% + date 5%; ~5% amount
  tolerance band (covers FX + fees), ~5-day date window, reference rates
  (Riksbank/ECB) for cross-currency comparison; auto-match ≥90% confidence.

### Existing products (buy instead of / alongside build)

| Product | What it does | Fortnox | Price |
|---|---|---|---|
| **GetMyInvoices** | Auto-fetches invoices from 10 000+ vendor portals + email scan — the only portal-fetcher with a native Fortnox push | Yes, direct sync | ~$15–75/mo |
| **Fortnox Företagskort** (Mynt-powered) | Card purchase auto-creates the transaction; photographed/emailed receipt auto-matches to it; FX diff auto-posted | Native | Card free; 4.90 kr/receipt interpretation, free for card purchases |
| **Mynt** | Cards; auto-retrieves receipts from email and matches to transactions | Yes | Free tier; Premium 499 kr/mo |
| **Pleo** | Cards + capture, multi-currency wallets | Yes | Per-user, ~£5–15/user/mo |
| **Fortnox Kvitto & Utlägg** | Photo/email → AI interpretation → booking proposal | Native | License free, 4.90 kr/receipt |
| invoicefetcher | Portal fetch (has an OpenAI connector) | No | Free tier + paid |
| Dext / Hubdoc | Portal fetch / capture | No | — |

Key gap: Swedish kvitto apps don't fetch vendor portals; portal fetchers other
than GetMyInvoices don't talk to Fortnox. And none of them solve "match my USD
receipt to my SEK charge **and explain it to my accountant**" — that's the
niche a custom pipeline fills.

---

## 2. Recommendation — three layers, adopt in order

### Layer 0 — no code, this week
1. **Gmail filters → arkivplats forwarding** for vendors that attach PDFs
   (`from:(invoice senders) has:attachment` → forward to the inbox address).
   One-time: approve the forwarding sender in Fortnox's trusted-sender queue
   (Gmail's verification mail should land in the temporary Arkivplats inbox).
   HTML-only receipts won't work this way — they go to Layer 2.
2. **Consider Fortnox Företagskort or Mynt (free)** for future SaaS spend: the
   receipt attaches to the SEK transaction inside the platform, which kills the
   FX-matching problem at source for everything bought on that card.
3. Optionally trial **GetMyInvoices** for portal auto-fetch if Layer 2 isn't
   built soon.

### Layer 1 — the matching brain (fits our stack; the differentiator)
A monthly job in our backend (we already have the ledger mirror + Pydantic AI):
1. Collect candidate receipts (Gmail API search of vendor senders; phone photos
   dropped in a folder).
2. **LLM-extract** vendor, date, total, currency, VAT from each PDF/image
   (vision model via OpenRouter, schema-validated — same stack as F8).
3. Convert HTML-body receipts to PDF (headless Chromium) so they're
   Fortnox-acceptable.
4. **Match against the mirror**: card/bank rows from the vouchers, Riksbank
   reference rate ± tolerance band + date window (Midday's weights as the
   template). Note: matching against *booked* vouchers means the mirror lags
   the accountant's work — matching against a raw card feed would be real-time,
   but voucher-level is enough for a monthly cadence.
5. Produce for each receipt a **cover annotation** — e.g. rename/stamp
   `2026-07-05 ExampleSaaS 19.99 USD = 216.89 SEK (card txn 2026-07-07, rate 10.85)`
   — so the accountant sees the pairing without doing FX arithmetic. Emit a
   **monthly digest**: matched receipts, unmatched bank rows (receipt missing —
   recurring vendor checklist), unmatched receipts.

### Layer 2 — delivery into Fortnox via API
- Add `inbox` + `connectfile` scopes (token re-consent) and `POST` the annotated
  PDFs to `Inbox_v` — the same place the email address feeds, so the
  accountant's workflow is unchanged. **This does not write to the books**, so
  the app's read-only-books principle survives: the inbox is a staging area and
  the accountant still creates/approves every voucher.
- Later, optionally: create **unbooked** supplier invoices with
  `Currency`/`CurrencyRate` + attached file for the recurring SaaS vendors, so
  the accountant only reviews and clicks bookkeep. Do this only after agreeing
  the workflow with the accountant (they own the books; discuss voucher series
  and whether they prefer inbox files vs. draft invoices).

### Open questions for the accountant
- Prefer receipts in `Inbox_v` (verifikationer) or as draft supplier invoices
  in `Inbox_s` / the tolkning flow (tolkning bills per interpreted invoice)?
- Which account do they use for FX diffs today (3960/7960 configured?).
- Confirm the card statement SEK amount as the booking basis (BFNAR 2013:2
  p.2.6) so the digest can state it as settled convention.

---

## 3. Source highlights
- Fortnox voucher best practice (inbox → voucher → fileconnection flow):
  fortnox.se/developer/guides-and-good-to-know/best-practices/vouchers
- Scopes: fortnox.se/developer/guides-and-good-to-know/scopes · Rate limits:
  …/rate-limits-for-fortnox-api
- SDK ground truth for field writability: github.com/FortnoxAB/csharp-api-sdk
  (`SupplierInvoice.cs`, `Voucher.cs`, `VoucherFileConnection.cs`)
- Email intake + trusted senders: support.fortnox.se "ta emot e-postfaktura
  direkt i Fortnox", "kom igång med Fortnox Arkivplats"
- FX rules: BFNAR 2013:2 (bfn.se, punkt 2.4–2.6); Skatteverket rättslig
  vägledning on bokföring i utländsk valuta
- Matching engine reference: midday.ai/updates/automatic-reconciliation-engine
  (open source); TaxHacker (github.com/vas3k/TaxHacker) for LLM extraction +
  historical FX conversion
- Products: getmyinvoices.com (Fortnox integration page); fortnox.se/produkt/
  fortnox-foretagskort, /produkt/kvitto-utlagg; Mynt/Pleo Fortnox integration
  pages
