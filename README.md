# Dfdata

Public data feed for the Dalit Finder Android app.

This repository intentionally contains public, source-backed data and the minimal refresh tooling needed to reproduce the feed. The Android application source and Google Play Billing implementation live separately in the private `ryanbytes/Dalit-finder` repository.

## Feed

- `feed/v1/companies.json` — matched company/event feed used by the app
- `feed/v1/companies.json.gz` — compressed copy
- `feed/v1/coverage.json` — 50 states + DC source coverage/status
- `feed/v1/stats.json` — generation statistics
- `state/ats_history.json` — observed foreign ATS postings used to preserve first/last-seen dates

## Evidence policy

Automated matching is capped at `POSSIBLE`. A U.S. WARN filing plus foreign job-posting activity is an overlap signal, not proof that a foreign job replaced a U.S. worker. `STRONG` and `CONFIRMED` require separately reviewed evidence.

A missing record is never presented as proof that no layoff occurred. WARN publication practices and historical coverage vary by jurisdiction.

## Refresh

The feed refreshes every six hours with GitHub Actions and only commits when generated data changes.
