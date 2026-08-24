"""Condense entree names for calendar titles.

Titles only. Event descriptions always carry the district's full menu text,
so nothing here loses information the reader cannot get back.

Three passes, in order:

1. ``PAIRS``   -- collapse near-identical variants the schools list separately
2. ``PHRASES`` -- multi-word rewrites, longest match first
3. ``WORDS``   -- token-level contractions

Every table is plain data. Add a school favourite, get a shorter title.
"""

from __future__ import annotations

import re

# --- Pass 1: variant pairs served side by side ------------------------------
# Matched on the district's exact names, before any shortening.
PAIRS: list[tuple[list[str], str]] = [
    (["Stuffed Crust Cheese Pizza", "Pepperoni Pizza"], "Ch/Pep Piz"),
    (["Chicken Filet on Brioche Bun", "Spicy Chicken Filet on Brioche Bun"],
     "Ckn Filet/Spcy"),
    (["Hamburger on Brioche Bun", "Cheeseburger on Brioche Bun"], "Hmbrg/Chzbrg"),
    (["Hamburger on Brioche Bun", "Double Cheeseburger on Brioche Bun"],
     "Hmbrg/Dbl Chzbrg"),
]

# --- Pass 2: phrases -------------------------------------------------------
# Filler that carries no information maps to "".
PHRASES: dict[str, str] = {
    # deletions
    "on Brioche Bun": "",
    "on Whole Grain Bun": "",
    "on a Bun": "",
    "Scratch Made": "",
    "Homestyle Baked": "",
    "Homestyle": "",
    "Whole Grain": "",
    "Plant Based": "",
    "with Brown Gravy": "",
    # rewrites
    "Stuffed Crust Cheese Pizza": "Ch Piz",
    "Pepperoni Pizza": "Pep Piz",
    "Cheese Pizza": "Ch Piz",
    "General Tso's Popcorn Chicken": "Gen Tso Ckn",
    "Macaroni & Cheese": "Mac & Ch",
    "Pimento Cheese & Crackers": "Pimnto Ch",
    "3 Bean Chili with Cheddar Cheese": "3-Bean Chili",
    "Chicken & Vegetable Dumplings": "Ckn Dmplngs",
    "Vanilla Yogurt &": "",
    "Butterball Turkey Hot Dog": "Hot Dog",
    "Butterball Double Dogs": "Dbl Dogs",
    "Grilled Cheese Sandwich": "Grld Ch",
    "Rice Bowl": "Bowl",
    "with Rice": "",
    "Soft Tacos": "Tacos",
    "Honey Sriracha": "Srrcha",
    "Chicken & Cheese Chef Salad": "Ckn Chef Sld",
    "Alfredo Pasta": "Alfrd",
    "Beef & Cheddar": "Beef",
    "& Crackers": "",
    "Baked Rotini &": "Rotini",
    "Chef Salad": "Chef Sld",
    "with": "w/",
}

# --- Pass 3: single words ---------------------------------------------------
WORDS: dict[str, str] = {
    "Chicken": "Ckn",
    "Hamburger": "Hmbrg",
    "Cheeseburger": "Chzbrg",
    "Cheeseburgers": "Chzbrgs",
    "Cheese": "Ch",
    "Cheddar": "Chdr",
    "Pepperoni": "Pep",
    "Pizza": "Piz",
    "Sandwich": "Sndwch",
    "Quesadillas": "Quesa",
    "Quesadilla": "Quesa",
    "Vegetable": "Veg",
    "Vegetables": "Veg",
    "Broccoli": "Brocc",
    "Alfredo": "Alfrd",
    "Marinara": "Marin",
    "Macaroni": "Mac",
    "Parfait": "Parf",
    "Spicy": "Spcy",
    "Grilled": "Grld",
    "Baked": "Bkd",
    "Roasted": "Rstd",
    "Popcorn": "Popcrn",
    "Salisbury": "Salsbry",
    "Strawberry": "Strwbry",
    "Blueberry": "Blubry",
    "Turkey": "Trky",
    "Dumplings": "Dmplngs",
    "Sriracha": "Srrcha",
    "Tangerine": "Tang",
    "Pimento": "Pimnto",
    "Double": "Dbl",
    "Creamy": "Crmy",
    "Spinach": "Spnch",
    "Crispy": "Crspy",
    "Buffalo": "Bflo",
    "Teriyaki": "Teri",
    "Barbecue": "BBQ",
    "Mashed": "Mshd",
    "Potatoes": "Pots",
    "Mozzarella": "Mozz",
    "Fresh": "",
    "Mini": "",
}


def _norm(text: str) -> str:
    """Collapse the stray double spaces MealViewer ships in item names."""
    return re.sub(r"\s+", " ", (text or "")).strip()


def abbreviate(name: str) -> str:
    """Shorten one entree name for display in a title."""
    text = _norm(name)

    # Longest phrase first, so "Cheese Pizza" cannot be eaten by "Cheese".
    for phrase in sorted(PHRASES, key=len, reverse=True):
        if phrase.lower() in text.lower():
            text = re.sub(re.escape(phrase), PHRASES[phrase], text, flags=re.I)

    words = [WORDS.get(w, w) for w in _norm(text).split(" ")]
    return _norm(" ".join(words)).strip(" &-/")


def condense(entrees: list[str]) -> list[str]:
    """Collapse variant pairs, then abbreviate whatever is left."""
    raw = [_norm(e) for e in entrees]
    labels: list[str] = []
    used: set[str] = set()

    for members, label in PAIRS:
        wanted = [_norm(m) for m in members]
        if all(w in raw for w in wanted) and not (set(wanted) & used):
            labels.append(label)
            used.update(wanted)

    labels += [abbreviate(e) for e in raw if e not in used]
    return [l for l in labels if l]
