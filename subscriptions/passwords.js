// Password work is delegated to Supabase Auth; never persist passwords in D1.
export function validPassword(password) {
  return typeof password === "string" && [...password].length >= 6 &&
    /[a-z]/.test(password) && /[A-Z]/.test(password) && /[0-9]/.test(password) &&
    new TextEncoder().encode(password).length <= 72;
}

export function passwordAuthConfigured(env) {
  return /^https:\/\/[a-z0-9-]+\.supabase\.co$/.test(env.SUPABASE_URL || "") &&
    Boolean(env.SUPABASE_SERVICE_ROLE_KEY);
}

export function authIdentityId(userId) {
  const hex = String(userId).replace(/^user-/, "");
  if (!/^[a-f0-9]{32}$/.test(hex)) throw new Error("Invalid account identity");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

async function authRequest(env, path, method, body) {
  if (!passwordAuthConfigured(env)) throw new Error("Password service unavailable");
  const response = await fetch(`${env.SUPABASE_URL}/auth/v1${path}`, {
    method,
    headers: {
      apikey: env.SUPABASE_SERVICE_ROLE_KEY,
      Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
      "Content-Type": "application/json",
      "X-Supabase-Api-Version": "2024-01-01",
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
    signal: AbortSignal.timeout(10_000),
    redirect: "error",
  });
  if (response.status >= 500 || response.status === 429) throw new Error("Password service unavailable");
  return { response, data: await response.json() };
}

function matchesIdentity(user, id, email) {
  return user?.id === id && user?.email?.toLowerCase() === email && Boolean(user.email_confirmed_at);
}

// Only called after atomically consuming a valid email code. A stable UUID
// allows retries to recover safely after a partial provider/D1 failure.
export async function setPassword(env, userId, email, password) {
  if (!validPassword(password)) throw new Error("Invalid password");
  const id = authIdentityId(userId);
  const existing = await authRequest(env, `/admin/users/${id}`, "GET");
  let result;
  if (existing.response.status === 404) {
    result = await authRequest(env, "/admin/users", "POST", { id, email, password, email_confirm: true });
  } else {
    if (!existing.response.ok || !matchesIdentity(existing.data, id, email)) throw new Error("Password identity mismatch");
    result = await authRequest(env, `/admin/users/${id}`, "PUT", { password });
  }
  if (!result.response.ok || !matchesIdentity(result.data, id, email)) throw new Error("Password update failed");
}

export async function verifyPassword(env, userId, email, password) {
  const { response, data } = await authRequest(env, "/token?grant_type=password", "POST", { email, password });
  if (!response.ok) {
    if (response.status === 400 && (data.code || data.error_code) === "invalid_credentials") return false;
    throw new Error("Password service unavailable");
  }
  // Provider tokens are never returned to the browser or persisted.
  return Boolean(userId) && matchesIdentity(data.user, authIdentityId(userId), email);
}
