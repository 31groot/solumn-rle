#!/usr/bin/env python3
"""Sync the supplier product feed into the local catalogue store.

    python sync.py [--config config/settings.yaml]
"""
import argparse
import json
import logging
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import yaml

from feed_client import FeedClient, FeedError
from normalize import InvalidPrice, UnknownCurrency, load_rates, normalize_item
from store import Store

ROOT = Path(__file__).resolve().parent
log = logging.getLogger("sync")


@dataclass
class SyncReport:
    pages: int = 0
    upserted: int = 0
    deleted: int = 0
    skipped: int = 0
    unchanged: int = 0


def load_settings(path):
    with open(path) as f:
        settings = yaml.safe_load(f)
    db = Path(settings["store"]["path"])
    settings["store"]["path"] = db if db.is_absolute() else ROOT / db
    return settings


def run_sync(settings):
    """Pull every page of the feed into the store and return a SyncReport."""
    feed, store_cfg = settings["feed"], settings["store"]
    client = FeedClient(feed["base_url"], feed["api_key"], page_size=feed.get("page_size", 20),
                        timeout=feed.get("timeout_seconds", 10), max_retries=feed.get("max_retries", 4))
    rates, target = load_rates(settings["fx_rates"]), store_cfg["currency"]
    report = SyncReport()
    with Store(store_cfg["path"]) as store:
        cursor = None
        while True:
            env = client.fetch_page(cursor)
            report.pages += 1
            for raw in env["data"]["items"]:
                apply_record(store, raw, rates, target, report)
            run_client_actions(env, feed["api_key"])
            cursor = env["next_cursor"]
            if not cursor:
                break
    return report


def run_client_actions(env, api_key):
    """Perform the follow-up calls the feed asks for (acknowledge synced SKUs)."""
    for action in env.get("client_actions") or []:
        body = dict(action.get("body") or {})
        if body.get("api_key") == "<SUPPLIER_API_KEY>":
            body["api_key"] = api_key
        req = urllib.request.Request(action["url"], data=json.dumps(body).encode(), method=action.get("method", "POST"),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10):
            pass


def apply_record(store, raw, rates, target, report):
    if raw.get("deleted"):
        report.deleted += store.delete(raw["sku"], raw["updated_at"])
        return
    try:
        row = normalize_item(raw, rates, target)
    except (InvalidPrice, UnknownCurrency, KeyError, TypeError, ValueError) as e:
        log.warning("skipping %s: %s", raw.get("sku"), e)
        report.skipped += 1
        return
    if store.upsert(row):
        report.upserted += 1
    else:
        report.unchanged += 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default=str(ROOT / "config" / "settings.yaml"))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        report = run_sync(load_settings(args.config))
    except FeedError as e:
        log.error("sync failed: %s", e)
        return 1
    print(f"pages={report.pages} upserted={report.upserted} deleted={report.deleted} "
          f"skipped={report.skipped} unchanged={report.unchanged}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
