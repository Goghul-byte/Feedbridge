from datetime import datetime, timezone, timedelta
from common.dynamo import list_active_verified_ngos, update_donation
from common.geo import distance_km, distance_tier
from common import whatsapp_client
from common.safe_window import remaining_minutes

ACCEPT_WINDOW_MINUTES = 20  # flat window for all distance tiers (Section 3.3)


def find_next_ngo(donation):
    """Nearest verified NGO within 15km, not already excluded for this donation."""
    excluded = set(donation.get("excluded_ngo_ids", []))
    restaurant_lat = donation["restaurant_lat"]
    restaurant_lng = donation["restaurant_lng"]

    candidates = []
    for ngo in list_active_verified_ngos():
        if ngo["ngo_id"] in excluded:
            continue
        km = distance_km(restaurant_lat, restaurant_lng, ngo["lat"], ngo["lng"])
        if distance_tier(km) is not None:
            candidates.append((km, ngo))

    if not candidates:
        return None, None

    candidates.sort(key=lambda pair: pair[0])
    nearest_km, nearest_ngo = candidates[0]
    return nearest_ngo, nearest_km


def send_offer(donation, ngo, distance):
    # tight-window rule (Section 3.7): shorten the accept-timer when little safe-window remains
    remaining = remaining_minutes(donation["safe_window_deadline"])
    accept_window = min(ACCEPT_WINDOW_MINUTES, max(1, remaining / 2)) if remaining < 15 else ACCEPT_WINDOW_MINUTES
    offer_expires_at = (datetime.now(timezone.utc) + timedelta(minutes=accept_window)).isoformat()

    item_summary = ", ".join(
        f"{i['quantity']}{i['unit']} {i['item_name']}" for i in donation["items"]
    )

    update_donation(donation["donation_id"], {
        "current_ngo_id": ngo["ngo_id"],
        "status": "awaiting_ngo_response",
        "offer_expires_at": offer_expires_at,
        "offer_distance_km": str(round(distance, 1)),
    })

    body = (
        f"New pickup: {item_summary} from {donation['restaurant_name']}. "
        f"Distance: {round(distance, 1)} km. Accept or Decline?"
    )
    if remaining < 15:
        body += f" Note: only ~{int(remaining)} min left on the food-safety window."

    whatsapp_client.send_buttons(
        ngo["phone"], body,
        [(f"accept_{donation['donation_id']}", "Accept"),
         (f"decline_{donation['donation_id']}", "Decline")],
    )


def escalate(donation, reason_message_to_restaurant=None):
    """Move to the next nearest NGO, or cancel entirely if the safe window has expired or no NGO is left."""
    if remaining_minutes(donation["safe_window_deadline"]) <= 0:
        cancel_unclaimed(donation)
        return

    excluded = donation.get("excluded_ngo_ids", [])
    if donation.get("current_ngo_id"):
        excluded = excluded + [donation["current_ngo_id"]]
        update_donation(donation["donation_id"], {"excluded_ngo_ids": excluded})
        donation["excluded_ngo_ids"] = excluded

    next_ngo, distance = find_next_ngo(donation)
    if next_ngo is None:
        cancel_unclaimed(donation)
        return

    if reason_message_to_restaurant:
        whatsapp_client.send_text(donation["restaurant_phone"], reason_message_to_restaurant)
    else:
        whatsapp_client.send_text(
            donation["restaurant_phone"],
            "Still finding a match - expanding our search radius. We'll keep you posted.",  # T4
        )

    send_offer(donation, next_ngo, distance)


def cancel_unclaimed(donation):
    update_donation(donation["donation_id"], {"status": "unclaimed"})
    whatsapp_client.send_text(
        donation["restaurant_phone"],
        "Unfortunately no NGO could make it in time and the food window has closed. "
        "We've marked this as unclaimed - thanks for trying to reduce waste with us.",  # T5
    )
