(() => {
  const logNode = document.querySelector('#request-log');
  const countNode = document.querySelector('#request-count');
  const stateNode = document.querySelector('#auth-state');
  const statusNode = document.querySelector('#workbench-status');
  const maxEntries = 100;
  const entries = [];
  const sensitiveKeyPattern = /(authorization|cookie|password|token|secret|api[-_]?key|credential)/i;
  const jwtPattern = /\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b/g;

  function sanitize(value, key = '') {
    if (sensitiveKeyPattern.test(key)) return '[REDACTED]';
    if (Array.isArray(value)) return value.map(item => sanitize(item));
    if (value && typeof value === 'object') {
      return Object.fromEntries(Object.entries(value).map(([name, item]) => [name, sanitize(item, name)]));
    }
    return typeof value === 'string' ? value.replace(jwtPattern, '[REDACTED]') : value;
  }

  function sanitizeUrl(value) {
    try {
      const url = new URL(value);
      url.username = url.username ? '[REDACTED]' : '';
      url.password = url.password ? '[REDACTED]' : '';
      for (const key of url.searchParams.keys()) {
        if (sensitiveKeyPattern.test(key)) url.searchParams.set(key, '[REDACTED]');
      }
      return url.href;
    } catch {
      return value.replace(jwtPattern, '[REDACTED]');
    }
  }

  function setAuthenticated(authenticated, user) {
    stateNode.textContent = authenticated
      ? `Autenticado: ${user?.username || user?.email || 'usuario'}`
      : 'Sin autenticar';
    stateNode.classList.toggle('is-authenticated', authenticated);
    document.querySelector('#logout-button').disabled = !authenticated;
  }

  function renderEntry(entry) {
    const item = document.createElement('li');
    const details = document.createElement('details');
    const summary = document.createElement('summary');
    const time = document.createElement('time');
    const status = document.createElement('span');
    const label = document.createElement('span');
    const requestId = document.createElement('code');
    const pre = document.createElement('pre');
    const date = new Date(entry.timestamp);
    time.dateTime = date.toISOString();
    time.textContent = date.toLocaleString();
    status.className = 'jwt-status-code';
    status.textContent = entry.status === null ? 'ERR' : String(entry.status);
    label.textContent = `${entry.service}  ${entry.method}  ${entry.url}`;
    requestId.textContent = entry.requestId;
    pre.textContent = JSON.stringify(entry, null, 2);
    summary.append(time, status, label, requestId);
    details.append(summary, pre);
    item.className = `jwt-log-entry${entry.status === null || entry.status >= 400 ? ' is-error' : ''}`;
    item.append(details);
    return item;
  }

  function addEntry(entry) {
    entries.unshift(sanitize(entry));
    if (entries.length > maxEntries) entries.length = maxEntries;
    logNode.replaceChildren(...entries.map(renderEntry));
    countNode.textContent = `${entries.length} peticiones`;
  }

  async function send(service, method, path, payload, options = {}) {
    const id = crypto.randomUUID();
    const url = new URL(path, location.origin).href;
    const headers = { 'X-Request-ID': id, Accept: 'application/json' };
    if (payload !== undefined) headers['Content-Type'] = 'application/json';
    if (options.withoutToken) headers['X-Demo-Without-Token'] = 'true';
    if (options.manipulateToken) headers['X-Demo-Manipulate-Token'] = 'true';
    if (options.reuseRevokedToken) headers['X-Demo-Reuse-Revoked-Token'] = 'true';
    const loggedHeaders = { ...headers };
    if (!options.withoutToken && (
      stateNode.classList.contains('is-authenticated') || options.manipulateToken || options.reuseRevokedToken
    )) {
      loggedHeaders.Authorization = '[REDACTED]';
    }
    loggedHeaders.Cookie = '[REDACTED]';
    const record = {
      timestamp: new Date().toISOString(), requestId: id, service, method, url: sanitizeUrl(url),
      headers: loggedHeaders, payload: payload === undefined ? null : sanitize(payload),
      status: null, durationMs: null, response: null
    };
    const started = performance.now();
    try {
      const response = await fetch(url, {
        method,
        headers,
        body: payload === undefined ? undefined : JSON.stringify(payload)
      });
      record.status = response.status;
      record.durationMs = Math.round((performance.now() - started) * 100) / 100;
      record.response = sanitize(await response.json());
      if (service === 'login' && response.status === 401) setAuthenticated(false);
      addEntry(record);
      return { response, body: record.response };
    } catch (error) {
      record.durationMs = Math.round((performance.now() - started) * 100) / 100;
      record.response = { error: error.message || 'Error de red' };
      addEntry(record);
      return { response: null, body: record.response };
    }
  }

  document.querySelector('#login-form').addEventListener('submit', async event => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await send('login', 'POST', '/api/jwt/login', {
      identity: form.get('identity'), password: form.get('password')
    });
    event.currentTarget.elements.password.value = '';
    statusNode.textContent = result.body?.error || result.body?.message || 'Error de login';
    if (result.response?.ok) setAuthenticated(true, result.body.user);
  });

  document.querySelector('#session-button').addEventListener('click', async () => {
    const result = await send('login', 'GET', '/api/jwt/session', undefined, {
      reuseRevokedToken: document.querySelector('#reuse-revoked-token').checked
    });
    statusNode.textContent = result.body?.authenticated ? 'Sesion JWT valida.' : 'No hay una sesion valida.';
    setAuthenticated(Boolean(result.body?.authenticated), result.body?.user);
  });

  document.querySelector('#logout-button').addEventListener('click', async () => {
    const result = await send('login', 'POST', '/api/jwt/logout');
    statusNode.textContent = result.body?.error || result.body?.message || 'Sesion cerrada.';
    setAuthenticated(false);
  });

  document.querySelector('#public-list-button').addEventListener('click', async () => {
    const result = await send('book', 'GET', '/api/jwt/books');
    statusNode.textContent = result.body?.error || 'Consulta publica completada.';
  });

  document.querySelector('#send-button').addEventListener('click', async () => {
    const method = document.querySelector('#method').value;
    const isbn = document.querySelector('#isbn').value.trim();
    const payloadText = document.querySelector('#payload').value.trim();
    const withoutToken = document.querySelector('#without-token').checked;
    const manipulateToken = document.querySelector('#manipulate-token').checked;
    const reuseRevokedToken = document.querySelector('#reuse-revoked-token').checked;
    const isCollection = method === 'POST' || (method === 'GET' && !isbn);
    if (!isCollection && !isbn) {
      statusNode.textContent = 'Indica un ISBN para este metodo.';
      return;
    }
    let payload;
    if (method !== 'GET' && method !== 'DELETE') {
      try { payload = JSON.parse(payloadText); }
      catch { statusNode.textContent = 'El payload no contiene JSON valido.'; return; }
    }
    const path = isCollection ? '/api/jwt/books' : `/api/jwt/books/${encodeURIComponent(isbn)}`;
    const result = await send('book', method, path, payload, {
      withoutToken, manipulateToken, reuseRevokedToken
    });
    statusNode.textContent = result.body?.error || `Respuesta HTTP ${result.response?.status || 'sin respuesta'}.`;
  });

  document.querySelector('#method').addEventListener('change', event => {
    const method = event.target.value;
    document.querySelector('#isbn').disabled = method === 'POST';
    document.querySelector('#payload').disabled = method === 'GET' || method === 'DELETE';
  });

  document.querySelector('#clear-log').addEventListener('click', () => {
    entries.length = 0;
    logNode.replaceChildren();
    countNode.textContent = '0 peticiones';
  });

  document.querySelector('#copy-log').addEventListener('click', async () => {
    await navigator.clipboard.writeText(JSON.stringify(entries, null, 2));
    statusNode.textContent = 'Registro copiado.';
  });

  document.querySelector('#export-log').addEventListener('click', () => {
    const file = new Blob([JSON.stringify(entries, null, 2)], { type: 'application/json' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(file);
    link.download = 'consola-peticiones-jwt.json';
    link.click();
    URL.revokeObjectURL(link.href);
  });

  send('login', 'GET', '/api/jwt/session').then(result => {
    setAuthenticated(Boolean(result.body?.authenticated), result.body?.user);
  });
})();