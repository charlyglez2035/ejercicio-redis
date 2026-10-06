const PAGE_SIZE = 8;

class CatalogController {
  constructor(model, view) {
    this.model = model;
    this.view = view;
    this.books = [];
    this.page = 1;
  }

  init() {
    this.view.setEndpoint(this.model.getEndpoint());
    this.view.bindEvents({
      onRefresh: () => this.loadCatalog(),
      onSaveEndpoint: () => this.saveEndpoint(),
      onPreviousPage: () => this.changePage(-1),
      onNextPage: () => this.changePage(1)
    });
    this.loadCatalog();
  }

  async loadCatalog() {
    const endpoint = this.view.getEndpoint();
    this.view.showLoading();
    try {
      this.books = await this.model.fetchBooks(endpoint);
      this.page = 1;
      this.model.saveEndpoint(endpoint);
      this.renderPage();
      this.view.showUpdated(this.books.length);
    } catch (error) {
      this.books = [];
      this.view.showError(error.message || 'No se pudo cargar el catálogo.');
    }
  }

  saveEndpoint() {
    try {
      this.model.saveEndpoint(this.view.getEndpoint());
      this.loadCatalog();
    } catch (error) {
      this.view.showError(error.message);
    }
  }

  changePage(direction) {
    const pages = Math.max(1, Math.ceil(this.books.length / PAGE_SIZE));
    this.page = Math.min(Math.max(this.page + direction, 1), pages);
    this.renderPage();
  }

  renderPage() {
    this.view.showCatalog(this.books, this.page, PAGE_SIZE);
  }
}

globalThis.CatalogController = CatalogController;
