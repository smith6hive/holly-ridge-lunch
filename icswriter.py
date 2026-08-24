"""Render menu days as an RFC 5545 iCalendar feed.

Two properties matter for a feed that is re-published daily:

* **Stable UIDs.** ``UID`` is derived from school + date, so when a menu changes
  the subscriber updates the existing event instead of adding a duplicate.
* **Deterministic output.** ``DTSTAMP`` comes from the event date, never from the
  clock, so regenerating an unchanged menu produces a byte-identical file. That is
  what lets the workflow commit only on real changes.
"""

from __future__ import annotations

from datetime import date

from mealviewer import SIDE_ORDER, Day

TITLE_BUDGET = 62

# Stripped from titles only; the description keeps the full menu name.
NOISE = [
    " on Brioche Bun",
    " on Whole Grain Bun",
    " on a Bun",
    "Whole Grain ",
]


def shorten(name: str) -> str:
    for token in NOISE:
        name = name.replace(token, "")
    return name.strip()


def escape(text: str) -> str:
    """Escape per RFC 5545 section 3.3.11. Backslash must be handled first."""
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def fold(line: str) -> str:
    """Fold to 75 octets per RFC 5545, counting bytes rather than characters.

    Unfolded long lines are the single most common reason a calendar client
    silently truncates a summary.
    """
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    chunks, current = [], b""
    for char in line:
        encoded = char.encode("utf-8")
        limit = 75 if not chunks else 74  # continuations lose a byte to the space
        if len(current) + len(encoded) > limit:
            chunks.append(current)
            current = b""
        current += encoded
    chunks.append(current)
    head = chunks[0].decode("utf-8")
    tail = ["\r\n " + c.decode("utf-8") for c in chunks[1:]]
    return head + "".join(tail)


def build_title(tag: str, day: Day) -> str:
    """School tag plus as many hot entrees as fit the title budget."""
    names = [shorten(n) for n in day.entrees] or [shorten(n) for n in day.grab_and_go]
    title = f"{tag}: "
    chosen: list[str] = []
    for name in names[:3]:
        candidate = " / ".join(chosen + [name])
        if chosen and len(title + candidate) > TITLE_BUDGET:
            break
        chosen.append(name)
    return title + " / ".join(chosen) if chosen else f"{tag}: Lunch"


def build_description(day: Day) -> str:
    parts: list[str] = []
    if day.entrees:
        parts.append("Entrees: " + ", ".join(day.entrees))
    if day.grab_and_go:
        parts.append("Grab and go: " + ", ".join(day.grab_and_go))

    ordered = [k for k in SIDE_ORDER if k in day.sides]
    ordered += [k for k in day.sides if k not in SIDE_ORDER]
    for kind in ordered:
        parts.append(f"{kind}: " + ", ".join(day.sides[kind]))
    return "\n".join(parts)


def build_calendar(tag: str, calname: str, days: list[Day]) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//smith6hive//holly-ridge-lunch//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape(calname)}",
        f"NAME:{escape(calname)}",
        "X-PUBLISHED-TTL:PT12H",
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
    ]

    for day in days:
        stamp = day.day.strftime("%Y%m%dT000000Z")
        lines += [
            "BEGIN:VEVENT",
            f"UID:{tag.lower()}-{day.day.isoformat()}@holly-ridge-lunch",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{day.day.strftime('%Y%m%d')}",
            # DTEND is exclusive for all-day events: the day after.
            f"DTEND;VALUE=DATE:{_next_day(day.day).strftime('%Y%m%d')}",
            f"SUMMARY:{escape(build_title(tag, day))}",
            f"DESCRIPTION:{escape(build_description(day))}",
            "TRANSP:TRANSPARENT",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    return "\r\n".join(fold(line) for line in lines) + "\r\n"


def _next_day(value: date) -> date:
    from datetime import timedelta

    return value + timedelta(days=1)
