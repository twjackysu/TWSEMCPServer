"""utils.Page 的單元測試，以及「工具裡不再手刻分頁」的守門測試（不打網路）。

分頁曾在 13 個工具模組裡各寫一份（切片、第 a–b 筆、還有 N 筆、翻過頭的訊息），措辭各異。
"""

import pathlib
import re

import pytest
from fastmcp.exceptions import ToolError

from toolkit import handle_api_errors
from utils import InvalidArgument, Page

pytestmark = pytest.mark.offline

ROWS = list(range(1, 121))  # 120 rows


def test_first_page_of_many():
    paged = Page(50).take(ROWS)
    assert paged.rows == list(range(1, 51)) and paged.total == 120
    assert paged.span() == "顯示第 1–50 筆"
    assert paged.more() == "... 還有 70 筆，使用 offset=50 查看更多"
    assert not paged.past_end


def test_last_partial_page():
    paged = Page(50, 100).take(ROWS)
    assert paged.rows == list(range(101, 121))
    assert paged.span() == "顯示第 101–120 筆"
    assert paged.more() == ""


def test_everything_fits_needs_no_range_or_hint():
    paged = Page(50).take(ROWS[:10])
    assert paged.span() == "" and paged.more() == ""


def test_units():
    paged = Page(10).take(ROWS)
    assert paged.span("則") == "顯示第 1–10 則"
    assert paged.more("名") == "... 還有 110 名，使用 offset=10 查看更多"


def test_offset_past_the_end():
    paged = Page(50, 200).take(ROWS)
    assert paged.past_end
    assert paged.out_of_range("測試資料") == "offset=200 已超出範圍，測試資料共 120 筆。"


def test_no_rows_is_not_past_the_end():
    """沒有資料時由工具自己回「查無…」，不是 offset 的問題."""
    assert not Page(50).take([]).past_end


@pytest.mark.parametrize("limit, offset, max_limit, message", [
    (0, 0, None, "limit 必須介於 1 以上（收到 0）"),
    (-5, 0, None, "limit 必須介於 1 以上（收到 -5）"),
    (101, 0, 100, "limit 必須介於 1～100（收到 101）"),
    (10, -1, None, "offset 不可為負數（收到 -1）"),
])
def test_invalid_arguments(limit, offset, max_limit, message):
    with pytest.raises(InvalidArgument) as err:
        Page(limit, offset, max_limit)
    assert str(err.value) == message


def test_invalid_argument_reaches_the_client_as_its_own_message():
    """handle_api_errors 把 InvalidArgument 轉成 ToolError，不加「查詢失敗」前綴：不是上游失敗."""

    @handle_api_errors()
    def tool(limit: int = 0) -> str:
        Page(limit)
        return "unreachable"

    with pytest.raises(ToolError) as err:
        tool()
    assert str(err.value) == "limit 必須介於 1 以上（收到 0）"


TOOLS_DIR = pathlib.Path(__file__).resolve().parents[2] / "tools"
HAND_ROLLED = re.compile(r"\[\s*offset\s*:\s*offset\s*\+|MSG_OFFSET_OUT_OF_RANGE|remaining\s*=\s*total\s*-\s*offset")


def test_tools_page_through_utils_page():
    offenders = [
        f"{path.relative_to(TOOLS_DIR.parent)}:{n}: {line.strip()}"
        for path in sorted(TOOLS_DIR.rglob("*.py"))
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if HAND_ROLLED.search(line)
    ]
    assert offenders == [], "分頁請用 utils.Page，不要手刻：\n" + "\n".join(offenders)
