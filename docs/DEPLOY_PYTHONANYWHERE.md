# دليل نشر UniGate على PythonAnywhere Free — بدون تغيير منطق النظام أو قاعدة البيانات

## متطلبات مسبقة

- نسخة آمنة من الشيفرة من `UniGate_PythonAnywhere_Deploy_Ready.zip` (هذه الحزمة **لا تحتوي أي قاعدة بيانات شخصية**).
- حساب مجاني في [PythonAnywhere](https://www.pythonanywhere.com/) (أو النظام الأوروبي إن كان متاحًا لحسابك).
- حساب GitHub اختياري لنقل الكود وتتبع التغييرات، يُنصح بمستودع **خاص** إن كانت وثائق المشروع سرية؛ حزمة النشر العامة لا تتضمن بيانات أو كلمات مرور.
- إذا عندك قاعدة SQLite حقيقية على Windows (بعد تعيين أسماء موظفي الشؤون): **لا ترفعها إلى GitHub**. احتفظ بها كملف خاص وارفعها إلى مساحة ملفات PythonAnywhere الخاصة بحسابك فقط.

## أولًا: تجربة محلية دون تغيير البيئة الحالية

1. فك ضغط الملفات في مجلد مستقل أو انسخ حزمة التحديث فوق نسخة مشروعك **دون استبدال قاعدة SQLite**.
2. احفظ نسخة احتياطية باستخدام: `python backup_database.py backup`.
3. شغّل `START_WINDOWS.bat` كالمعتاد، أو `python server.py`.
4. افتح `http://127.0.0.1:8765`.
5. اختبر التكيّف مع WSGI بشكل مستقل: `python test_deployment_wsgi.py`.
6. لتشغيل مدخل WSGI مؤقتًا على جهازك للاختبار، استخدم `python -c "from wsgiref.simple_server import make_server; from app.wsgi import application; make_server('127.0.0.1', 8766, application).serve_forever()"` ثم افتح `http://127.0.0.1:8766` (لا تضع `UNIGATE_PUBLIC_ORIGIN` أثناء اختبار HTTP المحلي).

## ثانيًا: رفع الشيفرة إلى GitHub (اختياري)

من مجلد المشروع في Terminal:

```bash
git init
git add .
git status
git commit -m "UniGate: public deployment preparation"
git branch -M main
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

أنشئ المستودع أولًا في موقع GitHub، واستبدل القيم الإرشادية. تأكد قبل `git push` باستخدام `git status` و `git ls-files` من عدم وجود `.env` أو `registration.sqlite3` أو نسخ احتياطية أو ملفات أشخاص حقيقيين. 

إذا لا تريد GitHub، استخدم شاشة **Files** في PythonAnywhere لرفع الحزمة النظيفة وفك ضغطها هناك.

## ثالثًا: تثبيت الكود على PythonAnywhere

1. افتح PythonAnywhere ← **Consoles** ← **Bash**.
2. ارفع الملفات أو استنسخ مستودع GitHub (إن كنت نشرته):

```bash
cd ~
git clone https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPOSITORY.git unigate
mkdir -p ~/unigate_data
chmod 700 ~/unigate_data
```

3. إذا أردت **قاعدة بيانات جديدة نظيفة**، لا ترفع ملف `registration.sqlite3`؛ ستنشأ الجداول والمقررات التجريبية تلقائيًا عند التشغيل.
4. إذا أردت **نقل قاعدة بياناتك القديمة**، أوقف التطبيق المحلي وDB Browser، وأنشئ نسخة متسقة عبر `python backup_database.py backup --file C:\\path\\to\\backup.sqlite3`. ثم من لوحة PythonAnywhere **Files** ارفعها باسم `/home/YOUR_USERNAME/unigate_data/registration.sqlite3` (لا تضعها في مستودع Git). تحقق من أنها النسخة الصحيحة وليست ملفًا ناقصًا نُسخ أثناء الكتابة.
5. لتعيين المدير وثلاثة حسابات شؤون جديدة على البيئة العامة، من Console نفّذ:

```bash
cd ~/unigate
MINDSCRIPT_DB="$HOME/unigate_data/registration.sqlite3" UNIGATE_SQLITE_JOURNAL=DELETE python3 manage_staff.py setup
```

إذا احتفظت بموظفين تم إعدادهم مسبقًا في قاعدتك المنقولة، يمكن اختبار دخولهم بدل إعادة تعيينهم. لا تُدخل كلمات مرور المستخدمين في المحادثة أو المستودع.

## رابعًا: إنشاء تطبيق ويب عام

1. في PythonAnywhere اختر **Web → Add a new web app**.
2. اختر نطاقًا مجانيًا من شكل `YOUR_USERNAME.pythonanywhere.com`.
3. اختر **Manual configuration**، واختر إصدار Python 3.10 أو أحدث المتاح.
4. من تبويب **Web** افتح رابط ملف **WSGI configuration file** الذي يوفره PythonAnywhere.
5. افتح `deploy/pythonanywhere_wsgi.py` الموجود في المشروع، وانسخ محتواه إلى ملف WSGI الفعلي في لوحة المنصة (ملف WSGI الذي يظهر تحت `/var/www/...`)، بعد استبدال `YOUR_PYTHONANYWHERE_USERNAME` باسم حسابك الحقيقي.
6. احفظ الملف، ثم اضغط **Reload** من Web.
7. افتح `https://YOUR_USERNAME.pythonanywhere.com`.

ملاحظة: **لا تشغّل** `python server.py` ضمن تطبيق PythonAnywhere؛ منصتها تستخدم WSGI لطلبات الإنترنت. لا تحتاج إلى أي إطار عمل جديد أو مكتبات خارجية؛ CSS/JS/HTML تُقدَّم من مدخل WSGI نفسه. إن رغبت لاحقًا يمكن فصل ملفات static عبر إعدادات Web لتحسين الأداء.

### إعدادات البيئة الموضوعة بواسطة ملف WSGI

| الاسم | الوظيفة |
|---|---|
| `MINDSCRIPT_DB` | `/home/YOUR_USERNAME/unigate_data/registration.sqlite3` (ثابت عبر تحديث ملفات Git) |
| `UNIGATE_PUBLIC_ORIGIN` | `https://YOUR_USERNAME.pythonanywhere.com` (فحص Origin والكوكيز الآمنة) |
| `UNIGATE_SQLITE_JOURNAL` | `DELETE` بدل WAL لبيئة التخزين الشبكي |
| `MINDSCRIPT_TEST_DEMO` | يجب أن يبقى **غير مفعّل** |

**لا يحتاج PythonAnywhere إلى `PORT` و`0.0.0.0` ضمن مسار WSGI.** الخادم التقليدي `server.py` يدعم هذه المتغيرات إذا انتقلت لاحقًا إلى Render أو منصة HTTP تقليدية، لكنها ليست الوسيلة المستخدمة هنا.

## خامسًا: التحقق من الوظائف الفعلية على الرابط العام

افتح الرابط باستخدام نافذة خاصة بالمتصفح، ثم اختبر بهذا الترتيب:

- الصفحة الرئيسية وتنسيق RTL واللغتين والوضعين الداكن والفاتح.
- إنشاء طالب تجريبي برقم جامعي فريد، ثم تسجيل الخروج والدخول من نافذة خاصة جديدة.
- إضافة مواد للسلة، وتسجيل الخروج والدخول للتأكد من بقاء المسودة.
- تسجيل الدخول بحساب شؤون الطلاب، البحث عن الطالب، تعديل بيانات تجريبية.
- فتح صفحة المدير واختبار الصلاحيات، دون اختيار زر مسح بيانات التجربة.
- إعادة تحميل **Web → Reload** ثم تسجيل الدخول مرة أخرى: **لا ينبغي أن تتغير الحسابات/التسجيلات**.
- حدّث كود غير متعلق بالبيانات بـ`git pull` وأعد التحميل وتحقق من استمرار الحساب؛ قاعدة البيانات خارج مجلد Git.

إذا ظهرت مشكلة، افتح **Web → Error log / Server log** في PythonAnywhere. لا تشارك مع الآخرين لقطات تحتوي بيانات مستخدمين أو توكنات أو بيانات اتصال خاصة.

## سادسًا: تحديث الكود لاحقًا

داخل **Consoles → Bash**:

```bash
cd ~/unigate
git pull --ff-only
```

ثم افتح **Web → Reload**. **لا تحذف مجلد** `~/unigate_data` عند تحديث التطبيق ولا تنسخ قاعدة البيانات التجريبية مكان القاعدة الحية.

## سابعًا: النسخ الاحتياطي والاستعادة

التصدير اليدوي:

```bash
cd ~/unigate
MINDSCRIPT_DB="$HOME/unigate_data/registration.sqlite3" python3 backup_database.py backup
```

بعد إنشاء ملف النسخة في `~/unigate_data/backups/`، حمّله عبر Files إلى جهازك واحفظه في مكان **مشفر وخاص**، خارج GitHub. احتفظ بنسخ دورية، قبل تحديث الكود وعقب جلسات التجربة المهمة؛ لا يتوفر جدولة مجانية للمهام للحسابات الجديدة وفق سياسة PythonAnywhere لعام 2026.

الاستعادة: أوقف تشغيل التطبيق مؤقتًا (في PythonAnywhere لا يكفي فقط عمل Reload؛ لا ينبغي أن تعيد الكتابة على ملف SQLite مفتوح)، واحتفظ بنسخة من القاعدة الحالية ثم غيّر اسمها، وتحقق من سلامة النسخة الاحتياطية ثم نفّذ:

```bash
cd ~/unigate
MINDSCRIPT_DB="$HOME/unigate_data/registration.sqlite3" python3 backup_database.py restore --file /home/YOUR_USERNAME/unigate_data/backups/backup.sqlite3 --confirm RESTORE_PRIVATE_BACKUP
```

بعد الاستعادة اضغط **Reload**. لا تستخدم اسمًا إرشاديًا كما هو؛ اختر اسم ملف النسخة الفعلي. أداة الاستعادة **ترفض الكتابة فوق قاعدة موجودة** لحمايتك، لذا يلزم نقل القاعدة الحالية جانبًا بعد إيقاف الخدمة. تحفظ النسخ الاحتياطية بيانات الحسابات وقد تتضمن معلومات شخصية؛ لا تنشرها أبدًا.

## القيود

- لا ضمان لخدمة عامة نشطة إلى الأبد؛ حسابات PythonAnywhere المجانية محدودة، والتطبيق غير المستخدم قد تنتهي صلاحيته خلال شهر. تابع إشعارات الحساب وحدّث نشاطه ضمن سياسة المزود.
- SQLite على PythonAnywhere ليست مخصصة لحمل عالٍ؛ ومع عامل ويب واحد ستنتظر بعض الطلبات دورها.
- إنشاء الحساب بالرقم الجامعي وحده لا يثبت ملكية الرقم؛ اطلب من المختبرين استخدام أرقام وأسماء وهمية.
- لا دفع حقيقي ولا تكامل خارجي للعلامات أو الجداول؛ تبقى هذه محاكاة مشروع Mind Script.
- رابط الموقع لا يمكن إنشاؤه أو اختباره من هنا دون أن تفتح حساب PythonAnywhere وتنشر المشروع بالفعل.
