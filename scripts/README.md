# Utility Scripts

This directory contains utility scripts for maintenance, debugging, and development tasks.

## Refactoring Scripts

### update_imports.py
Updates imports after restructuring to production-ready module organization.
- Migrates old import paths to new module structure
- Updates references across src/ and tests/ directories

### update_logging_imports.py
Updates logging imports from infrastructure to utils.logger package.
- Changes `from src.infrastructure.logging import` to `from src.utils.logger import`
- Processes all Python files in the project

### update_test_imports.py
Updates test imports after restructuring test directory.
- Updates fixture imports to new location
- Processes all test files

## Development & Debugging Scripts

### view_logs.py
Log viewer utility for inspecting application logs.
- List all log files
- View latest logs
- Filter by level (info, warning, error)
- Filter by session_id or component
- Colored output for better readability

Usage:
```bash
python scripts/view_logs.py                    # View latest logs
python scripts/view_logs.py --level error      # Show only errors
python scripts/view_logs.py --session <id>     # Filter by session
python scripts/view_logs.py --component asr    # Filter by component
```

### test_logging_demo.py
Comprehensive demonstration script for the logging system.
- Shows basic logging (info, warning, error)
- Demonstrates contextual fields
- Shows bound loggers with persistent context
- Demonstrates exception logging with tracebacks
- Simulates real voice assistant session

Usage:
```bash
python scripts/test_logging_demo.py
```

## Usage

Refactoring scripts were used during development and are kept for reference:

```bash
python scripts/update_imports.py
python scripts/update_logging_imports.py
python scripts/update_test_imports.py
```

Development scripts can be used anytime:

```bash
python scripts/view_logs.py
python scripts/test_logging_demo.py
```

## Note

These are utility scripts and not part of the main application. They are kept for maintenance, debugging, and potential future refactoring needs.
