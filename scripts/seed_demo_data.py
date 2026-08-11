"""Run once after `sam deploy`, from your own machine (needs AWS credentials configured).
Usage: python scripts/seed_demo_data.py
"""
import json
import boto3
from decimal import Decimal

dynamo = boto3.resource("dynamodb")

def to_decimal(obj):
    """Recursively convert any float in a dict/list to Decimal for DynamoDB."""
    return json.loads(json.dumps(obj), parse_float=Decimal)

# --- seed the dish dictionary ---
with open("data/dish_dictionary_seed.json") as f:
    dishes = json.load(f)

dish_table = dynamo.Table("feedbridge-dish-dictionary")
for dish in dishes:
    dish_table.put_item(Item=to_decimal(dish))
print(f"Seeded {len(dishes)} dishes")

# --- seed a couple of demo NGOs so the matcher has something to find ---
# swap phone numbers for real WhatsApp test numbers before your demo
ngo_table = dynamo.Table("feedbridge-ngos")
demo_ngos = [
    {"ngo_id": "ngo-1", "name": "Robin Hood Army - Puducherry", "phone": "919360799093",
     "lat": 11.9416, "lng": 79.8083, "fssai_darpan_id": "DEMO123", "verified": True,
     "active": True, "reliability_score": 100},
    {"ngo_id": "ngo-2", "name": "Annamitra Foundation", "phone": "918341525369",
     "lat": 11.9139, "lng": 79.8145, "fssai_darpan_id": "DEMO456", "verified": True,
     "active": True, "reliability_score": 100},
]
for ngo in demo_ngos:
    ngo_table.put_item(Item=to_decimal(ngo))
print(f"Seeded {len(demo_ngos)} demo NGOs")