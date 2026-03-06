# Changelog

All notable changes to this project are documented in this file.

## [5.9.1] - 2026-03-06

### Fixed
- Metrics date filtering now supports numeric timestamps (seconds/milliseconds) and string dates.
- Sleep stage unit inference improved (hours/minutes auto-detection using duration consistency).
- Added stricter email validation for `receiver_email`, `email_config.oauth2.sender_email`, `email_config.smtp.sender_email`.
- Monthly CLI args hardened (`year/month` integer parse + month range check).
- Workout cross-day filtering now applies consistently in both daily loader and extract script.
- Fixed regression where workout records were appended twice in daily loader.

### Docs
- README template fallback strategy aligned with actual `get_template_path()` logic.
- README now includes regression-check commands and explicit `config.json` prerequisite before `validate_config.py`.
- Version status clarified as V5.9.x with recommended patch version.

## [5.9.0] - 2026-03

### Added
- Dynamic metrics table (`report_metrics`) with 32 supported metrics.
- Multi-member flow (up to 3 members) across extract/generate/send.
- CN/EN templates and language-aware validation.
- Provider-based email sending (OAuth2/SMTP/Mail.app/Local) with fallback/retry.

### Improved
- Daily cache-driven weekly/monthly aggregation.
- Safer JSON input handling and template rendering checks.

## [5.8.1] - 2026-03

### Added / Fixed
- Sleep parsing compatibility for multiple Health Auto Export structures.
- Personalized scoring based on profile parameters.
- Strict/warn validation modes and multiple robustness fixes.
