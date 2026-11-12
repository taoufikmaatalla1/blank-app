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
        self.assertEqual(len(at.tabs), 7)


if __name__ == "__main__":
    unittest.main()
