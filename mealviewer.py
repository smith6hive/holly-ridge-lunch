"""Fetch lunch menus from the public MealViewer API.

No auth required. The API returns a date skeleton for every calendar day in the
requested range; days that have not been published yet come back with an empty
``menuBlocks`` list, which is how we detect the publishing horizon.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date, timedelta

API = "https://api.mealviewer.com/api/v4/school/{lookup}/{start}/{end}"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Safari/537.36"

# Categories in the order we want them rendered in the event description.
SIDE_ORDER = ["Grains", "Vegetables", "Fresh Fruits", "Fruits", "Protein", "Milk"]


@dataclass
class Day:
    """One school day's lunch service at one school."""

    day: date
    entrees: list[str] = field(default_factory=list)
    grab_and_go: list[str] = field(default_factory=list)
    sides: dict[str, list[str]] = field(default_factory=dict)

    def is_empty(self) -> bool:
        return not (self.entrees or self.grab_and_go)


def _clean(name: str) -> str:
    """Collapse the stray double spaces MealViewer ships in item names."""
    return re.sub(r"\s+", " ", (name or "").strip())


def _get(url: str, timeout: int = 60) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def _month_spans(start: date, end: date) -> list[tuple[date, date]]:
    """Split a range into calendar-month chunks to keep each request small."""
    spans = []
    cur = start
    while cur <= end:
        if cur.month == 12:
            nxt = date(cur.year + 1, 1, 1)
        else:
            nxt = date(cur.year, cur.month + 1, 1)
        spans.append((cur, min(end, nxt - timedelta(days=1))))
        cur = nxt
    return spans


def fetch_days(lookup: str, start: date, end: date) -> list[Day]:
    """Return every published lunch day for ``lookup`` between start and end.

    Days with no published menu are omitted entirely rather than returned empty,
    so callers never have to distinguish "no school" from "not posted yet".
    """
    days: dict[date, Day] = {}

    for span_start, span_end in _month_spans(start, end):
        url = API.format(
            lookup=lookup,
            start=span_start.strftime("%m-%d-%Y"),
            end=span_end.strftime("%m-%d-%Y"),
        )
        payload = _get(url)

        for sched in payload.get("menuSchedules") or []:
            info = sched.get("dateInformation") or {}
            key = info.get("dateKey")
            if not key:
                continue
            when = date(int(str(key)[:4]), int(str(key)[4:6]), int(str(key)[6:8]))

            for block in sched.get("menuBlocks") or []:
                if (block.get("blockName") or "").strip().lower() != "lunch":
                    continue
                if block.get("blackedOut"):
                    continue

                entry = days.setdefault(when, Day(day=when))
                lines = (block.get("cafeteriaLineList") or {}).get("data") or []
                for line in lines:
                    items = (line.get("foodItemList") or {}).get("data") or []
                    for item in items:
                        name = _clean(item.get("item_Name"))
                        if not name:
                            continue
                        kind = (item.get("item_Type") or "").strip()
                        if kind == "Entrees":
                            # The "... Box" items are the same cold grab-and-go
                            # options every single day; they are real entrees but
                            # they are noise in a headline.
                            bucket = (
                                entry.grab_and_go
                                if name.endswith("Box")
                                else entry.entrees
                            )
                            if name not in bucket:
                                bucket.append(name)
                        else:
                            side = entry.sides.setdefault(kind or "Other", [])
                            if name not in side:
                                side.append(name)

    return [d for d in (days[k] for k in sorted(days)) if not d.is_empty()]
