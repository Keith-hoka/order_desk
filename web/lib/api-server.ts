/**
 * Server-side review API client (Phase 11, block B).
 *
 * Every call runs on the Next.js server: it reads the session, mints an API
 * token carrying the user's org scope, and calls FastAPI. The backend then
 * filters the review queue by that org (Phase 11 block A), so a user only ever
 * sees their own org's exceptions.
 */
import "server-only";
import { auth } from "@/auth";
import { mintApiToken } from "./api-token";
import type { ReviewItem, ReviewStatus } from "./types";

const API_BASE = process.env.API_BASE ?? "http://localhost:8000";

async function authHeaders(): Promise<HeadersInit> {
  const session = await auth();
  const user = session?.user as
    | { email?: string | null; orgId?: string; role?: "admin" | "reviewer" }
    | undefined;
  if (!user?.email || !user.orgId || !user.role) {
    throw new Error("not authenticated");
  }
  const token = await mintApiToken({
    email: user.email,
    orgId: user.orgId,
    role: user.role,
  });
  return { "Content-Type": "application/json", Authorization: `Bearer ${token}` };
}

export async function fetchExceptions(): Promise<ReviewItem[]> {
  const res = await fetch(`${API_BASE}/exceptions`, {
    headers: await authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to load queue (${res.status})`);
  return res.json();
}

export async function extractInbox(address: string): Promise<ReviewItem[]> {
  const res = await fetch(`${API_BASE}/exceptions/extract-inbox`, {
    method: "POST",
    headers: await authHeaders(),
    body: JSON.stringify({ address }),
  });
  if (!res.ok) {
    const detail = await res.json().then((d) => d.detail ?? "").catch(() => "");
    throw new Error(`Extraction failed (${res.status})${detail ? `: ${detail}` : ""}`);
  }
  return res.json();
}

export async function extractEmail(subject: string, body: string): Promise<ReviewItem> {
  const res = await fetch(`${API_BASE}/exceptions/extract`, {
    method: "POST",
    headers: await authHeaders(),
    body: JSON.stringify({ subject, body }),
  });
  if (!res.ok) {
    const detail = await res.json().then((d) => d.detail ?? "").catch(() => "");
    throw new Error(`Extraction failed (${res.status})${detail ? `: ${detail}` : ""}`);
  }
  return res.json();
}

export async function submitReview(
  id: string,
  action: ReviewStatus,
  edits: Record<string, string> = {}
): Promise<ReviewItem> {
  const res = await fetch(`${API_BASE}/exceptions/${id}/review`, {
    method: "POST",
    headers: await authHeaders(),
    body: JSON.stringify({ action, edits }),
  });
  if (!res.ok) throw new Error(`Failed to submit review (${res.status})`);
  return res.json();
}
