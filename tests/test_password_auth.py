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
import { hashPassword, verifyPassword } from PASSWORD_URI;
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
  ROADMAP_VOTER_HASH_KEY: 'test-ip-key', RESEND_API_KEY: 'test-key', RESEND_FROM: 'test@example.com' };
let code;
globalThis.fetch = async (_url, options) => {
  const email = JSON.parse(options.body);
  code = email.text.match(/\b\d{6}\b/)[0];
  return Response.json({ id: 'local-only' });
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
const firstHash = await hashPassword(password);
assert.notEqual(firstHash, await hashPassword(password));
assert.equal(await verifyPassword(password, firstHash), true);
assert.equal(await verifyPassword(secondPassword, firstHash), false);
assert.equal(await verifyPassword(password, null), false);
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
const stored = await DB.prepare('SELECT password_hash FROM user_passwords WHERE user_id=?1').bind(reset.data.user.id).first();
assert.ok(stored.password_hash.startsWith('scrypt$16384$8$5$'));
assert.equal(stored.password_hash.includes(secondPassword), false);
await request('/auth/logout', {}, reset.data.token);
assert.equal((await request('/me', null, reset.data.token, 'GET')).status, 401);
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
