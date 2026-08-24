import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from abbrev import abbreviate, condense  # noqa: E402
from icswriter import build_calendar, build_title, escape, fold  # noqa: E402
from mealviewer import Day, _month_spans  # noqa: E402


def sample():
    return Day(
        day=date(2026, 8, 24),
        entrees=["Stuffed Crust Cheese Pizza", "Honey Sriracha Chicken Bites"],
        grab_and_go=["Hummus & String Cheese Box"],
        sides={"Vegetables": ["Creamy Garlic Spinach"], "Grains": ["Steamed Brown Rice"]},
    )


def test_all_day_event_uses_exclusive_dtend():
    ics = build_calendar("HRMS", "Middle", [sample()])
    assert "DTSTART;VALUE=DATE:20260824" in ics
    assert "DTEND;VALUE=DATE:20260825" in ics


def test_uid_is_stable_across_menu_changes():
    a = build_calendar("HRMS", "Middle", [sample()])
    changed = sample()
    changed.entrees = ["Something Else Entirely"]
    b = build_calendar("HRMS", "Middle", [changed])
    uid = "UID:hrms-2026-08-24@holly-ridge-lunch"
    assert uid in a and uid in b


def test_output_is_deterministic():
    assert build_calendar("HRMS", "Middle", [sample()]) == build_calendar(
        "HRMS", "Middle", [sample()]
    )


def test_no_line_exceeds_75_octets():
    long_day = sample()
    long_day.sides = {"Vegetables": ["Extremely Long Vegetable Name " * 6]}
    ics = build_calendar("HRMS", "Middle", [long_day])
    for line in ics.split("\r\n"):
        assert len(line.encode("utf-8")) <= 75, line


def test_folded_lines_rejoin_to_original():
    text = "DESCRIPTION:" + "abcdefghij" * 30
    assert fold(text).replace("\r\n ", "") == text


def test_escaping_handles_backslash_first():
    assert escape("a\\b;c,d") == r"a\\b\;c\,d"


def test_title_carries_tag_and_abbreviated_entrees_within_budget():
    title = build_title("HRMS", sample())
    assert title.startswith("HRMS: ")
    assert "Ch Piz" in title
    assert len(title) <= 54


def test_title_falls_back_to_grab_and_go_when_no_hot_entree():
    day = Day(day=date(2026, 8, 24), grab_and_go=["Turkey & Cheese Box"])
    assert build_title("HRES", day) == "HRES: Trky & Ch Box"


def test_abbreviate_drops_filler_and_contracts_words():
    assert abbreviate("Hamburger on Brioche Bun") == "Hmbrg"
    assert abbreviate("Homestyle Baked Macaroni & Cheese") == "Mac & Ch"
    assert abbreviate("Stuffed Crust Cheese Pizza") == "Ch Piz"


def test_longer_phrase_wins_over_shorter_word():
    """"Cheese Pizza" must not be eaten by the bare "Cheese" -> "Ch" rule."""
    assert abbreviate("Pepperoni  Pizza") == "Pep Piz"


def test_condense_collapses_variant_pairs():
    pair = ["Stuffed Crust Cheese Pizza", "Pepperoni Pizza"]
    assert condense(pair) == ["Ch/Pep Piz"]
    burgers = ["Hamburger on Brioche Bun", "Cheeseburger on Brioche Bun"]
    assert condense(burgers) == ["Hmbrg/Chzbrg"]


def test_condense_leaves_unpaired_items_alone():
    out = condense(["Stuffed Crust Cheese Pizza", "Beef Nachos"])
    assert out == ["Ch Piz", "Beef Nachos"]


def test_condense_never_emits_empty_labels():
    assert "" not in condense(["Fresh", "Mini Cheese Quesadillas"])


def test_single_long_entree_is_kept_not_replaced_by_lunch():
    day = Day(day=date(2026, 8, 24), entrees=["Some Extremely Long Dish Name " * 3])
    assert build_title("HRMS", day) != "HRMS: Lunch"


def test_empty_day_is_detected():
    assert Day(day=date(2026, 10, 1)).is_empty()
    assert not sample().is_empty()


def test_month_spans_cover_range_without_gaps():
    spans = _month_spans(date(2026, 8, 15), date(2026, 11, 3))
    assert spans[0] == (date(2026, 8, 15), date(2026, 8, 31))
    assert spans[-1] == (date(2026, 11, 1), date(2026, 11, 3))
    for (_, prev_end), (next_start, _) in zip(spans, spans[1:]):
        assert (next_start - prev_end).days == 1


def test_crlf_survives_a_write_read_round_trip(tmp_path):
    """Guards the trap that made the build rewrite an unchanged feed every run.

    read_text() translates newlines, so CRLF content read back that way never
    equals what was written. build.py must use newline="" on both sides.
    """
    ics = build_calendar("HRMS", "Middle", [sample()])
    target = tmp_path / "feed.ics"
    with open(target, "w", encoding="utf-8", newline="") as fh:
        fh.write(ics)
    with open(target, encoding="utf-8", newline="") as fh:
        assert fh.read() == ics
    assert target.read_text(encoding="utf-8") != ics  # the trap itself
