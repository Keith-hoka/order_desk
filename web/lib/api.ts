import type { ReviewItem, ReviewStatus } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
const TOKEN = process.env.NEXT_PUBLIC_API_TOKEN ?? "";

function authHeaders(): HeadersInit {
  const h: HeadersInit = { "Content-Type": "application/json" };
  if (TOKEN) h["Authorization"] = `Bearer ${TOKEN}`;
  return h;
}

export async function fetchExceptions(): Promise<ReviewItem[]> {
  const res = await fetch(`${API_BASE}/exceptions`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to load queue (${res.status})`);
  return res.json();
}

export async function submitReview(
  id: string,
  action: ReviewStatus,
  edits: Record<string, string> = {}
): Promise<ReviewItem> {
  const res = await fetch(`${API_BASE}/exceptions/${id}/review`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ action, edits }),
  });
  if (!res.ok) throw new Error(`Failed to submit review (${res.status})`);
  return res.json();
}
