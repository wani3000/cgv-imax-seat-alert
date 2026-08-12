# Agent handoff rules

This repository monitors CGV Odyssey IMAX remaining-seat counts for the owner.

## Monitoring policy

- Recompute the nearest three Friday/Saturday/Sunday groups in Asia/Seoul on every run.
- Fridays: screenings starting at 19:00 or later. Saturdays and Sundays: all day.
- Include future dates in `extra_dates` from `watch-config.json` when present.
- Theaters: Yongsan I'Park Mall (`0013`) and Cheonho (`0199`).
- Read only the remaining/total seat count shown in each timetable screening. Never enter the attendee, seat-map, reservation, or payment flow.
- Report only screenings whose remaining-seat ratio is at least 50% (inclusive). Example: 312/624 is included and 311/624 is omitted.
- Tracking does not require CGV login.
- Notify every Telegram subscriber on every scheduled run, including a friendly explicit no-seat result.
- Follow `TELEGRAM_STYLE.md` and `BROWSER_MONITOR_WORKFLOW.md` exactly.
- Import and run `cgv_iab_monitor.mjs` for browser monitoring. Do not replace it with an ad-hoc loop in the automation prompt.
- Do not inspect individual seat names or availability.
- Never commit `.env`, subscriber IDs, browser sessions, cookies, payment data, or runtime state.

## No reservation actions

- This monitor is notification-only. Never select attendees or seats and never enter reservation or payment pages.

## New-machine recovery

Read `MULTI_PC_FAILOVER.md` and `OPERATIONS.md`. A newly cloned or replacement machine must remain `standby` unless the user explicitly promotes it after the old primary is offline. Then create `.env` locally, run the tests, install the service, and recreate the scheduler from `watch-config.example.json`.
