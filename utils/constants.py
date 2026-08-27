"""Constants for TWSE Stock MCP Server."""

from .config import DisplayConfig

# Display limits (imported from config for backward compatibility)
DEFAULT_DISPLAY_LIMIT = DisplayConfig.DEFAULT_DISPLAY_LIMIT

# Error messages
MSG_NO_DATA = "目前沒有{data_type}資料。"
MSG_QUERY_FAILED = "查詢失敗: {error}"
MSG_NO_DATA_FOR_CODE = "查無{query_target}的{data_type}"

# Success messages
MSG_TOTAL_RECORDS = "共有 {count} 筆{data_type}："

# TWSE legacy endpoints append a market-wide summary row to the per-stock `data`
# array (BFIAUU 的「總計」、TWT93U/TWTASU 的「合計」). It is not a security and must
# not be counted or rendered as one — its 量/金額 是全市場加總，與明細列同構，
# 混進清單會讓下游把它當成一筆真實成交。
SUMMARY_ROW_LABELS = ("總計", "合計")
