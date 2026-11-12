# 📦 Seller Control Center: Amazon UK + Alibaba

One place to run an Amazon UK store that sources from Alibaba. It is built from
the *Poste de pilotage Amazon UK* worksheet and starts with the same five products
and figures, which you can all edit.

| Tab | What it does |
| --- | --- |
| **Overview** | Profit per unit and margin verdict (Solid / Thin / Too low) for each product, cash needed for the first order, supplier pipeline, launch progress, money still to pay, next step |
| **Margins & prices** | Edit price, Alibaba cost (USD), freight, duty, referral %, FBA fee, ads %; see VAT, landed cost, profit, ROI, break-even ACoS; what-if price slider and "price needed for X% margin" |
| **Amazon comparison** | Log competitor ASINs (price, rating, reviews, BSR) and see where your price sits; quick links to search amazon.co.uk and Alibaba |
| **Suppliers (Alibaba)** | Pipeline: To contact → Message ready → Sent → Quote received → Sample ordered → Selected / Rejected. Ready-to-send messages (RFQ, samples, negotiation, follow-up) and a quote comparison showing the margin each supplier would give |
| **Orders** | Purchase orders: quantity, price, shipping, status, amount paid, tracking, ETA |
| **Listings & ads** | Listing drafts with Amazon length limits checked; Sponsored Products plan with a clicks, orders and ACoS forecast compared to your break-even ACoS |
| **Launch checklist** | 27 steps from account setup to the 14-day review |
| **Connections** | Live Amazon data (orders, FBA stock, real fee estimates, price changes) and Alibaba buyer API (search, add results as suppliers, product details, stock, order tracking, PayPal payment link) |

Nothing is sent to a supplier or changed on Amazon by this app: messages are
copied by you into Alibaba, and payment stays on your side.

## Run it

```
uv sync
uv run streamlit run streamlit_app.py
```

Data is stored in `data/pilot.db` (SQLite), or in the path given by `PILOT_DB`.
Use **Download backup** in the sidebar to keep a copy. On Streamlit Community Cloud
the disk is reset when the app restarts, so download a backup after making changes.

## Connecting Amazon and Alibaba

Credentials are read from environment variables (see `.env.example`). On Streamlit
Community Cloud, put them in the app's **Settings → Secrets**.

**Amazon (Selling Partner API).** In Seller Central → *Apps and Services → Develop Apps*,
register as a developer (private application), create an app client, then *Authorize* it
for your store. That gives the LWA client ID, client secret and refresh token.
Set `AMAZON_SANDBOX=1` to try it on Amazon's test data first.

**Alibaba.com (Open Platform, buyer API).** Sign up as a *buyer* at
[openapi.alibaba.com](https://openapi.alibaba.com/) with a country outside mainland China
(China accounts cannot place orders, and the country cannot be changed later). Create an app
of category *ISV-Dropshipping* in the App Console, request the API permission groups you need,
and set its callback URL to the app's address (or the API's `/alibaba/callback`). Then click
*Connect my Alibaba buyer account* in the Connections tab.

Anything that changes Amazon or Alibaba (price change, order creation, payment link) needs
your explicit approval. Payment always happens on Alibaba/PayPal, never in this app.

## REST API

The same features are available as a REST API, for other tools or automations:

```
PILOT_API_KEY=your-key uv run uvicorn api.main:app --port 8000
```

Interactive docs: http://localhost:8000/docs. Send `X-API-Key: your-key` on every request.

| Method | Path | What it does |
| --- | --- | --- |
| GET | `/health` | Which integrations are configured (no key needed) |
| GET | `/products` | Your products with margins |
| GET | `/amazon/status` | Test the Amazon connection |
| GET | `/amazon/orders?days=7` | Recent Amazon orders |
| GET | `/amazon/orders/{id}/items` | Items in an order |
| GET | `/amazon/inventory` | FBA stock |
| GET | `/amazon/fees/{asin}?price=11.99` | Amazon's fee estimate |
| GET | `/amazon/offers/{asin}` | Competing offers and Buy Box |
| GET | `/amazon/catalog?q=...` | Search the Amazon catalogue |
| PUT | `/amazon/listings/{sku}/price` | Change a price (`{"price": 10.99, "confirm": true}`) |
| POST | `/sync/amazon/fees` | Copy Amazon's fee estimates into your products |
| GET | `/alibaba/auth/url` | Link to authorize your Alibaba buyer account |
| GET | `/alibaba/callback` | OAuth redirect target (no key; protected by a one-time state) |
| GET | `/alibaba/search?q=...` | Search Alibaba products |
| GET | `/alibaba/products/{id}` | Product details, SKUs, prices |
| GET | `/alibaba/products/{id}/inventory` | Stock |
| GET | `/alibaba/orders/{id}` / `.../tracking` | Order detail and tracking |
| POST | `/alibaba/orders` | Create a BuyNow order (`"confirm": true` required) |
| POST | `/alibaba/orders/pay` | Get a PayPal payment link (`"confirm": true` required) |
| POST | `/alibaba/call` | Any other read-only Alibaba buyer API (allow-listed) |
| POST | `/alibaba/webhook` | Receives Alibaba price/order events (signature checked) |

Alibaba only sends webhooks to an HTTPS URL with an OV or EV certificate, so the API must
be deployed to a real server for events to arrive.

## Tests

```
uv run python -m unittest discover -s tests
```

The tests check that the starting data reproduces the worksheet's figures
(e.g. phone stands £1.64 per unit, 13.7 %).

## Code layout

- `streamlit_app.py`: the interface
- `pilot/calc.py`: margin, VAT, fee and ads calculations (no UI code)
- `pilot/db.py`: SQLite storage, backup and restore
- `pilot/seed.py`: starting products, suppliers and checklist
- `pilot/messages.py`: supplier message templates
- `pilot/connections.py`: the Connections tab
- `pilot/integrations/amazon.py`: Amazon SP-API client (LWA auth, orders, inventory, fees, pricing, listings)
- `pilot/integrations/alibaba.py`: Alibaba.com Open Platform client (signing, OAuth, search, products, orders, webhooks)
- `api/main.py`: the REST API (FastAPI)
