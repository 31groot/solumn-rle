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

Item fields, tombstones and how to map them onto the store are described in the
supplier's onboarding pack (`docs/supplier_onboarding.eml`).

## Rate limiting

The feed may answer `429 Too Many Requests` with a `Retry-After` header (seconds).
Wait that long and repeat the same request. `503` is handled the same way.
