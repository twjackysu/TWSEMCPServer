"""MCP tools for TWStockMCPServer."""

def register_all_tools(mcp):
    """Register all MCP tools from different modules."""
    # Import tool registration functions
    from .company.basic_info import register_tools as register_company_basic_tools
    from .company.financials import register_tools as register_company_financial_tools
    from .company.esg import register_tools as register_company_esg_tools
    from .trading.daily import register_tools as register_trading_daily_tools
    from .trading.periodic import register_tools as register_trading_periodic_tools
    from .trading.valuation import register_tools as register_trading_valuation_tools
    from .market.indices import register_tools as register_market_indices_tools
    from .market.statistics import register_tools as register_market_statistics_tools
    
    # Company tools
    register_company_basic_tools(mcp)
    register_company_financial_tools(mcp)
    register_company_esg_tools(mcp)
    
    # Trading tools
    register_trading_daily_tools(mcp)
    register_trading_periodic_tools(mcp)
    register_trading_valuation_tools(mcp)
    
    # Market tools
    register_market_indices_tools(mcp)
    register_market_statistics_tools(mcp)