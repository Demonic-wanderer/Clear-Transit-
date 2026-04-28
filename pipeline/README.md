# pipeline

This folder is the real backend heart of the MVP.

If the frontend is the face of the project, `pipeline/` is the working layer that turns raw conditions into a dashboard snapshot the UI can actually use.

This folder currently handles:

- loading and saving route state
- reading traffic and weather inputs
- normalizing those signals into simple severity levels
- building risk factors and delay predictions
- attaching route geometry and alternates
- logging disruption events
- producing the dashboard payload served by Flask

It is not a formal data pipeline in the big-platform sense. It is a practical application layer for a small live demo.

If you want to understand how the app thinks, this is the folder to read first.
