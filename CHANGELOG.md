# Changelog

## [2.2.0] - 2025-01-06

### Changed
- **Major Architecture Simplification**: Removed LiteLLM proxy in favor of direct SDK usage
- Reduced from 3 services to 1 (API Server only)
- Removed PostgreSQL database dependency
- Server now uses `litellm.completion()` SDK directly
- Emulations stored in JSON file instead of database
- Simplified installation (no Prisma, no psycopg2, no proxy extras)

### Removed
- `start_litellm.py` - LiteLLM proxy launcher
- `start_postgres.py` - PostgreSQL launcher
- `stop_postgres.py` - PostgreSQL stopper
- `postgres_manager.py` - PostgreSQL lifecycle management
- `postgres_config.py` - PostgreSQL configuration
- `validate_config.py` - Pre-flight validation
- PostgreSQL database requirement
- LiteLLM proxy server requirement

### Benefits
- Faster startup (no waiting for PostgreSQL or proxy)
- Single port needed (8775 only)
- Fewer dependencies
- Simpler debugging and maintenance
- ~1500 fewer lines of code

### Breaking Changes
- API endpoint changed from `localhost:11435` to `localhost:8775`
- PostgreSQL no longer used for configuration storage

## [2.1.4] - 2025-01-04

### Added
- Cross-tab synchronization (BroadcastChannel + polling)
- Visibility change detection for instant UI updates
- Fallback polling for older browsers
- Complete architectural refactor

### Fixed
- Tab synchronization in Pinokio interface
- Port mismatch cascade issues
- Deadlock on Windows with pipe buffers
- Blocking startup health checks
- Static port initialization preventing dynamic allocation
- Missing public directory
- Fragile string parsing in DATABASE_URL

### Changed
- Unified launcher architecture (app_launcher.py)
- All services run as subprocesses under single master process
- Background threading for non-blocking I/O
- Windows process isolation (CREATE_NEW_PROCESS_GROUP)
- Dynamic port allocation (5450-5550)
- In-process module mocking for litellm_enterprise

### Breaking Changes
None - fully backward compatible

## [2.1.2] - Previous Release

## [2.0.0] - Initial Release
