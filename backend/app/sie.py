"""Parser for SIE type-4 files (Swedish standard accounting export).

Fortnox's `GET /3/sie/4?financialyear=N` returns one file containing the full
general ledger for a financial year: accounts, opening/closing balances,
result balances, and every voucher with its transactions. SIE files are
encoded in IBM PC8 (cp437) per the standard.

Format essentials handled here:
  #KONTO <no> <name>              account definition
  #RAR <yearno> <start> <end>     financial year (0 = the file's year)
  #IB / #UB <yearno> <acct> <amt> opening / closing balance (balance accounts)
  #RES <yearno> <acct> <amt>      result balance (P&L accounts)
  #VER <series> <no> <date> <text> [regdate]
  { #TRANS <acct> {dims} <amt> [date] [text] ... }
Amounts follow the SIE sign convention: debit > 0, credit < 0.
"""

from dataclasses import dataclass, field


@dataclass
class Trans:
    account: int
    amount: float
    date: str = ""
    text: str = ""


@dataclass
class Voucher:
    series: str
    number: int
    date: str
    text: str = ""
    trans: list[Trans] = field(default_factory=list)


@dataclass
class ParsedSIE:
    accounts: dict[int, str] = field(default_factory=dict)  # number -> name
    ib: dict[int, float] = field(default_factory=dict)      # yearno 0 only
    ub: dict[int, float] = field(default_factory=dict)
    res: dict[int, float] = field(default_factory=dict)
    year_start: str = ""
    year_end: str = ""
    vouchers: list[Voucher] = field(default_factory=list)


def _tokenize(line: str) -> list:
    """Split a SIE line into tokens: bare words, "quoted strings" (with \\"
    escapes), and { … } groups (returned as sub-lists)."""
    tokens: list = []
    stack = [tokens]
    i, n = 0, len(line)
    while i < n:
        c = line[i]
        if c in " \t":
            i += 1
        elif c == "{":
            group: list = []
            stack[-1].append(group)
            stack.append(group)
            i += 1
        elif c == "}":
            if len(stack) > 1:
                stack.pop()
            i += 1
        elif c == '"':
            i += 1
            buf = []
            while i < n and line[i] != '"':
                if line[i] == "\\" and i + 1 < n:
                    i += 1
                buf.append(line[i])
                i += 1
            i += 1  # closing quote
            stack[-1].append("".join(buf))
        else:
            j = i
            while j < n and line[j] not in ' \t{}"':
                j += 1
            stack[-1].append(line[i:j])
            i = j
    return tokens


def _iso(date: str) -> str:
    d = date.strip()
    if len(d) == 8 and d.isdigit():
        return f"{d[0:4]}-{d[4:6]}-{d[6:8]}"
    return d


def _num(value) -> float:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def _int(value) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def parse(data: bytes) -> ParsedSIE:
    text = data.decode("cp437", errors="replace")
    out = ParsedSIE()
    current_ver: Voucher | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line == "{" or line == "}":
            if line == "}":
                current_ver = None
            continue
        if not line.startswith("#"):
            continue

        tokens = _tokenize(line)
        if not tokens:
            continue
        label = tokens[0].upper()
        args = tokens[1:]

        if label == "#KONTO" and len(args) >= 2:
            acct = _int(args[0])
            if acct is not None:
                out.accounts[acct] = str(args[1])

        elif label == "#RAR" and len(args) >= 3 and str(args[0]) == "0":
            out.year_start = _iso(str(args[1]))
            out.year_end = _iso(str(args[2]))

        elif label in ("#IB", "#UB", "#RES") and len(args) >= 3:
            if str(args[0]) != "0":  # only the file's own year
                continue
            acct = _int(args[1])
            if acct is None:
                continue
            target = {"#IB": out.ib, "#UB": out.ub, "#RES": out.res}[label]
            target[acct] = _num(args[2])

        elif label == "#VER" and len(args) >= 3:
            number = _int(args[1])
            ver = Voucher(
                series=str(args[0]),
                number=number if number is not None else 0,
                date=_iso(str(args[2])),
                text=str(args[3]) if len(args) >= 4 else "",
            )
            out.vouchers.append(ver)
            current_ver = ver

        elif label == "#TRANS" and current_ver is not None and len(args) >= 3:
            # args: account {dims} amount [date] [text]
            acct = _int(args[0])
            if acct is None:
                continue
            rest = [a for a in args[1:] if not isinstance(a, list)]
            if not rest:
                continue
            amount = _num(rest[0])
            date = _iso(str(rest[1])) if len(rest) >= 2 and str(rest[1]).strip() else ""
            txt = str(rest[2]) if len(rest) >= 3 else ""
            current_ver.trans.append(
                Trans(account=acct, amount=amount, date=date or current_ver.date, text=txt)
            )

    return out
