"""Contract test 只能驗介面，不能替第三方驗資料（不打網路）。

tests/contract/ 的工作是：第三方改了什麼會讓我們的工具壞掉（網址、回應格式、欄位、我們會解析的數字格式、
我們依賴的參數行為或標籤），提早知道。上游的資料本身對不對——加總、餘額等式、成交價×股數、數值範圍、單位、
高 ≥ 低——是資料來源自己的事，不是我們的測試範圍（CLAUDE.md「Testing」）。這類檢查幾次被寫進 contract test，
所以這裡掃描 tests/contract/*.py，出現下列寫法就失敗：

- 算術：+ - * / // % **（字串或 list 的串接、len(...) 加減整數常數的欄數除外）
- 大小比較 < <= > >=：只允許 len(...) 和整數常數比（欄數、有沒有資料），以及集合的子集關係（參數篩選）；
  一次比三個值（a <= b <= c）不行
- 呼叫 abs、sum、min、max、round

assert 的錯誤訊息與 f-string 裡的運算只是顯示用，不掃。真的需要例外時，在那一行寫 `# contract-ok: <理由>`，
理由說明它檢查的是哪個介面（例如「成交時間欄仍是 HHMMSS，intraday 依此解析」），review 時一眼看得到。
"""

import ast
import pathlib
import re

import pytest

pytestmark = pytest.mark.offline

CONTRACT_DIR = pathlib.Path(__file__).resolve().parents[1] / "contract"
ARITHMETIC = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)
ORDERING = (ast.Lt, ast.LtE, ast.Gt, ast.GtE)
FORBIDDEN_CALLS = {"abs", "sum", "min", "max", "round"}
EXCEPTION = re.compile(r"#\s*contract-ok:\s*\S")


def _is_sequence_literal(node) -> bool:
    """A string, list or slice operand: + is concatenation, not arithmetic."""
    return (isinstance(node, (ast.JoinedStr, ast.List, ast.ListComp, ast.Tuple))
            or (isinstance(node, ast.Constant) and isinstance(node.value, str))
            or (isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Slice)))


def _is_len(node) -> bool:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "len"


def _is_int(node) -> bool:
    return isinstance(node, ast.Constant) and type(node.value) is int


def _is_set(node) -> bool:
    return isinstance(node, (ast.Set, ast.SetComp)) or (
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("set", "frozenset"))


def _is_width(left, right) -> bool:
    """len(...) against an int constant: a column count or "has rows", not the data's values."""
    return (_is_len(left) and _is_int(right)) or (_is_int(left) and _is_len(right))


def _problem(node):
    if isinstance(node, ast.BinOp) and isinstance(node.op, ARITHMETIC):
        if not (_is_sequence_literal(node.left) or _is_sequence_literal(node.right)
                or _is_width(node.left, node.right)):
            return "算術（替上游驗算資料？）"
    if isinstance(node, ast.Compare) and any(isinstance(op, ORDERING) for op in node.ops):
        if len(node.ops) > 1:
            return "範圍比較 a <= b <= c（替上游驗資料？）"
        left, right = node.left, node.comparators[0]
        if not (_is_width(left, right) or _is_set(left) or _is_set(right)):
            return "大小比較（只允許 len() 對整數常數、集合子集）"
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
        return f"{node.func.id}()（替上游驗算資料？）"
    return None


def _children(node):
    """Child nodes, without assert messages and f-strings: what is only shown is not checked."""
    for child in ast.iter_child_nodes(node):
        if isinstance(node, ast.Assert) and child is node.msg:
            continue
        if isinstance(child, ast.JoinedStr):
            continue
        yield child


def _statement_lines(stmt: ast.stmt, lines):
    """The statement's own lines: for a compound statement only its header, not its body."""
    body = getattr(stmt, "body", None)
    end = body[0].lineno - 1 if isinstance(body, list) and body else (stmt.end_lineno or stmt.lineno)
    return lines[stmt.lineno - 1:max(end, stmt.lineno)]


def violations(source: str):
    """(line, problem, code) for every forbidden expression in a contract test module's source."""
    lines = source.splitlines()
    found = []

    def visit(node, stmt):
        if isinstance(node, ast.stmt):
            stmt = node
        problem = _problem(node)
        hit = (node.lineno, problem, lines[node.lineno - 1].strip()) if problem else None
        if hit and hit not in found and stmt is not None and not any(
                EXCEPTION.search(line) for line in _statement_lines(stmt, lines)):
            found.append(hit)
        for child in _children(node):
            visit(child, stmt)

    visit(ast.parse(source), None)
    return found


def test_contract_tests_only_check_the_interface():
    offenders = [
        f"{path.relative_to(CONTRACT_DIR.parent)}:{line}  {problem}\n    {code}"
        for path in sorted(CONTRACT_DIR.glob("*.py"))
        for line, problem, code in violations(path.read_text(encoding="utf-8"))
    ]
    assert offenders == [], (
        "contract test 只驗我們依賴的介面，不替第三方驗資料（加總、等式、範圍、單位、高低價）。"
        "真的是介面檢查時，在該行加 `# contract-ok: <理由>`：\n" + "\n".join(offenders))


# The checks #144 removed must be caught; the interface checks it kept must pass.
@pytest.mark.parametrize("code", [
    "assert s.today == s.previous + s.sold - s.bought - s.cash_returned",
    "assert abs(t.price * t.volume - t.value) <= Decimal('0.5')",
    "assert r.low <= r.close <= r.high",
    "assert q.last_ask <= q.close * Decimal('1.1')",
    "assert v.pe is None or v.pe > 0",
    "assert v.dividend_yield >= 0",
    "assert int(v.dividend_year) in (roc - 1, roc - 2)",
    "net = a.buy - a.sell\nassert net == a.net",
    "assert sum(x.net for x in rows) == total",
    "assert len(rows) > 6 and rows[0].close > 0",
])
def test_data_validation_is_caught(code):
    assert violations(code), f"未被攔下：{code}"


@pytest.mark.parametrize("code", [
    "assert month is not None and month.rows",
    "assert None not in (r.open, r.close), f'數字格式已變更：{r.close * 2}'",
    "assert len(data[0]) == 6",
    "assert data and all(len(r) >= 4 for r in data)",
    "assert len(rows) > 1, '查無資料'",
    "assert directions <= {'+', '-', ''}",
    "assert {'a', 'b'} <= set(parent)",
    "assert fields[:11] + fields[12:13] == ['代號']",
    "assert levels == [str(i) for i in range(1, 16)] + ['total']",
    "assert all(0 <= t[2] <= 235959 for t in ticks)  # contract-ok: 成交時間欄仍是 HHMMSS",
    "assert x == 1, f'{a - b}'",
])
def test_interface_checks_pass(code):
    assert violations(code) == [], code
