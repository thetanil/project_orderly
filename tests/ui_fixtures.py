"""Browser fixtures (plugin of tests/conftest.py)

Browser tests: the built frontend, driven by headless Chromium, talking to the real Api.

pywebview's `js_api` is replaced by a tiny HTTP shim that forwards every call to the same `Api`
object the desktop window uses, so these tests exercise the real UI code and the real backend
without starting a window. They need `playwright` and a built frontend (`npm run build`); locally
they skip when either is missing, in CI (CI=true) a missing prerequisite is a failure.
"""
import json
import os
import shutil
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from project_orderly.api import open_store

UI = Path(__file__).resolve().parents[1] / "src" / "project_orderly" / "ui" / "index.html"
SHIM = """<script>
window.pywebview = {api: new Proxy({}, {get: (_, name) => async (...args) => {
  const r = await fetch('/api/' + name, {method: 'POST', body: JSON.stringify(args)});
  return await r.json();
}})};
setTimeout(() => window.dispatchEvent(new Event('pywebviewready')), 50);
</script>"""


def _missing(why):
    if os.environ.get("CI"):
        pytest.fail(why)
    pytest.skip(why)


def serve(api):
    html = UI.read_text().replace("<head>", "<head>" + SHIM, 1).encode()

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(html)

        def do_POST(self):
            name = self.path.rsplit("/", 1)[1]
            args = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or "[]")
            out = json.dumps(getattr(api, name)(*args)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(out)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


@pytest.fixture(scope="session")
def browser():
    if not UI.exists():
        _missing("frontend is not built (cd frontend && npm ci && npm run build)")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        _missing("playwright is not installed")
    with sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception:
            exe = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
            if not exe:
                _missing("no Chromium available (playwright install chromium)")
            b = p.chromium.launch(executable_path=exe, args=["--no-sandbox"])
        yield b
        b.close()


@pytest.fixture
def ui(browser, backlog):
    """open(api=None, width=1300, height=800) -> (page, api); fails the test on any page error."""
    opened = []

    def open_page(api=None, width=1300, height=800, wait=True):
        api = api or open_store(str(backlog))
        srv = serve(api)
        page = browser.new_page(viewport={"width": width, "height": height})
        page.set_default_timeout(8000)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        opened.append((srv, page, errors))
        page.goto(f"http://127.0.0.1:{srv.server_address[1]}/")
        if wait:
            page.wait_for_selector(".row")
        return page, api

    yield open_page
    for srv, page, errors in opened:
        page.close()
        srv.shutdown()
        assert not errors, errors
