---
name: stock-dashboard
description: صيانة وتطوير «لوحة تحليل الأسهم» (index.html واحد بالعربية RTL + data/market.json يحدّثه GitHub Actions). استخدمه عند أي طلب عن لوحة الأسهم أو Scanner أو RVOL أو ترتيب الفرص أو معايير الدرجات أو Backtest/Forward Test أو إضافة سهم أو تغيير مصدر البيانات أو MCP أو workflow التحديث. Use for the Arabic stock analyzer dashboard, scoring rules, backtest, data fetch script, GitHub Pages deploy.
---
# لوحة تحليل الأسهم (Observation Only)

## الفكرة
مصادر البيانات (بالترتيب مع تبديل تلقائي: Alpaca ← Polygon ← Twelve Data ← Stooq ← Yahoo؛ SEC EDGAR؛ أخبار Finnhub أو Yahoo) ← `scripts/fetch_data.py` (أو خادم MCP) ← `data/market.json` ← `index.html` يحلل ويرتب ويعرض.
**المرحلة الحالية: مراقبة وتحليل وتنبيهات فقط.** لا تُضف أي تنفيذ أوامر (شراء/بيع) ولا ربطاً بوسيط تداول. أبقِ تنبيه «ليست نصيحة استثمارية» ظاهراً.

## الملفات
- `index.html`: كل الواجهة والمنطق (HTML+CSS+JS بلا مكتبات). RTL، خط Tajawal.
- `scripts/fetch_data.py`: يكتب `data/market.json` (stdlib فقط). الفشل في الأسعار يوقف التشغيل ويبقي الملف القديم؛ فشل SEC/الأخبار يُتجاوز.
- `.github/workflows/update.yml`: cron كل 30 دقيقة في ساعات السوق (UTC) ثم commit للملف.
- `data/market.json`: `{updated, dates[], bars:{SYM:{o,h,l,c,v}}, events:{SYM:[{d,t,txt,tone}]}}`؛ `d` فهرس داخل `dates`، `tone` = +1/0/-1. كل الرموز بنفس الطول والتواريخ (تتطلب 220 شمعة على الأقل).
- إذا غاب الملف، تعمل الصفحة بمحاكاة عشوائية (دالة `step()`).

## منطق الصفحة (index.html)
- `U`: قائمة الرموز (الأسهم ثم SPY/QQQ/IWM). عند إضافة سهم عدّله هنا وفي `SYMS` بالسكربت (الأسهم أولاً، المؤشرات في النهاية، و`STOCKS=SYMS[:N]`).
- `ind(s)`: EMA20/50/200، RSI14، ATR14، RVOL (حجم اليوم ÷ متوسط 20 يوماً).
- `regime()`: Bull إذا SPY > EMA50 > EMA200؛ Bear إذا تحت EMA50 وEMA200؛ وإلا Neutral.
- `an(s)`: يحسب مستويات الإبطال (أعلى من أدنى 10 أيام وسعر−2.5ATR، بحد أدنى 0.8ATR)، الأهداف (2/3.5/5 ATR)، R:R للهدف 2، و6 معايير `cr` بالقيم 0/0.5/1.
- الأوزان `W=[25,20,15,15,15,10]` بالترتيب `WN`: اتجاه، RVOL، محفز، مخاطر، السوق، قرب الدخول. التصنيف: ≥80 فرصة قوية، ≥60 متابعة، غير ذلك مراقبة.
- `bt(p)`: Backtest (السعر>EMA20>EMA50، RVOL≥1.3، SPY>EMA50، دخول افتتاح اليوم التالي، وقف/هدف بـATR، مدة قصوى، أسوأ حالة عند تلامس الاثنين). `opt()` يبحث في شبكة صغيرة (تنبيه: ملاءمة للتاريخ).
- Forward Test: في وضع المحاكاة `advance()`؛ في الوضع الحقيقي `liveFw()` يحفظ الإشارات في localStorage لكل متصفح.

## أوامر شائعة
- تشغيل محلي: `python scripts/fetch_data.py && python -m http.server 8000` ثم افتح http://localhost:8000
- فحص JS: انسخ وسم script إلى ملف و`node --check`.
- النشر: GitHub Pages من الفرع الرئيسي (Settings ← Pages ← Deploy from branch ← / root). فعّل Actions ثم Run workflow مرة أولى.

## قواعد التعديل
- حافظ على ملف HTML واحداً بلا أطر خارجية؛ أي تغيير في المنطق يُختبر بتشغيل `bt` والتأكد من عدم ظهور NaN.
- لا تُدخل مفاتيح API في الصفحة. المفاتيح تُحفظ كـ GitHub Secrets وتُستخدم داخل السكربت فقط (مثال Alpaca: `ALPACA_KEY`, `ALPACA_SECRET`).
- Yahoo غير رسمي وقد يتغير أو يحجب؛ اذكر ذلك عند أي عطل، وقدّم Alpaca/Polygon بديلاً.
- أي نتيجة اختبار تاريخي لا تثبت ربحية مستقبلية؛ لا تعرضها كذلك.

## مزودو الأسعار
- المزودون ذوو المفاتيح يُفعَّلون فقط إذا وُجدت أسرارهم: `ALPACA_KEY_ID`+`ALPACA_SECRET` (feed افتراضي iex عبر `ALPACA_FEED`)، `POLYGON_KEY`، `TWELVEDATA_KEY`، و`FINNHUB_KEY` للأخبار. Stooq وYahoo بلا مفتاح.
- يستخدم السكربت مزوداً واحداً لكل الرموز (لتجنب خلط الأحجام)، وينتقل للتالي عند الفشل أو نقص البيانات. الترتيب عبر المتغير `PROVIDERS` (GitHub Variable).
- لإضافة مزود: دالة تعيد `{SYM:{'YYYY-MM-DD':[o,h,l,c,v]}}` وتسجيلها في `FN` و`NEED`.
- الصفحة تعيد تحميل `data/market.json` كل 60 ثانية. الحداثة الفعلية = جدولة Actions (5 دقائق كحد أدنى وقد تتأخر)، وهي ليست بثاً لحظياً. البث الحقيقي يحتاج خادماً/WebSocket خلفياً.

## النسخة المدمجة
- `index.html` الآن هو برنامج «سيولة الأسهم وتوصيات البنوك» المدمج: يجلب بيانات Yahoo/Finnhub من المتصفح، مع وحدات إضافية في آخر السكربت: `strongInd` (ADX/DI، Supertrend، Ichimoku، Stochastic، MFI، CMF، Donchian) مع ترتيبها بدقتها التاريخية على السهم نفسه (أفق 10 أيام) وقرار مرجّح، و`planUI` (6 معايير، ATR، إبطال، 3 أهداف، اختبار القاعدة، حالة السوق SPY).
- وزن التوصية: 30% فنية + 25% مؤشرات قوية + 35% إجماع الخبراء + 10% أخبار. توصيات الخبراء تُعرض كأعداد، والتفاصيل داخل `<details>`.
- `dashboard.html` هو اللوحة السابقة التي تقرأ `data/market.json` من GitHub Actions.
