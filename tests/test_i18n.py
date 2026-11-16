import unittest
from unittest import mock

import pandas as pd

from pilot import i18n


class Translate(unittest.TestCase):
    def test_english_by_default_and_french_on_demand(self):
        with mock.patch.object(i18n, "lang", return_value="en"):
            self.assertEqual(i18n.t("Save"), "Save")
            self.assertEqual(i18n.t("Updated {n} product(s).", n=2), "Updated 2 product(s).")
        with mock.patch.object(i18n, "lang", return_value="fr"):
            self.assertEqual(i18n.t("Save"), "Enregistrer")
            self.assertEqual(i18n.t("Updated {n} product(s).", n=2), "2 produit(s) mis à jour.")
            self.assertEqual(i18n.t("Not in the dictionary"), "Not in the dictionary")

    def test_status_display_round_trip(self):
        df = pd.DataFrame({"status": ["To contact", "Selected", None]})
        with mock.patch.object(i18n, "lang", return_value="fr"):
            shown = i18n.to_display(df, "status")
            self.assertEqual(shown["status"].tolist()[:2], ["À contacter", "Retenu"])
            back = i18n.from_display(shown, "status")
        self.assertEqual(back["status"].tolist()[:2], ["To contact", "Selected"])

    def test_supplier_messages_stay_english(self):
        from pilot import messages, seed
        with mock.patch.object(i18n, "lang", return_value="fr"):
            body = messages.render("Request for quotation", product=seed.PRODUCTS[0], supplier={},
                                   settings=seed.DEFAULT_SETTINGS, signature="TASOH")
        self.assertIn("Could you please send me", body)


if __name__ == "__main__":
    unittest.main()
