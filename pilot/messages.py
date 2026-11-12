"""Ready-to-send supplier messages. Nothing here sends anything: the user copies
the text into Alibaba's message centre themselves."""

from __future__ import annotations

TEMPLATES = {
    "Request for quotation": """Hello {contact},

I run an Amazon UK store ({store}) and I am looking for a supplier for:

  Product: {product} ({pack})
  First order: {qty} units, then regular reorders if quality is good
  Destination: United Kingdom (Amazon FBA)

Could you please send me:
  1. Unit price for {qty}, 500 and 1,000 units (EXW and FOB)
  2. MOQ and production lead time
  3. Available colours / options and custom logo or packaging cost
  4. Sample price and shipping cost to the UK
  5. Certificates you hold for the UK/EU market (UKCA/CE, EN71, RoHS...)

I prefer to pay via Alibaba Trade Assurance.

Thank you,
{signature}""",
    "Sample request": """Hello {contact},

Thank you for your quotation for {product}. Before placing an order of {qty} units,
I would like to order 1-2 samples shipped to the UK.

Please send a Trade Assurance order for the samples including express shipping,
and confirm the samples are identical to bulk production.

Best regards,
{signature}""",
    "Negotiation": """Hello {contact},

Thank you for the samples of {product}. Quality is good and I am ready to order {qty} units.

Your price is ${price:.2f}/unit. Other suppliers have quoted lower, so could you offer
${target:.2f}/unit for this first order? I plan to reorder every 6-8 weeks if sales go well.

Please also confirm: carton dimensions and weight, and that each unit will carry the
FNSKU barcode label I provide.

Best regards,
{signature}""",
    "Order follow-up": """Hello {contact},

Could you please send me an update on order for {product} ({qty} units):
production progress, photos of finished goods, and the expected ship date?

Thank you,
{signature}""",
}


def render(kind: str, *, product: dict, supplier: dict, settings: dict, signature: str) -> str:
    price = float(supplier.get("unit_price_usd") or product.get("unit_cost_usd") or 0)
    return TEMPLATES[kind].format(
        contact=supplier.get("contact") or "there",
        store=settings.get("store_name", ""),
        product=product.get("name", ""),
        pack=product.get("pack", ""),
        qty=int(supplier.get("moq") or product.get("first_order_qty") or 0),
        price=price,
        target=price * 0.9,
        signature=signature or settings.get("store_name", ""),
    )
