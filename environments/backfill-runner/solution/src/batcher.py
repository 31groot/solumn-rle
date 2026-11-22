"""Batch iteration and batched updates for backfill jobs."""
import sys
import time


def iter_batches(conn, table, columns, size, after=None):
    """Yield (rows, cursor) batches of `size` rows in id order (keyset pagination).

    Passing a yielded cursor back as `after` continues just after that batch."""
    cols = ", ".join(("id",) + tuple(columns))
    last_id = int(after or 0)
    while True:
        rows = conn.execute(
            f"SELECT {cols} FROM {table} WHERE id > ? ORDER BY id LIMIT ?", (last_id, size)
        ).fetchall()
        if not rows:
            return
        last_id = rows[-1]["id"]
        yield rows, str(last_id)


def apply_updates(conn, table, updates):
    """updates: list of (id, {column: value}); all dicts in one call share the same columns."""
    if not updates:
        return 0
    cols = list(updates[0][1])
    sets = ", ".join(f"{c} = ?" for c in cols)
    conn.executemany(f"UPDATE {table} SET {sets} WHERE id = ?",
                     [tuple(values[c] for c in cols) + (row_id,) for row_id, values in updates])
    return len(updates)


def run(conn, table, columns, transform, size=500, after=None, initial=0, on_progress=None, log_every=20):
    """Transform rows of `table` (all of them, or those after cursor `after`) and write the results back,
    one transaction per batch. on_progress(rows_done, cursor) runs inside each batch's transaction."""
    total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    done, t0 = initial, time.monotonic()
    for n, (rows, cursor) in enumerate(iter_batches(conn, table, columns, size, after), 1):
        with conn:
            done += apply_updates(conn, table, [(r["id"], transform(r)) for r in rows])
            if on_progress:
                on_progress(done, cursor)
        if n % log_every == 0 or done == total:
            print(f"{table}: {done}/{total} rows ({time.monotonic() - t0:.1f}s)", file=sys.stderr, flush=True)
    return done
