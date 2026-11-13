"""回填分點資料庫的參考表：券商總公司（brokers、broker_code）與股票主檔（stocks）。

This is the only tool in the whole server that writes anywhere. It touches exactly
three tables — ``brokers``, ``broker_branches.broker_code`` and ``stocks`` — and never
the trade tables (``branch_daily_trades``, ``branch_stock_daily``, ``import_log``),
which belong to the user's import pipeline.

Guards:

* ``dry_run=True`` is the default. It reads everything, resolves the mapping and
  reports exactly what would change, without opening a write transaction.
* Writes go through ``BranchDBConfig.WRITE_URL`` when set, so the query tools can hold
  a read-only role.
* All three statements run in one transaction, so a partially mapped reference table
  is not a possible outcome.

Why this is needed: ``branch_trades_schema.sql`` leaves ``broker_code`` nullable
because the branch → firm link cannot be derived from the code. Until it is filled,
``group_by="broker"`` cannot work; until ``stocks`` is filled, the branch tools can
only show stock codes. See ``utils/broker_mapping.py`` for the resolution rules and
the measured hit rates.
"""

from typing import Optional

from fastmcp import FastMCP

from utils import MSG_BRANCH_DB_NOT_CONFIGURED, TWSEAPIClient, handle_api_errors
from utils.broker_mapping import resolve_broker_mapping
from utils.market_snapshot import LISTED, OTC, market_snapshot
from utils.neon_db import Statement, get_branch_db

HQ_ENDPOINT = "/brokerService/brokerList"
BRANCH_ENDPOINT = "/opendata/OpenData_BRK02"

HQ_CODE_FIELD, HQ_NAME_FIELD = "Code", "Name"
BRANCH_CODE_FIELD, BRANCH_NAME_FIELD = "證券商代號", "證券商名稱"

MARKET_BY_LABEL = {LISTED: "TWSE", OTC: "TPEx"}

TARGETS = ("all", "brokers", "stocks")

UPSERT_BROKER_SQL = """
INSERT INTO brokers (broker_code, broker_name)
VALUES (%s, %s)
ON CONFLICT (broker_code) DO UPDATE SET broker_name = EXCLUDED.broker_name
"""

UPDATE_BRANCH_SQL = """
UPDATE broker_branches
SET broker_code = %s, updated_at = now()
WHERE branch_code = %s AND broker_code IS DISTINCT FROM %s
"""

UPSERT_STOCK_SQL = """
INSERT INTO stocks (stock_id, stock_name, market)
VALUES (%s, %s, %s)
ON CONFLICT (stock_id) DO UPDATE
SET stock_name = EXCLUDED.stock_name, market = EXCLUDED.market
"""

# brokers.broker_name / stocks.stock_name are VARCHAR(32); a longer upstream name
# would abort the whole transaction, so it is truncated rather than allowed to fail.
NAME_MAX = 32


def register_tools(mcp: FastMCP, client: Optional[TWSEAPIClient] = None) -> None:
    """Register the reference-table backfill tool."""
    _client = client or TWSEAPIClient.get_instance()

    @mcp.tool
    @handle_api_errors()
    def backfill_branch_reference_data(target: str = "all", dry_run: bool = True) -> str:
        """回填分點資料庫的參考表：券商總公司對照（brokers、broker_code）與股票主檔（stocks）。

        資料來源為證交所公開資料：證券商總公司基本資料（brokerService/brokerList）、
        證券商分公司基本資料（OpenData_BRK02），以及上市／上櫃股票清單。分點與券商的
        歸屬無法由代號前綴推得（1020 合庫與 1030 土銀同前綴卻是不同券商），因此改以
        分公司名稱「總公司-分公司」的前綴比對總公司名稱，無法確定者保留空值並列出。

        只會寫入 brokers、broker_branches.broker_code、stocks 三處，不會動到
        branch_daily_trades、branch_stock_daily、import_log 等交易資料。

        Args:
            target: "all"（預設，兩者都做）、"brokers"（券商總公司與 broker_code）、
                "stocks"（股票主檔）
            dry_run: True（預設）只試算並回報將變更的內容，完全不寫入；
                確認無誤後再以 dry_run=False 實際寫入

        Returns:
            試算或寫入結果：各表筆數、對應方式統計，以及無法解析的分點清單
        """
        db = get_branch_db()
        if not db.configured:
            return MSG_BRANCH_DB_NOT_CONFIGURED

        target = (target or "all").strip().lower()
        if target not in TARGETS:
            return f"target 只接受 {', '.join(TARGETS)}，收到 {target!r}"
        if not dry_run and not db.write_configured:
            return (
                "未設定可寫入的連線字串。請設定 BRANCH_DB_WRITE_URL（或讓 BRANCH_DB_URL "
                "指向具寫入權限的角色）後再以 dry_run=False 執行。"
            )

        lines = [("【試算】尚未寫入任何資料" if dry_run else "【實際寫入】")]
        statements = []

        if target in ("all", "brokers"):
            result = _plan_brokers(_client, db, statements)
            if isinstance(result, str):
                return result
            lines.extend(result)

        if target in ("all", "stocks"):
            result = _plan_stocks(_client, statements)
            if isinstance(result, str):
                return result
            lines.extend(result)

        if not statements:
            lines.append("沒有需要變更的資料。")
            return "\n".join(lines)

        if dry_run:
            lines.append("")
            lines.append(
                f"確認無誤後請執行 backfill_branch_reference_data(target=\"{target}\", dry_run=False) 實際寫入。"
            )
            return "\n".join(lines)

        counts = db.write_transaction(statements)
        lines.append("")
        lines.append("寫入完成（單一 transaction）：")
        for stmt, count in zip(statements, counts):
            lines.append(f"- {_describe(stmt)}：影響 {max(count, 0):,} 列")
        return "\n".join(lines)


def _describe(stmt: Statement) -> str:
    sql = stmt.sql.strip()
    if sql.startswith("INSERT INTO brokers"):
        return "brokers 券商總公司"
    if sql.startswith("UPDATE broker_branches"):
        return "broker_branches.broker_code 分點對應"
    if sql.startswith("INSERT INTO stocks"):
        return "stocks 股票主檔"
    return sql.splitlines()[0]


def _plan_brokers(client: TWSEAPIClient, db, statements: list):
    """Resolve the branch → firm mapping and queue its statements. Returns report lines."""
    hq_raw = client.fetch_data(HQ_ENDPOINT) or []
    branch_raw = client.fetch_data(BRANCH_ENDPOINT) or []
    if not hq_raw or not branch_raw:
        return (
            "無法取得證交所券商參考資料（brokerService/brokerList 或 "
            "OpenData_BRK02 回傳空值），請稍後重試。"
        )

    hq_rows = [
        (str(r.get(HQ_CODE_FIELD, "")).strip(), str(r.get(HQ_NAME_FIELD, "")).strip())
        for r in hq_raw
    ]
    branch_rows = [
        (
            str(r.get(BRANCH_CODE_FIELD, "")).strip(),
            str(r.get(BRANCH_NAME_FIELD, "")).strip(),
        )
        for r in branch_raw
    ]

    db_rows = db.query(
        "SELECT branch_code, branch_name, broker_code FROM broker_branches",
        max_rows=10000,
    )
    db_branches = {r["branch_code"]: r.get("branch_name") or "" for r in db_rows}
    existing = {r["branch_code"]: r.get("broker_code") for r in db_rows}

    resolved = resolve_broker_mapping(branch_rows, hq_rows, db_branches)

    # Only the branches that actually exist in broker_branches get updated, and only
    # where the value would change.
    updates = [
        (resolved.mapping[code], code, resolved.mapping[code])
        for code in db_branches
        if code in resolved.mapping and existing.get(code) != resolved.mapping[code]
    ]
    brokers = sorted(
        (code, name[:NAME_MAX]) for code, name in resolved.brokers.items()
    )

    if brokers:
        statements.append(Statement(UPSERT_BROKER_SQL, brokers, many=True))
    if updates:
        statements.append(Statement(UPDATE_BRANCH_SQL, updates, many=True))

    method_names = {
        "exact": "總公司名稱精確比對",
        "hq_name_longer": "總公司名稱前綴比對",
        "name_prefix": "全名前綴比對",
        "headquarters": "本身即總公司",
        "db_name_prefix": "既有分點名稱比對",
        "sibling_prefix": "兄弟分點代號一致",
    }
    counts = resolved.method_counts()
    breakdown = "、".join(
        f"{method_names.get(m, m)} {n:,}" for m, n in sorted(counts.items(), key=lambda kv: -kv[1])
    )

    resolvable = sum(1 for code in db_branches if code in resolved.mapping)
    lines = [
        "",
        f"brokers 券商總公司：來源 {len(hq_rows):,} 家，將新增或更新 {len(brokers):,} 家",
        f"broker_branches.broker_code：資料庫 {len(db_branches):,} 個分點，"
        f"其中 {resolvable:,} 個可解析、{len(resolved.unresolved_db):,} 個無法解析，"
        f"本次需更新 {len(updates):,} 個",
    ]
    if breakdown:
        lines.append(f"對應方式（含來源全部 {len(resolved.methods):,} 筆）：{breakdown}")
    if resolved.unresolved_db:
        lines.append("無法解析的分點（保留空值，不猜測）：")
        for code, name in resolved.unresolved_db[:20]:
            lines.append(f"- {code} {name}")
        if len(resolved.unresolved_db) > 20:
            lines.append(f"...（共 {len(resolved.unresolved_db):,} 個）")
    if resolved.unresolved_source:
        lines.append(
            f"來源資料中有 {len(resolved.unresolved_source):,} 筆分公司名稱比不到總公司"
            "（未出現在本資料庫者不影響）"
        )
    return lines


def _plan_stocks(client: TWSEAPIClient, statements: list):
    """Queue the stocks upsert from the listed/OTC snapshot. Returns report lines."""
    snapshot, data_date = market_snapshot(client)
    if not snapshot:
        return "無法取得上市／上櫃股票清單，請稍後重試。"

    rows = []
    skipped = 0
    for code, stock in sorted(snapshot.items()):
        market = MARKET_BY_LABEL.get(stock.market)
        if not market or not stock.name:
            skipped += 1
            continue
        rows.append((code, stock.name[:NAME_MAX], market))

    if rows:
        statements.append(Statement(UPSERT_STOCK_SQL, rows, many=True))

    listed = sum(1 for r in rows if r[2] == "TWSE")
    otc = len(rows) - listed
    lines = [
        "",
        f"stocks 股票主檔：將新增或更新 {len(rows):,} 檔"
        f"（上市 {listed:,} / 上櫃 {otc:,}），資料日 {data_date or '未知'}",
    ]
    if skipped:
        lines.append(f"（略過 {skipped:,} 檔缺少名稱或市場別的標的）")
    return lines
