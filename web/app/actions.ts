"use server";

import { revalidatePath } from "next/cache";
import { deleteException, extractEmail, extractInbox, submitReview } from "@/lib/api-server";
import type { ReviewItem, ReviewStatus } from "@/lib/types";

/**
 * Run a pasted email through the live pipeline (OpenAI routing + the adapter
 * on Modal) and append the result to this org's review queue. Returns either
 * the new item or the failure message -- a thrown error would take down the
 * page with an overlay, and a slow cold start failing is an expected outcome,
 * not a crash.
 */
/**
 * Pull the configured mailbox's recent unseen emails through the live
 * pipeline into this org's review queue. The address is a confirmation of
 * which mailbox -- credentials live server-side in the API's environment.
 */
export async function extractInboxAction(
  address: string,
  host: string,
  password: string
): Promise<{ items: ReviewItem[] } | { error: string }> {
  try {
    const items = await extractInbox(address, host, password);
    revalidatePath("/");
    return { items };
  } catch (e) {
    return { error: e instanceof Error ? e.message : String(e) };
  }
}

/** Remove a live-extracted item; the backend refuses on the committed seed. */
export async function deleteExceptionAction(
  id: string
): Promise<{ ok: true } | { error: string }> {
  try {
    await deleteException(id);
    revalidatePath("/");
    return { ok: true };
  } catch (e) {
    return { error: e instanceof Error ? e.message : String(e) };
  }
}

export async function extractEmailAction(
  subject: string,
  body: string
): Promise<{ item: ReviewItem } | { error: string }> {
  try {
    const item = await extractEmail(subject, body);
    revalidatePath("/");
    return { item };
  } catch (e) {
    return { error: e instanceof Error ? e.message : String(e) };
  }
}

/**
 * Submit a review decision and return what the backend did with it.
 *
 * The result carries the fulfilment outcome, so the UI can report whether the
 * order reached the ERP, was held on an unresolved SKU, or went nowhere because
 * no sink is configured -- rather than asserting an outcome it never observed.
 *
 * Runs on the server: the session's org scope is minted into the API token, so
 * a user can only act on their own org's items (the backend 404s on anything
 * else).
 */
export async function submitReviewAction(
  id: string,
  action: ReviewStatus,
  edits: Record<string, string> = {}
): Promise<ReviewItem> {
  const item = await submitReview(id, action, edits);
  revalidatePath("/");
  return item;
}
