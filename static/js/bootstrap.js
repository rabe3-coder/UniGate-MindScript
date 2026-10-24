document.addEventListener('input', ev => { if (ev.target?.id === 'courseSearch') {
    S.search = ev.target.value;
    renderCatalogCards();
}
else if (ev.target?.id === 'eligibleOnly') {
    S.eligibleOnly = ev.target.checked;
    renderCatalogCards();
} });
applyStyle();
load().catch(() => renderLogin());
