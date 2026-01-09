# Requirements Files

This repository uses different requirement files for different purposes:

## `requirements.txt` (Minimal - for Vercel)
Contains only the essential dependencies needed for the Vercel deployment demo:
- FastAPI + uvicorn (web server)
- numpy (market simulation)
- pydantic, python-dateutil (utilities)

**Total size:** ~30MB of packages

Use this for:
- Vercel deployment (stays under 250MB limit)
- Testing the minimal demo API
- CI/CD pipelines that only need the API

## `requirements-full.txt` (Complete)
Contains all dependencies for full local development:
- All packages from `requirements.txt`
- pandas, SQLAlchemy (data processing & persistence)
- ccxt (exchange connectivity)
- cryptography, aiohttp (async operations)
- Development tools

**Total size:** ~200MB+ of packages

Use this for:
- Full local development
- Running all exploits (FundingCapture, FlowPressure, etc.)
- Backtesting and analysis
- Contributing to the codebase

## `pyproject.toml`
Primary package definition with:
- Core dependencies (matches `requirements-full.txt`)
- Optional development dependencies
- Package metadata

Use this for:
- Installing as a package: `pip install -e .`
- Development with extras: `pip install -e .[dev]`

## Installation

### For Vercel-style minimal deployment:
```bash
pip install -r requirements.txt
uvicorn api.app:app
```

### For full local development:
```bash
pip install -r requirements-full.txt
# or
pip install -e .[dev]
```

## Why Two Files?

Vercel has a 250MB unzipped limit for serverless functions. The full dependency set exceeds this limit. By splitting requirements:

1. **Vercel deployments** use minimal deps and stay under the limit
2. **Local development** has full capabilities with all deps
3. **Code is compatible** with both setups via conditional imports

The codebase uses try/except imports for heavy dependencies (pandas, SQLAlchemy) so it works with either requirements file.
