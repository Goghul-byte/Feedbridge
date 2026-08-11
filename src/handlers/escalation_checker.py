from datetime import datetime, timezone
from common.dynamo import scan_donations_by_status
from common import ngo_matcher
from common.safe_window import remaining_minutes


def lambda_handler(event, context):
    check_offer_timeouts()
    check_expired_safe_windows()
    return {"statusCode": 200}


def check_offer_timeouts():
    # any donation whose current NGO didn't respond within the accept window gets escalated
    now = datetime.now(timezone.utc)
    for donation in scan_donations_by_status("awaiting_ngo_response"):
        expires_at = donation.get("offer_expires_at")
        if expires_at and datetime.fromisoformat(expires_at) <= now:
            ngo_matcher.escalate(donation)


def check_expired_safe_windows():
    # safe window is a hard wall-clock deadline - stop escalating entirely once it hits zero
    active_statuses = ["awaiting_ngo_response", "eta_collection", "confirmed"]
    for status in active_statuses:
        for donation in scan_donations_by_status(status):
            if remaining_minutes(donation["safe_window_deadline"]) <= 0:
                ngo_matcher.cancel_unclaimed(donation)
