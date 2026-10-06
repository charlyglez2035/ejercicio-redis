async function fetchXml(endpoint) {
  const url = new URL(endpoint);
  if (!['http:', 'https:'].includes(url.protocol)) {
    throw new Error('La URL debe usar HTTP o HTTPS.');
  }

  let response;
  try {
    response = await fetch(url, {
      headers: { Accept: 'application/xml, text/xml' },
      signal: AbortSignal.timeout(15000)
    });
  } catch (error) {
    const code = error.cause?.code || error.code;
    if (code === 'UND_ERR_CONNECT_TIMEOUT' || code === 'ETIMEDOUT' || error.name === 'TimeoutError') {
      throw new Error(`No se pudo conectar con ${url.hostname}:${url.port || 80}. Verifica que el microservicio Flask este ejecutandose y que el puerto 5001 este permitido.`);
    }
    throw new Error(`No se pudo conectar con el servicio XML: ${error.message}`);
  }
  const contentType = response.headers.get('content-type') || '';
  const body = await response.text();

  if (!response.ok) {
    throw new Error(`El servidor respondio con ${response.status}.`);
  }
  if (contentType.includes('json') || /^\s*[\[{]/.test(body)) {
    throw new Error('La aplicacion solo acepta respuestas XML.');
  }

  return body;
}

module.exports = { fetchXml };
