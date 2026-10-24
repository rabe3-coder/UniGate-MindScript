/** Section swap workflow. Uses the same state, helpers and API client as other pages. */
async function pageSwaps() {
    const data = await api('swap');
    const options = data.options.filter(item => item.targets.length);
    const rows = data.requests.map(request => `
    <tr>
      <td>${esc(request.code)}</td>
      <td>${esc(request.source_label)} → ${esc(request.target_label)}</td>
      <td>${badge(request.status, request.status === 'matched' ? 'teal' : 'blue')}</td>
      <td>${fmtdate(request.created_at)}</td>
      <td>${request.status === 'pending'
        ? `<button class="btn ghost sm" data-action="cancelSwap" data-id="${request.id}">${L('إلغاء الطلب', 'Cancel request')}</button>`
        : esc(request.explanation || '—')}</td>
    </tr>`).join('');
    const choices = options.map(item => `
    <div class="card">
      <h3>${esc(item.source.code)} — ${esc(item.source.label)}</h3>
      <p class="muted small">${L('اختر الشعبة التي ترغب بالانتقال إليها؛ لا يُنفّذ التبديل إلا عند العثور على طلب عكسي متوافق.', 'Choose a target section. The swap happens only if a compatible reciprocal request exists.')}</p>
      <div class="field">
        <label>${L('الشعبة المطلوبة', 'Target section')}</label>
        <select id="swapTarget_${item.source.section_id}">
          ${item.targets.map(t => `<option value="${t.id}">${esc(t.label)} · ${day(t.weekday)} ${time(t.start_time)}–${time(t.end_time)}</option>`).join('')}
        </select>
      </div>
      <button class="btn" data-action="requestSwap" data-from="${item.source.section_id}">${L('طلب تبديل', 'Request swap')}</button>
    </div>`).join('');
    show(heading(t('swap'), L('تبديل آمن بين شعبتين للمقرر نفسه، حتى لو كانتا ممتلئتين.', 'Exchange full sections safely when another student requests the reverse move.'))
        + `<div class="notice">${L('الطلبات بحسب الأسبقية. التبديل ذري، وتظل هوية الطالب الآخر مخفية. قد يُلغى الطلب إن تغيّر جدول أحد الطرفين.', 'FIFO matching, atomic change and no disclosure of the other student’s identity. Requests can become invalid if schedules change.')}</div>`
        + `<div class="sectionhead"><h2>${L('طلب تبديل جديد', 'New section swap')}</h2></div>`
        + `<div class="grid cols2">${choices || `<div class="empty">${L('لا توجد شعب بديلة لمقرراتك المسجلة.', 'No alternative sections for your enrolled courses.')}</div>`}</div>`
        + `<div class="sectionhead"><h2>${L('طلباتي السابقة', 'My swap requests')}</h2></div>`
        + `<div class="card">${rows ? `<div class="tablewrap"><table><thead><tr><th>${t('course')}</th><th>${L('التبديل', 'Swap')}</th><th>${t('status')}</th><th>${L('التاريخ', 'Date')}</th><th>${t('actions')}</th></tr></thead><tbody>${rows}</tbody></table></div>` :
            `<div class="empty">${L('لم ترسل طلبات تبديل بعد.', 'No swap requests yet.')}</div>`}</div>`);
}
