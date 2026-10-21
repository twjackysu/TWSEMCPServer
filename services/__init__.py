"""Services: data the tools need, assembled from one or more gateways (sources/) plus pure logic.

Example: price_series fetches a stock's daily bars month by month from the right market's gateway
and backward-adjusts them for ex-rights events. Layering: services/ may use sources/ and utils/,
never toolkit/ or tools/ (see tests/unit/test_layering_unit.py).
"""
