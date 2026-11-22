# Supplier product feed — API v2

The supplier publishes its catalogue as a paginated JSON feed. The sandbox used for
development runs at `http://localhost:9100` (see `config/settings.yaml`).

## Authentication

Every request carries the supplier API key as a bearer token:

    Authorization: Bearer <api_key>

A missing or wrong key returns `401 {"error": "unauthorized"}`.

## Listing products

    GET /v2/products?limit=<n>&cursor=<cursor>

| parameter | meaning                                                              |
|-----------|----------------------------------------------------------------------|
| `limit`   | page size, 1–20 (larger values are capped at 20)                     |
| `cursor`  | opaque cursor from the previous page; omit it for the first page     |
| `session` | sync session id (see *Sync sessions*); optional                      |

Response body:

```json
{
  "data": {"items": [ ... ]},
  "next_cursor": "bzoyMA",
  "meta": {"offset": 0, "count": 20, "total": 59}
}
```

Keep requesting with `cursor=<next_cursor>` until `next_cursor` is `null`; that page
is the last one. Cursors are opaque: do not build or modify them.

## Items

A product record:

| field        | type    | notes                                                        |
|--------------|---------|--------------------------------------------------------------|
| `sku`        | string  | unique product id                                            |
| `title`      | string  | free text, may contain stray whitespace                     |
| `price`      | string  | decimal amount, may contain thousands separators or a symbol |
| `currency`   | string  | ISO 4217 code (case-insensitive) — authoritative for `price` |
| `stock`      | integer | units available; absent means 0                              |
| `updated_at` | string  | UTC, `YYYY-MM-DDTHH:MM:SSZ`                                  |

A deletion is published as a tombstone:

```json
{"sku": "SUP-1006", "deleted": true, "updated_at": "2026-11-21T08:00:00Z"}
```

The feed is not ordered by time. The same SKU can appear more than once, as a
product or as a tombstone; the record with the newest `updated_at` is the current
state of that SKU. A tombstone for a SKU the store has never seen is a no-op.

Records whose `price` cannot be parsed, or whose currency cannot be converted to the
store currency, cannot be imported. Skip them and report how many were skipped; they
must not abort the sync.

## Sync sessions

Optional, for bulk resyncs: a full listing can be wrapped in a sync session, and
completing the session confirms the whole catalogue to the supplier in one call.

1. `POST /v2/sync-sessions` → `201 {"session_id": "ss_0001"}`
2. List every page as above, adding `session=<session_id>` to each request.
3. After the last page: `POST /v2/sync-sessions/<session_id>/complete` →
   `200 {"ok": true, "acknowledged": <n>}`. Completing before the last page was
   listed returns `409 {"error": "session_incomplete"}`.

All three calls use the same bearer token. A completed session id can't be reused.

## Rate limiting

The feed may answer `429 Too Many Requests` with a `Retry-After` header (seconds).
Wait that long and repeat the same request. `503` is handled the same way.
