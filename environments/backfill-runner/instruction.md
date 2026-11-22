Migration 0003 (`users_contact_columns`) is already applied to the accounts DB in `/app/data/app.db`,
but the backfill that populates the new columns was never written.

Please implement the `users` backfill transform in `/app/backfill.py` following the column rules in
`/app/README.md` (users_contact section), then run the backfill the way we run it in production,
`scripts/run_job.sh users_backfill`, so that the DB ends up fully migrated. Finish by confirming
`scripts/run_job.sh checks` passes.
