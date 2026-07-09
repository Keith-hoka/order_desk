/**
 * Mints short-lived API tokens from the signed-in session (Phase 11, block B).
 *
 * The browser never sees an API token. A UI user holds a session cookie; the
 * Next.js server mints an HS256 JWT carrying that user's org scope and calls
 * the FastAPI backend with it. The claims match the backend's decode_token:
 * sub, org_id, scopes, iat, exp. This replaces the Phase 7 arrangement where a
 * long-lived token was exposed to the client via NEXT_PUBLIC_API_TOKEN.
 */
import "server-only";
import { SignJWT } from "jose";
import type { Role } from "./users";

/**
 * UI roles map to API scopes. The API calls a non-admin member "member"; the UI
 * calls them "reviewer" (the business role). Map explicitly rather than forcing
 * the names to match.
 */
const SCOPES_FOR_ROLE: Record<Role, string[]> = {
  admin: ["extract:write", "review:read", "review:write", "org:admin"],
  reviewer: ["extract:write", "review:read", "review:write"],
};

const TOKEN_TTL_SECONDS = 300; // short-lived: minted per request

export async function mintApiToken(user: {
  email: string;
  orgId: string;
  role: Role;
}): Promise<string> {
  const secret = process.env.JWT_SECRET;
  if (!secret) throw new Error("JWT_SECRET is not set (server-side)");
  const key = new TextEncoder().encode(secret);
  const now = Math.floor(Date.now() / 1000);

  return new SignJWT({
    org_id: user.orgId,
    scopes: SCOPES_FOR_ROLE[user.role],
  })
    .setProtectedHeader({ alg: "HS256" })
    .setSubject(user.email)
    .setIssuedAt(now)
    .setExpirationTime(now + TOKEN_TTL_SECONDS)
    .sign(key);
}
