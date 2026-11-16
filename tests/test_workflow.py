import os
import sqlite3
import tempfile
import unittest
from unittest import mock

os.environ["PILOT_DB"] = os.path.join(tempfile.mkdtemp(), "wf.db")

from pilot import db, pipeline, seed  # noqa: E402
from pilot.integrations import mailer  # noqa: E402
from pilot.views import purchases, quotes  # noqa: E402


class Pipeline(unittest.TestCase):
    def test_stage_progression(self):
        s, o, li = [], [], []
        self.assertEqual(pipeline.stage(1, s, o, li), "Researched")
        self.assertEqual(pipeline.next_action(1, s, o, li)[1], "Product search")
        s = [{"product_id": 1, "status": "To contact"}]
        self.assertEqual(pipeline.next_action(1, s, o, li)[1], "Supplier quotes")
        s.append({"product_id": 1, "status": "Sent"})
        self.assertEqual(pipeline.stage(1, s, o, li), "Quotes requested")
        s.append({"product_id": 1, "status": "Quote received"})
        self.assertEqual(pipeline.stage(1, s, o, li), "Quotes received")
        s.append({"product_id": 1, "status": "Selected"})
        self.assertEqual(pipeline.stage(1, s, o, li), "Supplier selected")
        o = [{"product_id": 1, "status": "Awaiting payment"}]
        self.assertEqual(pipeline.next_action(1, s, o, li), ("Pay the order", "Purchases & payments"))
        o = [{"product_id": 1, "status": "At Amazon FC"}]
        self.assertEqual(pipeline.stage(1, s, o, li), "At Amazon")
        li = [{"product_id": 1, "status": "Published"}]
        self.assertEqual(pipeline.stage(1, s, o, li), "On sale")
        self.assertEqual(pipeline.stage(2, s, o, li), "Researched")  # other product unaffected

    def test_every_next_action_points_to_a_page(self):
        import streamlit_app  # noqa: F401  (registers page titles)
        from pilot import ui
        for _, page in pipeline.NEXT_ACTION.values():
            self.assertIn(page, ui.PAGES)


class Quotes(unittest.TestCase):
    def test_quote_economics_uses_supplier_shipping(self):
        p = seed.PRODUCTS[0]
        cheap = quotes.quote_economics(p, {"unit_price_usd": 2.0, "moq": 200}, seed.DEFAULT_SETTINGS)
        shipped = quotes.quote_economics(p, {"unit_price_usd": 2.0, "moq": 200, "shipping_usd": 254},
                                         seed.DEFAULT_SETTINGS)
        self.assertAlmostEqual(shipped.freight, 254 / 200 / 1.27)
        self.assertLess(shipped.profit, cheap.profit + (p["freight_per_unit"] - shipped.freight) + 1e-9)


class Purchases(unittest.TestCase):
    def test_status_mapping(self):
        m = purchases.map_alibaba_status
        self.assertEqual(m("unpay"), "Awaiting payment")
        self.assertEqual(m("wait_seller_send_goods"), "Paid")
        self.assertEqual(m("wait_buyer_receive_goods"), "Shipped")
        self.assertEqual(m("trade_close"), "Cancelled")
        self.assertIsNone(m(""))

    def test_find_url(self):
        self.assertEqual(purchases.find_url({"a": [{"b": "x"}, {"pay_url": "https://paypal.test/1"}]}),
                         "https://paypal.test/1")
        self.assertIsNone(purchases.find_url({"a": 1}))


class Mailer(unittest.TestCase):
    def test_not_configured(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GMAIL_ADDRESS", None)
            with self.assertRaises(mailer.MailError):
                mailer.send("a@b.com", "s", "b")

    def test_send_and_reject_bad_address(self):
        env = {"GMAIL_ADDRESS": "me@gmail.com", "GMAIL_APP_PASSWORD": "abcd efgh ijkl mnop"}
        with mock.patch.dict(os.environ, env), mock.patch("smtplib.SMTP_SSL") as smtp:
            mailer.send("sup@factory.cn", "Quote", "Hello", from_name="TASOH")
            conn = smtp.return_value.__enter__.return_value
            conn.login.assert_called_once_with("me@gmail.com", "abcdefghijklmnop")
            msg = conn.send_message.call_args[0][0]
            self.assertEqual(msg["To"], "sup@factory.cn")
            self.assertIn("TASOH", msg["From"])
            with self.assertRaises(mailer.MailError):
                mailer.send("a@b.com, evil@x.com", "s", "b")


class Migration(unittest.TestCase):
    def test_old_database_gets_new_columns(self):
        path = os.path.join(tempfile.mkdtemp(), "old.db")
        con = sqlite3.connect(path)
        con.execute("CREATE TABLE suppliers (id INTEGER PRIMARY KEY, product_id INTEGER, name TEXT, status TEXT)")
        con.execute("INSERT INTO suppliers VALUES (1, 1, 'Old supplier', 'Sent')")
        con.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, sale_price REAL)")
        con.execute("INSERT INTO products VALUES (1, 'Old product', 9.99)")
        con.commit()
        con.close()
        with mock.patch.object(db, "DB_PATH", __import__("pathlib").Path(path)):
            db.init()
            row = db.records("suppliers")[0]
        self.assertEqual(row["name"], "Old supplier")
        self.assertIn("email", row)
        self.assertIn("shipping_usd", row)


if __name__ == "__main__":
    unittest.main()
