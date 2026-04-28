# Data Architect

This folder holds the seed shipment data for the demo.

Right now that means one file:

- `routes.json`

That JSON is the starting point for the route records that get bootstrapped into the local database. We are using it as a practical demo source, not as a serious data engineering layer.

At the moment the data is intentionally scoped to Indore so the map, traffic signal, and weather signal all feel like part of the same story.

If you change the route data here and restart the app, the bootstrap flow will sync the stored route metadata back toward these seeded values.
