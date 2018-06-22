# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.1] - 2018-06-22
### Changed
- Fix debian package build

## [1.1.0] - 2018-06-22
### Added
- This changelog.
- Mirror task logs, now you can view status of each mirror task and check what went wrong.


### Changed
- Note in mirror list is now only title for row.
- Webhook URL is inside ro input to preserve space.


### Removed
- Redis backend was replaced by RabbitMQ.
- Flask-Caching was unused.
