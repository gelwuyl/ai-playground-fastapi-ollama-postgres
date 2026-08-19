"""Saved results for USE_FIXTURES=1 (mirrors the guide's saved-results fallback).

Lets Mr. Kaypoh run end-to-end without consuming SerpApi quota or hitting the
network. Toggle via USE_FIXTURES=1 in the environment.
"""
FIXTURE_SEARCH = [
    {
        "query": "gold price today past month movement factors",
        "title": "Gold Price Charts & Historical Data - GoldPrice.org",
        "url": "https://goldprice.org/",
        "snippet": "Live gold spot price per ounce.",
    },
    {
        "query": "gold price today past month movement factors",
        "title": "Gold Spot Price - Trading Economics",
        "url": "https://tradingeconomics.com/commodity/gold",
        "snippet": "Gold rose roughly 9.9% over the past month to around $4,403/oz.",
    },
    {
        "query": "gold price today",
        "title": "World Gold Council",
        "url": "https://gold.org/",
        "snippet": "Official gold demand and price statistics.",
    },
    {
        "query": "gold price today",
        "title": "Kitco Gold Charts",
        "url": "https://www.kitco.com/charts/historicalgold.html",
        "snippet": "Historical gold price charts.",
    },
    {
        "query": "gold price today",
        "title": "Gold Avenue",
        "url": "https://goldavenue.com/",
        "snippet": "Buy and track gold.",
    },
]

FIXTURE_PAGES = {
    "https://tradingeconomics.com/commodity/gold":
        "Gold spot price is around $4,403-4,405 per troy ounce as of Aug 17-18, 2026. "
        "Over the past month gold has risen roughly 9.9%, driven by central-bank buying "
        "and a weaker US dollar. [https://tradingeconomics.com/commodity/gold]",
    "https://gold.org/":
        "The World Gold Council publishes official gold demand trends. The live number "
        "was not listed in the text body. Demand remained strong across central banks. "
        "[https://gold.org/]",
    "https://www.kitco.com/charts/historicalgold.html":
        "Gold spot price is around $4,403-4,405 per troy ounce as of Aug 17-18, 2026. "
        "Historical charts show a steady climb over the past month. "
        "[https://www.kitco.com/charts/historicalgold.html]",
}
