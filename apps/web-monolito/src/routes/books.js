const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const db = require('../db');
const { requireAuth, requireAdmin } = require('../middleware/auth');
const router = express.Router();
const uploadDir = path.join(__dirname, '../../public/uploads');
fs.mkdirSync(uploadDir, { recursive: true });
const upload = multer({ dest: uploadDir, limits: { fileSize: 5 * 1024 * 1024 } });

async function options() {
  const [authors, genres, concepts, formats, categories] = await Promise.all([
    db.query('SELECT * FROM author ORDER BY name'), db.query('SELECT * FROM genre ORDER BY name'), db.query('SELECT * FROM concept ORDER BY name'), db.query('SELECT * FROM book_format ORDER BY name'), db.query('SELECT * FROM book_category ORDER BY name')
  ]);
  return { authors: authors.rows, genres: genres.rows, concepts: concepts.rows, formats: formats.rows, categories: categories.rows };
}
async function getBook(isbn) {
  const book = (await db.query(`SELECT b.*, f.name AS format_name, c.name AS category_name,
    COALESCE((SELECT string_agg(a.name, ', ' ORDER BY ba.author_order NULLS LAST, a.name) FROM book_author ba JOIN author a USING(author_id) WHERE ba.isbn=b.isbn), '') authors,
    COALESCE((SELECT string_agg(g.name, ', ' ORDER BY g.name) FROM book_genre bg JOIN genre g USING(genre_id) WHERE bg.isbn=b.isbn), '') genres
    FROM book b JOIN book_format f USING(format_id) JOIN book_category c USING(category_id) WHERE b.isbn=$1`, [isbn])).rows[0];
  if (!book) return null;
  book.images = (await db.query('SELECT * FROM book_image WHERE isbn=$1 ORDER BY display_order', [isbn])).rows;
  book.concepts = (await db.query('SELECT bc.*, c.name FROM book_concept bc JOIN concept c USING(concept_id) WHERE bc.isbn=$1 ORDER BY c.name', [isbn])).rows;
  return book;
}
router.get('/', async (req, res, next) => {
  try {
    const query = typeof req.query.q === 'string'
      ? req.query.q.trim()
      : '';

    const serviceUrl = process.env.BOOKS_SERVICE_URL
      || 'http://127.0.0.1:5001';

    const url = new URL('/books', serviceUrl);
    url.searchParams.set('format', 'json');

    const response = await fetch(url, {
      signal: AbortSignal.timeout(10000)
    });

    if (!response.ok) {
      throw new Error(`El microservicio respondió HTTP ${response.status}`);
    }

    const data = await response.json();

    if (!Array.isArray(data)) {
      throw new Error('El microservicio no devolvió una lista de libros');
    }

    // Adaptar los nombres que usa tu plantilla EJS.
    let books = data.map(book => ({
      ...book,
      format_name: book.format,
      category_name: book.category
    }));

    if (query) {
      const text = query.toLocaleLowerCase();

      books = books.filter(book =>
        [book.title, book.isbn, book.authors]
          .join(' ')
          .toLocaleLowerCase()
          .includes(text)
      );
    }

    res.render('books/index', {
      title: 'Catálogo',
      books,
      query
    });
  } catch (error) {
    console.error('Error al consultar Flask:', error);

    res.status(502).render('error', {
      title: 'Servicio no disponible',
      message: 'No se pudo consultar el catálogo. Verifica que Flask esté ejecutándose en el puerto 5001.'
    });
  }
});
router.get('/new', requireAuth, async (req, res, next) => { try { res.render('books/form', { title: 'Nuevo libro', book: {}, ...await options() }); } catch (e) { next(e); } });
router.get('/:isbn', async (req, res, next) => { try { const book = await getBook(req.params.isbn); if (!book) return res.status(404).render('error', { title: 'No encontrado', message: 'Libro no encontrado.' }); res.render('books/show', { title: book.title, book }); } catch (e) { next(e); } });
router.get('/:isbn/edit', requireAuth, async (req, res, next) => { try { const book = await getBook(req.params.isbn); res.render('books/form', { title: 'Editar libro', book, ...await options() }); } catch (e) { next(e); } });
router.post('/:isbn/delete', requireAuth, async (req, res, next) => { try { await db.query('DELETE FROM book WHERE isbn=$1', [req.params.isbn]); res.redirect('/books?notice=Libro%20eliminado'); } catch (e) { next(e); } });
router.post('/:isbn/images', requireAuth, upload.single('image'), async (req, res, next) => { try { if (!req.file) return res.redirect(`/books/${req.params.isbn}`); const imageUrl = `/uploads/${req.file.filename}`; await db.query('INSERT INTO book_image (isbn, image_url, alt_text, display_order, is_cover) VALUES ($1,$2,$3,COALESCE((SELECT max(display_order)+1 FROM book_image WHERE isbn=$1),1),false)', [req.params.isbn, imageUrl, req.body.alt_text || null]); res.redirect(`/books/${req.params.isbn}`); } catch (e) { next(e); } });
router.post('/:isbn/images/:imageId', requireAuth, async (req, res, next) => { try { await db.query('UPDATE book_image SET alt_text=$1, display_order=$2, is_cover=$3 WHERE image_id=$4 AND isbn=$5', [req.body.alt_text || null, req.body.display_order, req.body.is_cover === 'on', req.params.imageId, req.params.isbn]); res.redirect(`/books/${req.params.isbn}`); } catch (e) { next(e); } });
router.post('/:isbn/images/:imageId/delete', requireAuth, async (req, res, next) => { try { await db.query('DELETE FROM book_image WHERE image_id=$1 AND isbn=$2', [req.params.imageId, req.params.isbn]); res.redirect(`/books/${req.params.isbn}`); } catch (e) { next(e); } });
router.post('/:isbn', requireAuth, async (req, res, next) => {
  const client = await db.pool.connect();
  try { await client.query('BEGIN'); const body = req.body; const oldIsbn = req.params.isbn; await client.query(`INSERT INTO book (isbn,title,publication_year,price,stock,format_id,category_id) VALUES ($1,$2,NULLIF($3,''),$4,$5,$6,$7) ON CONFLICT (isbn) DO UPDATE SET title=EXCLUDED.title, publication_year=EXCLUDED.publication_year, price=EXCLUDED.price, stock=EXCLUDED.stock, format_id=EXCLUDED.format_id, category_id=EXCLUDED.category_id`, [body.isbn, body.title, body.publication_year, body.price, body.stock, body.format_id, body.category_id]); await client.query('DELETE FROM book_author WHERE isbn=$1', [body.isbn]); await client.query('DELETE FROM book_genre WHERE isbn=$1', [body.isbn]); await client.query('DELETE FROM book_concept WHERE isbn=$1', [body.isbn]); for (const id of [].concat(body.author_ids || [])) await client.query('INSERT INTO book_author(isbn,author_id) VALUES($1,$2)', [body.isbn, id]); for (const id of [].concat(body.genre_ids || [])) await client.query('INSERT INTO book_genre(isbn,genre_id) VALUES($1,$2)', [body.isbn, id]); for (const id of [].concat(body.concept_ids || [])) { const definition = body[`definition_${id}`]; if (definition) await client.query('INSERT INTO book_concept(isbn,concept_id,definition) VALUES($1,$2,$3)', [body.isbn, id, definition]); } if (oldIsbn !== body.isbn) await client.query('DELETE FROM book WHERE isbn=$1', [oldIsbn]); await client.query('COMMIT'); res.redirect(`/books/${body.isbn}?notice=Libro%20guardado`); } catch (e) { await client.query('ROLLBACK'); next(e); } finally { client.release(); }
});
module.exports = router;
