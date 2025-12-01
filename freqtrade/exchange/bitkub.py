"""Skeleton Bitkub exchange adapter for Freqtrade

This file provides a starting point for implementing a custom exchange adapter
for Bitkub. It is intentionally self-contained and does NOT assume a specific
base class from the repo because the project's internal exchange base class
was not discovered automatically.

How to proceed:
- Replace the placeholder endpoints and signing logic with Bitkub's official API
  details (https://api.bitkub.com/ or Bitkub API docs).
- If the project defines a BaseExchange or common exchange interface, change
  BitkubExchange to inherit from that base class and implement required
  abstract methods.
- Implement proper error handling, rate-limit handling and retries.
- Add unit/integration tests (mocked) and test thoroughly in dry-run.

This skeleton implements the common methods Freqtrade expects from an
exchange adapter: fetch_ohlcv, fetch_markets, fetch_balance, create_order,
cancel_order, fetch_order, fetch_open_orders. The methods contain TODOs where
Bitkub-specific logic must be implemented.
"""