# Deployment

This repo is prepared for a simple single-service deployment for hackathon judging.

## Recommended Path

Use Render or Railway with the existing Flask app.

- build command: `pip install -r requirements.txt`
- start command: `python app.py`

`app.py` is already configured to bind to `0.0.0.0:$PORT`, so it can run directly on a hosted web service.

## Environment Variables

Set these values in the hosting dashboard:

- `SECRET_KEY`
- `WEATHER_API_KEY`
- `TRAFFIC_API_KEY`
- `TRAFFIC_API`
- `WEATHER_CITY`
- `TRAFFIC_LAT`
- `TRAFFIC_LON`
- `ROUTING_API_BASE`
- `WEBHOOK_URL`
- `ALERT_COOLDOWN_SECONDS`

You can start from `.env.example`.

## Reviewer Flow

The cleanest review flow is:

1. Open the live app.
2. Register a temporary account.
3. Land on the shipment dashboard.
4. Refresh the dashboard once.
5. Show the reroute recommendation and ETA comparison.

## Deployment Notes

- The repo uses SQLite for demo persistence.
- On platforms with ephemeral filesystems, reviewer-created accounts may reset after a restart or redeploy.
- That tradeoff is acceptable for the hackathon MVP as long as registration works and the seeded shipment data is available.
- If live traffic or weather keys are unavailable, the app still falls back to demo-friendly conditions so the prototype remains functional.

## Before Submission

- replace the placeholder live URL in the root `README.md`
- test the hosted app in an incognito window
- confirm login, dashboard load, refresh, and reroute all work at least once
