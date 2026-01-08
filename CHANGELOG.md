# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

*

### Changed

*

### Fixed

*

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
