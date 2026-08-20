# Dfdata

Public read-only distribution feed for the Dalit Finder Android app.

This repository intentionally contains **only sanitized public output** needed by the free application. It must not contain collector code, ATS source configuration, historical job-posting observations, scoring internals, entity-resolution state, or other commercial/private data.

The Android application, collector, matching logic, Google Play Billing implementation, and accumulated private intelligence history live in the private `ryanbytes/Dalit-finder` repository.

## Public feed

- `feed/v1/companies.json` — sanitized company/event records used by the free app
- `feed/v1/companies.json.gz` — compressed copy
- `feed/v1/coverage.json` — 50 states + DC coverage/status metadata
- `feed/v1/stats.json` — public generation statistics

The public feed may expose basic facts such as company name, layoff event, approximate WARN location, evidence rating, affected-worker count when available, source links, and the existence/country of overlapping foreign activity. It must not expose the retained job-posting history or internal matching evidence that creates the paid research product.

## Evidence policy

Automated matching is capped at `POSSIBLE`. A U.S. WARN filing plus foreign job-posting activity is an overlap signal, not proof that a foreign job replaced a U.S. worker. `STRONG` and `CONFIRMED` require separately reviewed evidence.

A missing record is never presented as proof that no layoff occurred. WARN publication practices and historical coverage vary by jurisdiction.

## Publishing

`Dfdata` is a distribution target, not the collector. Sanitized exports are generated from private state in `ryanbytes/Dalit-finder/public-export/` and then published here. Never add private-history or collector directories to this repository.
