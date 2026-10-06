const express = require('express');

const router = express.Router();
const loginServiceUrl = (process.env.LOGIN_SERVICE_URL || 'http://localhost:5000').replace(/\/$/, '');
const booksServiceUrl = (process.env.BOOKS_SERVICE_URL || 'http://127.0.0.1:5001').replace(/\/$/, '');
const sessionTimeoutMs = Number(process.env.SESSION_TIMEOUT_MINUTES || 30) * 60 * 1000;

function requestId(req) {
  const supplied = req.get('x-request-id') || '';
  return /^[\w.-]{1,100}$/.test(supplied) ? supplied : require('crypto').randomUUID();
}

async function forward(req, res, serviceUrl, servicePath, method, body, withToken) {
  const id = requestId(req);
  const url = new URL(servicePath, serviceUrl);
  url.searchParams.set('format', 'json');
  const headers = { Accept: 'application/json', 'X-Request-ID': id };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (req.get('x-demo-without-token') !== 'true') {
    if (req.get('x-demo-reuse-revoked-token') === 'true' && req.session.revokedDemoToken) {
      headers.Authorization = `Bearer ${req.session.revokedDemoToken}`;
    } else if (req.get('x-demo-manipulate-token') === 'true') {
      headers.Authorization = 'Bearer invalid.jwt.token';
    } else if (withToken && req.session.accessToken) {
      headers.Authorization = `Bearer ${req.session.accessToken}`;
    }
  }

  try {
    const response = await fetch(url, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(10000)
    });
    const text = await response.text();
    let result;
    try { result = text ? JSON.parse(text) : null; }
    catch { result = { response: text.slice(0, 20000) }; }
    res.set('X-Request-ID', id);
    if (response.status === 401 && serviceUrl === loginServiceUrl
      && req.get('x-demo-reuse-revoked-token') !== 'true') {
      delete req.session.accessToken;
    }
    return res.status(response.status).json(result);
  } catch (error) {
    res.set('X-Request-ID', id);
    return res.status(502).json({ error: 'No se pudo contactar al microservicio.' });
  }
}

router.get('/jwt-demo', (req, res) => {
  res.render('jwt-demo', {
    title: 'Consola de peticiones',
    currentUser: req.session.user,
    notice: null,
    error: null
  });
});

router.post('/api/jwt/login', async (req, res) => {
  const id = requestId(req);
  try {
    const response = await fetch(`${loginServiceUrl}/login?format=json`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json', 'X-Request-ID': id },
      body: JSON.stringify({ identity: req.body.identity, password: req.body.password }),
      signal: AbortSignal.timeout(10000)
    });
    const body = await response.json();
    res.set('X-Request-ID', id);
    if (!response.ok) return res.status(response.status).json(body);
    req.session.accessToken = body.access_token;
    req.session.user = {
      id: body.user.id,
      username: body.user.username,
      fullName: body.user.full_name,
      role: body.user.role
    };
    req.session.createdAt = Date.now();
    req.session.lastActivity = Date.now();
    req.session.cookie.maxAge = sessionTimeoutMs;
    return res.status(response.status).json({
      message: body.message,
      user: body.user,
      token_type: body.token_type,
      expires_in: body.expires_in
    });
  } catch (error) {
    res.set('X-Request-ID', id);
    return res.status(502).json({ error: 'No se pudo contactar al servicio de login.' });
  }
});

router.get('/api/jwt/session', (req, res) => {
  return forward(req, res, loginServiceUrl, '/session', 'GET', undefined, true);
});

router.post('/api/jwt/logout', async (req, res) => {
  const id = requestId(req);
  let status = 200;
  let result = { message: 'Sesion cerrada.' };
  const accessToken = req.session.accessToken;
  if (accessToken) req.session.revokedDemoToken = accessToken;
  try {
    const headers = { Accept: 'application/json', 'X-Request-ID': id };
    if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
    const response = await fetch(`${loginServiceUrl}/logout?format=json`, {
      method: 'POST',
      headers,
      signal: AbortSignal.timeout(10000)
    });
    status = response.status;
    result = await response.json();
  } catch (error) {
    status = 502;
    result = { error: 'No se pudo contactar al servicio de login.' };
  }
  req.session.accessToken = null;
  req.session.user = null;
  res.set('X-Request-ID', id);
  return res.status(status).json(result);
});

router.get('/api/jwt/books', (req, res) =>
  forward(req, res, booksServiceUrl, '/api/books', 'GET', undefined, false));

router.post('/api/jwt/books', (req, res) => {
  const withoutToken = req.get('x-demo-without-token') === 'true';
  return forward(req, res, booksServiceUrl, '/api/books', 'POST', req.body, !withoutToken);
});

router.get('/api/jwt/books/:isbn', (req, res) =>
  forward(req, res, booksServiceUrl, `/api/books/${encodeURIComponent(req.params.isbn)}`, 'GET', undefined, false));

for (const method of ['put', 'patch', 'delete']) {
  router[method]('/api/jwt/books/:isbn', (req, res) => {
    const withoutToken = req.get('x-demo-without-token') === 'true';
    return forward(
      req,
      res,
      booksServiceUrl,
      `/api/books/${encodeURIComponent(req.params.isbn)}`,
      method.toUpperCase(),
      method === 'delete' ? undefined : req.body,
      !withoutToken
    );
  });
}

module.exports = router;