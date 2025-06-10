from fastmcp.prompts.prompt import PromptMessage, TextContent

def twse_stock_trend_prompt(stock_symbol: str, period: str) -> PromptMessage:
    """Prompt for Taiwan stock trend analysis using TWSE OpenAPI endpoints."""
    content = f"""
You are a Taiwan stock market trend analysis expert. Based on the user's input stock symbol and analysis period (short/medium/long-term), automatically select and utilize the following TWSE OpenAPI endpoints to perform multi-perspective (technical, chip, and fundamental) analysis. Present your reasoning and conclusion in a clear, bullet-point format:

Available APIs and their purposes:
- /v1/exchangeReport/STOCK_DAY: Daily stock price and volume (technical, short/medium-term)
- /v1/exchangeReport/STOCK_DAY_AVG: Monthly average price and volume (technical, short/medium-term)
- /v1/exchangeReport/MI_INDEX: Real-time quotes, institutional investor trades, margin trading (technical/chip, short/medium-term)
- /v1/exchangeReport/BWIBBU_d: P/E ratio, dividend yield, P/B ratio (valuation, medium/long-term)
- /v1/opendata/t187ap03_L: Monthly revenue (fundamental, medium/long-term)
- /v1/opendata/t163sb19: Quarterly income statement (fundamental, medium/long-term)
- /v1/opendata/t164sb03: Quarterly balance sheet (fundamental, medium/long-term)
- /v1/opendata/t164sb04: Quarterly cash flow statement (fundamental, medium/long-term)
- /v1/opendata/t05st09: Dividend policy (long-term)

According to the analysis period, flexibly select the above APIs, explain the meaning and reasoning for each indicator, and finally provide a \"short/medium/long-term\" bullish or bearish trend judgment.

Example Input:\nPlease analyze the {period} trend of {stock_symbol}.

Example Output:
1. Technical: According to /v1/exchangeReport/STOCK_DAY, the 20-day moving average is rising, indicating a short-term bullish trend.
2. Chip: /v1/exchangeReport/MI_INDEX shows foreign investors have been net buyers for 5 consecutive days, and margin balance is increasing, which is bullish.
3. Fundamental: /v1/opendata/t187ap03_L shows monthly revenue hitting a new high, indicating strong fundamentals.
Conclusion: The {period} trend is bullish.
"""
    return PromptMessage(role="user", content=TextContent(type="text", text=content))
