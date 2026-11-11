#!/usr/bin/env python3
"""يجلب بيانات السوق إلى data/market.json من عدة مصادر بالترتيب مع تبديل تلقائي عند الفشل.
المصادر: alpaca, polygon, twelvedata (تحتاج مفاتيح في GitHub Secrets) ثم stooq, yahoo (بلا مفتاح).
غيّر الترتيب عبر المتغير PROVIDERS مثل: PROVIDERS=alpaca,polygon,stooq,yahoo
الأخبار: Finnhub إن وُجد FINNHUB_KEY وإلا Yahoo. ملفات SEC من EDGAR. مكتبات بايثون القياسية فقط."""
import os, json, re, sys, time, bisect, csv, io, datetime as dt, urllib.request
SYMS = ["NVDA", "AVGO", "TSLA", "AAPL", "AMD", "PLTR", "SPY", "QQQ", "IWM"]   # عدّل القائمة هنا (وفي U داخل index.html)
STOCKS = SYMS[:6]; KEEP = 300
UA = {"User-Agent": "stock-dashboard/1.0 (contact: your-email@example.com)"}  # SEC تشترط بريداً حقيقياً
env = os.environ.get
TODAY = dt.date.today(); START = (TODAY - dt.timedelta(days=620)).isoformat()

def get(url, headers=None, raw=False):
    with urllib.request.urlopen(urllib.request.Request(url, headers={**UA, **(headers or {})}), timeout=30) as r:
        return r.read().decode() if raw else json.load(r)

def alpaca():
    h = {"APCA-API-KEY-ID": env("ALPACA_KEY_ID", ""), "APCA-API-SECRET-KEY": env("ALPACA_SECRET", "")}
    out = {s: {} for s in SYMS}; tok = ""
    while True:
        u = (f"https://data.alpaca.markets/v2/stocks/bars?symbols={','.join(SYMS)}&timeframe=1Day&start={START}"
             f"&limit=10000&adjustment=split&feed={env('ALPACA_FEED', 'iex')}" + (f"&page_token={tok}" if tok else ""))
        j = get(u, h)
        for s, L in (j.get("bars") or {}).items():
            for b in L: out[s][b["t"][:10]] = [b["o"], b["h"], b["l"], b["c"], b["v"]]
        tok = j.get("next_page_token")
        if not tok: return out

def polygon():
    out = {}
    for s in SYMS:
        j = get(f"https://api.polygon.io/v2/aggs/ticker/{s}/range/1/day/{START}/{TODAY}?adjusted=true&sort=asc&limit=50000&apiKey={env('POLYGON_KEY')}")
        out[s] = {dt.datetime.utcfromtimestamp(b["t"] / 1000).strftime("%Y-%m-%d"): [b["o"], b["h"], b["l"], b["c"], b["v"]] for b in j["results"]}
        time.sleep(12.5)   # الخطة المجانية: 5 طلبات/دقيقة
    return out

def twelvedata():
    out = {}
    for s in SYMS:
        j = get(f"https://api.twelvedata.com/time_series?symbol={s}&interval=1day&outputsize=400&apikey={env('TWELVEDATA_KEY')}")
        out[s] = {v["datetime"][:10]: [float(v[k]) for k in ("open", "high", "low", "close", "volume")] for v in j["values"]}
        time.sleep(8)      # الخطة المجانية: 8 طلبات/دقيقة
    return out

def stooq():
    out = {}
    for s in SYMS:
        rows = csv.DictReader(io.StringIO(get(f"https://stooq.com/q/d/l/?s={s.lower()}.us&i=d", raw=True)))
        out[s] = {r["Date"]: [float(r[k]) for k in ("Open", "High", "Low", "Close", "Volume")] for r in rows}
    return out

def yahoo():
    out = {}
    for s in SYMS:
        r = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{s}?range=2y&interval=1d")["chart"]["result"][0]; q = r["indicators"]["quote"][0]; out[s] = {}
        for i, t in enumerate(r["timestamp"]):
            v = [q[k][i] for k in ("open", "high", "low", "close", "volume")]
            if None not in v: out[s][dt.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d")] = v
    return out

NEED = {"alpaca": ("ALPACA_KEY_ID", "ALPACA_SECRET"), "polygon": ("POLYGON_KEY",), "twelvedata": ("TWELVEDATA_KEY",), "stooq": (), "yahoo": ()}
FN = {"alpaca": alpaca, "polygon": polygon, "twelvedata": twelvedata, "stooq": stooq, "yahoo": yahoo}
raw = dates = source = None
for name in env("PROVIDERS", "alpaca,polygon,twelvedata,stooq,yahoo").split(","):
    name = name.strip()
    if name not in FN or not all(env(k) for k in NEED[name]): continue
    try:
        r = FN[name](); d = sorted(set.intersection(*[set(r[s]) for s in SYMS]))[-KEEP:]
        if len(d) >= 220: raw, dates, source = r, d, name; break
        print(name, "بيانات غير كافية:", len(d))
    except Exception as e:
        print(name, "فشل:", e)
if not raw: sys.exit("فشلت كل مصادر الأسعار؛ يبقى الملف القديم")
out_bars = {}
for s in SYMS:
    cols = list(zip(*[raw[s][d] for d in dates]))
    out_bars[s] = {k: [round(x, 4) for x in c] for k, c in zip("ohlcv", cols)}

def idx(date): return bisect.bisect_right(dates, date) - 1
events = {s: [] for s in STOCKS}
cutoff = (dt.date.fromisoformat(dates[-1]) - dt.timedelta(days=30)).isoformat()
try:
    cik = {v["ticker"]: v["cik_str"] for v in get("https://www.sec.gov/files/company_tickers.json").values()}
    for s in STOCKS:
        rc = get(f"https://data.sec.gov/submissions/CIK{int(cik[s]):010d}.json")["filings"]["recent"]
        for form, d in zip(rc["form"], rc["filingDate"]):
            if form in ("8-K", "10-Q", "10-K") and d >= cutoff and idx(d) >= 0:
                events[s].append({"d": idx(d), "t": "SEC Filing", "txt": f"نموذج {form} بتاريخ {d}", "tone": 0})
        time.sleep(.2)
except Exception as e:
    print("SEC skipped:", e)

UP = re.compile(r"raise|upgrad|beat|surge|record|boost|soar|jump", re.I)
DN = re.compile(r"cut|downgrad|miss|plunge|probe|lawsuit|slump|fall|drop", re.I)
def news(s):
    if env("FINNHUB_KEY"):
        L = get(f"https://finnhub.io/api/v1/company-news?symbol={s}&from={cutoff}&to={TODAY}&token={env('FINNHUB_KEY')}")
        return [(n["headline"], n["datetime"]) for n in L[:8]]
    j = get(f"https://query2.finance.yahoo.com/v1/finance/search?q={s}&newsCount=6&quotesCount=0")
    return [(n["title"], n["providerPublishTime"]) for n in j.get("news", [])]
for s in STOCKS:
    try:
        for title, ts in news(s):
            d = dt.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
            if d < cutoff or idx(d) < 0: continue
            up, dn = bool(UP.search(title)), bool(DN.search(title))
            t, tone = ("رفع توقعات", 1) if up and not dn else ("خفض توقعات", -1) if dn and not up else ("خبر مهم", 0)
            events[s].append({"d": idx(d), "t": t, "txt": title[:90], "tone": tone})
    except Exception as e:
        print("news skipped:", s, e)

os.makedirs("data", exist_ok=True)
json.dump({"updated": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), "source": source, "dates": dates, "bars": out_bars, "events": events},
          open("data/market.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("ok", source, dates[-1])
