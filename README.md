# تشغيل محلل الأسهم من GitHub بتحديث حي

## 1) انشر الوسيط على Cloudflare (مجاني، بدون بطاقة)
1. أنشئ حساباً على dash.cloudflare.com ← **Workers & Pages** ← **Create** ← **Create Worker**.
2. سمّه `stock-proxy` واضغط **Deploy**، ثم **Edit code**.
3. احذف الكود الافتراضي والصق محتوى `worker.js` كاملاً، ثم **Deploy**.
4. من **Settings ← Variables and Secrets** أضف:
   - `FINNHUB_KEY` (نوع **Secret**): مفتاح Finnhub *الجديد* (يلزم تغيير القديم، كان ظاهراً في الملف).
   - `ALLOWED_ORIGIN` (نوع Text، اختياري): `https://USERNAME.github.io` ليقبل الوسيط موقعك فقط.
5. افتح `https://stock-proxy.<حسابك>.workers.dev/health` ← يجب أن ترى `{"ok":true,...}`.

## 2) ارفع التطبيق على GitHub Pages
1. أنشئ مستودعاً (Repository) وارفع `index.html` في الجذر.
2. **Settings ← Pages ← Deploy from a branch ← main / root**.
3. افتح `https://USERNAME.github.io/REPO/?api=https://stock-proxy.<حسابك>.workers.dev`
   (الرابط يُحفظ في المتصفح بعد أول فتح، أو الصقه في حقل «رابط الوسيط» داخل «ربط البيانات»).

## ملاحظات
- المصدر Finnhub يعطي الأسعار اللحظية، والشموع اليومية (للتحليل المعمّق) تأتي من Yahoo عبر الوسيط.
- بدون `FINNHUB_KEY` اختر المصدر «Yahoo Finance» من القائمة.
- الخطة المجانية في Cloudflare: 100,000 طلب يومياً. كل تحديث يستهلك طلباً لكل سهم في القائمة، فلا تتركه مفتوحاً بفاصل قصير طوال اليوم.
- التطبيق للمراقبة والتحليل فقط وليس توصية مالية.
