#!/usr/bin/env python3
"""Regenerate the lunch-menu ICS feeds into docs/ for GitHub Pages.

Run with no arguments. Writes one .ics per school plus an index page.
"""

from __future__ import annotations

import json
import pathlib
import sys
from datetime import date, timedelta

from icswriter import build_calendar
from mealviewer import fetch_days

ROOT = pathlib.Path(__file__).parent
DOCS = ROOT / "docs"

# Look back a week so a menu corrected after the fact still lands, and forward
# far enough to always sit past the publishing horizon.
LOOKBACK_DAYS = 7
LOOKAHEAD_DAYS = 180


def main() -> int:
    schools = json.loads((ROOT / "schools.json").read_text())
    today = date.today()
    start = today - timedelta(days=LOOKBACK_DAYS)
    end = today + timedelta(days=LOOKAHEAD_DAYS)

    DOCS.mkdir(exist_ok=True)
    summary = []

    for school in schools:
        try:
            days = fetch_days(school["lookup"], start, end)
        except Exception as exc:
            # A failed fetch must not blank an existing feed, so bail out
            # non-zero and leave the last good file in place.
            print(f"ERROR fetching {school['lookup']}: {exc}", file=sys.stderr)
            return 1

        ics = build_calendar(school["tag"], school["calname"], days)
        target = DOCS / f"{school['slug']}.ics"

        if target.exists() and target.read_text(encoding="utf-8") == ics:
            state = "unchanged"
        else:
            target.write_text(ics, encoding="utf-8", newline="")
            state = "written"

        last = days[-1].day.isoformat() if days else "none"
        print(f"{school['calname']}: {len(days)} days, through {last} ({state})")
        summary.append(
            {
                "name": school["calname"],
                "slug": school["slug"],
                "days": len(days),
                "through": last,
            }
        )

    (DOCS / "index.html").write_text(render_index(summary), encoding="utf-8")
    (DOCS / "status.json").write_text(
        json.dumps({"generated": today.isoformat(), "feeds": summary}, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


def render_index(summary: list[dict]) -> str:
    rows = "\n".join(
        f"    <tr><td>{s['name']}</td><td>{s['days']}</td><td>{s['through']}</td>"
        f'<td><a href="{s["slug"]}.ics">{s["slug"]}.ics</a></td></tr>'
        for s in summary
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Holly Ridge Lunch Feeds</title>
<style>
 body {{ font-family: system-ui, sans-serif; margin: 3rem auto; max-width: 44rem;
        padding: 0 1rem; line-height: 1.5; }}
 table {{ border-collapse: collapse; width: 100%; margin: 1.5rem 0; }}
 th, td {{ text-align: left; padding: .5rem .75rem; border-bottom: 1px solid #ddd; }}
 code {{ background: #f4f4f5; padding: .15rem .35rem; border-radius: 3px; }}
</style>
</head>
<body>
<h1>Holly Ridge Lunch Feeds</h1>
<p>Subscribable iCalendar feeds of the daily lunch menu, rebuilt from the
public MealViewer API. Add either URL to Skylight under
<em>Synced Calendars &rarr; Sync new calendar &rarr; Calendar URL</em>.</p>
<table>
  <thead><tr><th>Feed</th><th>Days</th><th>Published through</th><th>File</th></tr></thead>
  <tbody>
{rows}
  </tbody>
</table>
<p>Menus are only published about a month ahead, so <em>Published through</em>
moves forward as the school district loads new weeks.</p>
</body>
</html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
