import unittest

from pilot import calc, seed

EXPECTED = {  # product id -> (profit/unit, margin %, band, first-order cash) from the PDF
    1: (1.64, 13.7, "Thin", 489.74),
    2: (1.73, 19.2, "Thin", 243.13),
    3: (2.19, 14.6, "Thin", 285.36),
    4: (3.03, 23.3, "Solid", 184.62),
    5: (1.52, 7.6, "Too low", 181.05),
}


class SeedMatchesWorksheet(unittest.TestCase):
    def test_seed_reproduces_pdf(self):
        for p in seed.PRODUCTS:
            e = calc.unit_economics(p, seed.DEFAULT_SETTINGS)
            profit, margin, band, cash = EXPECTED[p["id"]]
            self.assertAlmostEqual(e.profit, profit, delta=0.006, msg=p["name"])
            self.assertAlmostEqual(e.margin * 100, margin, delta=0.06, msg=p["name"])
            self.assertEqual(e.band, band)
            self.assertAlmostEqual(e.first_order_cash, cash, delta=1.0, msg=p["name"])

    def test_price_for_margin(self):
        p = seed.PRODUCTS[0]
        price = calc.price_for_margin(p, seed.DEFAULT_SETTINGS, 0.20)
        self.assertAlmostEqual(calc.unit_economics({**p, "sale_price": price},
                                                   seed.DEFAULT_SETTINGS).margin, 0.20, delta=0.002)

    def test_not_vat_registered_raises_profit(self):
        p = seed.PRODUCTS[0]
        a = calc.unit_economics(p, seed.DEFAULT_SETTINGS)
        b = calc.unit_economics(p, {**seed.DEFAULT_SETTINGS, "vat_registered": False})
        self.assertGreater(b.profit, a.profit)

    def test_ads_forecast(self):
        f = calc.ads_forecast(10, 0.5, 0.1, 20)
        self.assertEqual(f["clicks"], 20)
        self.assertAlmostEqual(f["acos"], 0.25)


if __name__ == "__main__":
    unittest.main()
