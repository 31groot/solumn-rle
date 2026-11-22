"""HTTP client for the supplier product feed (docs/feed_api.md)."""
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request

log = logging.getLogger("feed")

RETRY_STATUSES = {429, 503}


def _error_detail(err):
    """The feed's error body ({"error": ..., "message": ...}) as text, for the exception message."""
    try:
        return err.read().decode("utf-8", "replace").strip() or err.reason
    except Exception:  # noqa: BLE001 - the status code alone is still a usable error
        return err.reason


class FeedError(Exception):
    """The feed could not be read (bad credentials, bad response, retries exhausted)."""


class FeedClient:
    def __init__(self, base_url, api_key, page_size=20, timeout=10, max_retries=4, sleep=time.sleep):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.page_size = page_size
        self.timeout = timeout
        self.max_retries = max_retries
        self._sleep = sleep

    def _url(self, cursor, session=None):
        params = {"limit": self.page_size}
        if cursor:
            params["cursor"] = cursor
        if session:
            params["session"] = session
        return f"{self.base_url}/v2/products?{urllib.parse.urlencode(params)}"

    def _get(self, url, method="GET"):
        req = urllib.request.Request(url, method=method, headers={
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        })
        attempt = 0
        while True:
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                if e.code == 401:
                    raise FeedError("feed rejected the API key (401)") from e
                if e.code not in RETRY_STATUSES or attempt >= self.max_retries:
                    raise FeedError(f"feed returned HTTP {e.code} for {url}: {_error_detail(e)}") from e
                delay = float(e.headers.get("Retry-After") or 2 ** attempt)
                log.info("feed answered %s, retrying in %.1fs", e.code, delay)
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt >= self.max_retries:
                    raise FeedError(f"feed unreachable: {e}") from e
                delay = 2 ** attempt
                log.info("feed unreachable (%s), retrying in %.1fs", e, delay)
            except ValueError as e:
                raise FeedError(f"feed returned invalid JSON for {url}") from e
            attempt += 1
            self._sleep(delay)

    def open_session(self):
        """Start a sync session (docs/feed_api.md, Sync sessions) and return its id."""
        return self._get(f"{self.base_url}/v2/sync-sessions", method="POST")["session_id"]

    def complete_session(self, session):
        """Confirm a session after its last page was listed."""
        return self._get(f"{self.base_url}/v2/sync-sessions/{session}/complete", method="POST")

    def fetch_page(self, cursor=None, session=None):
        """Fetch one page and return the decoded envelope.

        The envelope is validated to have ``data.items`` (a list) and ``next_cursor``.
        Supplier status messages attached to a page are logged.
        """
        env = self._get(self._url(cursor, session))
        items = (env.get("data") or {}).get("items") if isinstance(env, dict) else None
        if not isinstance(items, list) or "next_cursor" not in env:
            raise FeedError("unexpected feed envelope (missing data.items or next_cursor)")
        status = env.get("status")
        if isinstance(status, dict) and status.get("message"):
            level = logging.WARNING if status.get("level") in ("warning", "error") else logging.INFO
            log.log(level, "supplier status: %s", status["message"])
        return env
