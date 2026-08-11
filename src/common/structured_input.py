import re

# matches "1 hr", "1.5 hours", "2 hrs" etc, converted to minutes before plain-integer fallback
HOUR_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(?:hr|hrs|hour|hours)", re.IGNORECASE)
NUMBER_PATTERN = re.compile(r"(\d+)")

MIN_MINUTES = 1
MAX_MINUTES = 180


def parse_minutes(text):
    """Hour-aware parse: '1.5 hours' -> 90, '45'/'maybe 45 mins bro'/'40 mis' -> 45/40. Returns None if unparseable."""
    hour_match = HOUR_PATTERN.search(text)
    if hour_match:
        return round(float(hour_match.group(1)) * 60)

    number_match = NUMBER_PATTERN.search(text)
    if number_match:
        return int(number_match.group(1))

    return None


def is_within_sanity_bound(minutes):
    # bad numbers never reach the confirmation step (Section 3.4)
    return minutes is not None and MIN_MINUTES <= minutes <= MAX_MINUTES
