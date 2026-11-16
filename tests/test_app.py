import os
import tempfile
import unittest

os.environ["PILOT_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")

from streamlit.testing.v1 import AppTest  # noqa: E402

VIEWS = ["dashboard", "research", "quotes", "purchases", "products", "competition", "listings",
         "fba", "customer_orders", "treasury", "checklist"]


def _page(view):
    return (f"from pilot import db\nfrom pilot.views import {view}\n"
            f"db.init()\n{view}.render()\n")


class AppSmoke(unittest.TestCase):
    def test_main_app_runs(self):
        at = AppTest.from_file("../streamlit_app.py", default_timeout=30).run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(at.title[0].value, "Dashboard")

    def test_every_page_renders(self):
        for view in VIEWS:
            with self.subTest(view=view):
                at = AppTest.from_string(_page(view), default_timeout=30).run()
                self.assertFalse(at.exception, f"{view}: {at.exception}")

    def test_connections_page_unconfigured(self):
        def script():
            from pilot import connections, db
            db.init()
            connections.render()
        at = AppTest.from_function(script, default_timeout=30).run()
        self.assertFalse(at.exception, at.exception)


class ConnectionsConfigured(unittest.TestCase):
    def test_connections_with_credentials(self):
        from pilot import db
        keys = dict(AMAZON_LWA_CLIENT_ID="a", AMAZON_LWA_CLIENT_SECRET="b", AMAZON_REFRESH_TOKEN="c",
                    ALIBABA_APP_KEY="k", ALIBABA_APP_SECRET="s")
        os.environ.update(keys)
        try:
            db.init()
            db.set_secret("alibaba_tokens", {"access_token": "AT", "user_nick": "me"})

            def script():
                from pilot import connections
                connections.render()
            at = AppTest.from_function(script, default_timeout=30).run()
            self.assertFalse(at.exception, at.exception)
            labels = [b.label for b in at.button]
            self.assertIn("Test connection", labels)
            self.assertIn("Refresh access token", labels)
        finally:
            for k in keys:
                os.environ.pop(k, None)
            db.set_secret("alibaba_tokens", {})


if __name__ == "__main__":
    unittest.main()
