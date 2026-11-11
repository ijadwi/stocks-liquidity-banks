# لوحة تحليل الأسهم · Observation Only
1. ارفع المجلد كاملاً إلى مستودع GitHub (مع `.claude` و`.github`).
2. Settings ← Pages ← Deploy from branch ← main ← / (root).
3. Actions ← update-market-data ← Run workflow (مرة أولى)، ثم يتحدّث `data/market.json` تلقائياً.
4. عدّل البريد في `UA` داخل `scripts/fetch_data.py` (تشترطه SEC).
5. لاستخدام الـ Skill في Claude Code: يعمل تلقائياً داخل المستودع (`.claude/skills/stock-dashboard`)، أو انسخ المجلد إلى `~/.claude/skills/`.
المحتوى للمراقبة والتعلم وليس نصيحة استثمارية.

6. (اختياري) Settings ← Secrets and variables ← Actions: أضف `ALPACA_KEY_ID` و`ALPACA_SECRET` أو `POLYGON_KEY` أو `TWELVEDATA_KEY` أو `FINNHUB_KEY`. بدونها يستخدم Stooq ثم Yahoo.
