# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

## [6.0.5] - 2026-03-25

### Fixed
- 修复多成员月报/周报 Body Age 计算时可能读取错误成员缓存的问题
- 添加 Pace of Aging 数据充足性标记，避免数据不足时误导用户
- 优化 Zone Times 计算路径，避免重复计算
- 增强 Sleep Debt 注释说明，明确 WHOOP 式债务模型

## [6.0.3] - 2026-03-23

### Fixed
- Pace of Aging 改为真实窗口比较（当前 7 天 vs 前 7 天），修复方向反转与过度缩放问题。
- Recovery baseline 改为读取真实缓存中的 HRV / RHR，而不是错误地使用 recovery 分数估算。
- Strain 改为优先使用真实 workout / zone_times，不再伪造全天心率。
- 修复 generate_cache_only.py 未传 member 专属 health_dir / workout_dir，导致运动数据丢失的问题。
- 修复 monthly Body Age 错把 avg_hrv 当 avg_rhr 的问题。
- 修复 sleep debt 从错误层级读取，导致累积睡眠债长期失真的问题。
- 缓存写入 health_scores 时补齐 zone_times / respiratory_rate / sleep_debt_accumulated。

### Docs
- 统一 README / SKILL / config schema / example configs / script headers 的版本号为 6.0.3。
- 示例路径统一改为中性 `~/Health Auto Export/...`，避免中文 Google Drive 硬编码误导。
- 示例成员名从 `Jimmy` 改为 `Member1`，去掉个人化硬编码。

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
