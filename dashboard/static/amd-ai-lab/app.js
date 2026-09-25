const dialog = document.querySelector('[data-detail-dialog]');
const openButton = document.querySelector('[data-open-detail]');
const closeButton = document.querySelector('[data-close-detail]');

openButton?.addEventListener('click', () => dialog.showModal());
closeButton?.addEventListener('click', () => dialog.close());
dialog?.addEventListener('click', (event) => {
  if (event.target === dialog) dialog.close();
});
