# Project Custom Instructions for GitHub Copilot

## Core Philosophy & Architecture
This repository is **NOT** a trading bot, strategy framework, indicator library, or decision-making system.

It is a **pure, deterministic execution infrastructure** for:
- Order placement & management
- Position tracking
- PnL attribution
- Risk enforcement
- State isolation

**Key principle – Strict Intent vs Execution separation:**
- The engine **NEVER** decides WHEN to trade, WHAT to trade, or generates any signals
- All trading intent (Actions) MUST come from **external ExploitModules**
- The engine only handles the **HOW**: validation, risk checks, execution, result reporting
- All decision logic lives outside → DSPy, MYCELIUM, custom rules, ML models, etc.

## ExploitModules – Full Modularity & Independence
- Each ExploitModule implements a simple, standalone interface:
  ```python
  evaluate(state: ExecutionState) → list[Action]
  on_execution_result(action: Action, result: ExecutionResult) → None  # optional
	•	Completely decoupled from each other and from the core engine
	•	Zero inter-dependency — modules do not know about or reference each other
	•	Any combination is supported:
	◦	Run zero modules (NullExploitModule → engine does nothing)
	◦	Run one module (e.g. DSPy only)
	◦	Run many in any order/combination (DSPy + MYCELIUM micro-exploit + rule-based + momentum + …)
	•	Hot-swap, add, or remove modules at runtime via config — no engine changes needed
Exchange Connectivity – Universal & Agnostic
	•	100% CCXT-based → single, unified exchange abstraction layer
	•	Supports centralized (CEX) and decentralized (DEX) venues without code changes
	◦	CEX examples: Binance, Bybit, OKX, Kraken, KuCoin, Bitvavo, Coinbase, etc.
	◦	DEX examples: Hyperliquid (native support), dYdX v4, and others via CCXT community drivers
	•	Switch venues by changing only the config: "exchange": { "name": "binance" }  →  "hyperliquid"  →  "dydx"  etc.
	•	
	•	Handles spot, futures, margin, WebSocket streams, rate limits, order types uniformly
	•	Engine remains completely exchange-agnostic → ideal for multi-venue strategies, CEX ↔ DEX migration, hybrid workflows
Important Facts
	•	Heavily stripped-down fork of Freqtrade (~40,000+ lines removed)
	•	No trading logic, no indicators, no ML (FreqAI), no optimization (Hyperopt), no UI/API/Telegram
	•	Persistence: SQLAlchemy + SQLite (trades, orders, key-value store)
	•	Risk enforced before execution — config-driven, deterministic
	•	Explicit capital tracking: total / available / deployed / reserved + realized/unrealized PnL
	•	No global mutable state — everything explicit & isolated
Folder Structure & Responsibilities
	•	/freqtrade/core/ → risk.py, state.py, execution engine
	•	/freqtrade/exploits/ → ExploitModule base + example stubs (empty by design!)
	•	/freqtrade/exchange/ → CCXT connectors, order/balance handling
	•	/freqtrade/persistence/ → DB models & migrations
	•	/freqtrade/optimize/ → Backtesting & price replay only (simulation mode)
Coding Conventions & Rules
	•	Python 3.11+, heavy use of type hints
	•	Prefer composition over inheritance
	•	Explicit state passing — avoid globals & side effects
	•	Risk checks must remain deterministic & config-driven
	•	Logging: structured (JSON-friendly), use INFO/WARNING/ERROR appropriately
	•	Tests: focus on execution correctness, risk enforcement, full lifecycle
	•	Never add, suggest, or reintroduce trading signals, indicators, or decision logic
When Working on Tasks / Pull Requests
	1	Always reference current RiskLimits & config first
	2	Treat incoming Actions as externally proposed — still enforce all limits
	3	Keep changes small, focused, and backward-compatible where possible
	4	Support both dry-run and live simulation modes
	5	Document any new config options clearly
	6	Never assume a specific exchange, exploit source, or trading style
Critical Reference Files
	•	README.md → Core explanation & quick start
	•	ARCHITECTURE.md → Detailed system design
	•	DEPENDENCIES.md → Current dependency graph
	•	FILES_DELETED.md → What was removed (never reintroduce!)
	•	REMAINING_WORK.md → Known areas needing attention
	•	config.json example → Full configuration reference
Follow these instructions in EVERY suggestion, plan, code generation, or review. The engine is infrastructure — keep it clean, agnostic, modular, and deterministic.