const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '../../../.env') });
const express = require('express');
const session = require('express-session');
const books = require('./routes/books');
const auth = require('./routes/auth');
const jwtDemo = require('./routes/jwt-demo');
const admin = require('./routes/admin');

const app = express();
const port = Number(process.env.PORT || 3000);
const SESSION_TIMEOUT_MS = Number(process.env.SESSION_TIMEOUT_MINUTES || 30) * 60 * 1000;
if (!process.env.SESSION_SECRET) {
  throw new Error('SESSION_SECRET debe configurarse en el entorno.');
}

app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, '../views'));
app.use(express.urlencoded({ extended: true }));
app.use(express.json({ limit: '64kb' }));
app.use(express.static(path.join(__dirname, '../public')));
app.use(session({
  secret: process.env.SESSION_SECRET,
  resave: false,
  saveUninitialized: false,
  rolling: false,
  cookie: {
    httpOnly: true,
    sameSite: 'lax',
    maxAge: SESSION_TIMEOUT_MS,
    secure: false
  }
}));
app.use((req, res, next) => {
  if (req.session && req.session.user) {
    const lastActivity = req.session.lastActivity || req.session.createdAt || Date.now();
    if (Date.now() - lastActivity > SESSION_TIMEOUT_MS) {
      req.session.destroy(() => {
        res.clearCookie('connect.sid');
        return res.redirect('/login?error=Tu%20sesion%20ha%20caducado%20por%20inactividad.');
      });
      return;
    }
    req.session.lastActivity = Date.now();
    req.session.cookie.maxAge = SESSION_TIMEOUT_MS;
  }

  res.locals.currentUser = req.session.user;
  res.locals.notice = req.query.notice;
  res.locals.error = req.query.error;
  next();
});

app.get('/', (req, res) => res.redirect('/books'));
app.use('/', auth);
app.use('/', jwtDemo);
app.use('/books', books);
app.use('/admin', admin);
app.use((req, res) => res.status(404).render('error', { title: 'No encontrado', message: 'La pagina solicitada no existe.' }));
app.use((err, req, res, next) => { console.error(err); res.status(500).render('error', { title: 'Error', message: 'No se pudo completar la operacion.' }); });

app.listen(port, () => console.log(`Libreria disponible en http://localhost:${port}`));
