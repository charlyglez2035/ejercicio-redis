const DEFAULT_ENDPOINT = 'http://34.51.13.137:5001/books';
const STORAGE_KEY = 'library.endpoint';

class BookModel {
  constructor(api) {
    this.api = api;
  }

  getEndpoint() {
    return localStorage.getItem(STORAGE_KEY) || DEFAULT_ENDPOINT;
  }

  saveEndpoint(endpoint) {
    try {
      new URL(endpoint);
    } catch {
      throw new Error('Escribe una URL valida.');
    }
    localStorage.setItem(STORAGE_KEY, endpoint);
  }

  async fetchBooks(endpoint) {
    const xmlText = await this.api.fetchXml(endpoint);
    return this.parseXml(xmlText);
  }

  parseXml(xmlText) {
    const documentXml = new DOMParser().parseFromString(xmlText, 'application/xml');
    if (documentXml.querySelector('parsererror')) {
      throw new Error('La respuesta no contiene XML valido.');
    }

    const nodes = this.elements(documentXml, 'book');
    if (!nodes.length) {
      throw new Error('El XML no contiene libros.');
    }

    return nodes.map((book) => {
      const priceNode = this.elements(book, 'price')[0];
      const imageNodes = this.elements(book, 'image');
      const cover = imageNodes.find((image) => ['true', '1'].includes(this.text(image, 'iscover').toLowerCase())) || imageNodes[0];
      const authorNodes = this.elements(book, 'author');
      const authors = authorNodes.length
        ? authorNodes.map((author) => author.textContent.trim()).join(', ')
        : this.text(book, 'authors');

      return {
        title: this.text(book, 'title') || 'Sin titulo',
        isbn: this.text(book, 'isbn') || 'Sin ISBN',
        authors: authors || 'Autor desconocido',
        year: this.text(book, 'publication_year') || this.text(book, 'publicationyear') || 'N/D',
        genre: this.text(book, 'genre') || this.text(book, 'category') || 'N/D',
        price: this.text(book, 'price') || '0.00',
        currency: priceNode?.getAttribute('currency') || 'USD',
        stock: this.text(book, 'stock') || '0',
        image: cover ? this.text(cover, 'url') || this.text(cover, 'image_url') : ''
      };
    });
  }

  text(parent, tag) {
    return this.elements(parent, tag)[0]?.textContent.trim() || '';
  }

  elements(parent, tag) {
    const expected = tag.toLowerCase();
    return [...parent.getElementsByTagName('*')].filter((element) => {
      return (element.localName || element.tagName).toLowerCase() === expected;
    });
  }
}

globalThis.BookModel = BookModel;
