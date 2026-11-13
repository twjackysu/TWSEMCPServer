"""Resolve 分點 (broker branch) codes to their 券商總公司 (headquarters) code.

``branch_trades_schema.sql`` warns that the mapping cannot be derived from the code
prefix, and it is right: ``1020`` 合庫 and ``1030`` 土銀 are different firms sharing
``10``. The authoritative link is in TWSE's own reference data instead —
``OpenData_BRK02`` (證券商分公司基本資料) names every branch as
``<總公司名稱>-<分公司名稱>`` (``合庫-台中``, ``臺銀-台南``), so the part before the
dash can be matched against ``brokerService/brokerList`` (證券商總公司基本資料).

Measured against a real ``broker_branches`` table of 804 codes (2026-11-14):

===== ====================================================== =====
stage method                                                 hit
===== ====================================================== =====
1     BRK02 name prefix matched to a headquarters name          801
2     fallback: the branch name already in ``broker_branches``     0
3     fallback: code siblings that all agree on one firm           1
===== ====================================================== =====

Normalisation the live data makes mandatory:

* ``臺`` / ``台`` are used inconsistently *between the two feeds* for the same firm:
  BRK02 says ``臺灣企銀-桃園`` while brokerList says ``台灣企銀``. Without folding
  them, ``111E`` and ``111G`` go unresolved.
* BRK02 names carry HTML entities (``&#29319;亞-台中`` for 犇亞).
* Three dash characters appear: ``-`` (U+002D), ``－`` (U+FF0D) and a doubled ``--``.
* Full-width and ASCII spaces appear inside names (``合庫- 台中``).

Two BRK02 rows still do not match any headquarters name and are reported rather than
guessed: ``136T 香港商麥格里--自營`` against headquarters ``港商麥格理``, and
``611T 台中商銀－自營`` against ``台中銀``. Neither appears in the 分點 feed.

Stage 3 is deliberately conservative — it only adopts a firm when *every* already
resolved sibling sharing the first three characters of the code agrees on it — so it
cannot repeat the prefix-guessing mistake the schema warns about. It exists for
branches that have closed since the reference data was published (``918P`` 群益天母,
last seen 2026-10-16, is gone from BRK02 while ``9183`` 群益高雄 and friends remain).
"""

import html
import re
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

# U+2010..U+2015 dashes, U+2212 minus, U+2500/01 box drawing, U+FF0D fullwidth hyphen
_DASH_RE = re.compile(r"[-‐-―−─━－]+")
_SPACE_RE = re.compile(r"[\s　]+")
# 臺 and 台 are the same character in practice and the two TWSE feeds disagree
_VARIANTS = str.maketrans({"臺": "台"})

CodeName = Tuple[str, str]


def normalize_name(name: Optional[str]) -> str:
    """Fold a firm name to a comparable form: entities decoded, spaces out, 臺→台."""
    if not name:
        return ""
    return _SPACE_RE.sub("", html.unescape(name)).translate(_VARIANTS).strip()


def headquarters_prefix(branch_name: Optional[str]) -> str:
    """The part of a BRK02 branch name before the dash, normalised.

    >>> headquarters_prefix("合庫- 台中")
    '合庫'
    >>> headquarters_prefix("香港商麥格里--自營")
    '香港商麥格里'
    """
    return _DASH_RE.split(normalize_name(branch_name), 1)[0]


@dataclass
class MappingResult:
    """Outcome of :func:`resolve_broker_mapping`."""

    # branch_code -> broker_code
    mapping: Dict[str, str] = field(default_factory=dict)
    # branch_code -> which stage resolved it
    methods: Dict[str, str] = field(default_factory=dict)
    # broker_code -> original (un-normalised) firm name, for writing to ``brokers``
    brokers: Dict[str, str] = field(default_factory=dict)
    # BRK02 rows whose name matched no firm
    unresolved_source: List[CodeName] = field(default_factory=list)
    # branch codes present in broker_branches that no stage could resolve
    unresolved_db: List[CodeName] = field(default_factory=list)

    def method_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for method in self.methods.values():
            counts[method] = counts.get(method, 0) + 1
        return counts


def resolve_broker_mapping(
    branch_rows: Sequence[CodeName],
    hq_rows: Sequence[CodeName],
    db_branches: Optional[Mapping[str, str]] = None,
) -> MappingResult:
    """Map branch codes to headquarters codes.

    Args:
        branch_rows: ``(證券商代號, 證券商名稱)`` from ``OpenData_BRK02``.
        hq_rows: ``(Code, Name)`` from ``brokerService/brokerList``.
        db_branches: ``branch_code -> branch_name`` already in ``broker_branches``.
            Drives stages 2 and 3 and decides what counts as unresolved; the
            reference feeds alone cannot tell which branches actually traded.

    Returns:
        A :class:`MappingResult`. Codes it cannot resolve are listed, never guessed.
    """
    db_branches = dict(db_branches or {})
    result = MappingResult()

    # (normalised name, code, original name), longest name first so that
    # "full name startswith firm name" picks the most specific firm.
    firms: List[Tuple[str, str, str]] = sorted(
        ((normalize_name(name), (code or "").strip(), name) for code, name in hq_rows),
        key=lambda item: len(item[0]),
        reverse=True,
    )
    firms = [f for f in firms if f[0] and f[1]]
    by_name = {name: code for name, code, _ in firms}
    for name, code, original in firms:
        result.brokers[code] = original

    def match(prefix: str, full_name: str) -> Tuple[Optional[str], str]:
        if not prefix:
            return None, "unresolved"
        if prefix in by_name:
            return by_name[prefix], "exact"
        # The firm name may be longer than the branch's prefix: BRK02 says 臺銀-台南
        # while the firm is 臺銀證券. Only accept it when exactly one firm matches.
        candidates = {code for name, code, _ in firms if name.startswith(prefix)}
        if len(candidates) == 1:
            return candidates.pop(), "hq_name_longer"
        # Rows without a dash carry the full company name; take the longest firm
        # name the branch name starts with (``firms`` is sorted longest first).
        for name, code, _ in firms:
            if full_name.startswith(name):
                return code, "name_prefix"
        return None, "unresolved"

    # --- stage 1: the reference feed -------------------------------------------------
    for raw_code, raw_name in branch_rows:
        code = (raw_code or "").strip()
        if not code:
            continue
        full = normalize_name(raw_name)
        broker_code, method = match(headquarters_prefix(raw_name), full)
        if broker_code:
            result.mapping[code] = broker_code
            result.methods[code] = method
        else:
            result.unresolved_source.append((code, raw_name))

    # A headquarters trades under its own code, which also shows up as a 分點.
    for _, code, _ in firms:
        if code not in result.mapping:
            result.mapping[code] = code
            result.methods[code] = "headquarters"

    # --- stage 2: the branch name we already stored ----------------------------------
    for code, name in db_branches.items():
        if code in result.mapping:
            continue
        normalized = normalize_name(name)
        for firm_name, broker_code, _ in firms:
            if normalized.startswith(firm_name):
                result.mapping[code] = broker_code
                result.methods[code] = "db_name_prefix"
                break

    # --- stage 3: siblings that unanimously agree -----------------------------------
    groups: Dict[str, List[str]] = {}
    for code in db_branches:
        groups.setdefault(code[:3], []).append(code)
    for prefix, codes in groups.items():
        missing = [c for c in codes if c not in result.mapping]
        if not missing:
            continue
        agreed = {result.mapping[c] for c in codes if c in result.mapping}
        if len(agreed) != 1:
            continue  # ambiguous prefix — leave NULL rather than guess
        broker_code = agreed.pop()
        for code in missing:
            result.mapping[code] = broker_code
            result.methods[code] = "sibling_prefix"

    result.unresolved_db = sorted(
        (code, name) for code, name in db_branches.items() if code not in result.mapping
    )
    return result
