# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

## Health Data Paths

### Apple Health Export
- **Health Data**: `~/我的云端硬盘/Health Auto Export/Health Data/`
  - Format: `HealthAutoExport-YYYY-MM-DD.json`
  - Size: ~400-600KB per day
  
- **Workout Data**: `~/我的云端硬盘/Health Auto Export/Workout Data/`
  - Format: `HealthAutoExport-YYYY-MM-DD.json`
  - Only exists on days with workouts

### Available Dates
- 2026-02-18: Health (657KB) + Workout (29KB) ✓
- 2026-02-19: Health (443KB)
- 2026-02-20: Health (459KB)
- 2026-02-21: Health (242KB)

### Data Sources Priority
1. Apple Health (primary)
2. Google Fit (backup for sleep if Apple Health missing)

---

Add whatever helps you do your job. This is your cheat sheet.
