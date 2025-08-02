"""Prompt for foreign investment analysis using TWSE OpenAPI endpoints."""

from fastmcp.prompts.prompt import PromptMessage, TextContent


def foreign_investment_analysis_prompt(analysis_type: str = "overview", industry: str = "", stock_symbol: str = "") -> PromptMessage:
    """Prompt for foreign investment analysis using TWSE OpenAPI endpoints."""
    content = f"""Foreign Investment Analysis for Taiwan Stock Market:

You are a Taiwan stock market foreign investment expert. Based on the analysis type requested, use the following TWSE OpenAPI endpoints to provide comprehensive foreign investment insights:

### Available APIs and their purposes:

**Foreign Investment Overview:**
- `get_foreign_investment_by_industry()`: Foreign investment holding ratios by industry category
- `get_top_foreign_holdings()`: Top 20 companies by foreign investment holdings
- `get_company_profile(code)`: Company basic information for context

**Enhanced Analysis:**
- `get_company_dividend(code)`: Dividend information for foreign-favored stocks
- `get_stock_valuation_ratios(code)`: P/E, dividend yield, P/B ratios
- `get_company_monthly_revenue(code)`: Revenue performance data

### Analysis Types:

**1. Industry Analysis (analysis_type="industry"):**
Use `get_foreign_investment_by_industry()` to analyze:
- Which industries attract the most foreign investment
- Foreign holding percentages by sector
- Number of companies per industry with foreign investment
- Industry-specific investment patterns

**2. Top Holdings Analysis (analysis_type="top_holdings"):**
Use `get_top_foreign_holdings()` and `get_company_profile()` to analyze:
- Top 20 companies by foreign investment holdings
- Available investment capacity vs current holdings
- Investment upper limits and restrictions
- Company profiles of foreign-favored stocks

**3. Specific Stock Analysis (analysis_type="stock", provide stock_symbol):**
Combine multiple APIs for stock_symbol analysis:
- Foreign investment position and limits
- Company fundamentals and dividend policy
- Valuation metrics compared to foreign investment trends

### Example Output Format:

**Foreign Investment Industry Analysis:**
- **Technology Sector**: 45.2% average foreign holding, 120 companies, driven by semiconductor and electronics
- **Financial Services**: 32.1% average foreign holding, concentrated in major banks
- **Healthcare**: 28.7% average foreign holding, growing interest in biotech

**Top Foreign Holdings Insights:**
1. **TSMC (2330)**: 78% foreign holding, near investment limit, strong fundamentals support
2. **Hon Hai (2317)**: 65% foreign holding, significant available capacity, EMS leader
3. **MediaTek (2454)**: 72% foreign holding, chip design focus, attractive valuations

**Investment Recommendations:**
Based on foreign investment patterns, consider stocks with:
- Strong foreign interest but available investment capacity
- Solid fundamentals supporting foreign confidence
- Industries showing increasing foreign allocation trends

### Current Analysis Request:
Analysis Type: {analysis_type}
{f"Target Industry: {industry}" if industry else ""}
{f"Target Stock: {stock_symbol}" if stock_symbol else ""}

Please provide comprehensive foreign investment analysis using the appropriate APIs above.
"""
    return PromptMessage(role="user", content=TextContent(type="text", text=content))