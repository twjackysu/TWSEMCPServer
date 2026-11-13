"""Constants for TWSE Stock MCP Server."""

from .config import DisplayConfig

# Display limits (imported from config for backward compatibility)
DEFAULT_DISPLAY_LIMIT = DisplayConfig.DEFAULT_DISPLAY_LIMIT

# Error messages
MSG_NO_DATA = "目前沒有{data_type}資料。"
MSG_QUERY_FAILED = "查詢失敗: {error}"
MSG_NO_DATA_FOR_CODE = "查無{query_target}的{data_type}"
# 清單經過篩選（name 關鍵字、有效欄位檢查）後一筆不剩時使用。與 MSG_NO_DATA 分開：
# 那句是「來源整份沒有資料」，這句是「來源有資料，但沒有符合這次查詢條件的」。
MSG_NO_MATCHING_DATA = "查無符合條件的{data_type}。"
# offset 翻過資料尾端時使用。與上面兩句再分開：資料存在、條件也有符合的，只是這一頁
# 已經沒有東西了。少了這句，表頭會印出「顯示第 101–2 筆」這種不可能的區間後接零列資料。
MSG_OFFSET_OUT_OF_RANGE = "offset={offset} 已超出範圍，{data_type}共 {count} 筆。"

# Success messages
MSG_TOTAL_RECORDS = "共有 {count} 筆{data_type}："

# TWSE legacy endpoints append a market-wide summary row to the per-stock `data`
# array (BFIAUU 的「總計」、TWT93U/TWTASU 的「合計」). It is not a security and must
# not be counted or rendered as one — its 量/金額 是全市場加總，與明細列同構，
# 混進清單會讓下游把它當成一筆真實成交。
SUMMARY_ROW_LABELS = ("總計", "合計")


# 分點進出資料庫（Neon PostgreSQL）訊息。
# 這三句刻意分開：呼叫端要能分辨「沒設定連線」、「資料庫沒收錄這檔股票」與
# 「這檔股票那天沒有資料」。混成一句的話，LLM 會把「沒收錄」誤讀成「沒人買賣」。
MSG_BRANCH_DB_NOT_CONFIGURED = (
    "尚未設定分點資料庫連線。請在環境變數 BRANCH_DB_URL 填入 PostgreSQL 連線字串"
    "（例如 Neon 的 connection string）後重新啟動服務。"
)
MSG_BRANCH_STOCK_NOT_COVERED = (
    "分點資料庫未收錄股票 {stock_id}。可用 get_branch_data_coverage 查看目前收錄了哪些股票與日期範圍。"
)
MSG_BRANCH_NO_DATA_ON_DATE = "股票 {stock_id} 在 {date} 沒有分點進出資料（該日可能非交易日，或尚未匯入）。"
MSG_BRANCH_NOT_FOUND = "查無分點「{keyword}」。可用 search_broker_branch 以名稱關鍵字查詢分點代號。"
MSG_BRANCH_AMBIGUOUS = "「{keyword}」對應到多個分點，請改用分點代號指定（代號區分大小寫）：\n{candidates}"
MSG_BROKER_MAPPING_MISSING = (
    "broker_branches.broker_code 尚未回填，無法依券商總公司彙總。"
    "請先執行 backfill_branch_reference_data(target=\"brokers\", dry_run=False)。"
)
