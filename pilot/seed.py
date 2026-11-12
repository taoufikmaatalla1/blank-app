"""Starting data, based on the 'Poste de pilotage Amazon UK' worksheet.

Every number is an editable assumption, not a quote from a supplier.
"""

from __future__ import annotations

DEFAULT_SETTINGS = {
    "store_name": "TASOH",
    "marketplace": "amazon.co.uk",
    "account_status": "Active, limited access",
    "currency": "GBP",
    "usd_per_gbp": 1.27,
    "vat_registered": True,
    "vat_rate": 0.20,
    "next_step_override": "",
}

_COMMON = {"referral_pct": 0.15, "duty_pct": 0.04, "ads_pct": 0.10, "freight_per_unit": 0.35,
           "other_per_unit": 0.10, "first_order_fixed": 30.0}

PRODUCTS = [
    {"id": 1, "name": "Phone & tablet stands", "pack": "Pack of 3", "sale_price": 11.99,
     "unit_cost_usd": 2.38, "fba_fee": 2.955, "first_order_qty": 200},
    {"id": 2, "name": "Silicone cable organisers", "pack": "Pack of 12", "sale_price": 8.99,
     "unit_cost_usd": 0.87, "fba_fee": 2.355, "first_order_qty": 200},
    {"id": 3, "name": "Precision screwdriver set", "pack": "115-in-1 kit", "sale_price": 14.99,
     "unit_cost_usd": 2.69, "fba_fee": 3.90, "first_order_qty": 100},
    {"id": 4, "name": "Christmas: felt tree for kids", "pack": "Single (decorate-it kit)",
     "sale_price": 12.99, "unit_cost_usd": 1.46, "fba_fee": 2.90, "first_order_qty": 100},
    {"id": 5, "name": "Christmas: shatterproof baubles", "pack": "Pack of 24 (4 boxes of 6)",
     "sale_price": 19.99, "unit_cost_usd": 6.95, "fba_fee": 4.00, "first_order_qty": 25},
]
for _p in PRODUCTS:
    for _k, _v in _COMMON.items():
        _p.setdefault(_k, _v)
    _p.update({"asin": "", "sku": "", "notes": ""})

_SEARCH_HINTS = {
    1: "adjustable aluminium phone tablet stand desk",
    2: "silicone cable ties organiser reusable",
    3: "precision screwdriver set 115 in 1 magnetic",
    4: "felt christmas tree kids detachable ornaments",
    5: "shatterproof christmas baubles set 24",
}

SUPPLIERS = []
_sid = 1
for _p in PRODUCTS:
    for n in (1, 2, 3, 4):
        SUPPLIERS.append({
            "id": _sid, "product_id": _p["id"],
            "name": f"Supplier {n} – {_p['name'].split(': ')[-1].lower()} (placeholder)",
            "url": "", "contact": "",
            "status": "Sent" if (_p["id"] == 1 and n == 1) else "To contact",
            "unit_price_usd": _p["unit_cost_usd"], "moq": _p["first_order_qty"],
            "lead_time_days": None, "trade_assurance": 1, "years_on_alibaba": None,
            "rating": None, "notes": f"Alibaba search: {_SEARCH_HINTS[_p['id']]}",
        })
        _sid += 1

CHECKLIST = [
    ("Account", "Create Amazon Seller Central account (amazon.co.uk)", 1),
    ("Account", "Choose store name", 1),
    ("Account", "Add payment method in Seller Central (Charge Method)", 0),
    ("Account", "Complete identity verification", 0),
    ("Account", "Add bank account for disbursements", 0),
    ("Account", "Set up VAT / tax information", 0),
    ("Product research", "Shortlist products and check margins", 1),
    ("Product research", "Compare competitor prices, reviews and BSR on Amazon", 0),
    ("Product research", "Check category restrictions and approvals", 0),
    ("Sourcing", "Contact at least 3 Alibaba suppliers per product", 0),
    ("Sourcing", "Collect quotes (unit price, MOQ, lead time)", 0),
    ("Sourcing", "Order samples and compare quality", 0),
    ("Sourcing", "Choose supplier and negotiate terms", 0),
    ("Sourcing", "Pay first order via Trade Assurance", 0),
    ("Shipping & compliance", "Get GTIN / barcodes (or GTIN exemption)", 0),
    ("Shipping & compliance", "Check UKCA/CE, toy safety (EN71) and labelling", 0),
    ("Shipping & compliance", "Book freight forwarder and customs (EORI number)", 0),
    ("Shipping & compliance", "Prepare FNSKU labels and carton labels", 0),
    ("Shipping & compliance", "Create FBA inbound shipment plan", 0),
    ("Listing", "Write titles, bullet points and description", 0),
    ("Listing", "Product photos (main white background + lifestyle)", 0),
    ("Listing", "Backend search terms", 0),
    ("Listing", "Publish listings and check they are buyable", 0),
    ("Launch", "Create Sponsored Products campaigns", 0),
    ("Launch", "Enrol in Amazon Vine / request reviews", 0),
    ("Launch", "Set reorder point and safety stock", 0),
    ("Launch", "Review results after 14 days and adjust price/ads", 0),
]


def snapshot() -> dict:
    return {
        "settings": DEFAULT_SETTINGS,
        "products": PRODUCTS,
        "suppliers": SUPPLIERS,
        "competitors": [],
        "orders": [],
        "listings": [
            {"id": p["id"], "product_id": p["id"], "title": "", "bullets": "", "description": "",
             "search_terms": "", "status": "Draft"} for p in PRODUCTS
        ],
        "ads": [
            {"id": p["id"], "product_id": p["id"], "campaign": f"SP - {p['name']} - Auto",
             "daily_budget": 5.0, "cpc": 0.45, "conversion_rate": 0.10, "keywords": "",
             "status": "Planned"} for p in PRODUCTS
        ],
        "checklist": [
            {"id": i + 1, "phase": ph, "step": st, "done": d, "sort": i + 1}
            for i, (ph, st, d) in enumerate(CHECKLIST)
        ],
    }
