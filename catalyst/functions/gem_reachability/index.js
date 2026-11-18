'use strict';

// Spike: prove a Catalyst (India DC) function can reach GeM directly,
// with no proxy. Returns the HTTP status GeM gives us plus our egress IP
// and its country. If GeM returns 200 from here, the whole "run from
// Indian infra instead of proxying" approach is validated.

const https = require('https');

function getJson(url, timeoutMs) {
  return new Promise((resolve) => {
    const start = Date.now();
    const req = https.request(
      url,
      { method: 'GET', headers: { 'User-Agent': 'Mozilla/5.0' } },
      (resp) => {
        let body = '';
        resp.on('data', (c) => { body += c; });
        resp.on('end', () =>
          resolve({ ok: true, status: resp.statusCode, ms: Date.now() - start, body })
        );
      }
    );
    req.setTimeout(timeoutMs, () => {
      req.destroy();
      resolve({ ok: false, error: 'timeout', ms: Date.now() - start });
    });
    req.on('error', (e) => resolve({ ok: false, error: e.message, ms: Date.now() - start }));
    req.end();
  });
}

module.exports = async (req, res) => {
  const target = 'https://bidplus.gem.gov.in/all-bids';

  // 1) The real test: can we reach GeM from this function's egress?
  const gem = await getJson(target, 20000);

  // 2) Diagnostics: what egress IP + country does Catalyst give us? (best-effort)
  let egress = null;
  try {
    const ip = await getJson('https://ipapi.co/json/', 8000);
    if (ip.ok && ip.body) {
      const j = JSON.parse(ip.body);
      egress = { ip: j.ip, country: j.country_name, region: j.region, org: j.org };
    }
  } catch (_) { /* diagnostics only */ }

  const verdict = gem.ok && gem.status && gem.status < 500
    ? 'REACHABLE — GeM answered, no proxy needed'
    : 'NOT REACHABLE — GeM did not answer (check egress country below)';

  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({
    verdict,
    gem: { target, status: gem.status || null, ms: gem.ms, error: gem.error || null },
    egress,
  }, null, 2));
};
