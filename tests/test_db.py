import os
import tempfile
import unittest

os.environ["PILOT_DB"] = os.path.join(tempfile.mkdtemp(), "db.db")

import pandas as pd  # noqa: E402

from pilot import db  # noqa: E402


class DbRoundTrip(unittest.TestCase):
    def test_seed_edit_and_new_rows(self):
        db.init(force_seed=True)
        self.assertEqual(len(db.records("products")), 5)
        self.assertEqual(len(db.read("checklist")), 27)
        orders = db.read("orders")
        new = pd.DataFrame([{"id": None, "product_id": 1, "qty": 200, "unit_price_usd": 2.4,
                             "status": "Draft", "order_date": "2026-11-12"}])
        db.write("orders", pd.concat([orders, new]))
        got = db.records("orders")
        self.assertEqual(len(got), 1)
        self.assertIsNotNone(got[0]["id"])
        snap = db.snapshot()
        db.init(force_seed=True)
        db.load_snapshot(snap)
        self.assertEqual(len(db.records("orders")), 1)

    def test_delete_product_cascades(self):
        db.init(force_seed=True)
        db.delete("products", 1)
        self.assertFalse((db.read("suppliers")["product_id"] == 1).any())


if __name__ == "__main__":
    unittest.main()
