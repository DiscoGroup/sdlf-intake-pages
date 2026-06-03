# Steigerwalt PLC Injury Claim Landing Page

A simple Steigerwalt PLC-branded injury claim calculator with persistent lead storage and automatic CSV email export.

[Deploy to Render](https://dashboard.render.com/blueprints/new?repo=https://github.com/DiscoGroup/sdlf-intake-pages)

## Run locally

```bash
python3 server.py
```

Open `http://localhost:8000`.

## Preview URLs

- Injuries, car accidents, and wrongful death: `http://localhost:8000/injuries/`
- Mesothelioma from asbestos: `http://localhost:8000/mesothelioma-asbestos/`
- Workplace sexual harassment: `http://localhost:8000/workplace-sexual-harassment/`
- Social media addiction: `http://localhost:8000/social-media-addiction/`
- California juvenile detention sexual abuse: `http://localhost:8000/juvenile-detention-abuse/`

## Data and exports

Submissions are stored in SQLite at `data/submissions.sqlite`. Each entry includes `caseCategory`, `leadStatus`, `leadScore`, `qualificationSummary`, and the raw `qualificationData` JSON for lead review.

Download all saved entries as CSV:

```text
http://localhost:8000/api/export
```

## Email export setup

Each successful submission attempts to email a one-row CSV export to `chaz@vnsfirm.com`.

The Render Blueprint is prefilled for Brevo's free SMTP relay. Add your private Brevo SMTP login/key and a verified sender address:

```bash
export SMTP_HOST="smtp-relay.brevo.com"
export SMTP_PORT="587"
export SMTP_USER="your-brevo-smtp-login"
export SMTP_PASSWORD="your-brevo-smtp-key"
export SMTP_FROM="verified-sender@example.com"
export EXPORT_EMAILS="chaz@vnsfirm.com"
export SMTP_STARTTLS="true"
export SMTP_SSL="false"
python3 server.py
```

If SMTP settings are missing, the submission is still saved in the database and the UI reports that email export is pending configuration.

## Render deployment

This repo includes `render.yaml` for a Render Blueprint with:

- Python web service
- Managed Render Postgres database
- `DATABASE_URL` wired automatically from the database
- Brevo SMTP relay defaults with secret credential placeholders

Render setup:

1. Click the Render deploy link above.
2. Connect the `DiscoGroup/sdlf-intake-pages` GitHub repo if Render asks for access.
3. Add the SMTP secrets in Render:
   - `SMTP_USER`
   - `SMTP_PASSWORD`
   - `SMTP_FROM`
   - optional: keep `SMTP_HOST=smtp-relay.brevo.com`, `SMTP_PORT=587`, `SMTP_STARTTLS=true`, `SMTP_SSL=false`
4. Deploy.

The app listens on Render's `PORT` environment variable and falls back to SQLite only for local development.

## Notes

The calculator estimate is informational only and is not legal advice. It is intended to collect intake details for attorney review.
