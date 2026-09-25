const dialog = document.querySelector('[data-detail-dialog]');
const dialogContent = document.querySelector('[data-dialog-content]');
const closeButton = document.querySelector('[data-close-detail]');
const catalogGrid = document.querySelector('[data-catalog-grid]');
const filters = [...document.querySelectorAll('[data-filter]')];
let records = [];

const statusLabel = (status) => status === 'measured' ? 'Measured' : status === 'planned' ? 'Planned' : 'Observed';
const statusClass = (status) => `status-${status}`;

function renderCatalog(filter = 'all') {
  const visible = records.filter((record) => filter === 'all' || record.hardware.includes(filter));
  const cards = visible.map((record) => `
    <article class="catalog-card">
      <div class="catalog-card-top"><span class="status ${statusClass(record.status)}"><i></i> ${statusLabel(record.status)}</span><span class="run-id">${record.id}</span></div>
      <div><h3>${record.title}</h3><div class="hardware">${record.hardware}</div><div class="headline">${record.headline}</div></div>
      <div class="catalog-card-bottom"><span class="detail">${record.detail}</span><span class="source">${record.source.split('/').slice(-1)[0]}</span></div>
    </article>`).join('');
  catalogGrid.innerHTML = cards || '<div class="loading">No records match this hardware filter.</div>';
}

async function loadCatalog() {
  try {
    const response = await fetch('data/catalog.json');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    records = (await response.json()).records;
    renderCatalog();
  } catch (error) {
    catalogGrid.innerHTML = `<div class="loading">Catalog unavailable: ${error.message}</div>`;
  }
}

function openDetail(record) {
  if (!dialog || !dialogContent) return;
  dialogContent.innerHTML = `<div class="catalog-card-top"><span class="status ${statusClass(record.status)}"><i></i> ${statusLabel(record.status)} record</span><span class="run-id">${record.id}</span></div><p class="card-eyebrow">AMD AI LAB / EVIDENCE RECORD</p><h2 id="detail-title">${record.title}</h2><p class="dialog-lede">${record.detail}</p><div class="detail-table"><div><span>Headline</span><strong>${record.headline}</strong></div><div><span>Hardware</span><strong>${record.hardware}</strong></div></div><div class="dialog-source">Source record: <code>${record.source}</code></div>`;
  dialog.showModal();
}

filters.forEach((filter) => filter.addEventListener('click', () => {
  filters.forEach((item) => item.classList.toggle('active', item === filter));
  renderCatalog(filter.dataset.filter);
}));

catalogGrid?.addEventListener('click', (event) => {
  const card = event.target.closest('.catalog-card');
  if (!card) return;
  const index = [...catalogGrid.querySelectorAll('.catalog-card')].indexOf(card);
  const visible = records.filter((record) => document.querySelector('.filter.active')?.dataset.filter === 'all' || record.hardware.includes(document.querySelector('.filter.active')?.dataset.filter));
  if (visible[index]) openDetail(visible[index]);
});

closeButton?.addEventListener('click', () => dialog.close());
dialog?.addEventListener('click', (event) => { if (event.target === dialog) dialog.close(); });
loadCatalog();
