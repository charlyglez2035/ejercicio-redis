const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  host: process.env.DB_HOST || 'localhost',
  port: Number(process.env.DB_PORT || 5432),
  database: process.env.DB_NAME || 'library',
  user: process.env.DB_USER || 'library_user',
  password: process.env.DB_PASSWORD
});

module.exports = {
  query(text, params) { return pool.query(text, params); },
  get pool() { return pool; }
};
