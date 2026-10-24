function roleList() {
    let nav = [['dashboard', '◈']]; if (role() === 'student')
        nav.push(['catalog', '▦'], ['basket', '◫'], ['schedule', '▤'], ['swap', '⇄'], ['waitlist', '☷'], ['payment', '◇']);
    else {
        nav.push(['catalog', '▦']);
        if (['affairs', 'admin'].includes(role()))
            nav.push(['students', '♙']);
        if (['head', 'admin'].includes(role()))
            nav.push(['sections', '▥']);
        if (['finance', 'admin'].includes(role()))
            nav.push(['payments', '◇']);
        if (['head', 'affairs', 'admin'].includes(role()))
            nav.push(['waitlist', '☷']);
        if (['affairs', 'finance', 'head', 'admin'].includes(role()))
            nav.push(['audit', '≡']);
        if (role() === 'admin')
            nav.push(['settings', '⚙']);
    } nav.push(['lab', '✳'], ['about', 'ⓘ']); return nav;
}
const roleText = r => t(r);
function heading(title, sub, aside = '') { return `<div class="heading"><div><div class="eyebrow">MIND SCRIPT / eng.rabe3</div><h1>${esc(title)}</h1><p>${esc(sub)}</p></div>${aside}</div>`; }
function badge(text, color = '') { return `<span class="tag ${color}">${esc(text)}</span>`; }
function cardMetric(value, name, icon = '◈') { return `<div class="card metric"><div class="metric-top"><span>${esc(name)}</span><span class="metric-icon">${icon}</span></div><div class="metric-value count">${esc(value)}</div><div class="metric-label">${L('بيانات فعلية من قاعدة التجربة', 'Live figures from demo database')}</div></div>`; }
function footer() { return `<footer class="footer"><span>© 2026 Mind Script · eng.rabe3 · UniGate</span><span>${L('نموذج تعليمي؛ لا يُستخدم في تسجيل جامعي إنتاجي.', 'Educational prototype — not for production university registration.')}</span></footer>`; }
function navHtml() { return roleList().map(([key, icon]) => `<button class="nav-btn ${S.page === key ? 'active' : ''}" data-action="go" data-page="${key}"><span class="nav-icon">${icon}</span><span>${t(key)}</span>${key === 'basket' && S.basket.length ? `<span class="pillnum">${S.basket.length}</span>` : ''}</button>`).join(''); }
function renderLayout() {
    if (!S.user)
        return renderLogin(); const user = S.user; $('#app').innerHTML = `<div class="layout"><aside class="sidebar"><div class="logo"><span class="logo-mark">UG</span><div><div class="logo-title">UniGate</div><div class="logo-sub">MIND SCRIPT · eng.rabe3</div></div></div><div class="nav-caption">${L('مساحة العمل', 'WORKSPACE')}</div><div class="nav">${navHtml()}</div><div class="sidebar-bottom"><div class="team"><b>eng.rabe3</b><div class="small muted">${L('نظام تسجيل المقررات — نسخة اختبارية', 'Course registration — sandbox application')}</div></div><div class="user-mini"><span class="avatar">${esc((lang() === 'ar' ? user.name_ar : user.name_en).slice(0, 1))}</span><div style="min-width:0;flex:1"><div class="mini-name">${esc(lang() === 'ar' ? user.name_ar : user.name_en)}</div><div class="small muted">${roleText(user.role)} · @${esc(user.username)}</div></div></div><button class="btn ghost full" data-action="logout">↪ ${t('logout')}</button></div></aside><div class="main"><div class="topbar"><div class="btnrow"><button class="iconbtn mobileMenu" data-action="menu" aria-label="Menu">☰</button><span class="path">${t(S.page)}</span></div><div class="top-actions"><span class="role-tag">● ${t('liveDemo')}</span><button class="iconbtn" data-action="lang">${lang() === 'ar' ? 'EN' : 'عربي'}</button><button class="iconbtn" data-action="theme">${theme() === 'dark' ? '☀' : '☾'}</button></div></div><main class="content" id="page"><div class="spinner"></div></main></div></div>`;
}
function show(html) { $('#page').innerHTML = html + footer(); }
async function load() {
    const d = await api('bootstrap');
    S.user = d.user;
    S.stats = d.stats;
    S.basket = role() === 'student' ? (await api('basket')).section_ids : [];
    await go(S.page);
}
async function go(page) {
    if (!roleList().some(x => x[0] === page))
        page = 'dashboard';
    S.page = page;
    document.body.classList.remove('menu-open');
    renderLayout();
    const p = $('#page');
    p.innerHTML = `<div class="boot" style="min-height:350px"><div class="spinner"></div></div>`;
    try {
        if (page === 'dashboard')
            await pageDashboard();
        else if (page === 'catalog')
            await pageCatalog();
        else if (page === 'basket')
            await pageBasket();
        else if (page === 'schedule')
            await pageSchedule();
        else if (page === 'swap')
            await pageSwaps();
        else if (page === 'waitlist')
            await pageWaitlist();
        else if (page === 'payment')
            await pagePayment();
        else if (page === 'students')
            await pageStudents();
        else if (page === 'sections')
            await pageSections();
        else if (page === 'payments')
            await pageFinance();
        else if (page === 'settings')
            await pageSettings();
        else if (page === 'audit')
            await pageAudit();
        else if (page === 'lab')
            pageLab();
        else
            pageAbout();
    }
    catch (e) {
        p.innerHTML = `<div class="notice error">${esc(e.message)}</div>`;
        if (e.status === 401) {
            S.user = null;
            renderLogin();
        }
    }
}
function renderLogin(mode = 'login') {
    S.user = null;
    const signing = mode === 'signup';
    const ar = lang() === 'ar';
    const toggle = `<div class="auth-tabs" role="group" aria-label="Account access">
      <button class="auth-tab ${!signing ? 'active' : ''}" data-action="authMode" data-mode="login" type="button">${L('تسجيل الدخول', 'Sign in')}</button>
      <button class="auth-tab ${signing ? 'active' : ''}" data-action="authMode" data-mode="signup" type="button">${L('إنشاء حساب طالب', 'Student sign up')}</button></div>`;
    const form = signing ? `<form id="signupForm" class="auth-form">
      <div class="field"><label for="signupName">${L('الاسم الكامل', 'Full name')}</label><input id="signupName" name="name" minlength="3" maxlength="100" required autocomplete="name" placeholder="${L('اسم الطالب الثلاثي', 'Student full name')}" /></div>
      <div class="field"><label for="signupNumber">${L('الرقم الجامعي', 'University ID')}</label><input id="signupNumber" name="student_number" dir="ltr" maxlength="24" minlength="3" pattern="[A-Za-z0-9_-]{3,24}" required autocomplete="username" placeholder="202612345" /></div>
      <div class="field"><label for="signupPassword">${L('كلمة المرور', 'Password')}</label><input id="signupPassword" name="password" type="password" minlength="10" maxlength="128" required autocomplete="new-password" /></div>
      <div class="field"><label for="signupConfirm">${L('تأكيد كلمة المرور', 'Confirm password')}</label><input id="signupConfirm" name="confirm" type="password" minlength="10" maxlength="128" required autocomplete="new-password" /></div>
      <p class="muted small">${L('10 أحرف على الأقل، وتتضمن حروفًا وأرقامًا. الرقم الجامعي يصبح اسم الدخول الخاص بك.', 'Minimum 10 characters including letters and digits. Your university ID becomes your login name.')}</p>
      <button class="btn full" type="submit">${L('إنشاء حساب الطالب', 'Create student account')} →</button></form>`
        : `<form id="loginForm" class="auth-form">
      <div class="field"><label for="loginUser">${L('الرقم الجامعي أو اسم الموظف', 'University ID or staff login')}</label><input name="username" id="loginUser" maxlength="128" required autocomplete="username" /></div>
      <div class="field"><label for="loginPw">${t('password')}</label><input name="password" id="loginPw" type="password" required autocomplete="current-password" /></div>
      <button class="btn full" type="submit">${t('enter')} ←</button></form>`;
    $('#app').innerHTML = `<div class="login-bg"><section class="login-brand"><div class="login-text"><div class="logo"><span class="logo-mark">UG</span><div><div class="logo-title" style="color:white">UniGate</div><div class="logo-sub">MIND SCRIPT · eng.rabe3</div></div></div><div class="eyebrow">COURSE REGISTRATION EXPERIENCE</div><h1>${L('حسابك الجامعي. مقرراتك. بياناتك محفوظة.', 'Your university account. Your courses, saved.')}</h1><p>${L('أنشئ حساب طالب مرة واحدة، ثم عد إليه في أي وقت لتجد جدولك وسلتك وبياناتك محفوظة في قاعدة البيانات.', 'Create a student account once, and return to your saved schedule and choices anytime.')}</p><div class="login-points"><span>${L('إنشاء الحساب متاح للطلاب فقط', 'Self-registration is for students only')}</span><span>${L('صلاحيات المدير والموظفين تُنشأ محلياً بإجراء إداري', 'Staff roles require secure local provisioning')}</span></div></div></section><section class="login-side"><div class="login-panel"><div class="btnrow" style="justify-content:flex-end"><button class="iconbtn" data-action="lang">${ar ? 'EN' : 'عربي'}</button><button class="iconbtn" data-action="theme">${theme() === 'dark' ? '☀' : '☾'}</button></div><div class="eyebrow">UNIGATE</div><h2>${signing ? L('إنشاء حساب جديد', 'Create your account') : t('welcome')}</h2><p>${signing ? L('املأ بياناتك لإنشاء حساب طالب جديد. لا يمكن إنشاء حساب إداري من هذه الصفحة.', 'Enter your details to create a student account. Staff accounts cannot be created here.') : L('الطلاب يدخلون بالرقم الجامعي؛ الموظفون يستخدمون بيانات الدخول التي يحددها المدير.', 'Students log in with their university ID; staff use privately assigned credentials.')}</p>${toggle}${form}<div class="notice" style="margin-top:18px">${L('بيئة تعليمية محلية؛ لا تدخل بيانات حساسة حقيقية هذه فقط نسخة تجريبية .', 'Local learning environment; Do not enter real sensitive data This is just a trial version.')}</div><div class="login-end muted small"><span>Phase One · Task </span><span>Eng.Rabe3</span></div></div></section></div>`;
}
