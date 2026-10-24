# مقارنة خيارات الاستضافة المجانية — 2026-10-24

استند القرار إلى وثائق الجهات الرسمية بتاريخ 24 أكتوبر 2026، ولا يعني أن استضافة مجانية تضمن توفرًا أو حفظ بيانات إلى الأبد.

| الخيار | الخادم المجاني | مكان حفظ البيانات | القيود | القرار |
|---|---|---|---|---|
| Render Free + SQLite | Python مدعوم | ملف مؤقت على الخادم | SQLite تُفقد عند الخمول 15 دقيقة، أو إعادة التشغيل أو النشر. | مرفوض |
| Render Free + Render PostgreSQL | Python مدعوم | PostgreSQL مستقل | قاعدة Render المجانية تنتهي بعد 30 يومًا، وفترة سماح 14 يومًا بعدها حذف البيانات. | مرفوض |
| Render Free + Neon PostgreSQL | Python مدعوم | Neon DB منفصل | Neon Free: 1GB ومئة CU-hours/شهر/مشروع، لا مدة تجربة محددة؛ الخادم ينام 15 دقيقة. يحتاج تحويل SQLite-specific SQL والإجراءات والـtriggers للاستخدام مع PostgreSQL، ثم اختبار التزامن من جديد. | بديل تطوير لاحق، ليس أقل تعديل |
| Render Free + Supabase Free | Python مدعوم | PostgreSQL مستقل | 500MB، قد يتوقف مشروع Supabase قليل الاستخدام بعد سبعة أيام؛ لا توجد نسخ احتياطية قابلة للتنزيل ضمن الخطة المجانية. يحتاج ترحيل SQL. | بديل مشروط |
| PythonAnywhere Free + SQLite | WSGI/Python | ملف SQLite داخل مساحة Home الخاصة بالحساب | عامل ويب واحد، 512MiB تخزين، تطبيق ويب واحد؛ تطبيقات المجاني غير المستخدمة تنتهي بعد شهر؛ SQLite على نظام ملفات شبكي ليست موصى بها لموقع إنتاجي/متزامن كثيف. | **المسار المنفذ لتجربة جامعية صغيرة** |

## مصادر رسمية

- https://render.com/docs/free
- https://render.com/docs/web-services
- https://neon.com/pricing
- https://neon.com/docs/introduction/plans
- https://supabase.com/pricing
- https://supabase.com/docs/guides/platform/free-project-pausing
- https://help.pythonanywhere.com/pages/FreeAccountsFeatures/
- https://help.pythonanywhere.com/pages/KindsOfDatabases
- https://help.pythonanywhere.com/pages/MySiteIsSlow/
- https://blog.pythonanywhere.com/221/

## ما الذي لا نضمنه؟

- لا يمكن ضمان عدم تغيير حدود الخطة المجانية مستقبلًا أو عدم انتهاء صلاحية الحساب أو فقدانه.
- PythonAnywhere Free ليس بديلًا عن بيئة تتحمل 12,000 طالب/5 دقائق، ولا يوفّر نسخًا احتياطية مجدولة جديدة مجانًا وفق قيود 2026.
- لا يمكن اعتبار الخادم/النظام الإنتاجي آمنًا دون تدقيق أوسع واختبارات أمن وحمل وإجراءات حماية هوية الطلاب.
