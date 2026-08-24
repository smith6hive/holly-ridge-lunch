# Holly Ridge lunch feeds

Publishes the daily lunch menu for **Holly Ridge Elementary** and **Holly Ridge
Middle** (Wake County Public Schools) as two subscribable iCalendar feeds, so the
menus show up on the family Skylight calendar.

## Why it works this way

The Skylight frame cannot be written to directly, and the family Google Calendar
is read-only to us. Skylight will, however, subscribe to any public calendar URL.
So instead of pushing events into someone's calendar, this repo publishes two
static `.ics` files to GitHub Pages and lets Skylight pull them.

Menus come from the public MealViewer API that Wake County uses — no key, no auth:

```
https://api.mealviewer.com/api/v4/school/{lookup}/MM-DD-YYYY/MM-DD-YYYY
```

## The publishing-horizon problem

Wake County only loads menus about a month ahead. Everything past that comes back
as an empty day, not an error. A hand-built calendar would therefore go stale and
silently stop showing lunches.

This repo solves that by rebuilding both feeds every morning. New weeks appear on
the frame within a day of the district publishing them, with no manual step. Days
with no published menu emit no event at all, so the calendar is simply blank
rather than showing a misleading placeholder.

## Feeds

| School | Feed |
|---|---|
| Holly Ridge Elementary | `docs/holly-ridge-elementary.ics` |
| Holly Ridge Middle | `docs/holly-ridge-middle.ics` |

Each is a separate feed on purpose: Skylight assigns a colour per synced
calendar, so elementary and middle can be told apart and toggled independently.

## Adding a feed to Skylight

Skylight app → menu (upper right) → **Synced Calendars** → **Sync new calendar**
→ **Calendar URL** → paste the feed URL → **Done**. Repeat for the second school,
then set each calendar's colour in the app.

## Event shape

One all-day event per school day. All-day keeps lunch out of the timed columns.

- **Title** — school tag plus up to four abbreviated entrées, e.g.
  `HRMS: Ckn Filet/Spcy / Brocc Alfrd`, capped at 54 characters. Abbreviation
  rules live in `abbrev.py` as plain data: variant pairs served side by side
  collapse into one label (`Ch/Pep Piz`), menu filler is dropped, and long words
  contract (`Chicken` → `Ckn`). Averages 36 characters against 51 unabbreviated,
  while showing more entrées per day.
- **Description** — the full line: every entrée, the cold grab-and-go boxes, and
  sides grouped by category.

Breakfast, allergens, and nutrition data are all available from the API but
deliberately excluded to keep the frame readable.

## Local use

```sh
python -m venv .venv && .venv/bin/pip install pytest
.venv/bin/python -m pytest tests/ -q
.venv/bin/python build.py
```

`build.py` is idempotent — it only rewrites a file when the menu changed, which
is what keeps the daily workflow from producing empty commits.

## Layout

| File | Purpose |
|---|---|
| `mealviewer.py` | Fetch and normalise menus; drops unpublished days |
| `abbrev.py` | Title abbreviation tables: pairs, phrases, words |
| `icswriter.py` | RFC 5545 rendering: folding, escaping, stable UIDs |
| `build.py` | Entry point; writes `docs/` |
| `schools.json` | The two schools; add or swap schools here |
| `tests/test_feed.py` | Feed-correctness tests |

## Changing schools

Edit `schools.json`. Find a school's `lookup` by trying its name without spaces
(`HollyRidgeMiddle`); the API echoes back the real school name, so a wrong guess
is obvious immediately.
