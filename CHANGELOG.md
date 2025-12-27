# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

* Rate limiting for WebSocket connections (configurable via `PUSHI_RATE_LIMIT_MESSAGES` and `PUSHI_RATE_LIMIT_WINDOW`)
* Connection limits: global (`PUSHI_MAX_CONNECTIONS_GLOBAL`), per-IP (`PUSHI_MAX_CONNECTIONS_PER_IP`), and per-app (`PUSHI_MAX_CONNECTIONS_PER_APP`)
* Message size limits (`PUSHI_MAX_MESSAGE_SIZE`)
* Channel and event name length limits (`PUSHI_MAX_CHANNEL_NAME_LENGTH`, `PUSHI_MAX_EVENT_NAME_LENGTH`)
* Subscription limits: channels per socket (`PUSHI_MAX_CHANNELS_PER_SOCKET`) and sockets per channel (`PUSHI_MAX_SOCKETS_PER_CHANNEL`)
* Webhook timeout configuration (`PUSHI_WEBHOOK_TIMEOUT`) and concurrent request limits (`PUSHI_WEBHOOK_MAX_CONCURRENT`)
* Proper error messages sent to clients when limits are exceeded

### Changed

* Webhook calls are now asynchronous and non-blocking with configurable timeout
* Improved error handling in disconnect flow to ensure proper cleanup even on failures

### Fixed

* Added `@appier.private` decorator to app creation endpoint to require authentication
* Fixed missing input validation in `handle_event` for required fields
* Fixed potential KeyError when event data is missing required fields
* Improved security by validating event names before dynamic method dispatch

## [0.3.1] - 2024-01-17

### Changed

* Aligned version number with the client versioning

## [0.2.1] - 2024-01-17

### Changed

* Moved CI/CD to GitHub Actions
* Bumped dependencies

## [0.2.0] - 2024-01-17

### Added

* Initial version of `CHANGELOG.md`

### Changed

* Made the `timestamp` field indexed in the event
* Changed default sorting field from `_id` to `id`
