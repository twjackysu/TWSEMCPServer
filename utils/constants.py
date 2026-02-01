"""Constants for TWSE Stock MCP Server."""

# Display limits
DEFAULT_DISPLAY_LIMIT = 20

# Error messages
MSG_NO_DATA = "目前沒有{data_type}資料。"
MSG_QUERY_FAILED = "查詢失敗: {error}"
MSG_QUERY_FAILED_WITH_CODE = "查詢{query_target}時發生錯誤: {error}"
MSG_NO_DATA_FOR_CODE = "查無{query_target}的{data_type}"
MSG_MORE_RECORDS = "\n... 還有 {count} 筆資料"

# Success messages
MSG_TOTAL_RECORDS = "共有 {count} 筆{data_type}："
