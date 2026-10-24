# فحوص الجودة وإعادة التحقق

من مجلد المشروع:

```bash
python -m compileall -q app server.py
python test_concurrency.py
python test_layered_workflows.py
python test_student_management.py
python test_academics.py
```

- `test_concurrency.py`: طالبان يحاولان حجز المقعد الأخير عبر اتصالات مختلفة؛ نتيجة واحدة ناجحة ودون جزء من السلة.
- `test_layered_workflows.py`: تبديل ذري، FIFO، خصوصية، قيود قاعدة البيانات، أولوية الخريجين وحماية الانتظار، وعدم مسح الأسماء عند ترقية قاعدة قديمة.
- `test_student_management.py`: إنشاء طالب، منع تكرار البيانات، البحث بالاسم والرقم، وصلاحيات شؤون الطلاب.
- `test_academics.py`: إضافة مقرر للخطة، علامة رقمية ومعدل تجريبي وصلاحيات العلامات.
- `test_api.py`: اختبار مجموعة واسعة من المسارات على خادم يعمل. يحتاج `requests` للتطوير فقط و**يعيد ضبط قاعدة الاختبار**، لذا لا تشغله مباشرة على ملف قاعدة المستخدم.

فحص JavaScript إذا كان Node.js موجودًا:

```bash
node --check static/js/core.js
node --check static/js/layout.js
node --check static/js/actions.js
node --check static/js/pages/swaps.js
```

## حدود الاختبارات

الاختبارات الحالية اختبارات وحدة/تكامل سيناريوهات محدودة. **لا تثبت** 12,000 جلسة متزامنة، أو تعافي عدة خوادم، أو عدم وجود ثغرات في بيئة الإنترنت. لم ننجز اختبارًا تفاعليًا كاملًا داخل متصفح بسبب حظر تصفح الخادم المحلي في بيئة الاختبار، رغم نجاح اختبار ملف HTML/JS وتحميل الصفحات عبر HTTP بعملاء برمجيين.

- `test_http_new_features.py`: تدفق التبديل عبر HTTP، الصلاحيات، الخصوصية، حماية Origin وإعادة الضبط.
- `python run_tests.py`: يشغّل اختبارات stdlib المعزولة السابقة كلها على قواعد مؤقتة.
