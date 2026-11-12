import os
import tempfile
import unittest

os.environ["PILOT_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")

from streamlit.testing.v1 import AppTest  # noqa: E402


class AppSmoke(unittest.TestCase):
    def test_runs_without_errors(self):
        at = AppTest.from_file("../streamlit_app.py", default_timeout=30).run()
        self.assertFalse(at.exception, at.exception)
        self.assertIn("Seller Control Center", at.title[0].value)
        self.assertGreaterEqual(len(at.tabs), 8)


if __name__ == "__main__":
    unittest.main()


class ConnectionsConfigured(unittest.TestCase):
    def test_connections_tab_with_credentials(self):
        from pilot import db
        os.environ.update(AMAZON_LWA_CLIENT_ID="a", AMAZON_LWA_CLIENT_SECRET="b",
                          AMAZON_REFRESH_TOKEN="c", ALIBABA_APP_KEY="k", ALIBABA_APP_SECRET="s")
        try:
            db.init()
            db.set_secret("alibaba_tokens", {"access_token": "AT", "user_nick": "me"})
            at = AppTest.from_file("../streamlit_app.py", default_timeout=30).run()
            self.assertFalse(at.exception, at.exception)
            labels = [b.label for b in at.button]
            self.assertIn("Test connection", labels)
            self.assertIn("Refresh access token", labels)
        finally:
            for k in ("AMAZON_LWA_CLIENT_ID", "AMAZON_LWA_CLIENT_SECRET", "AMAZON_REFRESH_TOKEN",
                      "ALIBABA_APP_KEY", "ALIBABA_APP_SECRET"):
                os.environ.pop(k, None)
