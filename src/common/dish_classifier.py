import re
from rapidfuzz import fuzz, process
from common.dynamo import scan_all_dishes

UNITS = r"(kg|kgs|trays|tray|litre|litres|l|meals|plates|people)"

# covers: "50kg Biryani", "Biryani 50kg", "Chicken Curry - 10 kg", "5 trays biryani"
PATTERN_QTY_FIRST = re.compile(rf"(\d+)\s*{UNITS}?\s*(?:of\s*)?([a-zA-Z ]+)", re.IGNORECASE)
PATTERN_NAME_FIRST = re.compile(rf"([a-zA-Z ]+?)\s*[-:]?\s*(\d+)\s*{UNITS}?", re.IGNORECASE)
# covers: "Biryani for 80 people"
PATTERN_FOR_PEOPLE = re.compile(r"([a-zA-Z ]+?)\s+for\s+(\d+)\s*people", re.IGNORECASE)

FUZZY_MATCH_THRESHOLD = 85  # Section 3.2 - similarity score below this counts as "unmatched"

# words that mean "there's food" but aren't an actual dish name (Section 3.2 edge case)
GENERIC_NON_DISH_WORDS = {"lunch", "ready", "food", "order", "items", "meal", "dinner", "breakfast"}


def extract_items(message_text):
    """Tier 1: turn free text into a list of {item_name, quantity, unit} dicts."""
    text = message_text.strip()
    items = []

    for match in PATTERN_FOR_PEOPLE.finditer(text):
        items.append({
            "item_name": match.group(1).strip(),
            "quantity": int(match.group(2)),
            "unit": "people",
        })

    # pick pattern order by whether the message leads with a number or a name -
    # this avoids "kg"/"trays" being swallowed as the item name (e.g. "Biryani 50kg")
    if not items:
        if text[:1].isdigit():
            for match in PATTERN_QTY_FIRST.finditer(text):
                name = match.group(3).strip()
                if name and not name.isdigit():
                    items.append({
                        "item_name": name,
                        "quantity": int(match.group(1)),
                        "unit": (match.group(2) or "units").lower(),
                    })
        else:
            for match in PATTERN_NAME_FIRST.finditer(text):
                name = match.group(1).strip()
                if name:
                    items.append({
                        "item_name": name,
                        "quantity": int(match.group(2)),
                        "unit": (match.group(3) or "units").lower(),
                    })

    # e.g. "Lunch Ready, 50 Meals" has a quantity but no real dish name - ask instead of guessing
    items = [i for i in items if i["item_name"].strip(", ").lower() not in GENERIC_NON_DISH_WORDS]

    return items  # empty list means "no identifiable dish name" -> caller should ask for item names


def match_dish_category(item_name):
    """Tier 2: RapidFuzz match against the dish dictionary. Returns (category, confident: bool)."""
    dictionary = scan_all_dishes()
    if not dictionary:
        return None, False

    choices = {d["dish_name"]: d["category"] for d in dictionary}
    best = process.extractOne(item_name.lower(), choices.keys(), scorer=fuzz.ratio)

    if best is None:
        return None, False

    matched_name, score, _ = best
    if score >= FUZZY_MATCH_THRESHOLD:
        return choices[matched_name], True
    return None, False  # Tier 3 (WhatsApp buttons) takes over from here
