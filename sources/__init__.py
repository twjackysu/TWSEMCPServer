"""Gateways: one module per upstream endpoint, the only code that knows that endpoint's layout.

A gateway sends the request through ``TWSEAPIClient``, checks the reply's shape, and returns typed
records (frozen dataclasses). Callers never index a raw row: when an exchange renames or moves a
column, its gateway is the one place to fix, and it raises ``UpstreamFormatError`` rather than
misreading the data. Layering: sources/ depends on utils/ only (see tests/unit/test_layering_unit.py).
"""
