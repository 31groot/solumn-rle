# accounts-db backfills

Schema migrations and data backfills for the accounts SQLite database (`data/app.db`).

| file | what it does |
|---|---|
| `db.py` | connection helper, schema, fixture generator |
| `migrate.py` | schema migrations, recorded in `schema_migrations` |
| `batcher.py` | batch iteration + batched `UPDATE`s used by every backfill |
| `backfill.py` | backfill jobs (`python3 backfill.py <job>`), progress in `backfill_runs` |
| `checks.py` | post-backfill data checks (exit 0 = pass) |
| `scripts/run_job.sh` | job runner used in production |
| `ops/jobs.toml` | job definitions for the runner |

## Running jobs

Production jobs are started with `scripts/run_job.sh <job>` (job names are in `ops/jobs.toml`).
The runner applies the job's `max_runtime`, sets `JOB_RUN_ID` and reports the run to the ops
scheduler API. Job output goes to stderr.

```
scripts/run_job.sh migrate
scripts/run_job.sh users_backfill
scripts/run_job.sh checks
```

Backfills are idempotent, so a failed run can simply be re-run.

## users_contact backfill (migration 0003)

Migration `0003_users_contact_columns` adds four columns to `users`. The `users` backfill fills
them from the legacy columns, which must not be modified.

**email_normalized** — `email` with surrounding whitespace removed, lower-cased. For the domains
`gmail.com` and `googlemail.com` the domain becomes `gmail.com` and the local part drops
everything from the first `+` and all `.` characters (`A.Sharma+news@GoogleMail.com` →
`asharma@gmail.com`). Other domains keep their local part as is (lower-cased).

**first_name / last_name** — `full_name` with runs of whitespace collapsed and trimmed. Empty →
both `''`. One word → `first_name` = the word, `last_name` = `''`. Otherwise `last_name` is the
last word and `first_name` is everything before it (`Asha M. Sharma` → `Asha M.` / `Sharma`).
Case is kept as given.

**phone_e164** — take the digits of `phone`. The calling code comes from `country`
(IN 91, US 1, GB 44). If the digits start with the calling code followed by exactly 10 digits, the
national number is those 10 digits; otherwise, if they are 11 digits starting with a trunk `0`,
drop the `0`; otherwise the digits are the national number. A 10-digit national number gives
`+<code><national>`; anything else, or a missing phone, gives `NULL`.

## Checks

`checks.py` verifies the row count and the legacy columns against `seed_meta`, that the latest
`users` backfill run is complete and covers every row, and that the new columns are well formed.
