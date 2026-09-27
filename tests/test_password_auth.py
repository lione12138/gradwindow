"""Exercise the actual Worker handlers against SQLite, without sending email."""

import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path


def test_password_account_lifecycle(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    database = tmp_path / "accounts.sqlite"
    with sqlite3.connect(database) as connection:
        connection.executescript((root / "subscriptions/schema.sql").read_text())
    bridge = tmp_path / "sqlite_bridge.py"
    bridge.write_text(
        """import json, sqlite3, sys
connection = sqlite3.connect(sys.argv[1])
connection.row_factory = sqlite3.Row
connection.execute('PRAGMA foreign_keys = ON')
results = []
with connection:
    for statement in json.load(sys.stdin):
        cursor = connection.execute(statement['sql'], statement['values'])
        results.append([dict(row) for row in cursor.fetchall()])
print(json.dumps(results))
""",
        encoding="utf-8",
    )
    script = r"""
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import worker from WORKER_URI;
import { hmacHex, bytesToBase64Url } from CORE_URI;
import { authIdentityId, validPassword } from PASSWORD_URI;
const execute = (statements) => {
  const result = spawnSync(PYTHON, [BRIDGE, DATABASE], { input: JSON.stringify(statements), encoding: 'utf8' });
  if (result.status !== 0) throw new Error(result.stderr);
  return JSON.parse(result.stdout);
};
const DB = {
  prepare(sql) { return { sql, values: [], bind(...values) { this.values = values; return this; },
    async first() { return execute([this])[0][0] || null; },
    async all() { return { results: execute([this])[0] }; },
    async run() { return { results: execute([this])[0] }; },
  }; },
  async batch(statements) { return execute(statements).map(results => ({ results })); },
};
const env = { DB, ALLOWED_ORIGINS: 'https://gradwindow.com', AUTH_SECRET_KEY: 'test-auth-secret',
  EMAIL_INDEX_KEY: 'test-index-key', EMAIL_ENCRYPTION_KEY: bytesToBase64Url(new Uint8Array(32).fill(7)),
  ROADMAP_VOTER_HASH_KEY: 'test-ip-key', RESEND_API_KEY: 'test-key', RESEND_FROM: 'test@example.com',
  SUPABASE_URL: 'https://test-project.supabase.co', SUPABASE_SERVICE_ROLE_KEY: 'server-only-secret' };
let code;
const identities = new Map();
let providerFailure = false;
let failAfterWrite = false;
let wrongIdentity = false;
let afterProviderLogin;
globalThis.fetch = async (url, options) => {
  const body = options.body ? JSON.parse(options.body) : {};
  if (url.startsWith('https://api.resend.com/')) {
    code = body.text.match(/\b\d{6}\b/)[0];
    return Response.json({ id: 'local-only' });
  }
  assert.ok(url.startsWith(env.SUPABASE_URL + '/auth/v1/'));
  assert.equal(options.headers.apikey, env.SUPABASE_SERVICE_ROLE_KEY);
  assert.equal(options.redirect, 'error');
  if (providerFailure) return Response.json({message:'unavailable'}, {status:503});
  if (url.endsWith('/token?grant_type=password')) {
    const user = [...identities.values()].find(item => item.email === body.email && item.password === body.password);
    if (!user) return Response.json({code:'invalid_credentials'}, {status:400});
    const result = {user: {...user, ...(wrongIdentity ? {id:crypto.randomUUID()} : {})}, access_token:'never-return-this', refresh_token:'never-persist-this'};
    if (afterProviderLogin) { const hook = afterProviderLogin; afterProviderLogin = null; await hook(); }
    return Response.json(result);
  }
  if (url.endsWith('/admin/users') && options.method === 'POST') {
    assert.equal(body.email_confirm, true);
    const user = {...body, email_confirmed_at:new Date().toISOString()};
    identities.set(user.id, user);
    if (failAfterWrite) return Response.json({message:'connection interrupted after commit'}, {status:503});
    return Response.json(user);
  }
  const id = url.split('/').at(-1);
  const user = identities.get(id);
  if (!user) return Response.json({code:'user_not_found'}, {status:404});
  if (options.method === 'PUT') Object.assign(user, body);
  return Response.json(user);
};
const request = async (path, body, token = '', method = 'POST', origin = 'https://gradwindow.com') => {
  const result = await worker.fetch(new Request('https://worker.test' + path, {
    method, headers: { Origin: origin, 'Content-Type': 'application/json',
      'CF-Connecting-IP': '192.0.2.1', ...(token ? { Authorization: 'Bearer ' + token } : {}) },
    ...(method !== 'GET' ? { body: JSON.stringify(body) } : {}),
  }), env);
  return { status: result.status, data: await result.json() };
};
const email = 'user@example.com';
const password = 'a long unique passphrase 123';
const secondPassword = 'another long passphrase 456';
assert.equal(validPassword('a'.repeat(72)), true);
assert.equal(validPassword('a'.repeat(73)), false);
assert.equal(validPassword('中'.repeat(24)), true);
assert.equal(validPassword('中'.repeat(25)), false);
assert.equal(validPassword('😀'.repeat(8)), false);
assert.equal((await request('/auth/login', {email, password}, '', 'POST', 'https://evil.test')).status, 403);
assert.equal((await request('/auth/login', {email, password})).status, 401);
assert.equal((await request('/auth/verify', {email, code:'000000', password})).status, 400);
assert.equal((await request('/auth/request', {email, language:'en'})).status, 200);
assert.equal((await request('/auth/verify', {email, code, password:'short'})).status, 400);
const verificationRace = await Promise.all([
  request('/auth/verify', {email, code, password}),
  request('/auth/verify', {email, code, password}),
]);
assert.deepEqual(verificationRace.map(result => result.status).sort(), [200, 400]);
const registered = verificationRace.find(result => result.status === 200);
assert.equal(registered.status, 200);
assert.equal('password_hash' in registered.data.user, false);
assert.equal(JSON.stringify(registered).includes('server-only-secret'), false);
assert.equal(JSON.stringify(registered).includes('never-return-this'), false);
assert.equal((await request('/auth/verify', {email, code, password})).status, 400);
const token = registered.data.token;
assert.equal((await request('/me/favorites', {favorites:['university:mit','window:mit-cs']}, token, 'PUT')).status, 200);
const login = await request('/auth/login', {email, password});
assert.equal(login.status, 200);
assert.deepEqual(login.data.favorites, ['university:mit','window:mit-cs']);
assert.equal(login.data.user.id, registered.data.user.id);
assert.equal((await request('/auth/login', {email, password:secondPassword})).status, 401);
assert.equal((await request('/me', null, '', 'GET')).status, 401);
// Existing email-only users upgrade without creating a second account.
assert.equal((await request('/auth/request', {email:'legacy@example.com'})).status, 200);
const legacy = await request('/auth/verify', {email:'legacy@example.com', code});
assert.equal(legacy.status, 200);
assert.deepEqual((await request('/me', null, legacy.data.token, 'GET')).data.favorites, []);
assert.equal((await request('/auth/login', {email:'legacy@example.com', password})).status, 401);
// Advance only challenge cooldown in the test fixture.
await DB.prepare("UPDATE auth_login_codes SET created_at='2020-01-01T00:00:00Z'").run();
await request('/auth/request', {email:'legacy@example.com'});
const upgraded = await request('/auth/verify', {email:'legacy@example.com', code, password});
assert.equal(upgraded.data.user.id, legacy.data.user.id);
assert.equal((await request('/me', null, legacy.data.token, 'GET')).status, 401);
// A reset invalidates every old session, preserves the account and favourites.
await request('/auth/request', {email});
const reset = await request('/auth/verify', {email, code, password:secondPassword});
assert.equal(reset.status, 200);
assert.equal(reset.data.user.id, registered.data.user.id);
assert.deepEqual(reset.data.favorites, login.data.favorites);
assert.equal((await request('/me', null, token, 'GET')).status, 401);
assert.equal((await request('/me', null, login.data.token, 'GET')).status, 401);
assert.equal((await request('/auth/login', {email, password})).status, 401);
assert.equal((await request('/auth/login', {email, password:secondPassword})).status, 200);
const stored = await DB.prepare('SELECT * FROM user_password_auth WHERE user_id=?1').bind(reset.data.user.id).first();
assert.equal(stored.ready, 1);
assert.equal(JSON.stringify(stored).includes(secondPassword), false);
assert.equal(identities.get(authIdentityId(reset.data.user.id)).password, secondPassword);
await request('/auth/logout', {}, reset.data.token);
assert.equal((await request('/me', null, reset.data.token, 'GET')).status, 401);
// Provider outage must not authenticate; a mismatched provider identity is rejected.
providerFailure = true;
assert.equal((await request('/auth/login', {email:'legacy@example.com', password})).status, 503);
providerFailure = false;
wrongIdentity = true;
assert.equal((await request('/auth/login', {email:'legacy@example.com', password})).status, 401);
wrongIdentity = false;
// A reset racing with an already-verified provider response cannot mint a stale session.
afterProviderLogin = async () => {
  await DB.prepare('UPDATE user_password_auth SET credential_version=?2 WHERE user_id=?1')
    .bind(legacy.data.user.id, crypto.randomUUID()).run();
};
assert.equal((await request('/auth/login', {email:'legacy@example.com', password})).status, 401);
// A failed reset keeps data and email login working, and a later verified reset repairs it.
await request('/auth/request', {email:'repair@example.com'});
failAfterWrite = true;
assert.equal((await request('/auth/verify', {email:'repair@example.com', code, password})).status, 503);
failAfterWrite = false;
assert.equal((await request('/auth/login', {email:'repair@example.com', password})).status, 401);
await DB.prepare("UPDATE auth_login_codes SET created_at='2020-01-01T00:00:00Z'").run();
await request('/auth/request', {email:'repair@example.com'});
const emailOnlyRepair = await request('/auth/verify', {email:'repair@example.com', code});
assert.equal(emailOnlyRepair.status, 200);
await DB.prepare("UPDATE auth_login_codes SET created_at='2020-01-01T00:00:00Z'").run();
await request('/auth/request', {email:'repair@example.com'});
const repaired = await request('/auth/verify', {email:'repair@example.com', code, password});
assert.equal(repaired.status, 200);
assert.equal(repaired.data.user.id, emailOnlyRepair.data.user.id);
assert.equal((await request('/auth/login', {email:'repair@example.com', password})).status, 200);
// A second reset cannot overwrite a provider write already in progress.
await DB.prepare('UPDATE user_password_auth SET reset_started_at=?2 WHERE user_id=?1')
  .bind(repaired.data.user.id, new Date().toISOString()).run();
await DB.prepare("UPDATE auth_login_codes SET created_at='2020-01-01T00:00:00Z'").run();
await request('/auth/request', {email:'repair@example.com'});
assert.equal((await request('/auth/verify', {email:'repair@example.com', code, password:secondPassword})).status, 409);
assert.equal(identities.get(authIdentityId(repaired.data.user.id)).password, password);
// Rate limits count failed attempts, including unknown accounts.
for (let i=0; i<10; i++) await request('/auth/login', {email:'missing@example.com',password});
assert.equal((await request('/auth/login', {email:'missing@example.com',password})).status, 429);
const hash = await hmacHex(env.EMAIL_INDEX_KEY, 'expired@example.com');
await DB.prepare(`INSERT INTO auth_login_codes(id,email_hash,code_hash,expires_at,created_at)
  VALUES('expired',?1,?2,'2020-01-01','2019-01-01')`).bind(hash, await hmacHex(env.AUTH_SECRET_KEY, hash+':123456')).run();
assert.equal((await request('/auth/verify', {email:'expired@example.com',code:'123456',password})).status, 400);
console.log('account lifecycle passed');
"""
    replacements = {
        "WORKER_URI": (root / "subscriptions/worker.js").as_uri(),
        "CORE_URI": (root / "subscriptions/core.js").as_uri(),
        "PASSWORD_URI": (root / "subscriptions/passwords.js").as_uri(),
        "PYTHON": sys.executable,
        "BRIDGE": str(bridge),
        "DATABASE": str(database),
    }
    for key, value in replacements.items():
        script = script.replace(key, json.dumps(value))
    result = subprocess.run(
        [shutil.which("node") or "node", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
