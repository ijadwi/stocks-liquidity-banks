#!/usr/bin/env python3
"""يجلب الأسعار وتوصيات البنوك ويكتبها في data/*.json

الاستخدام:
  python scripts/update_data.py          # الأسعار فقط
  python scripts/update_data.py --recs   # الأسعار + توصيات البنوك
"""
import json, sys, datetime as dt
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
QUOTES = DATA / "quotes.json"
RECS = DATA / "recommendations.json"
HIST = DATA / "history.json"
EXTRA = ROOT / "symbols.txt"          # رموز إضافية، رمز في كل سطر (اختياري)

# نفس قائمة المتابعة الموجودة في index.html
WATCHLIST = ["NVDA","TSLA","AAPL","AMD","AMZN","MSFT","META","GOOGL","SPY","QQQ","PLTR",
             "NFLX","AVGO","MU","INTC","UBER","LLY","NOW","GLW","WDC","CRWV","MSCI"]

# البنوك الأمريكية المطلوبة (مفتاح البحث بحروف صغيرة : الاسم المعروض)
BANKS = {"goldman": "Goldman Sachs", "morgan stanley": "Morgan Stanley",
         "jp morgan": "JPMorgan", "jpmorgan": "JPMorgan",
         "bank of america": "Bank of America", "bofa": "Bank of America",
         "citi": "Citigroup", "wells fargo": "Wells Fargo"}

REC_MAP = {"buy": "Buy", "strong buy": "Buy", "outperform": "Buy", "overweight": "Overweight",
           "positive": "Buy", "neutral": "Neutral", "hold": "Hold", "equal-weight": "Neutral",
           "market perform": "Neutral", "sector perform": "Neutral", "underweight": "Underweight",
           "sell": "Sell", "underperform": "Sell", "reduce": "Sell"}
KEEP_DAYS = 90


def load(p, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def money(v):
    try:
        v = float(v)
        return f"${v:,.0f}" if v > 0 else "-"
    except Exception:
        return "-"


def symbols(recs):
    s = list(WATCHLIST) + [r["ticker"] for r in recs]
    if EXTRA.exists():
        s += [x.strip().upper() for x in EXTRA.read_text().splitlines() if x.strip() and not x.startswith("#")]
    # رموز غير مدعومة في Yahoo (مثل SPACEX) تُتجاهل تلقائياً لاحقاً
    return sorted(set(s))


def fetch_quotes(syms):
    df = yf.download(syms, period="5d", interval="1d", group_by="ticker",
                     progress=False, threads=True, auto_adjust=False)
    out, failed = [], []
    for s in syms:
        try:
            d = df[s].dropna(subset=["Close"]) if len(syms) > 1 else df.dropna(subset=["Close"])
            if d.empty:
                raise ValueError("no data")
            last = float(d["Close"].iloc[-1])
            prev = float(d["Close"].iloc[-2]) if len(d) > 1 else last
            vol = float(d["Volume"].iloc[-1] or 0)
            out.append({"sym": s, "price": round(last, 4), "chg": round((last / prev - 1) * 100, 4), "vol": vol})
        except Exception:
            failed.append(s)
    return out, failed


def fetch_recs(syms, existing):
    cutoff = dt.date.today() - dt.timedelta(days=KEEP_DAYS)
    names = {r["ticker"]: r["name"] for r in existing}
    seen = {(r["ticker"], r["bank"], r["date"]) for r in existing}
    added = []
    for s in syms:
        try:
            ud = yf.Ticker(s).upgrades_downgrades
        except Exception:
            continue
        if ud is None or ud.empty:
            continue
        for idx, row in ud.iterrows():
            day = pd.Timestamp(idx).date()
            if day < cutoff:
                continue
            firm = str(row.get("Firm", "")).lower()
            bank = next((v for k, v in BANKS.items() if k in firm), None)
            if not bank:
                continue
            rec = REC_MAP.get(str(row.get("ToGrade", "")).strip().lower())
            if not rec:
                continue
            key = (s, bank, day.isoformat())
            if key in seen:
                continue
            seen.add(key)
            added.append({"name": names.get(s, s), "ticker": s, "bank": bank, "rec": rec,
                          "prev": money(row.get("priorPriceTarget")), "new": money(row.get("currentPriceTarget")),
                          "date": day.isoformat(), "source": "Yahoo Finance"})
    merged = [r for r in existing if r["date"] >= cutoff.isoformat()] + added
    merged.sort(key=lambda r: r["date"], reverse=True)
    return merged, len(added)


def fetch_history(syms):
    """سنة من الأسعار اليومية لكل رمز (للمؤشرات الفنية وماسح الانعكاس)"""
    df = yf.download(syms, period="1y", interval="1d", group_by="ticker",
                     progress=False, threads=True, auto_adjust=False)
    out = {}
    for s in syms:
        try:
            d = df[s].dropna(subset=["Close"]) if len(syms) > 1 else df.dropna(subset=["Close"])
            if len(d) < 30:
                continue
            r2 = lambda col: [round(float(x), 2) for x in d[col].fillna(d["Close"])]
            out[s] = {"c": r2("Close"), "hi": r2("High"), "lo": r2("Low"),
                      "v": [int(x or 0) for x in d["Volume"].fillna(0)],
                      "d": [pd.Timestamp(i).strftime("%m-%d") for i in d.index]}
        except Exception:
            pass
    return out


def main():
    do_recs = "--recs" in sys.argv
    recs = load(RECS, [])
    syms = symbols(recs)

    quotes, failed = fetch_quotes(syms)
    if quotes:  # لا نكتب ملفاً فارغاً إذا فشل الجلب بالكامل
        QUOTES.write_text(json.dumps({"updated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                                      "quotes": quotes}, ensure_ascii=False), encoding="utf-8")
    print(f"quotes: {len(quotes)} ok, {len(failed)} failed {failed}")

    if do_recs:
        h = fetch_history([x for x in syms if x not in failed])
        if h:
            HIST.write_text(json.dumps(h, separators=(",", ":")), encoding="utf-8")
        print(f"history: {len(h)} symbols")
        merged, n = fetch_recs([s for s in syms if s not in failed], recs)
        RECS.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"recommendations: +{n} new, {len(merged)} total")

    if not quotes:
        sys.exit("لم يتم جلب أي سعر")


if __name__ == "__main__":
    main()
