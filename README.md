# 📦 Seller Control Center: Amazon UK + Alibaba

One place to run an Amazon UK store that sources from Alibaba. It is built from
the *Poste de pilotage Amazon UK* worksheet and starts with the same five products
and figures, which you can all edit.

The app follows the journey of each product, from finding it on Alibaba to selling it on Amazon:

| Page | What it does |
| --- | --- |
| **Dashboard** | How many products are at each stage (Researched → Quotes requested → Quotes received → Supplier selected → Ordered → Paid → In transit → At Amazon → On sale), what to do next for each one, money committed |
| **Product search** | Search Alibaba (supplier prices) and Amazon (competition, prices) for a keyword, see the estimated margin of every result, add the best ones to the pipeline. Products found on alibaba.com can also be added by hand |
| **Supplier quotes** | Send a quote request to several suppliers at once: by e-mail from your Gmail when you have their address, or through Alibaba's messages (the app prepares the text and opens the supplier page). Record each quote (price, MOQ, shipping, lead time), compare the margin each one gives, choose one |
| **Purchases & payments** | Create the purchase order from the chosen quote, get the Alibaba PayPal payment link, record payments, refresh status and tracking from Alibaba |
| **Products & margins** | Every cost per unit (VAT, Amazon fees, freight, duty, ads) and the profit, with a what-if price slider |
| **Amazon competition** | Log competing listings and see where your price sits |
| **Listings & ads** | Listing drafts (Amazon limits checked), Sponsored Products plan, approved price changes on Amazon |
| **Stock & FBA shipments** | Goods on their way from suppliers, stock in Amazon's warehouses |
| **Customer orders** | Amazon orders (with FBA, Amazon ships them itself) |
| **Cash** | Supplier purchases paid and left to pay |
| **Launch checklist** | 27 steps from account setup to the 14-day review |
| **Connections** | Status and setup of Amazon, Alibaba and Gmail |

Coming next: publishing listings and creating FBA shipments from the app (part 2), then Amazon
payouts and ad campaigns (part 3).

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

**Gmail (supplier e-mails).** Turn on 2-Step Verification on your Google account, create an app
password (Google account → Security → App passwords) and set `GMAIL_ADDRESS` and
`GMAIL_APP_PASSWORD`.

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

- `streamlit_app.py`: the menu and sidebar
- `pilot/calc.py`: margin, VAT, fee and ads calculations (no UI code)
- `pilot/db.py`: SQLite storage, backup and restore
- `pilot/seed.py`: starting products, suppliers and checklist
- `pilot/messages.py`: supplier message templates
- `pilot/views/`: one file per page
- `pilot/pipeline.py`: works out each product's stage and next action
- `pilot/ui.py`: shared page helpers
- `pilot/integrations/mailer.py`: Gmail sending
- `pilot/connections.py`: the Connections page
- `pilot/integrations/amazon.py`: Amazon SP-API client (LWA auth, orders, inventory, fees, pricing, listings)
- `pilot/integrations/alibaba.py`: Alibaba.com Open Platform client (signing, OAuth, search, products, orders, webhooks)
- `api/main.py`: the REST API (FastAPI)
