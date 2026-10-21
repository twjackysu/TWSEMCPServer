"""回應大小的最後保險（toolkit.response_limit：FastMCP ResponseLimitingMiddleware），不打網路。

多數 limit 沒有上限，limit=100000 查 44,717 檔權證就是 5.6 MB。超過 TWSE_MAX_RESPONSE_BYTES 的回應
保留前段文字、在截斷處接上中文說明；正常回應與錯誤訊息都不受影響。
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware.response_limiting import ResponseLimitingMiddleware

import server
import tools
from tests.offline import OfflineClient
from toolkit import ArgumentErrorsInChinese, response_limit
from utils.config import ServerConfig

pytestmark = pytest.mark.offline

ROOT = Path(__file__).resolve().parents[2]
WARRANTS = [{"權證代號": f"03{i:04d}", "權證簡稱": f"台積電元大{i:02d}購{i % 9:02d}", "權證類型": "認購",
             "類別": "一般型", "標的證券/指數": "2330", "最新履約價格(元)/履約指數": "1,234.5",
             "最後交易日": "1160320"} for i in range(400)]


def _server(max_size=None):
    """A server like server.py (argument errors in Chinese, then the cap) over canned warrants."""
    mcp = FastMCP("probe")
    mcp.add_middleware(ArgumentErrorsInChinese())
    if max_size:
        mcp.add_middleware(response_limit(max_size))
    tools.register_all_tools(mcp, OfflineClient({"/opendata/t187ap37_L": WARRANTS}))
    return mcp


def _call(mcp, name, args):
    async def run():
        async with Client(mcp) as client:
            return await client.call_tool(name, args)
    return asyncio.run(run())


def test_server_caps_replies_by_default():
    caps = [m for m in server.mcp.middleware if isinstance(m, ResponseLimitingMiddleware)]
    assert [m.max_size for m in caps] == [ServerConfig.MAX_RESPONSE_BYTES] == [500_000]
    # every text tool; structured tools bound themselves (the cap would hide their output schema)
    assert caps[0].tools == server.registered.text_tools
    assert len(caps[0].tools) == 173 and "get_stock_screener" not in caps[0].tools


def test_structured_tools_keep_their_output_schema_on_the_server():
    async def listed():
        async with Client(server.mcp) as client:
            return {t.name: t.output_schema for t in await client.list_tools()}

    schemas = asyncio.run(listed())
    assert {name for name, s in schemas.items() if s} == server.registered.structured
    assert schemas["get_stock_screener"]["properties"]["stocks"]["type"] == "array"


def test_a_runaway_reply_is_cut_and_says_so():
    full = _call(_server(), "get_warrant_basic_info", {"limit": 100000}).content[0].text
    assert len(full.encode("utf-8")) > 20_000

    result = _call(_server(5_000), "get_warrant_basic_info", {"limit": 100000})
    assert not result.is_error and len(result.content) == 1
    text = result.content[0].text
    assert len(text.encode("utf-8")) <= 5_000  # FastMCP sizes the text, leaving ~50 bytes for the JSON around it
    notice = "……\n\n⚠️ 回應超過 5,000 位元組上限，以上只是前段，最後一行可能不完整。"
    head, _, tail = text.partition(notice)
    assert full.startswith(head) and head.startswith("共有 400 筆上市權證基本資料")
    assert tail.startswith("請縮小查詢：用 limit／offset 分頁")


def test_a_reply_within_the_cap_is_untouched():
    args = {"limit": 3}
    assert _call(_server(5_000), "get_warrant_basic_info", args).content == \
        _call(_server(), "get_warrant_basic_info", args).content


def test_argument_errors_pass_through_whole():
    with pytest.raises(ToolError) as raised:
        _call(_server(200), "get_warrant_basic_info", {"limit": 0})
    assert "limit" in str(raised.value) and "位元組上限" not in str(raised.value)


def test_a_cap_must_be_positive():
    with pytest.raises(ValueError, match="max_size must be positive"):
        response_limit(-1)


_PROBE = """
import logging
logging.disable(logging.CRITICAL)
import server
from fastmcp.server.middleware.response_limiting import ResponseLimitingMiddleware
print([m.max_size for m in server.mcp.middleware if isinstance(m, ResponseLimitingMiddleware)])
"""


@pytest.mark.parametrize("setting, caps", [("0", "[]"), ("1234", "[1234]")])
def test_server_reads_the_cap_from_the_environment(setting, caps):
    env = {**os.environ, "TWSE_MAX_RESPONSE_BYTES": setting}
    result = subprocess.run([sys.executable, "-c", _PROBE], cwd=ROOT, env=env, capture_output=True, text=True,
                            timeout=120)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == caps
