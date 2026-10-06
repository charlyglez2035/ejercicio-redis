const express = require('express');
const bcrypt = require('bcryptjs');
const db = require('../db');
const { requireAdmin } = require('../middleware/auth');
const router = express.Router();
const resources = { authors: ['author', 'author_id', 'name', null], genres: ['genre', 'genre_id', 'name', 'description'], concepts: ['concept', 'concept_id', 'name', null], formats: ['book_format', 'format_id', 'name', null], categories: ['book_category', 'category_id', 'name', 'description'] };
router.use(requireAdmin);
router.get('/', async (req, res, next) => { try { const counts = {}; for (const [key, [table]] of Object.entries(resources)) counts[key] = (await db.query(`SELECT count(*) FROM ${table}`)).rows[0].count; counts.books = (await db.query('SELECT count(*) FROM book')).rows[0].count; counts.users = (await db.query('SELECT count(*) FROM app_user')).rows[0].count; res.render('admin/index', { title: 'Administracion', counts }); } catch (e) { next(e); } });
router.get('/users', async (req, res, next) => { try { const users = (await db.query('SELECT user_id,username,email,full_name,role,created_at FROM app_user ORDER BY created_at DESC')).rows; res.render('admin/users', { title: 'Usuarios', users }); } catch (e) { next(e); } });
router.post('/users', async (req, res, next) => {
  try {
    const { username, email, full_name: fullName, password, role = 'customer' } = req.body;
    if (!username || !email || !fullName || !password) {
      return res.redirect('/admin/users?error=Completa%20todos%20los%20campos%20del%20nuevo%20usuario');
    }
    const passwordHash = await bcrypt.hash(password, 12);
    await db.query(
      'INSERT INTO app_user (username,email,full_name,password_hash,role,email_verified) VALUES ($1,$2,$3,$4,$5,TRUE)',
      [username.trim(), email.trim().toLowerCase(), fullName.trim(), passwordHash, role]
    );
    res.redirect('/admin/users?notice=Usuario%20creado');
  } catch (e) { next(e); }
});
router.post('/users/:id', async (req, res, next) => { try { const hash = req.body.password ? await bcrypt.hash(req.body.password, 12) : null; await db.query(`UPDATE app_user SET username=$1,email=$2,full_name=$3,role=$4, password_hash=COALESCE($5,password_hash) WHERE user_id=$6`, [req.body.username, req.body.email, req.body.full_name, req.body.role, hash, req.params.id]); res.redirect('/admin/users'); } catch (e) { next(e); } });
router.post('/users/:id/delete', async (req, res, next) => { try { if (String(req.session.user.id) === String(req.params.id)) return res.redirect('/admin/users?error=No%20puedes%20eliminar%20tu%20propia%20cuenta'); await db.query('DELETE FROM app_user WHERE user_id=$1', [req.params.id]); res.redirect('/admin/users?notice=Usuario%20eliminado'); } catch (e) { next(e); } });
for (const [key, [table, idColumn, nameColumn, descriptionColumn]] of Object.entries(resources)) {
  router.get(`/${key}`, async (req, res, next) => { try { const rows = (await db.query(`SELECT * FROM ${table} ORDER BY ${nameColumn}`)).rows; res.render('admin/resource', { title: key, key, table, idColumn, nameColumn, descriptionColumn, rows }); } catch (e) { next(e); } });
  router.post(`/${key}`, async (req, res, next) => { try { const values = descriptionColumn ? [req.body.name, req.body.description || null] : [req.body.name]; await db.query(`INSERT INTO ${table} (${nameColumn}${descriptionColumn ? ',description' : ''}) VALUES ($1${descriptionColumn ? ',$2' : ''})`, values); res.redirect(`/admin/${key}`); } catch (e) { next(e); } });
  router.post(`/${key}/:id`, async (req, res, next) => { try { const values = descriptionColumn ? [req.body.name, req.body.description || null, req.params.id] : [req.body.name, req.params.id]; await db.query(`UPDATE ${table} SET ${nameColumn}=$1${descriptionColumn ? ',description=$2' : ''} WHERE ${idColumn}=$${descriptionColumn ? 3 : 2}`, values); res.redirect(`/admin/${key}`); } catch (e) { next(e); } });
  router.post(`/${key}/:id/delete`, async (req, res, next) => { try { await db.query(`DELETE FROM ${table} WHERE ${idColumn}=$1`, [req.params.id]); res.redirect(`/admin/${key}`); } catch (e) { next(e); } });
}
module.exports = router;
