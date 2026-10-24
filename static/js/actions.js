document.addEventListener('click', ev => {
    const el = ev.target.closest('[data-action]');
    if (!el)
        return;
    const a = el.dataset.action;
    guard(async () => {
        if (a === 'lang') {
            setLang();
            return;
        }
        if (a === 'theme') {
            setTheme();
            return;
        }
        if (a === 'menu') {
            document.body.classList.toggle('menu-open');
            return;
        }
        if (a === 'authMode') {
            S.authMode=el.dataset.mode;
            renderLogin(S.authMode);
            return;
        }
        if (a === 'go') {
            if (el.dataset.page !== 'students')
                S.profileStudentId = null;
            await go(el.dataset.page);
            return;
        }
        if (a === 'logout') {
            await api('logout', 'POST', {});
            S.user = null;
            S.catalog = [];
            S.basket = [];
            S.me = null;
            renderLogin();
            return;
        }
        if (a === 'addBasket') {
            const id = Number(el.dataset.id), s = S.catalog.find(s => s.id === id);
            if (S.basket.includes(id))
                return;
            if (S.basket.some(x => S.catalog.find(v => v.id === x)?.course_id === s.course_id)) {
                toast(L('اختر شعبة واحدة لكل مقرر', 'Only one section per course'), true);
                return;
            }
            S.basket = (await api('basket','POST',{action:'add',section_id:id})).section_ids;
            await go('catalog');
            toast(L('تمت الإضافة إلى السلة — لم يُحجز المقعد بعد', 'Added to basket; no seat reserved yet'));
            return;
        }
        if (a === 'removeBasket') {
            S.basket = (await api('basket','POST',{action:'remove',section_id:Number(el.dataset.id)})).section_ids;
            if (S.page === 'basket')
                await go('basket');
            else
                await go('catalog');
            return;
        }
        if (a === 'clearBasket') {
            S.basket = (await api('basket','POST',{action:'clear'})).section_ids;
            await go('basket');
            return;
        }
        if (a === 'checkout') {
            if (!S.basket.length)
                return;
            el.disabled = true;
            try {
                const x = await api('register', 'POST', { section_ids: S.basket, request_key: uid() });
                toast(L('نجح تسجيل: ', 'Confirmed: ') + x.codes.join(', '));
                S.basket = (await api('basket','POST',{action:'clear'})).section_ids;
                S.catalog = [];
                await go('schedule');
            }
            finally {
                el.disabled = false;
            }
            return;
        }
        if (a === 'requestSwap') {
            const from = Number(el.dataset.from), target = $('#swapTarget_' + from);
            if (!target)
                return;
            const result = await api('swap/request', 'POST', { from_section_id: from, to_section_id: Number(target.value) });
            toast(result.status === 'matched' ? L('تم التبديل بأمان', 'Swap successfully completed') : L('تم حفظ طلب التبديل؛ ننتظر الطلب العكسي', 'Swap request queued'));
            await go('swap');
            return;
        }
        if (a === 'cancelSwap') {
            await api('swap/cancel', 'POST', { request_id: Number(el.dataset.id) });
            toast(L('أُلغي طلب التبديل', 'Swap request cancelled'));
            await go('swap');
            return;
        }
        if (a === 'joinWaitlist') {
            const x = await api('waitlist/join', 'POST', { section_id: Number(el.dataset.id) });
            toast(L('أُضيف الطلب إلى قائمة الانتظار', 'Joined waitlist'));
            await go('waitlist');
            return;
        }
        if (a === 'leaveWaitlist') {
            await api('waitlist/leave', 'POST', { waitlist_id: Number(el.dataset.id) });
            toast(L('ألغيت طلب الانتظار', 'Waitlist request cancelled'));
            await go('waitlist');
            return;
        }
        if (a === 'drop') {
            if (!confirm(L('هل تريد الانسحاب من هذه الشعبة؟ قد يُمنح المقعد لمستخدم في الانتظار.', 'Drop this section? Seat may be assigned to a waiting student.')))
                return;
            const x = await api('drop', 'POST', { enrollment_id: Number(el.dataset.id) });
            toast(L('تم الانسحاب. ترقية منتظرين: ', 'Dropped. Promoted: ') + x.promotion.promoted.length);
            await go('schedule');
            return;
        }
        if (a === 'pay') {
            const x = await api('payment/request', 'POST', { outcome: el.dataset.outcome, request_key: uid() });
            toast(L('دفعة افتراضية: ', 'Simulated payment: ') + x.payment.reference);
            await go('payment');
            return;
        }
        if (a === 'reconcile') {
            await api('payment/reconcile', 'POST', { payment_id: Number(el.dataset.id), status: el.dataset.status });
            toast(L('تمت مطابقة الدفعة', 'Payment reconciled'));
            await go('payments');
            return;
        }
        if (a === 'searchStudents') {
            S.studentSearch = $('#studentSearch')?.value?.trim() || '';
            await go('students');
            return;
        }
        if (a === 'toggleCreateStudent') {
            S.showStudentCreate = !S.showStudentCreate;
            await go('students');
            return;
        }
        if (a === 'openStudentProfile') {
            S.profileStudentId = Number(el.dataset.id);
            await go('students');
            return;
        }
        if (a === 'closeStudentProfile') {
            S.profileStudentId = null;
            await go('students');
            return;
        }
        if (a === 'removePlan') {
            if (!confirm(L('إزالة المقرر من الخطة؟ لا تُحذف العلامة.', 'Remove course from plan? Its grade remains.')))
                return;
            await api('affairs/academic', 'POST', { operation: 'plan_remove', user_id: +el.dataset.student, course_id: +el.dataset.course, reason: 'Removal from assigned student plan / حذف من الخطة المعينة' });
            S.profileStudentId = +el.dataset.student;
            await pageStudentProfile(S.profileStudentId);
            toast(L('تم تعديل الخطة', 'Plan updated'));
            return;
        }
        if (a === 'hold') {
            await api('affairs/hold', 'POST', { user_id: Number(el.dataset.id), hold: el.dataset.hold === '1' });
            toast(L('تم تحديث القيد الإداري', 'Student hold updated'));
            await go('students');
            return;
        }
        if (a === 'toggleReg') {
            await api('admin/settings', 'POST', { key: 'registration_enabled', value: el.dataset.value });
            toast(L('تم تحديث وضع التسجيل', 'Registration setting updated'));
            S.stats = (await api('bootstrap')).stats;
            await go('settings');
            return;
        }
        if (a === 'resetDB') {
            if (!confirm(L('سيتم مسح كل بيانات التجربة، بما فيها تسجيلاتكم. هل أنت متأكد؟', 'This permanently clears all sandbox records. Continue?')))
                return;
            const confirmation = prompt(L('اكتب RESET DEMO للتأكيد', 'Type RESET DEMO to confirm'));
            if (confirmation !== 'RESET DEMO')
                return;
            await api('admin/reset', 'POST', { confirmation });
            S.user = null;
            S.basket = [];
            S.catalog = [];
            toast(L('أعيدت قاعدة البيانات إلى حالتها الأولى', 'Database restored to initial demo data'));
            renderLogin();
            return;
        }
        if (a === 'runLab') {
            el.disabled = true;
            try {
                S.labSelected = Number(el.dataset.id);
                S.labResult = await api('lab/run', 'POST', { case: S.labSelected });
                document.querySelectorAll('[data-action="runLab"]').forEach(b => b.classList.toggle('secondary', Number(b.dataset.id) !== S.labSelected));
                renderLabResult();
            }
            finally {
                el.disabled = false;
            }
            return;
        }
    });
});
document.addEventListener('submit', ev => {
    const form = ev.target;
    if (!form.id && !form.dataset.form)
        return;
    ev.preventDefault();
    guard(async () => {
        const data = Object.fromEntries(new FormData(form));
        if (form.id === 'signupForm') {
            if (data.password !== data.confirm) {
                toast(L('كلمتا المرور غير متطابقتين','Passwords do not match'),true);
                return;
            }
            await api('signup','POST',{name:data.name,student_number:data.student_number,password:data.password});
            S.page='dashboard';
            S.catalog=[];
            S.authMode='login';
            await load();
            toast(L('تم إنشاء حسابك، وبياناتك محفوظة في قاعدة البيانات','Your account is created and saved in the database'));
            return;
        }
        if (form.id === 'loginForm') {
            await api('login', 'POST', { username: data.username, password: data.password });
            S.catalog = [];
            S.basket = [];
            S.page = 'dashboard';
            await load();
            return;
        }
        if (form.dataset.form === 'capacity') {
            const result = await api('section/capacity', 'POST', { section_id: Number(form.dataset.id), capacity: Number(data.capacity) });
            toast(L('تم تحديث السعة. ترقية منتظرين: ', 'Capacity updated. Promoted: ') + result.promotion.promoted.length);
            S.catalog = [];
            await go('sections');
            return;
        }
        if (form.id === 'newSectionForm') {
            await api('section/create', 'POST', { course_id: +data.course_id, label: data.label, capacity: +data.capacity, weekday: +data.weekday, start_time: +data.start_time, end_time: +data.end_time });
            toast(L('تم إنشاء الشعبة', 'Section created'));
            S.catalog = [];
            await go('sections');
            return;
        }
        if (form.id === 'studentCreateForm') {
            const result = await api('affairs/student/create', 'POST', {
                username: data.username, name_ar: data.name_ar, name_en: data.name_en,
                student_number: data.student_number, phone: data.phone || '', email: data.email || '', reason: data.reason
            });
            S.showStudentCreate = false;
            S.studentSearch = '';
            await go('students');
            const container = document.createElement('div');
            container.className = 'card';
            container.style.marginBottom = '18px';
            container.innerHTML = `<h3>${L('تم إنشاء حساب الطالب', 'Student account created')}</h3><p>${L('اسم الدخول', 'Username')}: <b>${esc(result.username)}</b></p><p>${L('كلمة المرور المؤقتة (تظهر مرة واحدة)', 'Temporary password (shown once)')}: <code style="user-select:all">${esc(result.temporary_password)}</code></p><p class="muted">${L('انسخ كلمة المرور الآن وشاركها بشكل آمن؛ لا تظهر في سجلات التدقيق.', 'Copy now and share securely. This password is not included in audit logs.')}</p>`;
            const page = $('#page');
            page.prepend(container);
            toast(L('تم إنشاء الطالب وتوثيق العملية', 'Student created and audited'));
            return;
        }
        if (form.id === 'studentProfileForm') {
            const result = await api('affairs/student/profile', 'POST', { user_id: Number(data.user_id), name_ar: data.name_ar, name_en: data.name_en, student_number: data.student_number, phone: data.phone, email: data.email, reason: data.reason });
            toast(result.changed_fields.length ? L('تم حفظ بيانات الطالب وتوثيق التعديل', 'Profile saved and audited') : L('لا توجد بيانات تغيرت', 'No changes detected'));
            await go('students');
            return;
        }
        if (form.id === 'planCourseForm' || form.id === 'numericGradeForm') {
            const action = form.id === 'planCourseForm' ? 'plan_add' : 'grade_record';
            const payload = { operation: action, user_id: +data.user_id, course_id: +data.course_id, reason: data.reason };
            if (action === 'plan_add')
                payload.required = data.required === 'true';
            else
                payload.score = Number(data.score);
            await api('affairs/academic', 'POST', payload);
            S.profileStudentId = +data.user_id;
            await pageStudentProfile(S.profileStudentId);
            toast(action === 'plan_add' ? L('تم تحديث الخطة', 'Study plan saved') : L('تم تحديث العلامة والمعدل', 'Grade and GPA updated'));
            return;
        }
        if (form.id === 'gradeForm') {
            const x = await api('affairs/grade', 'POST', { user_id: +data.user_id, course_id: +data.course_id, passed: data.passed === 'true' });
            toast(L('تم تعديل الأهلية. تسجيلات تحتاج مراجعة: ', 'Grade updated. Enrollments needing review: ') + x.review_enrollments.length);
            await go('students');
            return;
        }
        if (form.id === 'exceptionForm') {
            await api('affairs/exception', 'POST', { user_id: +data.user_id, min_override: +data.min_override, reason: data.reason });
            toast(L('تم توثيق الاستثناء التجريبي', 'Demo exception recorded'));
            await go('students');
            return;
        }
        if (form.id === 'phaseForm') {
            await api('admin/settings', 'POST', { key: 'phase', value: data.value });
            toast(L('تم تحديث نافذة التسجيل', 'Registration phase updated'));
            S.stats = (await api('bootstrap')).stats;
            await go('settings');
            return;
        }
    });
});
