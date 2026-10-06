const SESSION_TIMEOUT_MS = Number(process.env.SESSION_TIMEOUT_MINUTES || 30) * 60 * 1000;

function sessionExpired(req) {
  if (!req.session || !req.session.user) return false;
  const lastActivity = req.session.lastActivity || req.session.createdAt || Date.now();
  return Date.now() - lastActivity > SESSION_TIMEOUT_MS;
}

function requireAuth(req, res, next) {
  if (!req.session || !req.session.user) {
    return res.redirect('/login?error=Inicia%20sesion%20para%20continuar');
  }

  if (sessionExpired(req)) {
    return req.session.destroy(() => {
      res.clearCookie('connect.sid');
      res.redirect('/login?error=Tu%20sesion%20ha%20caducado%20por%20inactividad.');
    });
  }

  req.session.lastActivity = Date.now();
  req.session.cookie.maxAge = SESSION_TIMEOUT_MS;
  next();
}

function requireAdmin(req, res, next) {
  if (!req.session || !req.session.user) {
    return res.redirect('/login?error=Inicia%20sesion%20para%20continuar');
  }

  if (sessionExpired(req)) {
    return req.session.destroy(() => {
      res.clearCookie('connect.sid');
      res.redirect('/login?error=Tu%20sesion%20ha%20caducado%20por%20inactividad.');
    });
  }

  if (req.session.user.role !== 'admin') {
    return res.status(403).render('error', { title: 'Acceso denegado', message: 'Necesitas permisos de administrador.' });
  }

  req.session.lastActivity = Date.now();
  req.session.cookie.maxAge = SESSION_TIMEOUT_MS;
  next();
}

module.exports = { requireAuth, requireAdmin };
