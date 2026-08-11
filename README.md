# FeedBridge - Deployment Guide

This is the full Phase-1 (MVP) build: restaurant submission → dish classification →
safe-window calculation → distance-tiered NGO matching → structured ETA collection →
OTP custody handshake. Everything from the reference PDF's Section 3 is implemented.

## What's in this folder
```
template.yaml              AWS SAM template - defines every AWS resource
requirements.txt           Python dependencies for the Lambdas
src/common/                shared logic (DynamoDB, WhatsApp client, dish classifier, safe window, NGO matching)
src/handlers/webhook_handler.py     receives every WhatsApp message, runs the whole state machine
src/handlers/escalation_checker.py  runs every minute, handles timeouts
data/dish_dictionary_seed.json      ~10 sample dishes (real version needs 1000-2000, see note below)
scripts/seed_demo_data.py           loads sample dishes + 2 demo NGOs into DynamoDB
events/                     sample webhook payloads for local testing without WhatsApp
```

## 1. One-time AWS setup
1. Install AWS CLI and SAM CLI, run `aws configure` with your AWS account's access key.
2. `cd feedbridge`
3. `sam build`
4. `sam deploy --guided` - it will ask for:
   - Stack name (e.g. `feedbridge`)
   - AWS Region (e.g. `ap-south-1`)
   - `WhatsAppToken`, `WhatsAppPhoneNumberId` - from Meta setup below
   - `WhatsAppVerifyToken` - make up any string, e.g. `feedbridge_verify_123`
5. Note the `WebhookUrl` printed at the end - you need it for step 2.

## 2. WhatsApp Cloud API setup (Meta)
1. Go to https://developers.facebook.com → create an app → add the "WhatsApp" product.
2. Under WhatsApp → API Setup, copy the **temporary access token** and **Phone number ID**
   (use these for the `sam deploy --guided` parameters above; the temporary token
   expires in 24h, so for the finals get a **permanent token** via System Users in
   Business Settings).
3. Under WhatsApp → Configuration → Webhook, click Edit and paste:
   - Callback URL: `<WebhookUrl from step 1>`
   - Verify Token: the same string you set as `WhatsAppVerifyToken`
4. Subscribe to the `messages` webhook field.
5. Under API Setup, add your own phone number (and your teammates') as a test
   recipient number - Meta only allows messaging verified test numbers until your
   app goes through Business Verification.

## 3. Load demo data
```
pip install boto3
python scripts/seed_demo_data.py
```
This loads the sample dish dictionary and two demo NGOs. **Edit the phone numbers
in `scripts/seed_demo_data.py` to real WhatsApp numbers you control** (e.g. two of
your team's phones acting as "NGOs") before running it - the matcher looks up NGOs
by phone number.

Also add a restaurant test flow: message the WhatsApp number from a phone that
is NOT one of the NGO numbers you seeded - the webhook auto-creates a restaurant
record for any new phone number on its first message.

## 4. Test it end-to-end
On the restaurant phone, send: `50kg Biryani`
You should get asked for location → then a spoilage-time estimate → then the NGO
phone gets an Accept/Decline offer → ETA collection → OTP → done.

## 5. Local testing without WhatsApp (fallback for the known Meta test-number restriction)
If your team's Meta Business Account restriction (error 131031) is still blocking
outbound messages when you present, you can demo the backend logic directly:
```
sam local invoke WebhookFunction --event events/restaurant_first_message.json
sam local invoke WebhookFunction --event events/restaurant_location.json
```
Then show the DynamoDB console (`feedbridge-donations` table) and CloudWatch Logs
for the Lambda to prove the matching/classification/safe-window logic ran
correctly, even if the outbound WhatsApp send itself gets rejected by Meta.

## 6. Known scope limits (documented, not bugs)
- Dish dictionary seed is ~10 dishes for the demo; production needs the full
  1,000-2,000 dish list mentioned in the PDF (Section 3.2) - swap the seed JSON.
- `scan()` calls in `dynamo.py` (NGO/restaurant lookup by phone) are fine at
  hackathon scale; before real launch, add a Global Secondary Index on `phone`
  and use `query()` instead.
- Tier 3 LLM-based classification, the 3-layer dish dictionary, voice-call
  fallback, and the biogas/cattle-feed diversion layer are Phase 2/3 per the
  roadmap and are intentionally not built yet.
