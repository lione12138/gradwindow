import { scrypt, randomBytes, timingSafeEqual } from "node:crypto";
import { Buffer } from "node:buffer";

// OWASP's 16 MiB scrypt configuration fits the Workers memory budget.
const PREFIX = "scrypt$16384$8$5";
const OPTIONS = { N: 16384, r: 8, p: 5, maxmem: 32 * 1024 * 1024 };

export function validPassword(password) {
  return typeof password === "string" && password.length >= 15 && password.length <= 128;
}

function derive(password, salt) {
  return new Promise((resolve, reject) => {
    scrypt(password, salt, 32, OPTIONS, (error, key) => error ? reject(error) : resolve(key));
  });
}

export async function hashPassword(password) {
  if (!validPassword(password)) throw new Error("invalid password length");
  const salt = randomBytes(16).toString("hex");
  const key = await derive(password, salt);
  return `${PREFIX}$${salt}$${key.toString("hex")}`;
}

export async function verifyPassword(password, encoded) {
  if (!validPassword(password)) return false;
  const parts = String(encoded || "").split("$");
  const valid = parts.slice(0, 4).join("$") === PREFIX &&
    /^[a-f0-9]{32}$/.test(parts[4] || "") && /^[a-f0-9]{64}$/.test(parts[5] || "") && parts.length === 6;
  // Pay the same hashing cost for an unknown account or passwordless account.
  const salt = valid ? parts[4] : "00000000000000000000000000000000";
  const expected = Buffer.from(valid ? parts[5] : "00".repeat(32), "hex");
  const actual = await derive(password, salt);
  return timingSafeEqual(actual, expected) && valid;
}
