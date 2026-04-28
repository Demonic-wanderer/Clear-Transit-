# Route Optimization

This folder contains the reroute helper logic.

The name sounds bigger than the implementation, so it is worth being direct about what it does today:

- marks a route as rerouted
- asks OSRM for alternate driving paths when possible
- updates route ETA and distance using the selected alternate

It is not running advanced optimization, network-wide balancing, or anything close to fleet planning. It is a focused utility that helps the dashboard show a believable alternate path for a shipment that has become risky.

That is enough for the current MVP, and it supports the main user story well.
