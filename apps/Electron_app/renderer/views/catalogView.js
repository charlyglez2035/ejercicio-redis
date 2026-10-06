const STOCK_COVERS = [
  'https://images.unsplash.com/photo-1543002588-bfa74002ed7e?auto=format&fit=crop&w=600&q=80',
  'https://images.unsplash.com/photo-1512820790803-83ca734da794?auto=format&fit=crop&w=600&q=80',
  'https://images.unsplash.com/photo-1495446815901-a7297e633e8d?auto=format&fit=crop&w=600&q=80',
  'https://images.unsplash.com/photo-1521587760476-6c12a4b040da?auto=format&fit=crop&w=600&q=80',
  'https://images.unsplash.com/photo-1544947950-fa07a98d237f?auto=format&fit=crop&w=600&q=80'
];

class CatalogView {
  constructor() {
    this.endpointInput = document.querySelector('#endpoint-input');
    this.catalog = document.querySelector('#catalog');
    this.status = document.querySelector('#status');
    this.emptyState = document.querySelector('#empty-state');
    this.bookCount = document.querySelector('#book-count');
    this.lastUpdated = document.querySelector('#last-updated');
    this.pageIndicator = document.querySelector('#page-indicator');
    this.previousPage = document.querySelector('#previous-page');
    this.nextPage = document.querySelector('#next-page');
    this.refreshButton = document.querySelector('#refresh-button');
    this.saveEndpointButton = document.querySelector('#save-endpoint');
  }

  bindEvents(handlers) {
    this.refreshButton.addEventListener('click', handlers.onRefresh);
    this.saveEndpointButton.addEventListener('click', handlers.onSaveEndpoint);
    this.previousPage.addEventListener('click', handlers.onPreviousPage);
    this.nextPage.addEventListener('click', handlers.onNextPage);
  }

  setEndpoint(endpoint) {
    this.endpointInput.value = endpoint;
  }

  getEndpoint() {
    return this.endpointInput.value.trim();
  }

  showLoading() {
    this.catalog.innerHTML = '';
    this.emptyState.hidden = true;
    this.setStatus('Cargando libros desde el servicio XML...');
  }

  showError(message) {
    this.bookCount.textContent = '0';
    this.emptyState.hidden = false;
    this.setStatus(message, true);
  }

  showCatalog(books, page, pageSize) {
    const pages = Math.max(1, Math.ceil(books.length / pageSize));
    const first = (page - 1) * pageSize;
    const visibleBooks = books.slice(first, first + pageSize);

    this.catalog.innerHTML = visibleBooks.map((book, index) => this.cardTemplate(book, index)).join('');
    this.emptyState.hidden = books.length > 0;
    this.bookCount.textContent = books.length;
    this.pageIndicator.textContent = `Página ${page} de ${pages}`;
    this.previousPage.disabled = page === 1;
    this.nextPage.disabled = page === pages;
    this.catalog.querySelectorAll('img').forEach((image) => image.addEventListener('error', () => {
      image.replaceWith(this.fallbackCover(image.alt));
    }));
  }

  showUpdated(count) {
    this.lastUpdated.textContent = `Actualizado ${new Date().toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })}`;
    this.setStatus(`${count} libros cargados bajo demanda.`);
  }

  setStatus(message, isError = false) {
    this.status.textContent = message;
    this.status.className = `status${isError ? ' error' : ''}`;
  }

  cardTemplate(book, index) {
    const cover = `<img src="${this.escapeHtml(book.image || this.stockCover(book, index))}" alt="Portada de ${this.escapeHtml(book.title)}">`;
    return `<article class="book-card" style="animation-delay:${index * 35}ms"><div class="book-cover">${cover}</div><div class="book-content"><h2 class="book-title">${this.escapeHtml(book.title)}</h2><p class="book-author">${this.escapeHtml(book.authors)}</p><dl class="metadata"><div><dt>ISBN</dt><dd>${this.escapeHtml(book.isbn)}</dd></div><div><dt>Año</dt><dd>${this.escapeHtml(book.year)}</dd></div><div><dt>Género</dt><dd>${this.escapeHtml(book.genre)}</dd></div><div><dt>Stock</dt><dd class="stock">${this.escapeHtml(book.stock)}</dd></div><div><dt>Precio</dt><dd class="price">${this.escapeHtml(book.price)} ${this.escapeHtml(book.currency)}</dd></div></dl></div></article>`;
  }

  fallbackCover(title) {
    const element = document.createElement('div');
    element.className = 'cover-fallback';
    element.textContent = title;
    return element;
  }

  stockCover(book, index) {
    const source = `${book.isbn || book.title}-${index}`;
    const hash = [...source].reduce((total, character) => total + character.charCodeAt(0), 0);
    return STOCK_COVERS[hash % STOCK_COVERS.length];
  }

  escapeHtml(value) {
    return String(value).replace(/[&<>'"]/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[character]);
  }
}

globalThis.CatalogView = CatalogView;
