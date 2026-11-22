#!/usr/bin/env python3
"""Sync the supplier product feed into the local catalogue store.

    python sync.py [--config config/settings.yaml]
"""
import argparse
import logging
import sys
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
    raise NotImplementedError("catalogue sync is not implemented yet")


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
