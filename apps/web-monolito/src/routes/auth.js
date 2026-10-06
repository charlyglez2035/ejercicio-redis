const express = require('express');
const router = express.Router();
const loginServiceUrl = (process.env.LOGIN_SERVICE_URL || 'http://localhost:5000').replace(/\/$/, '');

async function callLoginService(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  const response = await fetch(`${loginServiceUrl}${path}`, {
    ...options,
    headers
  });
  const body = await response.json();
  return { response, body };
}

router.get('/login', (req, res) => res.render('auth/login', { title: 'Iniciar sesion' }));
router.post('/login', async (req, res, next) => {
  try {
    const { response, body } = await callLoginService('/login?format=json', {
      method: 'POST',
      body: JSON.stringify({ identity: req.body.identity, password: req.body.password })
    });
    if (!response.ok) return res.redirect(`/login?error=${encodeURIComponent(body.error || 'Credenciales invalidas')}`);
    const user = body.user;
    req.session.user = { id: user.id, username: user.username, fullName: user.full_name, role: user.role };
    req.session.createdAt = Date.now();
    req.session.lastActivity = Date.now();
    req.session.cookie.maxAge = Number(process.env.SESSION_TIMEOUT_MINUTES || 30) * 60 * 1000;
    req.session.accessToken = body.access_token;
    res.redirect('/books?notice=Sesion%20iniciada');
  } catch (error) { next(error); }
});
router.get('/register', (req, res) => res.render('auth/register', { title: 'Crear cuenta' }));
router.post('/register', async (req, res, next) => {
  try {
    const { response, body } = await callLoginService('/register?format=json', {
      method: 'POST',
      body: JSON.stringify(req.body)
    });
    if (!response.ok) return res.redirect(`/register?error=${encodeURIComponent(body.error || 'No se pudo crear la cuenta')}`);
    res.redirect('/login?notice=Cuenta%20creada.%20Revisa%20tu%20correo%20para%20verificarla');
  } catch (error) { next(error); }
});
router.post('/logout', async (req, res, next) => {
  try {
    if (req.session.accessToken) {
      await callLoginService('/logout?format=json', {
        method: 'POST',
        headers: { Authorization: `Bearer ${req.session.accessToken}` }
      });
    }
    req.session.destroy(() => res.redirect('/books'));
  } catch (error) { next(error); }
});
module.exports = router;
