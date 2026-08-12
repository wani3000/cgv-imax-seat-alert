# Agent handoff rules

This repository monitors CGV Odyssey IMAX seats for the owner.

## Monitoring policy

- Recompute the nearest three Friday/Saturday/Sunday groups in Asia/Seoul on every run.
- Fridays: screenings starting at 19:00 or later. Saturdays and Sundays: all day.
- Include future dates in `extra_dates` from `watch-config.json` when present.
- Theaters: Yongsan I'Park Mall (`0013`) and Cheonho (`0199`).
- Target: two adjacent standard seats in rows G-J, within 15 seats of the auditorium center.
- Continue timetable and seat tracking when CGV is logged out. Login is required only after a matching pair is found and reservation steps begin.
- Notify every Telegram subscriber on every scheduled run, including a friendly explicit no-seat result.
- Follow `TELEGRAM_STYLE.md` exactly. Apply scope and seat filters before counting, never report unchanged entries, and never send a correction caused by an unvalidated count.
- Do not report aggregate remaining-seat fluctuations as target-seat discoveries. The actionable result is based only on an actual adjacent pair satisfying every target condition.
- Never commit `.env`, subscriber IDs, browser sessions, cookies, payment data, or runtime state.

## Reservation safety

- When matching seats are found, notify first and begin reservation in the owner's authenticated CGV session.
- If logged out, notify the owner immediately and keep tracking while waiting for login.
- Select the screening, two attendees, and matching seats; proceed through discounts/payment preparation.
- Follow `PAYMENT_AUTOMATION.md`: use Toss, accept required terms only, and load the phone and six-digit birthdate from macOS Keychain through `payment_identity.py`. Never print either value.
- Stop before the final action that submits a purchase. Show theater, date, time, seats, and total price and obtain the owner's confirmation at action time.
- Never expose, copy, or store saved-card details.

## New-machine recovery

Read `OPERATIONS.md` and `PAYMENT_AUTOMATION.md`, create `.env` locally, run `setup_payment_keychain.sh`, run the tests, install the subscription service, sign in to CGV in the selected browser, and recreate the scheduler from `watch-config.example.json`.
