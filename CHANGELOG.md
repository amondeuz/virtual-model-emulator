# Changelog

## [2.2.2] - 2026-01-07

### Security (Critical - 5 fixes)
- **Encrypted Emulations**: API keys now encrypted in `emulations.json` using Fernet
- **Environment-Based Master Key**: Master key now loaded from `VME_MASTER_KEY` environment variable (with config.yaml fallback)
- **Protected /emulator/active**: Removed API keys from response, added thread-safe locking
- **Authenticated /emulator/stop**: Requires `ADMIN_SECRET` bearer token when set
- **File Permissions**: Sensitive files (accounts.json, emulations.json, config.yaml) set to 0600

### Major Functionality (8 fixes)
- **Atomic File Writes**: save_accounts() and save_emulations() now use temp file + rename pattern
- **Retry Logic for Completions**: litellm.completion() now uses call_with_retry() with exponential backoff
- **Provider Validation**: /providers/connect validates provider against PROVIDERS list
- **Temperature Validation**: Validated to be float in range 0.0-2.0
- **max_tokens Validation**: Validated to be positive integer <= 32000
- **Message Structure Validation**: Each message must have role (user/assistant/system) and content
- **Thread-Safe Emulation Reads**: All _active_emulations access now protected by lock

### Reliability (5 fixes)
- **Thread-Safe RateLimiter**: Added threading.Lock() for concurrent request handling
- **Thread-Safe ModelCache**: All cache operations now protected by lock
- **API Timeouts**: 15s for model fetch, 30s for chat completions
- **Request Body Limit**: 10MB max to prevent memory exhaustion
- **Improved Error Sanitization**: More patterns (sk-, pk_, auth=, etc.) detected and removed

### Infrastructure (3 fixes)
- **Optional HTTPS/SSL**: Set `SSL_CERT_FILE` and `SSL_KEY_FILE` environment variables to enable
- **Restricted CORS**: Now only allows `http://localhost:8775` origin
- **Security Headers**: Added Content-Security-Policy, X-Frame-Options, X-Content-Type-Options

### Minor Improvements (4 fixes)
- **Client-Side API Key Validation**: Format validation in connect.html before save
- **Reduced Polling**: Changed from 10s to 30s in config.html for better efficiency

### Environment Variables
New environment variables for secure deployment:
- `VME_MASTER_KEY`: Encryption key for API keys (required for production)
- `ADMIN_SECRET`: Bearer token for /emulator/stop authentication (optional)
- `SSL_CERT_FILE`: Path to SSL certificate file (optional)
- `SSL_KEY_FILE`: Path to SSL private key file (optional)

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
