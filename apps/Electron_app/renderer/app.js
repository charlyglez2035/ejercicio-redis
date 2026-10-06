const model = new BookModel(window.libraryApi);
const view = new CatalogView();
const controller = new CatalogController(model, view);

controller.init();
