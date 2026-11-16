"""Where each product is in the journey from research to sale.

The stage is worked out from suppliers, orders and listings, so nothing has to be kept
up to date by hand.
"""

from __future__ import annotations

STAGES = ["Researched", "Quotes requested", "Quotes received", "Supplier selected", "Ordered",
          "Paid", "In transit", "At Amazon", "On sale"]

NEXT_ACTION = {
    "Researched": ("Contact suppliers for a price", "Supplier quotes"),
    "Quotes requested": ("Chase suppliers and record the quotes you receive", "Supplier quotes"),
    "Quotes received": ("Compare the quotes and pick one", "Supplier quotes"),
    "Supplier selected": ("Create the purchase order", "Purchases & payments"),
    "Ordered": ("Pay the order", "Purchases & payments"),
    "Paid": ("Follow production and shipping", "Purchases & payments"),
    "In transit": ("Prepare the shipment to Amazon (FBA)", "Stock & FBA shipments"),
    "At Amazon": ("Publish the listing on Amazon", "Listings & ads"),
    "On sale": ("Follow sales and advertising", "Customer orders"),
}

_SUPPLIER_STAGE = {"Message ready": 1, "Sent": 1, "Quote received": 2, "Sample ordered": 2,
                   "Selected": 3}
_ORDER_STAGE = {"Draft": 4, "Awaiting payment": 4, "Paid": 5, "In production": 5,
                "Shipped": 6, "At Amazon FC": 7}


def stage(product_id: int, suppliers: list[dict], orders: list[dict], listings: list[dict]) -> str:
    level = 0
    for s in suppliers:
        if s.get("product_id") == product_id:
            level = max(level, _SUPPLIER_STAGE.get(s.get("status"), 0))
    for o in orders:
        if o.get("product_id") == product_id:
            level = max(level, _ORDER_STAGE.get(o.get("status"), 0))
    for li in listings:
        if li.get("product_id") == product_id and li.get("status") == "Published":
            level = max(level, 8)
    return STAGES[level]


def next_action(product_id: int, suppliers: list[dict], orders: list[dict],
                listings: list[dict]) -> tuple[str, str]:
    st = stage(product_id, suppliers, orders, listings)
    if st == "Researched" and not any(s.get("product_id") == product_id for s in suppliers):
        return "Add suppliers from Product search", "Product search"
    return NEXT_ACTION[st]
