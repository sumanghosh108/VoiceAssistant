# Utils Package

Common utilities and helper modules used across the application.

## Structure

```
src/utils/
├── __init__.py           # Package exports
├── logger/               # Logging utilities
│   ├── __init__.py
│   └── logger.py        # Production logging system
└── README.md            # This file
```

## Modules

### Logger

Production-ready structured logging system using structlog.

**Features:**
- Structured JSON logging
- Timestamp-based log files for each run
- Dual output (console + file)
- ISO 8601 UTC timestamps
- Dynamic contextual fields
- Bound loggers with persistent context

**Usage:**
```python
from src.utils.logger import logger

# Basic logging
logger.info("Application started")

# With context
logger.info("Processing audio", session_id="123", component="asr")

# Bound logger
session_logger = logger.bind(session_id="123")
session_logger.info("Session started")
```

**Documentation:** [docs/logging_system.md](../../docs/logging_system.md)

## Adding New Utilities

When adding new common utilities to this package:

1. Create a new module/package under `src/utils/`
2. Add exports to `src/utils/__init__.py`
3. Create tests in `tests/unit/utils/`
4. Document in this README

### Example: Adding a new utility

```python
# src/utils/helpers.py
def format_duration(ms: int) -> str:
    """Format milliseconds as human-readable duration."""
    return f"{ms}ms"

# src/utils/__init__.py
from src.utils.logger import ProductionLogger, logger
from src.utils.helpers import format_duration

__all__ = [
    "ProductionLogger",
    "logger",
    "format_duration",
]
```

## Design Principles

Utilities in this package should be:

1. **Reusable**: Used by multiple modules across the application
2. **Independent**: Minimal dependencies on other application modules
3. **Well-tested**: Comprehensive unit tests
4. **Documented**: Clear documentation and examples
5. **Production-ready**: Suitable for production use

## Current Utilities

| Utility | Purpose | Status |
|---------|---------|--------|
| logger | Structured logging system | ✅ Production-ready |

## Future Utilities

Consider adding:
- **Validators**: Common validation functions
- **Formatters**: Data formatting utilities
- **Converters**: Type conversion helpers
- **Decorators**: Reusable decorators
- **Constants**: Shared constants and enums

## Testing

Run utils tests:
```bash
pytest tests/unit/utils/ -v
```

## Dependencies

The utils package should have minimal dependencies:
- Standard library modules preferred
- External dependencies only when necessary
- Document all external dependencies

Current external dependencies:
- `structlog` (for logger module)
