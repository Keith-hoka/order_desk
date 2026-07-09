"use server";

import { revalidatePath } from "next/cache";
import { submitReview } from "@/lib/api-server";
import type { ReviewItem, ReviewStatus } from "@/lib/types";

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
