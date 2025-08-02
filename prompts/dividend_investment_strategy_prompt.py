"""Prompt for dividend investment strategy using TWSE OpenAPI endpoints."""

from fastmcp.prompts.prompt import PromptMessage, TextContent


def dividend_investment_strategy_prompt(strategy_type: str = "high_yield", time_horizon: str = "quarterly") -> PromptMessage:
    """Prompt for dividend investment strategy using TWSE OpenAPI endpoints.""" 
    content = f"""Dividend Investment Strategy for Taiwan Stock Market:

You are a Taiwan stock market dividend investment expert. Use the following TWSE OpenAPI endpoints to develop comprehensive dividend investment strategies:

### Available APIs for Dividend Analysis:

**Dividend Scheduling & Planning:**
- `get_dividend_rights_schedule(code)`: Ex-dividend dates and dividend amounts
- `get_company_dividend(code)`: Historical dividend distribution data
- `get_stock_valuation_ratios(code)`: P/E ratios, dividend yields, P/B ratios

**Fundamental Analysis:**
- `get_company_profile(code)`: Company basic information and industry classification
- `get_company_monthly_revenue(code)`: Revenue trends supporting dividend sustainability
- `get_company_income_statement(code)`: Earnings data for payout ratio analysis
- `get_company_balance_sheet(code)`: Financial strength assessment

**Market Validation:**
- `get_top_foreign_holdings()`: Foreign investor dividend stock preferences  
- `get_etf_regular_investment_ranking()`: Popular dividend-focused investment trends
- `get_stock_daily_trading(code)`: Price stability around ex-dividend dates

### Investment Strategy Types:

**1. High Yield Strategy (strategy_type="high_yield"):**
Focus on stocks with attractive dividend yields:
- Use `get_stock_valuation_ratios()` to identify high dividend yield stocks (>4%)
- Validate sustainability with `get_company_income_statement()` and revenue trends
- Check `get_dividend_rights_schedule()` for upcoming distributions
- Assess foreign interest via `get_top_foreign_holdings()`

**2. Dividend Growth Strategy (strategy_type="growth"):**
Target companies with consistent dividend increases:
- Analyze `get_company_dividend()` for historical dividend growth patterns
- Cross-reference with `get_company_monthly_revenue()` for business growth
- Use `get_company_balance_sheet()` to ensure financial strength
- Monitor foreign investment trends as quality validation

**3. Ex-Dividend Timing Strategy (strategy_type="timing"):**
Optimize entry/exit around ex-dividend dates:
- Use `get_dividend_rights_schedule()` for precise timing
- Analyze `get_stock_daily_trading()` for historical price patterns
- Consider `get_stock_valuation_ratios()` for fair value assessment
- Factor in upcoming dividend announcements

**4. Sector Dividend Strategy (strategy_type="sector"):**
Focus on dividend-paying sectors:
- Group companies by industry via `get_company_profile()`
- Compare sector dividend yields and sustainability
- Analyze foreign investor sector preferences
- Diversify across stable dividend-paying industries

### Time Horizon Analysis:

**Quarterly Focus ({time_horizon}="quarterly"):**
- Next 3 months' ex-dividend schedule
- Quarterly earnings impact on dividend sustainability
- Short-term price movements around ex-dates

**Annual Planning ({time_horizon}="annual"):**
- Full year dividend calendar planning
- Annual dividend growth trend analysis
- Long-term sector rotation strategies

### Analysis Framework:

**Step 1: Dividend Screening**
- Screen for target dividend yields or growth rates
- Verify upcoming ex-dividend dates and amounts
- Check historical dividend consistency

**Step 2: Fundamental Validation**  
- Assess earnings coverage and payout ratios
- Review revenue stability and growth trends
- Analyze balance sheet strength and cash flow

**Step 3: Market Positioning**
- Compare with foreign investment preferences
- Monitor popular dividend investment trends
- Assess market timing and valuation levels

### Output Format:

**📊 Dividend Investment Recommendations:**

**Top Dividend Stocks:**
1. **Company (Code)**: Yield X%, Ex-date: Date, Rationale
2. **Company (Code)**: Yield X%, Ex-date: Date, Rationale

**📅 Dividend Calendar (Next 3 Months):**
- Week 1: Companies going ex-dividend, expected yields
- Week 2: Companies going ex-dividend, expected yields  
- [Continue for planning horizon]

**🎯 Strategy Insights:**
- **Risk Assessment**: Dividend sustainability factors
- **Entry Timing**: Optimal purchase windows
- **Portfolio Construction**: Diversification recommendations
- **Market Conditions**: Current dividend environment analysis

**💡 Advanced Strategies:**
- Dividend capture opportunities  
- Sector rotation based on dividend cycles
- Tax optimization considerations
- Foreign investment flow implications

### Current Strategy Request:
Strategy Type: {strategy_type}
Time Horizon: {time_horizon}

Please provide comprehensive dividend investment strategy using the appropriate APIs above.
"""
    return PromptMessage(role="user", content=TextContent(type="text", text=content))