"""HTTP regression checks for the Cloudflare Pages clean-URL loop."""

import contextlib
import http.client
import io
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
from unittest.mock import patch

import check_brand
import preview


class RoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = preview.ThreadingHTTPServer(("127.0.0.1", 0), preview.PreviewHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, path, method="GET"):
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=5)
        try:
            connection.request(method, path)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_clean_urls_serve_correct_documents_without_redirects(self):
        for route, filename in [("/", "index.html"), ("/privacy", "index.html"),
                                ("/delete-account", "delete-account.html")]:
            expected = (preview.SITE_ROOT / filename).read_bytes()
            for method in ["GET", "HEAD"]:
                with self.subTest(route=route, method=method):
                    status, headers, body = self.request(route, method)
                    self.assertEqual(status, 200)
                    self.assertNotIn("Location", headers)
                    self.assertEqual(body, expected if method == "GET" else b"")

    def test_query_does_not_change_clean_url_document(self):
        status, headers, body = self.request("/delete-account?source=privacy")
        self.assertEqual(status, 200)
        self.assertNotIn("Location", headers)
        self.assertEqual(body, (preview.SITE_ROOT / "delete-account.html").read_bytes())

    def test_html_alias_redirects_once_to_working_clean_url(self):
        for method in ["GET", "HEAD"]:
            with self.subTest(method=method):
                status, headers, _ = self.request("/delete-account.html?source=privacy", method)
                self.assertEqual(status, 307)
                self.assertEqual(headers["Location"], "/delete-account?source=privacy")
                status, headers, _ = self.request(headers["Location"], method)
                self.assertEqual(status, 200)
                self.assertNotIn("Location", headers)

    def test_static_assets_and_unknown_routes(self):
        status, _, body = self.request("/styles.css")
        self.assertEqual(status, 200)
        self.assertEqual(body, (preview.SITE_ROOT / "styles.css").read_bytes())
        status, _, body = self.request("/assets/fonts/InterVariable.woff2")
        self.assertEqual(status, 200)
        self.assertEqual(body[:4], b"wOF2")
        status, _, body = self.request("/favicon.ico")
        self.assertEqual(status, 200)
        self.assertEqual(body[:4], b"\x00\x00\x01\x00")
        for path in ["/no-such-page", "/no-such-page.html"]:
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)

    def test_previous_proxy_reproduces_self_redirect(self):
        # Demonstrate that the old rule is observable rather than silently
        # bypassed by a hardcoded local mapping.
        with patch.object(preview, "load_rewrites", return_value={
            "/delete-account": "/delete-account.html",
        }):
            status, headers, _ = self.request("/delete-account")
            self.assertEqual(status, 307)
            self.assertEqual(headers["Location"], "/delete-account")


class BrandRoutingGuardTests(unittest.TestCase):
    def test_checker_rejects_reintroduced_clean_url_proxy(self):
        with tempfile.TemporaryDirectory(prefix="numberinbox-routing-") as temporary:
            site = Path(temporary) / "site"
            shutil.copytree(check_brand.SITE_ROOT, site,
                            ignore=shutil.ignore_patterns(".git", "docs", "__pycache__"))
            with (site / "_redirects").open("a", encoding="utf-8") as redirects:
                redirects.write("/delete-account /delete-account.html 200\n")
            output = io.StringIO()
            with patch.object(check_brand, "SITE_ROOT", site), \
                 patch("sys.argv", ["check_brand.py"]), \
                 contextlib.redirect_stdout(output):
                self.assertEqual(check_brand.main(), 1)
            self.assertIn("Cloudflare clean-URL loop", output.getvalue())


if __name__ == "__main__":
    unittest.main()
