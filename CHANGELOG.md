# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

* Web Push notification support using W3C Push API (RFC 8030)
* VAPID authentication for Web Push (RFC 8292)
* WebPush model for storing push subscriptions
* WebPushController with REST API endpoints for subscription management
* WebPushHandler for sending notifications to web browsers
* Unit tests for WebPushHandler
* Module entry point to run app via `python -m pushi.app`
* Documentation for all models (Association, Subscription, PushiEvent, WebPush, App, Web, PushiBase, APN) with purpose, cardinality, lifecycle, and cautions

### Changed

*

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
