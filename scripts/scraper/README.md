# MAIS scraper (T-001)

Standalone Python 3.10+ crawler for public MAIS study plans and course sheets.
Run commands from the repository root. No backend, database, or login is needed.

```sh
python -m venv .venv
# Windows PowerShell:
.venv/Scripts/python.exe -m pip install -r scripts/scraper/requirements.txt
.venv/Scripts/python.exe -X utf8 scripts/scraper/scrape.py
.venv/Scripts/python.exe -X utf8 scripts/scraper/scrape.py --parse-only
.venv/Scripts/python.exe -m pytest scripts/scraper/tests -q
.venv/Scripts/python.exe -X utf8 scripts/scraper/verify.py
```

On Linux/macOS use `.venv/bin/python` instead. On this Windows workstation the
system `python` points to a broken installation; create the environment using a
working Python installation explicitly if necessary.

## Options

- `--year 2026/2027`: academic year (resolved from the live portal select).
- `--faculty FEI`: faculty abbreviation or numeric portal ID.
- `--degree PRVY PRVY_PROFES_ORIENTOVANY DRUHY`: one or more portal degree values.
- `--form DENNA`: one or more portal form values, for example `EXTERNA`.
- `--out data/mais/2026-27`: output directory; default derived from the year.
- `--cache .cache/mais`: raw HTML and download timestamp sidecars, separated by
  year and faculty. Keep this directory to resume an interrupted run.
- `--parse-only`: requires an existing program index, plans, sheets and timestamp
  sidecars; never creates an HTTP client or uses the network.

Use a separate `--out` when exploring a different faculty or scope. Each run
replaces `programs.json`, `manifest.json` and the generated numeric course files
in its output directory. Failed sheets are excluded and recorded in the manifest;
any failure gives exit status 1.

## Network and cache

One HTTP session, sequential requests only, at least 1.05 seconds between request
starts, including redirect requests. Each request has a 60-second timeout and at
most three retries, with 2/4/8-second backoff. Responses are explicitly decoded
as UTF-8. Successful pages and their original UTC download timestamps are cached.
An interrupted download without a sidecar is fetched again. To refresh an existing
snapshot, choose a new cache directory. Re-parsing does not refresh timestamps.

A full cold run needs hundreds of course requests, usually two HTTP requests per
sheet because of redirects: allow roughly 25–45 minutes, longer if MAIS is slow
or requests require retries. A warm-cache re-parse takes seconds to tens of seconds.
Measured duration of the delivered run is recorded in the task report.

## Parsing and coverage

`sections` retains every bold colon-terminated label, including unknown and empty
labels, in DOM order. Bold values without a colon remain values. Explicit HTML
line breaks and block boundaries become newlines; whitespace inside each line is
collapsed. The entire sheet table is also independently rendered as `full_text`
(excluding its fixed title). Coverage compares Unicode word tokens (`\w+`) from
all section labels and values with `full_text`, in order. Missing, added or
reordered words reject the sheet. Punctuation is preserved in stored text but is
not treated as a word by this check.

Recommended-semester cells containing multiple programs are expanded into one
record per program with aligned degree and method. Tables remain in section text.
Unparseable convenience values are null; the source text remains available.

Study-plan rows preserve source order, including `Prerekvizita` and `Zameniteľný`
rows. Their source type is retained; merged type cells have empty profile/hours
values. State-exam rows have null period/hours and retain the faculty column.
These linked historical/alternative sheets increase totals beyond the regular
course count. All `V období od …` rules are retained, including registration rules.

Raw HTML is ignored by git except for the public regression fixtures in `tests/`.
The committed JSON is official source data, not generated/seeded sample content.
