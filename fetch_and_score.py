"""
FX Currency Strength Engine - 5 pillars:
 1. Growth          (World Bank GDP growth)
 2. Inflation       (World Bank CPI inflation vs 2% target)
 3. Monetary policy (BIS central-bank policy rates: level + 6m trend)
 4. Geopolitics     (GDELT news tone for each country, last 7 days)
 5. Market risk     (VIX level/change vs each currency's safe-haven profile)

Run:  python fetch_and_score.py   -> writes data.json
All sources are free and need no API key.
"""
import json, time, datetime as dt
import requests
from events import fetch_events, pillar_adjustments

CCY = {
    # ccy: (World Bank code, BIS code, GDELT query term, safe-haven beta)
    "USD": ("US",  "US", "United States", 0.5),
    "EUR": ("EMU", "XM", "Eurozone",      0.0),
    "GBP": ("GB",  "GB", "United Kingdom", -0.3),
    "JPY": ("JP",  "JP", "Japan",          1.0),
    "AUD": ("AU",  "AU", "Australia",     -1.0),
    "NZD": ("NZ",  "NZ", "New Zealand",   -1.0),
    "CAD": ("CA",  "CA", "Canada",        -0.5),
    "CHF": ("CH",  "CH", "Switzerland",    1.0),
}
INFLATION_TARGET = 2.0
UA = {"User-Agent": "fx-strength-app/1.0"}


def get_json(url, tries=3):
    for i in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
