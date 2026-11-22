The catalogue sync job was never finished: `sync.py` still has an empty `run_sync`.

Please implement it. It should pull every page of the supplier product feed (connection
details are in `config/settings.yaml`, the API is described in `docs/feed_api.md`, and the
supplier's field mappings are in their onboarding email, `docs/supplier_onboarding.eml`),
normalize prices into the store currency with `normalize.py`, and write the results into the
SQLite store through `store.py`.

Done means: running `python sync.py` from the repo root leaves `data/catalog.db` matching the
current state of the feed, and running it again doesn't change anything. The supplier's
sandbox feed is running at the URL in the settings, so you can try it for real. Please
don't change the existing conversion behaviour in `normalize.py`; other jobs use it.
