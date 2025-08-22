"""Prompt for investment screening using TWSE OpenAPI endpoints."""

from fastmcp.prompts.prompt import PromptMessage, TextContent


def investment_screening_prompt(screening_criteria: str = "comprehensive", risk_level: str = "moderate") -> PromptMessage:
    """Prompt for investment screening using TWSE OpenAPI endpoints."""
    content = f"""Investment Screening for Taiwan Stock Market:

You are a Taiwan stock market investment screening expert. Use the following TWSE OpenAPI endpoints to screen and recommend investment opportunities based on multiple criteria:

### Available APIs for Investment Screening:

**Valuation & Performance:**
- `get_stock_valuation_ratios(code)`: P/E ratios, dividend yields, P/B ratios
- `get_stock_daily_trading(code)`: Price performance and trading volume
- `get_stock_monthly_trading(code)`: Monthly performance trends
- `get_company_monthly_revenue(code)`: Revenue growth patterns

**Quality Indicators:**
- `get_company_profile(code)`: Company basic information and industry
- `get_company_income_statement(code)`: Profitability and growth metrics
- `get_company_balance_sheet(code)`: Financial strength and stability
- `get_company_dividend(code)`: Dividend history and consistency

**Market Validation:**
- `get_market_index_info(category, count, format)`: Sector performance and market context
  - Use `category="sector", format="summary"` to identify outperforming industries
  - Use `category="esg", count=10` for ESG investment universe
  - Use `category="dividend", format="simple"` for income-focused screening
- `get_top_foreign_holdings()`: Foreign investor preferences (quality signal)
- `get_etf_regular_investment_ranking()`: Popular retail investment choices
- `get_margin_trading_info()`: Institutional vs retail interest
- `get_foreign_investment_by_industry()`: Sector allocation trends

**Risk Assessment:**
- `get_company_major_news(code)`: Recent corporate developments
- `get_dividend_rights_schedule(code)`: Upcoming corporate actions
- `get_warrant_daily_trading(code)`: Speculation activity levels

### Screening Criteria:

**1. Value Investing (screening_criteria="value"):**
- Low P/E ratios (<15) with stable earnings
- High dividend yields (>3%) with sustainable payouts  
- Low P/B ratios (<1.5) with strong balance sheets
- Foreign investment validation for quality confirmation

**2. Growth Investing (screening_criteria="growth"):**
- Consistent revenue growth (>10% annually)
- Expanding profit margins from income statements
- Increasing foreign ownership (growth recognition)
- Popular in ETF regular investment rankings

**3. Dividend Focus (screening_criteria="dividend"):**
- High dividend yields with consistent payment history
- Strong cash flow from operations
- Stable or growing dividend trends
- Foreign investor dividend stock preferences

**4. Momentum & Trends (screening_criteria="momentum"):**
- Strong recent price performance with volume confirmation
- Positive news flow and corporate developments
- Increasing foreign investment interest
- Above-average trading activity

**5. Comprehensive Analysis (screening_criteria="comprehensive"):**
Combine all factors for balanced recommendations:
- Value metrics within reasonable ranges
- Growth prospects with quality indicators
- Dividend sustainability and yield attractiveness
- Market validation through foreign/institutional interest

### Risk Level Adjustments:

**Conservative ({risk_level}="conservative"):**
- Large-cap companies with stable business models
- Strong balance sheets and consistent dividends
- High foreign ownership (>30%) as quality indicator
- Established market leaders in defensive sectors

**Moderate ({risk_level}="moderate"):**
- Mix of large and mid-cap opportunities
- Growth with reasonable valuations
- Moderate foreign ownership (15-30%)
- Balanced risk-return characteristics

**Aggressive ({risk_level}="aggressive"):**
- Small to mid-cap growth opportunities
- Higher growth rates with acceptable valuations
- Emerging trends and market themes
- Some speculation through warrant activity

### Screening Process:

**Step 1: Universe Definition**
- Use `get_top_foreign_holdings()` and `get_etf_regular_investment_ranking()` for quality universe
- Filter by market cap and liquidity requirements
- Consider sector diversification needs

**Step 2: Quantitative Screening**
- Apply valuation, growth, and dividend criteria
- Screen for financial strength metrics
- Analyze trading patterns and volume trends

**Step 3: Qualitative Validation**
- Review recent news and corporate developments
- Assess foreign investor interest trends
- Evaluate upcoming corporate actions impact

**Step 4: Risk Assessment**
- Check margin trading levels for speculation risks
- Review warrant activity as sentiment indicator
- Assess sector and market concentration risks

### Output Format:

**🎯 Investment Recommendations:**

**Top Picks:**
1. **Company (Code)**: Rationale, Key Metrics, Risk Level
2. **Company (Code)**: Rationale, Key Metrics, Risk Level
3. **Company (Code)**: Rationale, Key Metrics, Risk Level

**📊 Screening Results by Criteria:**
- **Value Stocks**: Best P/E, P/B, dividend yield combinations
- **Growth Stocks**: Revenue growth, margin expansion, market expansion
- **Dividend Stocks**: Yield, sustainability, growth potential
- **Foreign Favorites**: High foreign ownership with strong fundamentals

**⚖️ Risk-Return Analysis:**
- Expected return profiles by risk level
- Diversification recommendations
- Sector allocation suggestions
- Position sizing guidelines

**📈 Market Context:**
- Current market environment assessment
- Sector rotation trends and opportunities  
- Foreign investment flow implications
- Timing considerations for entry

**🔍 Further Research Recommendations:**
- Companies requiring deeper fundamental analysis
- Emerging trends worth monitoring
- Potential catalysts and risk factors
- Portfolio construction considerations

### Current Screening Request:
Screening Criteria: {screening_criteria}
Risk Level: {risk_level}

Please provide comprehensive investment screening using the appropriate APIs above.
"""
    return PromptMessage(role="user", content=TextContent(type="text", text=content))