import os
import requests

WHATSAPP_TOKEN = os.environ["WHATSAPP_TOKEN"]
PHONE_NUMBER_ID = os.environ["WHATSAPP_PHONE_NUMBER_ID"]
API_URL = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"

_HEADERS = {
    "Authorization": f"Bearer {WHATSAPP_TOKEN}",
    "Content-Type": "application/json",
}


def send_text(to_phone, body):
    # plain text message, e.g. status updates like T2/T3/T4/T5
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": body},
    }
    return _post(payload)


def send_buttons(to_phone, body, buttons: list):
    # buttons: list of (id, label) tuples - WhatsApp allows a max of 3 reply buttons per message
    if len(buttons) > 3:
        return send_list(to_phone, body, buttons)
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": bid, "title": label[:20]}}
                    for bid, label in buttons
                ]
            },
        },
    }
    return _post(payload)


def send_list(to_phone, body, options: list, section_title="Choose one"):
    # WhatsApp list message - use this when there are more than 3 options (e.g. 6 spoilage presets)
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": body},
            "action": {
                "button": "Select",
                "sections": [
                    {
                        "title": section_title,
                        "rows": [
                            {"id": oid, "title": label[:24]} for oid, label in options
                        ],
                    }
                ],
            },
        },
    }
    return _post(payload)


def send_location_request(to_phone, body):
    # asks the user to share a WhatsApp location pin
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "interactive",
        "interactive": {
            "type": "location_request_message",
            "body": {"text": body},
            "action": {"name": "send_location"},
        },
    }
    return _post(payload)


def _post(payload):
    response = requests.post(API_URL, headers=_HEADERS, json=payload, timeout=10)
    if response.status_code >= 300:
        # don't let a WhatsApp API hiccup crash the whole Lambda - log and move on
        print(f"WhatsApp API error {response.status_code}: {response.text}")
    return response