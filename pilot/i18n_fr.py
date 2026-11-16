"""French translations of the interface (English text -> French).

Only screens are translated. Supplier messages and Amazon listings stay in English.
"""

from __future__ import annotations

FR: dict[str, str] = {
    # ------------------------------------------------------------ menu & sidebar
    "Overview": "Vue d'ensemble",
    "Buy (Alibaba)": "Acheter (Alibaba)",
    "Sell (Amazon)": "Vendre (Amazon)",
    "Money & setup": "Argent & réglages",
    "Dashboard": "Tableau de bord",
    "Product search": "Recherche de produits",
    "Supplier quotes": "Devis fournisseurs",
    "Purchases & payments": "Achats & paiements",
    "Products & margins": "Produits & marges",
    "Amazon competition": "Concurrence Amazon",
    "Listings & ads": "Annonces & publicité",
    "Stock & FBA shipments": "Stock & envois FBA",
    "Customer orders": "Commandes clients",
    "Cash": "Trésorerie",
    "Launch checklist": "Checklist de lancement",
    "Connections": "Connexions",
    "⚙️ Settings": "⚙️ Réglages",
    "💾 Backup": "💾 Sauvegarde",
    "Streamlit Cloud erases the data when the app restarts. Download a backup after making changes.":
        "Streamlit Cloud efface les données quand l'application redémarre. Téléchargez une sauvegarde "
        "après vos modifications.",
    "Download backup (JSON)": "Télécharger la sauvegarde (JSON)",
    "Restore backup": "Restaurer une sauvegarde",
    "Restore from file": "Restaurer ce fichier",
    "Reset to example data": "Revenir aux données d'exemple",
    "Amazon seller": "Vendeur Amazon",
    "Marketplace": "Place de marché",
    "Sourcing": "Sourcing",
    "Store": "Boutique",
    "Store name": "Nom de la boutique",
    "Account status": "Statut du compte",
    "Exchange rate (USD per £1)": "Taux de change (USD pour 1 £)",
    "VAT registered (prices include VAT)": "Assujetti à la TVA (prix TTC)",
    "VAT rate %": "Taux de TVA %",
    "Message signature": "Signature des messages",
    "Save settings": "Enregistrer les réglages",
    "not set up": "non configuré",

    # ------------------------------------------------------------ common words
    "Save": "Enregistrer",
    "Product": "Produit",
    "Products": "Produits",
    "Supplier": "Fournisseur",
    "Status": "Statut",
    "Notes": "Notes",
    "Contact": "Contact",
    "Details": "Détails",
    "Date": "Date",
    "Order": "Commande",
    "Orders": "Commandes",
    "Amount": "Montant",
    "Paid": "Payé",
    "Left to pay": "Reste à payer",
    "Payment": "Paiement",
    "Tracking": "Suivi",
    "ETA": "Arrivée prévue",
    "Quantity": "Quantité",
    "Qty": "Qté",
    "Total": "Total",
    "Total £": "Total £",
    "Paid £": "Payé £",
    "Left £": "Reste £",
    "Price £": "Prix £",
    "Price $": "Prix $",
    "Price $/unit": "Prix $/unité",
    "$/unit": "$/unité",
    "MOQ": "Minimum",
    "Pack": "Lot",
    "Title": "Titre",
    "Description": "Description",
    "Message": "Message",
    "Subject": "Objet",
    "Channel": "Canal",
    "To": "À",
    "Link": "Lien",
    "Image": "Image",
    "Pick": "Choisir",
    "Verdict": "Verdict",
    "Brand": "Marque",
    "Sales rank": "Classement",
    "Items": "Articles",
    "Available": "Disponible",
    "Inbound": "En arrivage",
    "Done": "Fait",
    "Phase": "Phase",
    "Step": "Étape",
    "You": "Vous",
    "unknown": "inconnu",
    "buyer": "acheteur",
    "sent": "envoyé",
    "e-mail": "e-mail",
    "E-mail": "E-mail",
    "Amazon": "Amazon",
    "Alibaba": "Alibaba",
    "Gmail": "Gmail",
    "Alibaba.com": "Alibaba.com",
    "ASIN": "ASIN",
    "SKU": "SKU",
    "BSR": "Classement (BSR)",

    # ------------------------------------------------------------ journey stages & actions
    "Researched": "Recherché",
    "Quotes requested": "Devis demandés",
    "Quotes received": "Devis reçus",
    "Supplier selected": "Fournisseur choisi",
    "Ordered": "Commandé",
    "In transit": "En route",
    "At Amazon": "Chez Amazon",
    "On sale": "En vente",
    "Contact suppliers for a price": "Demander un prix aux fournisseurs",
    "Chase suppliers and record the quotes you receive": "Relancer les fournisseurs et noter les devis reçus",
    "Compare the quotes and pick one": "Comparer les devis et en choisir un",
    "Create the purchase order": "Créer la commande fournisseur",
    "Pay the order": "Payer la commande",
    "Follow production and shipping": "Suivre la production et l'expédition",
    "Prepare the shipment to Amazon (FBA)": "Préparer l'envoi vers Amazon (FBA)",
    "Publish the listing on Amazon": "Publier l'annonce sur Amazon",
    "Follow sales and advertising": "Suivre les ventes et la publicité",
    "Add suppliers from Product search": "Ajouter des fournisseurs depuis la Recherche",

    # ------------------------------------------------------------ statuses (stored in English)
    "To contact": "À contacter",
    "Message ready": "Message prêt",
    "Sent": "Envoyé",
    "Quote received": "Devis reçu",
    "Sample ordered": "Échantillon commandé",
    "Selected": "Retenu",
    "Rejected": "Écarté",
    "Draft": "Brouillon",
    "Awaiting payment": "En attente de paiement",
    "In production": "En production",
    "Shipped": "Expédiée",
    "At Amazon FC": "Arrivée chez Amazon",
    "Cancelled": "Annulée",
    "Ready": "Prête",
    "Published": "Publiée",
    "Alibaba Trade Assurance": "Alibaba Trade Assurance",
    "PayPal link (Alibaba)": "Lien PayPal (Alibaba)",
    "Bank transfer": "Virement bancaire",
    "Other": "Autre",
    "Thin": "Mince",
    "Solid": "Solide",
    "Too low": "Trop faible",
    "Request for quotation": "Demande de prix (devis)",
    "Sample request": "Demande d'échantillon",
    "Price negotiation": "Négociation du prix",
    "Order follow-up": "Relance sur une commande",

    # ------------------------------------------------------------ dashboard
    "Each product's journey, from searching on Alibaba to selling on Amazon. Nothing is sent to a supplier or changed on Amazon without your approval.":
        "Le parcours de chaque produit, de la recherche sur Alibaba à la vente sur Amazon. Rien n'est "
        "envoyé à un fournisseur ni modifié sur Amazon sans votre accord.",
    "The journey": "Le parcours",
    "To do now": "À faire maintenant",
    "Money": "Argent",
    "Supplier purchases": "Achats fournisseurs",
    "Open Cash →": "Voir la trésorerie →",
    "Your products": "Vos produits",
    "Starting figures you can change in Products & margins.":
        "Chiffres de départ modifiables dans Produits & marges.",
    "No products yet. Start by searching for a product.": "Aucun produit. Commencez par chercher un produit.",
    "Search for a product →": "Chercher un produit →",
    "**Getting started: {pct:.0f} %** ({done} of {total} steps)":
        "**Démarrage : {pct:.0f} %** ({done} étapes sur {total})",
    "Next step: {step}": "Prochaine étape : {step}",
    "selling at": "vendu",
    "per unit sold": "par unité vendue",
    "First order of {qty} units: about {cash} to pay upfront.":
        "Première commande de {qty} unités : environ {cash} à avancer.",

    # ------------------------------------------------------------ product search
    "🔎 Product search": "🔎 Recherche de produits",
    "Type a product: the app looks up supplier prices on Alibaba and the competition on Amazon, then estimates your margin. Add the best ones to your pipeline.":
        "Tapez un produit : l'application cherche les prix fournisseurs sur Alibaba et la concurrence "
        "sur Amazon, puis estime votre marge. Ajoutez les meilleurs à votre suivi.",
    "Product to search": "Produit recherché",
    "e.g. magnetic screwdriver set": "ex. magnetic screwdriver set",
    "Target selling price £": "Prix de vente visé £",
    "Replaced by the average Amazon price when Amazon prices are loaded.":
        "Remplacé par le prix moyen Amazon quand les prix Amazon sont chargés.",
    "Search": "Rechercher",
    "Open on alibaba.com ↗": "Voir sur alibaba.com ↗",
    "Open on amazon.co.uk ↗": "Voir sur amazon.co.uk ↗",
    "Assumptions (Amazon fees, freight…)": "Hypothèses (frais Amazon, transport…)",
    "FBA fee £/unit": "Frais FBA £/unité",
    "Amazon referral %": "Commission Amazon %",
    "Freight £/unit": "Transport £/unité",
    "Ads % of price": "Publicité % du prix",
    "Import duty %": "Droits de douane %",
    "These are estimates. Real fees come from Amazon once the ASIN is known (Connections → Update fees from Amazon).":
        "Ce sont des estimations. Les vrais frais viennent d'Amazon une fois l'ASIN connu "
        "(Connexions → Mettre à jour les frais depuis Amazon).",
    "Competition on Amazon": "Concurrence sur Amazon",
    "Amazon is not connected: use the \"Open on amazon.co.uk\" button above.":
        "Amazon n'est pas connecté : utilisez le bouton « Voir sur amazon.co.uk » ci-dessus.",
    "Run a search.": "Lancez une recherche.",
    "No Amazon results.": "Aucun résultat Amazon.",
    "Load prices for the top 5": "Charger les prix des 5 premiers",
    "Amazon prices: average {avg}, from {low} to {high}. Target price used: {target}.":
        "Prix Amazon : moyenne {avg}, de {low} à {high}. Prix visé utilisé : {target}.",
    "Suppliers on Alibaba": "Fournisseurs sur Alibaba",
    "Alibaba is not connected yet (permissions pending). Meanwhile, add products you find on alibaba.com with the form below.":
        "Alibaba n'est pas encore connecté (permissions en attente). En attendant, ajoutez les "
        "produits trouvés sur alibaba.com avec le formulaire ci-dessous.",
    "➕ Add a product found on alibaba.com by hand": "➕ Ajouter à la main un produit trouvé sur alibaba.com",
    "Product / supplier name": "Nom du produit / fournisseur",
    "Alibaba link (product page)": "Lien Alibaba (page du produit)",
    "Minimum order (MOQ)": "Minimum de commande (MOQ)",
    "Add to the list": "Ajouter à la liste",
    "No products yet.": "Aucun produit pour l'instant.",
    "Estimated margin when selling at {price}, most profitable first.":
        "Marge estimée pour une vente à {price}, du plus rentable au moins rentable.",
    "Landed cost £": "Coût rendu £",
    "Profit £/unit": "Bénéfice £/unité",
    "Margin %": "Marge %",
    "Open ↗": "Ouvrir ↗",
    "**Add the ticked products to your pipeline**": "**Ajouter les produits cochés à votre suivi**",
    "Add them to": "Les ajouter à",
    "A new product": "Un nouveau produit",
    "An existing product": "Un produit existant",
    "New product name": "Nom du nouveau produit",
    "Existing product": "Produit existant",
    "Add {n} supplier(s) to the pipeline": "Ajouter {n} fournisseur(s) au suivi",
    "Tick at least one product in the table.": "Cochez au moins un produit dans le tableau.",
    "Give the product a name.": "Donnez un nom au produit.",
    "Added {n} supplier(s). Next step: ask them for a price.":
        "{n} fournisseur(s) ajouté(s). Étape suivante : leur demander un prix.",

    # ------------------------------------------------------------ supplier quotes
    "✉️ Supplier quotes": "✉️ Devis fournisseurs",
    "Ask several suppliers for a price, record their answers, compare the margin you would make with each, and pick the best.":
        "Demandez un prix à plusieurs fournisseurs, notez leurs réponses, comparez la marge obtenue "
        "avec chacun et choisissez le meilleur.",
    "No products yet. Start with Product search.": "Aucun produit. Commencez par la Recherche de produits.",
    "Go to Product search →": "Aller à la Recherche →",
    "No suppliers for this product yet. Add some from Product search.":
        "Aucun fournisseur pour ce produit. Ajoutez-en depuis la Recherche.",
    "1. Suppliers for this product": "1. Fournisseurs de ce produit",
    "Add a supplier's e-mail if they gave it to you: quote requests can then be sent straight from your Gmail.":
        "Ajoutez l'e-mail d'un fournisseur s'il vous l'a donné : les demandes de prix pourront alors "
        "partir directement de votre Gmail.",
    "Shipping total $": "Port total $",
    "Lead time (days)": "Délai (jours)",
    "Alibaba link": "Lien Alibaba",
    "2. Ask for a price": "2. Demander un prix",
    "Send to": "Envoyer à",
    "Choose suppliers": "Choisir les fournisseurs",
    "Message (you can edit it)": "Message (modifiable ; il reste en anglais pour les fournisseurs)",
    "**📧 By e-mail** ({n}):": "**📧 Par e-mail** ({n}) :",
    "Gmail is not set up: see Connections → Gmail.": "Gmail n'est pas configuré : voir Connexions → Gmail.",
    "I approve sending this message to {n} supplier(s) from {sender}":
        "J'approuve l'envoi de ce message à {n} fournisseur(s) depuis {sender}",
    "Send e-mails": "Envoyer les e-mails",
    "{n} e-mail(s) sent.": "{n} e-mail(s) envoyé(s).",
    "**💬 Through Alibaba messages** ({n}): Alibaba does not share suppliers' e-mail addresses. Open the supplier's page, click **Contact Supplier** and paste the message (copy icon below).":
        "**💬 Par la messagerie Alibaba** ({n}) : Alibaba ne communique pas l'e-mail des fournisseurs. "
        "Ouvrez la page du fournisseur, cliquez sur **Contact Supplier** et collez le message "
        "(icône de copie ci-dessous).",
    "Open {name} on Alibaba ↗": "Ouvrir {name} sur Alibaba ↗",
    "{name} (no link saved)": "{name} (pas de lien enregistré)",
    "Mark as sent": "Marquer comme envoyé",
    "3. Record a quote you received": "3. Noter un devis reçu",
    "Shipping to the UK, total $": "Port total jusqu'au Royaume-Uni $",
    "Leave 0 if unknown: the product's freight estimate is used.":
        "Laissez 0 si inconnu : l'estimation de transport du produit est utilisée.",
    "Production lead time (days)": "Délai de production (jours)",
    "Sample price $": "Prix de l'échantillon $",
    "Notes (options, logo, packaging…)": "Notes (options, logo, emballage…)",
    "Save quote": "Enregistrer le devis",
    "Enter the unit price.": "Indiquez le prix unitaire.",
    "Quote saved.": "Devis enregistré.",
    "4. Compare and choose": "4. Comparer et choisir",
    "No prices yet.": "Aucun prix pour l'instant.",
    "When selling at {price} (change it in Products & margins).":
        "Pour une vente à {price} (modifiable dans Produits & marges).",
    "Lead time (d)": "Délai (j)",
    "First order £": "1re commande £",
    "Quote to choose": "Devis à retenir",
    "(most profitable)": "(le plus rentable)",
    "Choose this quote": "Retenir ce devis",
    "Quote from {name} chosen. Next step: create the purchase order.":
        "Devis de {name} retenu. Étape suivante : créer la commande.",
    "Message history ({n})": "Historique des messages ({n})",
    "No messages sent yet.": "Aucun message envoyé.",

    # ------------------------------------------------------------ purchases
    "🧾 Purchases & payments": "🧾 Achats & paiements",
    "Create the order with the chosen supplier, pay it (Trade Assurance or Alibaba PayPal link) and follow it until it reaches Amazon. The app never pays for you: it opens the payment page and records what has been paid.":
        "Créez la commande chez le fournisseur retenu, payez-la (Trade Assurance ou lien PayPal Alibaba) "
        "et suivez-la jusqu'à son arrivée chez Amazon. L'application ne paie jamais à votre place : elle "
        "ouvre la page de paiement et note ce qui est réglé.",
    "Total ordered": "Total commandé",
    "Open orders": "Commandes en cours",
    "New purchase order": "Nouvelle commande fournisseur",
    "No suppliers yet. Start with Product search.": "Aucun fournisseur. Commencez par la Recherche.",
    "Shipping $": "Frais de port $",
    "Alibaba order number (if already created)": "N° de commande Alibaba (si déjà créée)",
    "The Trade Assurance order number, shown in My Orders on Alibaba.":
        "Le numéro de commande Trade Assurance, visible dans « My Orders » sur Alibaba.",
    "Total: {usd} ≈ {gbp}": "Total : {usd} ≈ {gbp}",
    "Create order": "Créer la commande",
    "Order created. Pay it, then record the payment below.":
        "Commande créée. Payez-la, puis notez le paiement ci-dessous.",
    "My orders on Alibaba ↗": "Mes commandes sur Alibaba ↗",
    "Pay and track an order": "Payer et suivre une commande",
    "**Payment**": "**Paiement**",
    "Pay this order ↗": "Payer cette commande ↗",
    "I approve requesting a PayPal payment link for this order":
        "J'approuve la demande d'un lien de paiement PayPal pour cette commande",
    "Get the Alibaba payment link": "Obtenir le lien de paiement Alibaba",
    "Payment link ready: click \"Pay this order\".": "Lien de paiement prêt : cliquez sur « Payer cette commande ».",
    "Pay on Alibaba (Trade Assurance), then record the payment here. Add the Alibaba order number in the table below to track the order automatically.":
        "Payez sur Alibaba (Trade Assurance), puis notez le paiement ici. Indiquez le n° de commande "
        "Alibaba dans le tableau ci-dessous pour suivre la commande automatiquement.",
    "Amount paid £": "Montant payé £",
    "Payment date": "Date du paiement",
    "Record this payment": "Noter ce paiement",
    "Payment recorded.": "Paiement enregistré.",
    "**Tracking**": "**Suivi**",
    "Refresh from Alibaba": "Actualiser depuis Alibaba",
    "Order refreshed (Alibaba status: {status}).": "Commande actualisée (statut Alibaba : {status}).",
    "Connect Alibaba (Connections page) to refresh the status automatically.":
        "Connectez Alibaba (page Connexions) pour actualiser le statut automatiquement.",
    "Alibaba status: {status}": "Statut Alibaba : {status}",
    "Tracking: {tracking}": "Suivi : {tracking}",
    "Change status": "Changer le statut",
    "Save status": "Enregistrer le statut",
    "All orders": "Toutes les commandes",
    "Alibaba order #": "N° Alibaba",

    # ------------------------------------------------------------ products & margins
    "📊 Products & margins": "📊 Produits & marges",
    "Edit any number, then **Save**. Percentages are in %. Supplier cost is in USD (converted at ${fx:.2f} = £1). Fees are per unit in £.":
        "Modifiez un chiffre puis **Enregistrer**. Pourcentages en %. Coût fournisseur en dollars "
        "(converti à {fx:.2f} $ = 1 £). Frais par unité en £.",
    "Supplier $/unit": "Fournisseur $/unité",
    "Duty %": "Douane %",
    "Referral %": "Commission Amazon %",
    "FBA fee £": "Frais FBA £",
    "Other £/unit": "Autres £/unité",
    "Storage, returns, packaging": "Stockage, retours, emballage",
    "1st order qty": "Qté 1re commande",
    "1st order fixed £": "Frais fixes 1re commande £",
    "Samples, inspection, labels": "Échantillons, inspection, étiquettes",
    "**Results per unit sold**": "**Résultat par unité vendue**",
    "Price": "Prix",
    "VAT": "TVA",
    "Referral": "Commission",
    "FBA": "FBA",
    "Landed cost": "Coût rendu",
    "Ads": "Pub",
    "Profit/unit": "Bénéfice/unité",
    "ROI %": "ROI %",
    "Break-even ACoS %": "ACoS max %",
    "1st order £": "1re commande £",
    "Break-even ACoS: the share of the price advertising can cost before a sale loses money.":
        "ACoS max : la part du prix que la publicité peut coûter avant que la vente ne fasse perdre de l'argent.",
    "**What if I changed the price?**": "**Et si je changeais le prix ?**",
    "Sale price £": "Prix de vente £",
    "Target margin %": "Marge visée %",
    "Profit per unit": "Bénéfice par unité",
    "{m:.1f}% margin · {band}": "marge {m:.1f} % · {band}",
    "Price needed for a {target}% margin: **{price}**": "Prix nécessaire pour {target} % de marge : **{price}**",
    "Where the {price} goes": "Où vont les {price}",
    "Referral fee": "Commission Amazon",
    "FBA fee": "Frais FBA",
    "Profit": "Bénéfice",

    # ------------------------------------------------------------ competition
    "🆚 Amazon competition": "🆚 Concurrence Amazon",
    "Add a product first.": "Ajoutez d'abord un produit.",
    "Search amazon.co.uk ↗": "Chercher sur amazon.co.uk ↗",
    "Note the top competing listings: price, rating, reviews, Best Sellers Rank.":
        "Notez les principales annonces concurrentes : prix, note, nombre d'avis, classement.",
    "Rating": "Note",
    "Reviews": "Avis",
    "Est. sales/month": "Ventes/mois estimées",
    "Your price": "Votre prix",
    "{pct:+.0f}% vs average": "{pct:+.0f} % vs moyenne",
    "Competitor average": "Moyenne concurrents",
    "Lowest / highest": "Moins cher / plus cher",
    "Median reviews": "Avis (médiane)",

    # ------------------------------------------------------------ listings & ads
    "📢 Listings & ads": "📢 Annonces & publicité",
    "Coming in part 2: publish the listing straight to Amazon from this page, with your EAN barcode. Until then, copy the text into Seller Central → Catalogue → Add products, then set the status to \"Published\".":
        "Bientôt (partie 2) : publier l'annonce directement sur Amazon depuis cette page, avec votre "
        "code EAN. En attendant, copiez le texte dans Seller Central → Catalogue → Add products, puis "
        "passez le statut à « Publiée ».",
    "**Listing**": "**Annonce** (en anglais pour Amazon UK)",
    "Title (max 200 characters)": "Titre (200 caractères max)",
    "Bullet points (one per line, 5 recommended)": "Points clés (un par ligne, 5 conseillés)",
    "Backend search terms (max 249 bytes)": "Mots-clés cachés (249 octets max)",
    "{chars}/200 title chars · {nb}/5 bullets · {nbytes}/249 search-term bytes":
        "{chars}/200 caractères · {nb}/5 points clés · {nbytes}/249 octets de mots-clés",
    "Search terms exceed 249 bytes: Amazon will ignore them.": "Mots-clés trop longs : Amazon les ignorera.",
    "Save listing": "Enregistrer l'annonce",
    "**Sponsored Products plan**": "**Publicité Sponsored Products**",
    "Campaign name": "Nom de la campagne",
    "Daily budget £": "Budget par jour £",
    "Expected cost per click £": "Coût par clic estimé £",
    "Conversion rate %": "Taux de conversion %",
    "Keywords (one per line)": "Mots-clés (un par ligne)",
    "Save plan": "Enregistrer le plan",
    "Clicks/day": "Clics/jour",
    "Ad orders/day": "Ventes pub/jour",
    "Expected ACoS": "ACoS prévu",
    "Expected ACoS is above your break-even ACoS of {be:.0f}%: each ad sale loses money. Lower the CPC or raise the price.":
        "L'ACoS prévu dépasse votre maximum de {be:.0f} % : chaque vente par la pub fait perdre de "
        "l'argent. Baissez le coût par clic ou montez le prix.",
    "Expected ACoS is below your break-even ACoS of {be:.0f}%.":
        "L'ACoS prévu reste sous votre maximum de {be:.0f} %.",
    "Coming in part 3: create the campaign on Amazon from here (needs Amazon Ads API access).":
        "Bientôt (partie 3) : créer la campagne sur Amazon depuis ici (nécessite l'accès Amazon Ads).",
    "Change the price on Amazon": "Changer le prix sur Amazon",
    "Connect Amazon (Connections page) to change prices from here.":
        "Connectez Amazon (page Connexions) pour changer vos prix depuis ici.",
    "Add this product's SKU in Products & margins.": "Indiquez le SKU de ce produit dans Produits & marges.",
    "New price £ (incl. VAT)": "Nouveau prix £ (TTC)",
    "Amazon product type": "Type de produit Amazon",
    "As shown on the listing, e.g. PHONE_ACCESSORY": "Tel qu'affiché sur l'annonce, ex. PHONE_ACCESSORY",
    "I approve changing {sku} on Amazon to {price}": "J'approuve le changement de {sku} à {price} sur Amazon",
    "Update price on Amazon": "Mettre à jour le prix sur Amazon",
    "Tick the approval box first.": "Cochez d'abord la case d'approbation.",
    "Amazon answered: {status}": "Réponse d'Amazon : {status}",

    # ------------------------------------------------------------ stock, orders, cash, checklist
    "🚚 Stock & FBA shipments": "🚚 Stock & envois FBA",
    "With FBA, Amazon stores your products and delivers every order itself, so your goods must be sent to its warehouses before you can sell.":
        "Avec FBA, Amazon stocke vos produits et livre lui-même chaque commande : votre marchandise "
        "doit donc être envoyée dans ses entrepôts avant de vendre.",
    "Coming in part 2: create the shipment to Amazon's warehouses and print the labels from this page. Until then: Seller Central → Inventory → Send to Amazon.":
        "Bientôt (partie 2) : créer l'envoi vers les entrepôts Amazon et imprimer les étiquettes depuis "
        "cette page. En attendant : Seller Central → Inventory → Send to Amazon.",
    "Goods on their way from suppliers": "Marchandise en route depuis les fournisseurs",
    "No supplier orders in progress.": "Aucune commande fournisseur en cours.",
    "Track orders →": "Suivre les commandes →",
    "Stock at Amazon": "Stock chez Amazon",
    "Connect Amazon (Connections page) to see your stock.": "Connectez Amazon (page Connexions) pour voir votre stock.",
    "Load FBA stock": "Charger le stock FBA",
    "No stock at Amazon yet.": "Aucun stock chez Amazon pour l'instant.",
    "🛒 Customer orders": "🛒 Commandes clients",
    "Your sales on Amazon. **With FBA there is nothing to approve**: as soon as a customer pays, Amazon packs the parcel in its warehouse and delivers it. The money then reaches your bank account (see Cash).":
        "Vos ventes sur Amazon. **En FBA, rien à valider** : dès qu'un client paie, Amazon prépare le "
        "colis dans son entrepôt et le livre. L'argent arrive ensuite sur votre compte (voir Trésorerie).",
    "Connect Amazon (Connections page) to see your orders.": "Connectez Amazon (page Connexions) pour voir vos commandes.",
    "Period (days)": "Période (jours)",
    "Load orders": "Charger les commandes",
    "Sales": "Chiffre d'affaires",
    "No orders in this period.": "Aucune commande sur cette période.",
    "Fulfilled by": "Expédié par",
    "You (FBM)": "Vous (FBM)",
    "💷 Cash": "💷 Trésorerie",
    "No purchase orders yet.": "Aucune commande fournisseur pour l'instant.",
    "Total purchases": "Total des achats",
    "**To pay**": "**À payer**",
    "Pay an order →": "Payer une commande →",
    "Amazon payouts": "Encaissements Amazon",
    "Coming in part 3: your sales, the fees Amazon keeps, and the payouts to your bank account (Amazon pays about every 2 weeks). This needs the **Finance and Accounting** role on your Amazon developer profile.":
        "Bientôt (partie 3) : vos ventes, les frais retenus par Amazon et les virements sur votre compte "
        "bancaire (Amazon paie environ toutes les 2 semaines). Il faut ajouter le rôle **Finance and "
        "Accounting** à votre profil développeur Amazon.",
    "✅ Launch checklist": "✅ Checklist de lancement",
    "{done} of {total} steps done": "{done} étapes sur {total} terminées",

    # ------------------------------------------------------------ connections
    "🔌 Connections": "🔌 Connexions",
    "Your Amazon seller, Alibaba buyer and Gmail accounts. Anything that changes Amazon or Alibaba asks you to confirm first; payments always happen on Alibaba/PayPal, by you.":
        "Vos comptes Amazon vendeur, Alibaba acheteur et Gmail. Tout ce qui modifie Amazon ou Alibaba "
        "vous demande une confirmation ; les paiements se font toujours sur Alibaba/PayPal, par vous.",
    "Amazon Seller": "Amazon Seller",
    "Keys saved": "Clés enregistrées",
    "Not set up": "Non configuré",
    "Connected": "Connecté",
    "Set up": "Configuré",
    "App set up, not authorized": "Application prête, compte non connecté",
    "Amazon is not connected yet.": "Amazon n'est pas encore connecté.",
    "**Sandbox** mode: Amazon returns test data, not yours.":
        "Mode **Sandbox** : Amazon renvoie des données de test, pas les vôtres.",
    "Test connection": "Tester la connexion",
    "Connected.": "Connexion réussie.",
    "Marketplaces: {names}": "Places de marché : {names}",
    "Update fees from Amazon": "Mettre à jour les frais depuis Amazon",
    "Uses Amazon's fee estimate for each product that has an ASIN":
        "Utilise l'estimation de frais d'Amazon pour chaque produit qui a un ASIN",
    "Updated {n} product(s).": "{n} produit(s) mis à jour.",
    "No ASIN yet:": "Sans ASIN :",
    "Alibaba is not set up yet.": "Alibaba n'est pas encore configuré.",
    "Connected as {name}": "Connecté en tant que {name}",
    "Refresh access token": "Renouveler l'accès",
    "Access refreshed.": "Accès renouvelé.",
    "Connect my Alibaba buyer account ↗": "Connecter mon compte acheteur Alibaba ↗",
    "You sign in on Alibaba and come back here automatically. The SystemAPI and ICBU Dropshipping permission groups must be \"Active\" in the App Console.":
        "Vous vous connectez sur Alibaba puis revenez ici automatiquement. Les permissions SystemAPI et "
        "ICBU Dropshipping doivent être « Active » dans l'App Console.",
    "**Events received from Alibaba** (price changes, order status)":
        "**Événements reçus d'Alibaba** (changements de prix, statut des commandes)",
    "None yet. They arrive through the REST API (/alibaba/webhook).":
        "Aucun pour l'instant. Ils arrivent par l'API REST (/alibaba/webhook).",
    "Search products on Alibaba →": "Chercher des produits sur Alibaba →",
    "This Alibaba authorization has expired or did not start from this app. Click **Connect my Alibaba buyer account** again (Connections page).":
        "Cette autorisation Alibaba a expiré ou ne vient pas de cette application. Cliquez à nouveau sur "
        "**Connecter mon compte acheteur Alibaba** (page Connexions).",
    "Alibaba account connected: {name}": "Compte Alibaba connecté : {name}",
    "E-mails are sent from {sender}.": "Les e-mails partent de {sender}.",
    "Gmail is not set up.": "Gmail n'est pas configuré.",
}

