"""Prompt for market hotspot monitoring using TWSE OpenAPI endpoints."""

from fastmcp.prompts.prompt import PromptMessage, TextContent


def market_hotspot_monitoring_prompt(monitoring_scope: str = "comprehensive", date_filter: str = "today") -> PromptMessage:
    """Prompt for market hotspot monitoring using TWSE OpenAPI endpoints."""
    content = f"""Market Hotspot Monitoring for Taiwan Stock Market:

You are a Taiwan stock market monitoring expert. Use the following TWSE OpenAPI endpoints to identify market hotspots, trending stocks, and important market developments:

### Available APIs for Hotspot Detection:

**News & Announcements:**
- `get_company_major_news(code)`: Company major announcements (filter by company or get all)
- `get_twse_news()`: Latest TWSE official news and announcements
- `get_twse_events()`: TWSE events and activities

**Market Activity Indicators:**
- `get_real_time_trading_stats()`: Real-time market statistics
- `get_stock_daily_trading(code)`: Daily trading volume and price movements
- `get_etf_regular_investment_ranking()`: Popular ETF investment trends
- `get_top_foreign_holdings()`: Foreign investment flow indicators

**Corporate Actions:**
- `get_dividend_rights_schedule(code)`: Upcoming ex-dividend dates
- `get_warrant_daily_trading(code)`: Warrant trading activity (speculation indicator)

### Monitoring Scopes:

**1. Breaking News Monitoring (monitoring_scope="news"):**
Focus on `get_company_major_news()` and `get_twse_news()` to identify:
- Companies with significant announcements today
- Regulatory changes or policy updates
- Market-moving news and corporate actions
- Industry-specific developments

**2. Trading Activity Hotspots (monitoring_scope="trading"):**
Use trading-related APIs to find:
- Stocks with unusual volume or price movements
- ETFs gaining popularity in regular investment plans
- Warrant activity indicating market speculation
- Foreign investment flow changes

**3. Comprehensive Market Scan (monitoring_scope="comprehensive"):**
Combine all APIs for complete market overview:
- Major news affecting multiple sectors
- Trading volume and foreign investment patterns
- Upcoming corporate actions and their potential impact
- Overall market sentiment indicators

### Analysis Framework:

**Step 1: News Impact Assessment**
- Scan major announcements for market-moving potential
- Identify companies with multiple recent announcements
- Assess regulatory or policy impact on sectors

**Step 2: Trading Pattern Analysis**
- Compare current trading volumes with historical averages
- Identify foreign investment flow changes
- Monitor ETF and warrant activity for sentiment

**Step 3: Forward-Looking Indicators**
- Upcoming ex-dividend dates affecting stock prices
- Corporate events that may drive future trading
- TWSE events that may impact market structure

### Output Format:

**Market Hotspots Summary:**
🔥 **Top Hotspots Today:**
1. **Company/Sector**: Reason for attention, relevant news, trading impact
2. **Market Theme**: Description, affected stocks, trend analysis

📈 **Trading Activity Alerts:**
- High volume stocks with supporting news
- Foreign investment flow changes
- Popular investment trends (ETF rankings)

📅 **Upcoming Events:**
- Ex-dividend dates in next 5 trading days
- Important TWSE announcements or events
- Corporate actions to watch

🎯 **Investment Implications:**
- Short-term trading opportunities
- Medium-term trend shifts
- Risk factors to monitor

### Current Monitoring Request:
Monitoring Scope: {monitoring_scope}
Date Filter: {date_filter}

Please provide comprehensive market hotspot analysis using the appropriate APIs above.
"""
    return PromptMessage(role="user", content=TextContent(type="text", text=content))