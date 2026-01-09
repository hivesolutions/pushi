# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

* CI/CD workflows for JavaScript library (`main-js.yml`, `deploy-js.yml`) with linting and NPM publishing
* ESLint configuration for JavaScript library using `eslint-config-hive`
* Package.json for JavaScript library with NPM publishing support
* CommonJS module exports in JavaScript client for Node.js compatibility
* Health check endpoints for monitoring and load balancer integration (`/health`, `/health/detailed`, `/health/live`, `/health/ready`)
* SMTP notification handler using netius SMTP client for email delivery
* SMTP model for storing email subscriptions to event channels
* SMTPController with REST API endpoints (`/smtps`) for subscription management
* SMTP configuration via environment variables (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_STARTTLS, SMTP_SENDER)
* SMTP URL support (`smtp://` and `smtps://` schemes) for simplified configuration via `SMTP_URL` environment variable
* Per-app SMTP configuration via `smtp_url` field in App model for multi-tenant email delivery
* SMTP URL parsing with support for credentials, port, and query parameters (e.g., `smtp://user:pass@host:587?sender=email`)
* Example script for email subscription (`examples/smtp/subscribe.py`)
* Reorganized examples into separate directories (`examples/base/`, `examples/smtp/`)
* Comprehensive module documentation for example scripts
* Debug and warning logging in SMTPHandler for better observability
* Session-based authentication support via `login()` and `logout()` methods in JavaScript client
* Added `appId` and `appSecret` configuration options to JavaScript client for authentication
* Web Push example now served as static files from the app at `/static/examples/web-push/`

### Changed

* Updated GitHub Actions checkout to v6 in all Python workflows
* Improved JavaScript client code quality with ESLint-compliant patterns (`Boolean()`, `new Error()`, unused params)
* Moved `examples/web-push/client.py` to `examples/base/notify.py` for reusability across examples
* Updated Web Push README to reference new examples structure
* SMTP configuration now resolves with priority: app-level smtp_url → global SMTP_URL → individual SMTP_* environment variables
* Added `.env` to `.gitignore` for local environment configuration
* Renamed Mail model, MailHandler, and MailController to SMTP, SMTPHandler, and SMTPController for consistency
* Web Push API endpoints now require session authentication instead of `app_key` query parameter
* Added `@appier.private` decorator to Web Push and VAPID endpoints to require authentication
* Removed CORS-specific options from Web Push routes in favor of session-based authentication
* JavaScript client Web Push API methods now include credentials for session cookie support
* `/vapid_key` endpoint now retrieves app context from session instead of query parameter
* Moved Web Push example files from `examples/web-push/` to `src/pushi/app/static/examples/web-push/`
* Removed `CORS` environment variable from VSCode launch configuration

### Fixed

* Fixed typo in JavaScript client: "underyling" → "underlying"

## [0.4.8] - 2026-01-08

### Fixed

* Fixed `long_description_content_type` incorrectly wrapped in a tuple in library setup.py

## [0.4.7] - 2026-01-08

### Fixed

* Fixed `long_description` incorrectly wrapped in a tuple in library setup.py

## [0.4.6] - 2026-01-08

### Fixed

* Fixed missing `long_description` variable assignment in library setup.py

## [0.4.5] - 2026-01-08

### Fixed

* Added fallback for README.md in library setup.py for standalone package builds

## [0.4.4] - 2026-01-08

### Added

* Added long description from README.md for PyPI package pages

## [0.4.3] - 2026-01-08

### Fixed

* Added setuptools upgrade step to deploy workflow for improved compatibility

## [0.4.2] - 2026-01-08

### Changed

* Updated CI deploy operation

## [0.4.1] - 2026-01-08

### Changed

* Updated deploy workflow to use Python 3.13 instead of Python 2.7
* Added setuptools upgrade step in deploy workflow for compatibility

## [0.4.0] - 2026-01-08

### Added

* Web Push notification support using W3C Push API (RFC 8030)
* VAPID authentication for Web Push (RFC 8292)
* WebPush model for storing push subscriptions
* WebPushController with REST API endpoints for subscription management
* WebPushHandler for sending notifications to web browsers
* Unit tests for WebPushHandler
* Module entry point to run app via `python -m pushi.app`
* Module entry point to run base via `python -m pushi.base`
* Documentation for all models (Association, Subscription, PushiEvent, WebPush, App, Web, PushiBase, APN) with purpose, cardinality, lifecycle, and cautions
* WebPushAPI mixin for Python client library with subscription management methods
* Web Push support in JavaScript client library with full browser integration
* VAPID public key endpoint (`GET /vapid_key`) for browser subscription
* High-level `setupWebPush()` and `teardownWebPush()` methods in JavaScript client
* Service worker registration helpers in JavaScript client
* Added `baseWebUrl` option in JavaScript client for configuring HTTP API URL separately from WebSocket URL
* Web Push example application with client, service worker, and server
* "Generate VAPID" operation in App model to create VAPID key pairs
* Enhanced Web Push example with full notification payload support (icon, badge, image, vibrate, tag, actions, etc.)
* Added notification icon and payload format documentation to Web Push example

### Fixed

* Refactored Web model lifecycle methods to use explicit if statements instead of short-circuit evaluation
* Refactored APN, Subscription, and WebPush model lifecycle methods to use explicit if statements instead of short-circuit evaluation

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
