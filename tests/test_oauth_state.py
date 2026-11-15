import os
import tempfile
import unittest
from unittest import mock

os.environ["PILOT_DB"] = os.path.join(tempfile.mkdtemp(), "oauth.db")

from pilot import db  # noqa: E402
from pilot.integrations import oauth_state  # noqa: E402


class OAuthState(unittest.TestCase):
    def setUp(self):
        db.init()
        oauth_state.clear()

    def test_nothing_pending_rejects(self):
        self.assertFalse(oauth_state.accept(""))
        self.assertFalse(oauth_state.accept("abc"))

    def test_matching_or_missing_state_accepted(self):
        s = oauth_state.start()
        self.assertEqual(oauth_state.start(), s)  # reused while recent
        self.assertTrue(oauth_state.accept(s))
        self.assertTrue(oauth_state.accept(""))   # Alibaba did not echo state
        self.assertFalse(oauth_state.accept("someone-else"))

    def test_expired_rejected(self):
        oauth_state.start()
        with mock.patch("pilot.integrations.oauth_state.time.time",
                        return_value=10**12):
            self.assertFalse(oauth_state.accept(""))

    def test_clear(self):
        oauth_state.start()
        oauth_state.clear()
        self.assertFalse(oauth_state.accept(""))


if __name__ == "__main__":
    unittest.main()
