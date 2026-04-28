# Frontend

This folder contains the UI that the Flask app serves directly.

The frontend is intentionally simple: plain HTML, CSS, and JavaScript. No framework, no build step, and no hidden complexity. That helped us move quickly during the hackathon.

The main UI responsibilities here are:

- render the map and active shipment
- show route status, delay, and reroute context
- present weather and traffic conditions clearly
- keep the interface usable even when the backend falls back to demo data

Files worth knowing:

- `index.html`
  Dashboard shell.

- `app.js`
  Fetches dashboard snapshots, updates the map, and renders the live route experience.

- `style.css`
  Dashboard styling.

- `auth.html`, `auth.js`, `auth.css`
  Minimal login and registration flow.

The frontend has been tuned to make one active shipment feel important rather than trying to show everything equally.
