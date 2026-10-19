"""
Economic-calendar module.
Source (free, no key): https://nfs.faireconomy.media/ff_calendar_thisweek.json (+ nextweek)
Each item: title, country (currency code), date (ISO), impact, forecast, previous.

Tracks 4 event groups and maps each to one of your pillars:
  central_bank -> monetary_policy   (FOMC, ECB, BOE, BOJ, RBA, BOC, SNB, RBNZ ...)
  employment   -> growth            (NFP, unemployment rate, employment change)
  inflation    -> inflation         (CPI core/YoY, PPI)
  growth       -> growth            (GDP, PMI flash mfg/services, retail sales)

Forecast-vs-previous gives an "expectation" signal (improving / weakening).
Dashboard shows the calendar; scorer nudges pillar scores by the signal.
"""
import time, datetime as dt
import requests

UA = {"User-Agent": "fx-strength-app/1.0"}
FEEDS = [
    "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
    "https://nfs.faireconomy.media/ff_calendar_nextweek.json",
]

# category -> (keywords matched against lower-case title, pillar)
CATEGORIES = {
    "central_bank": (["fomc", "federal funds rate", "main refinancing", "official bank rate",
                      "boj policy rate", "monetary policy statement", "rate statement",
                      "cash rate", "official cash rate", "policy rate",
                      "monetary policy assessment", "monetary policy meeting",
                      "press conference", "mpc"], "monetary_policy"),
    "employment":   (["non-farm", "nonfarm", "employment change", "unemployment rate",
                      "claimant count", "jobless"], "growth"),
    "inflation":    (["cpi", "ppi", "inflation"], "inflation"),
    "growth":       (["gdp", "pmi", "retail sales"], "growth"),
}
# events where a HIGHER number is bad for the currency
INVERSE = ["unemployment rate", "claimant count", "jobless"]
IMPACT_W = {"High": 1.0, "Medium": 0.5}


def _get(url):
    for i in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=30)
            if r.status_code == 404:
                return []          # next week not published yet
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print("  events retry", i + 1, url[-30:], e)
            time.sleep(3)
    return []


def _num(s):
    """'225K' -> 225000, '3.4%' -> 3.4, '<0.5%' -> 0.5, '' -> None"""
    if s is None:
        return None
    s = str(s).strip().replace(",", "").replace("<", "").replace(">", "")
    if not s:
        return None
    mult = 1.0
    if s[-1] in "KMBT":
        mult = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}[s[-1]]
        s = s[:-1]
    s = s.rstrip("%")
    try:
        return float(s) * mult
    except ValueError:
        return None


def _category(title):
    t = title.lower()
    for cat, (words, pillar) in CATEGORIES.items():
        if any(w in t for w in words):
            return cat, pillar
    return None, None


def fetch_events(currencies):
    seen, out = set(), []
    for url in FEEDS:
        for e in _get(url):
            ccy = e.get("country")
            impact = e.get("impact")
            title = e.get("title", "")
            if ccy not in currencies or impact not in IMPACT_W:
                continue
            cat, pillar = _category(title)
            if not cat:
                continue
            key = (ccy, title, e.get("date"))
            if key in seen:
                continue
            seen.add(key)

            try:
                when = dt.datetime.fromisoformat(e["date"]).astimezone(dt.timezone.utc)
            except Exception:
                continue

            fc, prev = _num(e.get("forecast")), _num(e.get("previous"))
            direction = 0
            if fc is not None and prev is not None and fc != prev:
                direction = 1 if fc > prev else -1
                if any(w in title.lower() for w in INVERSE):
                    direction = -direction          # higher unemployment = weaker ccy
            out.append({
                "date_utc": when.isoformat(timespec="minutes").replace("+00:00", "Z"),
                "
