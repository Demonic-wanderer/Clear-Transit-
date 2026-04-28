# Submission Copy

Use this wording consistently across the README, deck, demo video, and submission form.

## One-Line Pitch

Clear-Transit is a dispatch dashboard for intra-city shipments that helps operators spot delay risk early and compare reroutes before deliveries slip.

## Problem Statement

Intra-city shipments are highly exposed to traffic disruptions and weather shifts, but smaller operators often react too late because they do not have a simple way to monitor route risk, understand the reason for a likely delay, and decide when rerouting is worth it.

## Solution Overview

Clear-Transit is a map-first shipment monitoring dashboard that combines route geometry, traffic signals, weather conditions, and alert history into one operator view. It identifies risky shipments, explains the factors behind the delay prediction, and recommends alternate routes with ETA impact so the operator can act faster.

## MVP Scope

The current MVP focuses on a seeded Indore shipment watchlist. A reviewer can log in, inspect the active route, view live or fallback conditions, refresh the monitoring state, and compare the recommended reroute against the current plan.

## Impact Framing

The value of the MVP is not full logistics automation. The value is faster, more confident operator decisions when a shipment starts to drift off plan.

## Honest Limitations

- The current release is a hackathon MVP, not a production deployment.
- The shipment dataset is intentionally small and centered on Indore.
- SQLite and simple auth are used for speed of delivery.
- Broader fleet workflows, stronger orchestration, and production infrastructure are future work.
