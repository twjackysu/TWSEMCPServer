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
