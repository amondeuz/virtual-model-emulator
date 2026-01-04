# Changelog

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
