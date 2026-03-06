# AGENTS.md - Weather Research Project

This file provides instructions for coding agents working on this project.

## Project Overview

Weather research project focused on replicating academic papers (e.g., Chen 2025) analyzing weather effects on financial markets.

## Tech Stack

- **Python**: 3.14
- **Package Manager**: uv
- **Linting/Formatting**: ruff
- **Dependencies**: matplotlib, pyarrow, statsmodels

## Project Structure

```
weather/
├── analysis/          # Analysis scripts and notebooks
│   ├── replicate_chen2025.py        # Main replication script
│   ├── table1_table13_replication.ipynb
│   └── *.md                         # Analysis notes
├── data/              # Data files (gitignored - large files)
│   ├── raw/
│   └── processed/
├── docs/              # Documentation
│   └── papers/        # Reference papers
├── reference/         # Reference materials and sample data
├── reports/           # Generated reports
├── src/               # Source modules
└── main.py            # Entry point
```

## Commands

```bash
# Install dependencies
uv sync

# Run linting
uv run ruff check .

# Run formatting check
uv run ruff format . --check

# Run formatting (fix)
uv run ruff format .

# Run scripts
uv run python analysis/replicate_chen2025.py

# Run all checks (validation)
uv run ruff check . && uv run ruff format . --check
```

## Code Style

- Line length: 88 characters (ruff default)
- Use double quotes for strings
- Use type hints for function parameters and returns
- Follow PEP 8 conventions

## Data Handling

- Large data files are gitignored (*.parquet, *.sas7bdat, *.dta, *.csv)
- Raw data is in `data/raw/`
- Processed data is in `data/processed/`
- Never commit files > 10MB

## Before Committing

1. Run `uv run ruff check .` - fix all errors
2. Run `uv run ruff format .` - format code
3. Ensure scripts run without errors
4. Update docstrings for new functions

## Skills Available

Located in `.codex/skills/`:
- `commit`: Create well-formed git commits
- `push`: Push branches and manage PRs
- `pull`: Sync with origin/main
- `land`: Automate PR landing
- `linear`: Linear API operations
- `debug`: Debugging workflow
