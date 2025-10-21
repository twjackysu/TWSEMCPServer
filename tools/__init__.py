"""MCP tools for TWStockMCPServer."""

def register_all_tools(mcp):
    """Register all MCP tools from different modules."""
    # Import tool registration functions
    from .company.basic_info import register_tools as register_company_basic_tools
    from .company.financials import register_tools as register_company_financial_tools
    from .company.esg import register_tools as register_company_esg_tools
    from .company.news import register_tools as register_company_news_tools
    from .company.listing import register_tools as register_company_listing_tools
    from .trading.daily import register_tools as register_trading_daily_tools
    from .trading.periodic import register_tools as register_trading_periodic_tools
    from .trading.valuation import register_tools as register_trading_valuation_tools
    from .trading.etf import register_tools as register_trading_etf_tools
    from .trading.warrants import register_tools as register_trading_warrants_tools
    from .trading.dividend_schedule import register_tools as register_trading_dividend_schedule_tools
    from .trading.market import register_tools as register_trading_market_tools
    from .market.indices import register_tools as register_market_indices_tools
    from .market.statistics import register_tools as register_market_statistics_tools
    from .market.foreign import register_tools as register_market_foreign_tools
    
    # Other tools
    from .other import register_tools as register_other_tools
    from .broker import register_tools as register_broker_tools
    
    # Company tools
    register_company_basic_tools(mcp)
    register_company_financial_tools(mcp)
    register_company_esg_tools(mcp)
    register_company_news_tools(mcp)
    register_company_listing_tools(mcp)
    
    # Trading tools
    register_trading_daily_tools(mcp)
    register_trading_periodic_tools(mcp)
    register_trading_valuation_tools(mcp)
    register_trading_etf_tools(mcp)
    register_trading_warrants_tools(mcp)
    register_trading_dividend_schedule_tools(mcp)
    register_trading_market_tools(mcp)
    
    # Market tools
    register_market_indices_tools(mcp)
    register_market_statistics_tools(mcp)
    register_market_foreign_tools(mcp)
    
    # Other tools
    register_other_tools(mcp)
    register_broker_tools(mcp)