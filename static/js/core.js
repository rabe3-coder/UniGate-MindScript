'use strict';
const $ = (s) => document.querySelector(s);
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, s => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[s]));
const lang = () => localStorage.getItem('ms_lang') || 'ar';
const theme = () => localStorage.getItem('ms_theme') || 'dark';
const L = (ar, en) => lang() === 'ar' ? ar : en;
const tr = {
    swap: ['تبديل الشعب', 'Section swaps'],
    dashboard: ['لوحة التحكم', 'Dashboard'], catalog: ['المقررات والشُعب', 'Courses & sections'], basket: ['سلة التسجيل', 'Registration basket'], schedule: ['جدولي الدراسي', 'My timetable'], waitlist: ['قائمة الانتظار', 'Waitlist'], payment: ['الدفع التجريبي', 'Demo payments'], students: ['شؤون الطلاب', 'Student affairs'], sections: ['إدارة الشعب', 'Section management'], payments: ['مطابقة الدفعات', 'Payment reconciliation'], settings: ['إدارة النظام', 'System controls'], lab: ['مختبر السيناريوهات', 'Scenario laboratory'], audit: ['سجل التدقيق', 'Audit log'], about: ['عن المشروع', 'About the project'],
    welcome: ['مرحبًا بعودتك', 'Welcome back'], login: ['تسجيل الدخول', 'Sign in'], logout: ['تسجيل الخروج', 'Sign out'], username: ['اسم المستخدم', 'Username'], password: ['كلمة المرور', 'Password'], demo: ['حسابات جاهزة للتجربة', 'Ready-to-use demo accounts'], enter: ['دخول إلى النظام', 'Enter the system'], student: ['طالب', 'Student'], affairs: ['شؤون الطلاب', 'Student affairs'], head: ['رئيس القسم', 'Department head'], finance: ['المالية', 'Finance'], admin: ['مدير النظام', 'Administrator'],
    liveDemo: ['بيئة تجريبية — لا مدفوعات حقيقية', 'Demo environment — no real charges'], registered: ['تسجيلات مؤكدة', 'Confirmed enrollments'], seats: ['الشُعب', 'Sections'], courses: ['المقررات', 'Courses'], people: ['الحسابات', 'Accounts'],
    credits: ['ساعات معتمدة', 'Credits'], available: ['متاح', 'Available'], full: ['ممتلئ', 'Full'], eligible: ['مؤهل', 'Eligible'], ineligible: ['غير مؤهل', 'Ineligible'], add: ['أضف للسلة', 'Add to basket'], waiting: ['انضم إلى الانتظار', 'Join waitlist'], remove: ['إزالة', 'Remove'], view: ['استعراض', 'View'], checkout: ['تأكيد تسجيل السلة', 'Confirm registration'], resetBasket: ['تفريغ السلة', 'Clear basket'], myBasket: ['سلتك الحالية', 'Your selected sections'], emptyBasket: ['السلة فارغة. اختر شعبًا من صفحة المقررات.', 'Your basket is empty. Select sections from the catalog.'],
    day: ['اليوم', 'Day'], time: ['الوقت', 'Time'], section: ['الشعبة', 'Section'], capacity: ['السعة', 'Capacity'], course: ['المقرر', 'Course'], status: ['الحالة', 'Status'], actions: ['إجراءات', 'Actions'], count: ['العدد', 'Count'], name: ['الاسم', 'Name'], search: ['ابحث عن مقرر أو رمز', 'Search by title or code'], all: ['الكل', 'All'], onlyEligible: ['المؤهل فقط', 'Eligible only'],
    confirmed: ['مؤكد', 'Confirmed'], pending: ['قيد التحقق', 'Pending verification'], failed: ['فشل', 'Failed'], cancelled: ['ملغى', 'Cancelled'], promoted: ['تمت الترقية', 'Promoted'], skipped: ['تم التجاوز', 'Skipped'], drop: ['انسحاب', 'Drop'], leave: ['مغادرة الانتظار', 'Leave waitlist'],
    run: ['تشغيل المحاكاة', 'Run simulation'], safe: ['اجتاز الاختبار', 'Invariant preserved'], isolation: ['تجربة معزولة عن بيانات المستخدمين الفعلية', 'Isolated test — live user data unchanged'],
    paid: ['دفع تجريبي ناجح', 'Simulate success'], delayed: ['خصم افتراضي دون إشعار', 'Simulate delayed callback'], paymentFail: ['فشل دفع تجريبي', 'Simulate payment failure'], reference: ['المرجع', 'Reference'], reconcile: ['تحقق من الدفعة', 'Reconcile payment'], approve: ['تأكيد النجاح', 'Confirm success'], reject: ['تأكيد الفشل', 'Confirm failure'],
    enable: ['تفعيل', 'Enable'], disable: ['تعطيل', 'Disable'], save: ['حفظ', 'Save'], increase: ['تحديث السعة', 'Update capacity'], openSection: ['إنشاء شعبة', 'Create section'], newCapacity: ['السعة الجديدة', 'New capacity'], phase: ['مرحلة التسجيل', 'Registration phase'], reset: ['إعادة بيانات التجربة', 'Reset demo database'],
    old: ['مسجل مسبقًا', 'Already registered'], total: ['الإجمالي', 'Total'], minimum: ['الحد الأدنى', 'Minimum'], maximum: ['الحد الأعلى', 'Maximum'],
    weekdays: [['الإثنين', 'Monday'], ['الثلاثاء', 'Tuesday'], ['الأربعاء', 'Wednesday'], ['الخميس', 'Thursday'], ['الجمعة', 'Friday'], ['السبت', 'Saturday'], ['الأحد', 'Sunday']]
};
const t = k => { const v = tr[k]; return v ? L(...v) : k; };
const day = n => { const w = tr.weekdays[n]; return w ? L(...w) : '-'; };
const time = s => `${String(s).padStart(2, '0')}:00`;
const fmtdate = s => { try {
    return new Date(s).toLocaleString(lang() === 'ar' ? 'ar-SY' : 'en-GB', { dateStyle: 'medium', timeStyle: 'short' });
}
catch {
    return s;
} };
const role = () => S.user?.role;
let S = { user: null, stats: {}, page: 'dashboard', basket: [], catalog: [], me: null, students: [], payments: [], waitlist: [], audit: [], labResult: null, labSelected: 1, search: '', eligibleOnly: false, profileStudentId: null, studentSearch: '', showStudentCreate: false };
function uid() { return (window.crypto?.randomUUID?.() || ('demo-' + Date.now() + '-' + Math.random().toString(36).slice(2))); }
async function api(path, method = 'GET', body) { const res = await fetch('/api/' + path, { method, credentials: 'same-origin', headers: body ? { 'Content-Type': 'application/json' } : {}, body: body ? JSON.stringify(body) : undefined }); let data; try {
    data = await res.json();
}
catch {
    throw Error('Server response could not be parsed');
} ; if (!res.ok)
    throw Object.assign(new Error(data.error || 'Operation failed'), { code: data.code, status: res.status }); return data; }
function toast(message, bad = false) { const box = $('#toast'); const el = document.createElement('div'); el.className = 'toastitem' + (bad ? ' error' : ''); el.textContent = message; box.appendChild(el); setTimeout(() => el.remove(), 5100); }
const guard = async (fn) => { try {
    await fn();
}
catch (e) {
    toast(e.message, true);
    if (e.status === 401) {
        S.user = null;
        renderLogin();
    }
} };
function applyStyle() { document.documentElement.lang = lang(); document.documentElement.dir = lang() === 'ar' ? 'rtl' : 'ltr'; document.body.dataset.theme = theme(); }
function setLang() { localStorage.setItem('ms_lang', lang() === 'ar' ? 'en' : 'ar'); applyStyle(); if (S.user)
    go(S.page);
else
    renderLogin(S.authMode || 'login'); }
function setTheme() { localStorage.setItem('ms_theme', theme() === 'dark' ? 'light' : 'dark'); applyStyle(); document.querySelectorAll('[data-action=theme]').forEach(el => el.textContent = theme() === 'dark' ? '☀' : '☾'); }
