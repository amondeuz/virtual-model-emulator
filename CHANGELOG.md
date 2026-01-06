# Changelog

## [2.2.1] - 2026-01-06

### Added
- **Rate Limiting**: 10 requests/second per IP to prevent abuse
- **Model Caching**: 1-hour TTL cache for provider model lists with force refresh option
- **Stale Fallback**: Returns cached models when provider is temporarily offline
- **Audit Logging**: All security-relevant actions logged to `config/audit.log`
- **Error Logging**: Structured error logs in `config/errors.log`
- **Retry Logic**: Exponential backoff for transient errors (timeouts, 503s)
- **Master Key Rotation**: `/admin/rotate-key` endpoint for key rotation
- **Cache Stats**: `/admin/cache-stats` endpoint for monitoring
- **Response Compression**: Gzip compression for responses >1KB
- **UI Validation**: Real-time validation feedback for emulated model configuration
- **API Documentation**: Comprehensive API.md documentation file
- **Troubleshooting Guide**: TROUBLESHOOTING.md for common issues
- **Unit Tests**: test_server.py with encryption, caching, rate limiting tests

### Changed
- `/models` endpoint now supports `force=true` parameter to bypass cache
- Improved error handling with structured logging context
- Better feedback in UI when emulation is configured

### Security
- Rate limiting prevents API abuse
- Audit logging for compliance and security monitoring
- Key rotation capability for credential management

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
