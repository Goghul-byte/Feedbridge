from datetime import datetime, timezone, timedelta

# category -> base safe-window minutes, sourced from FSSAI time-temperature danger-zone guidance
CATEGORY_BASE_MINUTES = {
    "gravy_curry": 120,     # gravies hold moisture - spoil fastest
    "dry_fried": 240,       # dry/fried items last longest
    "meat_seafood": 90,     # highest-risk category
}

DEFAULT_MINUTES = 120  # fallback if a category is somehow missing


def category_base_minutes(category):
    return CATEGORY_BASE_MINUTES.get(category, DEFAULT_MINUTES)


def final_safe_window_minutes(category, restaurant_estimate_minutes=None):
    # Section 3.1 rule: final = MIN(category_table, restaurant_estimate) - never averaged, never extended
    base = category_base_minutes(category)
    if restaurant_estimate_minutes is None:
        return base
    return min(base, restaurant_estimate_minutes)


def compute_deadline(prep_time_iso, safe_window_minutes):
    # the safe-window timer starts the moment classification completes (Section 4)
    # cast to float in case safe_window_minutes came back from DynamoDB as a Decimal
    prep_time = datetime.fromisoformat(prep_time_iso)
    return prep_time + timedelta(minutes=float(safe_window_minutes))


def remaining_minutes(deadline_iso):
    deadline = datetime.fromisoformat(deadline_iso)
    now = datetime.now(timezone.utc)
    return (deadline - now).total_seconds() / 60


def overall_deadline_for_items(item_deadlines: list):
    # multi-item rule (Section 3.1/3.2): overall deadline = earliest (shortest) item deadline
    return min(item_deadlines)
