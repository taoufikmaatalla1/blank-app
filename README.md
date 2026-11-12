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
