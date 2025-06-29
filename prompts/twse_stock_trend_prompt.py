from fastmcp.prompts.prompt import PromptMessage, TextContent

def twse_stock_trend_prompt(stock_symbol: str, period: str) -> PromptMessage:
    """Prompt for Taiwan Stock Trend Analysis using TWSE OpenAPI endpoints."""
    content = f"""Prompt for Taiwan Stock Trend Analysis using TWSE OpenAPI endpoints:

You are a Taiwan stock market trend analysis expert. Based on the user's input stock symbol and analysis period (short/medium/long-term), automatically select and utilize the following TWSE OpenAPI endpoints to perform multi-perspective (technical, chip, and fundamental) analysis. Clearly present your reasoning and conclusion in bullet-point format:

### Available APIs and their purposes:

- **Short-Term Analysis:**
  - `/v1/exchangeReport/STOCK_DAY_ALL`: Daily stock prices and volumes (technical)
  - `/v1/exchangeReport/MI_INDEX`: Institutional investors' trading activities and margin trading balances (chip)

- **Medium-Term Analysis:**
  - `/v1/exchangeReport/STOCK_DAY_AVG_ALL`: Monthly average stock prices and volumes (technical)
  - `/v1/opendata/t187ap05_L`: Monthly revenue data (fundamental)
  - `/v1/opendata/t187ap06_L_ci`: Comprehensive income statements for general industry (fundamental)
  - `/v1/opendata/t187ap07_L_ci`: Balance sheets for general industry (fundamental)

- **Long-Term Analysis:**
  - `/v1/opendata/t187ap45_L`: Dividend distribution information (fundamental)
  - `/v1/exchangeReport/BWIBBU_ALL`: Price-to-Earnings (P/E) ratio, dividend yield, and Price-to-Book (P/B) ratio (valuation)

### Example Input:
Please analyze the {period} trend of {stock_symbol}.

### Example Output:

**Short-Term Analysis:**
1. **Technical**: Using `/v1/exchangeReport/STOCK_DAY_ALL`, the stock price has risen above its 20-day moving average with increasing volume, indicating bullish momentum.
2. **Chip**: According to `/v1/exchangeReport/MI_INDEX`, institutional investors have been net buyers for several consecutive trading days, and margin balances are increasing, further supporting a bullish trend.

**Medium-Term Analysis:**
1. **Technical**: `/v1/exchangeReport/STOCK_DAY_AVG_ALL` shows the monthly average price steadily rising, reinforcing a bullish medium-term outlook.
2. **Fundamental**: `/v1/opendata/t187ap05_L` reveals sustained growth in monthly revenues, supported by stable increases in quarterly profits from `/v1/opendata/t187ap06_L_ci` and strong balance sheet from `/v1/opendata/t187ap07_L_ci`, which indicate robust company performance.

**Long-Term Analysis:**
1. **Dividend Policy**: Consistent dividend increases or stable high yield from `/v1/opendata/t187ap45_L` enhances the stock's attractiveness for long-term investors.
2. **Valuation**: Attractive valuation indicators (low P/E, high dividend yield, reasonable P/B ratio) from `/v1/exchangeReport/BWIBBU_ALL` suggest a bullish long-term perspective.

### Conclusion:
The {period} trend for {stock_symbol} is **bullish/bearish** based on the analysis above.
"""
    return PromptMessage(role="user", content=TextContent(type="text", text=content))
