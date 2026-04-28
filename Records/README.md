# Records

This folder is the app's local persistence layer.

It stores the SQLite database and the SQLAlchemy models used by the Flask app. For a hackathon MVP, this is enough: we get persistent users, routes, and disruption events without having to stand up a separate database service.

What lives here:

- route records
- disruption event history
- user accounts for the simple login flow

The database file is local and disposable. It is useful for demos, local development, and keeping state between runs, but it is not being treated like a production database setup.
