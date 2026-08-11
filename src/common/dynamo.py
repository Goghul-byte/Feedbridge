import os
import json
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Attr

# one shared resource object, reused across warm Lambda invocations
_dynamo = boto3.resource("dynamodb")

donations_table = _dynamo.Table(os.environ["DONATIONS_TABLE"])
ngos_table = _dynamo.Table(os.environ["NGOS_TABLE"])
restaurants_table = _dynamo.Table(os.environ["RESTAURANTS_TABLE"])
dish_dictionary_table = _dynamo.Table(os.environ["DISH_DICTIONARY_TABLE"])
conversation_state_table = _dynamo.Table(os.environ["CONVERSATION_STATE_TABLE"])

def to_decimal(obj):
    # DynamoDB rejects plain Python floats and json.dumps can't serialize
    # Decimals - this handles both, converting everything to Decimal cleanly
    return json.loads(
        json.dumps(obj, default=lambda o: float(o) if isinstance(o, Decimal) else str(o)),
        parse_float=Decimal,
    )


def get_donation(donation_id):
    # fetch one donation record by its primary key
    result = donations_table.get_item(Key={"donation_id": donation_id})
    return result.get("Item")


def put_donation(item):
    # create or fully overwrite a donation record
    donations_table.put_item(Item=to_decimal(item))


def update_donation(donation_id, updates: dict):
    # partial update - builds an UpdateExpression from a plain dict
    updates = to_decimal(updates)
    expr_names = {f"#{k}": k for k in updates}
    expr_values = {f":{k}": v for k, v in updates.items()}
    set_clause = ", ".join(f"#{k} = :{k}" for k in updates)
    donations_table.update_item(
        Key={"donation_id": donation_id},
        UpdateExpression=f"SET {set_clause}",
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
    )


def get_conversation_state(phone_number):
    # what step of the flow this phone number is currently on
    result = conversation_state_table.get_item(Key={"phone_number": phone_number})
    return result.get("Item")


def set_conversation_state(phone_number, state: dict):
    # overwrite the conversation state for a phone number
    state["phone_number"] = phone_number
    conversation_state_table.put_item(Item=to_decimal(state))


def clear_conversation_state(phone_number):
    conversation_state_table.delete_item(Key={"phone_number": phone_number})


def get_ngo(ngo_id):
    result = ngos_table.get_item(Key={"ngo_id": ngo_id})
    return result.get("Item")


def get_ngo_by_phone(phone_number):
    # scan is fine at hackathon scale - swap for a GSI on phone_number before real launch
    result = ngos_table.scan(FilterExpression=Attr("phone").eq(phone_number))
    items = result.get("Items", [])
    return items[0] if items else None


def list_active_verified_ngos():
    result = ngos_table.scan(
        FilterExpression=Attr("active").eq(True) & Attr("verified").eq(True)
    )
    return result.get("Items", [])


def get_restaurant_by_phone(phone_number):
    result = restaurants_table.scan(FilterExpression=Attr("phone").eq(phone_number))
    items = result.get("Items", [])
    return items[0] if items else None


def put_restaurant(item):
    restaurants_table.put_item(Item=to_decimal(item))


def get_dish(dish_name):
    result = dish_dictionary_table.get_item(Key={"dish_name": dish_name.lower()})
    return result.get("Item")


def upsert_dish(dish_name, category, confirmed_by):
    # Tier 4 auto-learning: save or reinforce a dish -> category mapping
    key = dish_name.lower()
    existing = get_dish(key)
    if existing:
        dish_dictionary_table.update_item(
            Key={"dish_name": key},
            UpdateExpression="SET category = :c, times_confirmed = times_confirmed + :one, last_confirmed = :now",
            ExpressionAttributeValues={
                ":c": category,
                ":one": 1,
                ":now": _now_iso(),
            },
        )
    else:
        dish_dictionary_table.put_item(
            Item=to_decimal({
                "dish_name": key,
                "aliases": [key],
                "category": category,
                "confidence_score": 1,
                "times_confirmed": 1,
                "last_confirmed": _now_iso(),
                "created_by": confirmed_by,
            })
        )


def scan_all_dishes():
    # used by the RapidFuzz matcher to build its in-memory candidate list
    result = dish_dictionary_table.scan()
    return result.get("Items", [])


def scan_donations_by_status(status):
    result = donations_table.scan(FilterExpression=Attr("status").eq(status))
    return result.get("Items", [])


def _now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()