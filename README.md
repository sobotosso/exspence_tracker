# Expense Tracker

This application tracks expenses and allows exporting reports.

## OAuth Configuration

Set the following environment variables before running the app:

- `GOOGLE_OAUTH_CLIENT_ID` – OAuth Client ID from Google
- `GOOGLE_OAUTH_CLIENT_SECRET` – OAuth Client Secret from Google

These are required for Google login via Flask-Dance.

## Deployment

Install dependencies from `requirements.txt` and run with the provided `Procfile` using Gunicorn.
