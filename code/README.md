# Saved Sanctuary Hotel design

The website now lives in `frontend/` and is served by the FastAPI application.
See the [root README](../README.md) for installation, database migration, seeding,
model configuration and checks. `scripts/verify_website.py` validates its local assets.

The hotel and all photos are fictional. The preserved hero is an 18-second silent
loop of three AI-generated stills, using four-second holds and two-second fades.
Reduced-motion visitors see the pool still. The earlier Seedance clip remains
an unused reference asset. All images and videos remain local in `frontend/assets/`.

The concierge reads published PostgreSQL policies through ADK. It cannot create
reservations or send requests to staff. Conversation history is private to an
opaque guest cookie and survives page reloads; New conversation starts a separate
conversation rather than deleting existing data.
