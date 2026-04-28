# Clear-Transit

Clear-Transit is a hackathon MVP for intra-city shipment monitoring. It helps a dispatcher spot a risky shipment early, understand what is driving the delay, and compare a reroute before making the call.

This is not a full logistics automation platform. It is a focused dispatch dashboard built to make one workflow feel clear and believable.

## Submission Summary

- **Problem statement:** intra-city shipments get delayed by traffic and weather, but small operators often notice too late and lack a simple way to understand risk and react quickly.
- **Solution overview:** Clear-Transit is a map-first dispatch dashboard that monitors shipments, combines route, traffic, and weather signals, explains why a route is risky, and recommends reroutes with ETA impact.
- **Current MVP outcome:** a reviewer can log in, inspect a seeded Indore shipment watchlist, refresh live conditions, and see a reroute recommendation with route context and alert history.

The working submission copy also lives in [docs/submission-copy.md](docs/submission-copy.md).

## Live Demo

- **Prototype link:** add your deployed URL here before submission
- **Deployment target:** the repo includes `render.yaml` and `Procfile` for a single-service Flask deployment
- **Hosted behavior:** if live API keys are missing, the app still falls back to demo-friendly values so the dashboard remains usable

Deployment steps are documented in [docs/deployment.md](docs/deployment.md).

## Demo Credentials

For the live demo, reviewers can create a temporary account directly from the login page:

- click `Create account`
- use any email address
- use a password with at least 8 characters

If you decide to publish a shared reviewer account after deployment, replace this section with that email and password before submission.

## What The MVP Actually Does

When the app loads, it pulls shipment data from the local SQLite-backed route store, enriches it with route geometry, checks traffic and weather conditions, and produces a dashboard snapshot for the frontend.

From there, the UI does three useful things:

- keeps one shipment in focus on the map
- explains the detected risk factors behind the delay prediction
- shows what the reroute recommendation would improve

The goal is not to pretend we built a giant logistics stack. The goal is to make a small dispatch tool feel coherent, useful, and believable.

## Current Scope

The product is best described as:

`An intra-city shipment monitoring and reroute recommendation dashboard for Indore.`

That scope matters because the demo data, traffic setup, and weather configuration are centered around Indore.

## Tech Stack

- Python + Flask
- SQLAlchemy + SQLite
- Vanilla HTML, CSS, and JavaScript
- MapLibre GL for the live map
- OSRM for route geometry and alternates
- OpenWeather and TomTom traffic when keys are configured

## Project Structure

- `app.py`  
  Main Flask entry point. Handles auth, serves the frontend, and exposes the dashboard APIs.

- `Frontend/`  
  The dashboard UI and login screen.

- `pipeline/`  
  Signal ingestion, normalization, prediction, reroute enrichment, and dashboard snapshot assembly.

- `Data Architect/`  
  Seed shipment data used to bootstrap the demo.

- `Route Optimization/`  
  The reroute helper that updates route status and alternate path details.

- `Records/`  
  SQLite-backed models and storage for users, routes, and disruption events.

- `LOGISTICS/`  
  Placeholder space for higher-level orchestration. This is not a mature subsystem yet.

- `docs/`  
  Deployment notes, submission copy, and future architecture context.

## Running It Locally

1. Create a virtual environment.
2. Install dependencies from `requirements.txt`.
3. Copy `.env.example` to `.env`.
4. Add your local keys if you want live weather or traffic.
5. Start the app with `python app.py`.
6. Open `http://127.0.0.1:5000`.

If keys are missing, the app falls back to demo-friendly values so the UI still works.

## Deploying The MVP

The app is set up to run as a single Flask web service:

- `render.yaml` provides a Render-ready service definition
- `Procfile` provides a simple platform start command
- `app.py` now binds to `0.0.0.0:$PORT` for hosted environments

For a submission deployment, keep the architecture simple: one web service, one SQLite-backed demo dataset, and environment variables loaded from the hosting provider.

## Environment Variables

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

`TRAFFIC_API_KEY` and `TRAFFIC_API` are both supported because the repo has used both names during development.

## Public Repo Notes

Before publishing:

- do not commit `.env`
- do not commit `.venv`
- do not commit local SQLite files such as `Records/alerts.db`
- rotate any API keys if they were ever pushed in a different copy of the project

This ZIP copy already ignores those items in `.gitignore`, but you should still confirm the final public repo contents before submission.

## What Is Still Rough

- The logistics orchestration layer is mostly not implemented yet.
- The app is still light on tests.
- The app is built for a hackathon demo, not production auth or infrastructure.
- A hosted deployment that uses SQLite may reset reviewer-created accounts if the platform filesystem is ephemeral.

`Clear-Transit helps an operator spot a risky shipment, understand the cause of the delay, and see the value of a reroute before making the call.`

That is the workflow this MVP is designed to prove.
